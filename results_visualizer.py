"""Presentation adapter for the existing VAWT simulation engine."""
import inspect
import json
from pathlib import Path

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from qblade_reference import configurations, reference_point, load_reference, ReferenceDomainError
from visualizer_bridge import SPECS, render_component
from cost_reference import load_cost_reference


def build_payload(context, compute):
    """Recompute comparable geometries with identical environmental/control inputs."""
    args = {name: context[name] for name in inspect.signature(compute).parameters
            if name in context}
    for name, table, column in (
        ('tab_power_rpm', 'tab_power', 'rpm'),
        ('tab_power_kw', 'tab_power', 'P_kW'),
        ('tab_volt_rpm', 'tab_volt', 'rpm'),
        ('tab_volt_vll', 'tab_volt', 'V_LL'),
    ):
        args[name] = tuple(context[table][column].tolist())
    n, c = int(args['N']), float(args['c'])
    candidates = [(n, c), (3, .8), (3, 1.), (3, 1.2), (3, 1.4),
                  (4, .9), (4, 1.2), (5, .72), (5, 1.2)]
    candidates = list(dict.fromkeys(candidates))
    if context.get("qblade_mode"):
        candidates = list(dict.fromkeys([(n, c)] + configurations()))
    scenarios = []
    for i, (count, chord) in enumerate(candidates):
        options = dict(args, N=count, c=chord)
        try:
            result = context['base_results'] if i == 0 else compute(**options)
        except ReferenceDomainError:
            if i == 0:
                raise
            continue
        energy = context['aep_from_weibull'](
            result['v_grid'], result['P_out_W'], context['k_w'], context['c_w'])
        # aep_from_weibull returns (annual kWh, mean power in watts).
        if isinstance(energy, tuple):
            energy = energy[0]
        def values(key, scale=1):
            return (np.asarray(result[key], dtype=float) / scale).tolist()
        azimuthal = []
        for wind in result['v_grid']:
            point = reference_point(count, chord, float(wind), context.get('rpm_limit')) if context.get('qblade_mode') else None
            azimuthal.append(point['az']['s'] if point and point['az'] else None)
        scenarios.append({
            'id': f'{count}x{chord:g}',
            'name': ('Actual · ' if i == 0 else '') + f'{count} palas × {chord:g} m',
            'n': count, 'c': chord, 'aep': float(energy), 'az': azimuthal,
            'v': values('v_grid'), 'rpm': values('rpm_rotor'),
            'tsr': values('lambda_eff'), 'aero': values('P_aero_W', 1000),
            'electric': values('P_out_W', 1000), 'torque': values('T_rotor_Nm'),
            'lossMechanical': ((np.asarray(result['P_aero_W'])-np.asarray(result['P_mec_gen_W']))/1000).clip(0).tolist(),
            'lossGenerator': ((np.asarray(result['P_mec_gen_W'])-np.asarray(result['P_el_gen_W']))/1000).clip(0).tolist(),
            'lossElectric': ((np.asarray(result['P_el_gen_W'])-np.asarray(result['P_el_ac']))/1000).clip(0).tolist(),
            'lossClip': ((np.asarray(result['P_el_ac'])-np.asarray(result['P_out_W']))/1000).clip(0).tolist(),
            **{target:values(source,scale) for target,source,scale in (
                ('rpmGen','rpm_gen',1),('tGen','T_gen_Nm',1),('current','I_A',1),('voltage','V_LL_curve',1),
                ('cp','Cp_aero',1),('cpElectric','Cp_el',1),('centrifugal','F_centripetal_series',1000),
                ('accel','g_per_blade_series',1),('moment','M_root_series_Nm',1000),
                ('momentStrut','M_strut_series_Nm',1000),('sigmaRoot','sigma_root_MPa',1),
                ('sigmaStrut','sigma_strut_MPa',1),('marginRoot','margin_root',1),('marginStrut','margin_strut',1),
                ('frequency','f_e_Hz',1),('frequency1P','f_1P',1),('dcDuty','dc_util_series',.01),('re','Re_mid',1),
            )},
        })
    polar = context['build_lift_drag_polar'](context['t_rel'], context['is_symmetric'])
    if context.get('qblade_mode'):
        import pandas as pd
        pol = load_reference()['polares']['NACA0015']
        re = max(float(np.mean(context['base_results']['Re_mid'])), 1)
        index = int(np.argmin(np.abs(np.log(np.asarray(pol['Re'])/re))))
        polar = pd.DataFrame({'alpha_deg':pol['a'], 'Cl':pol['cl'][index]})
        polar = polar[polar.alpha_deg.between(-30,30)]
    ymin, ymax = float(polar.Cl.min()), float(polar.Cl.max())
    span = max(ymax-ymin, .1)
    v = context['base_results']['v_grid']
    k, scale = float(context['k_w']), float(context['c_w'])
    coverage = float(np.exp(-(max(float(v[0]), 0)/scale)**k)
                     - np.exp(-(max(float(v[-1]), 0)/scale)**k))
    limit = context.get('rpm_limit')
    method = (f'Modelo Cp–TSR paramétrico del simulador. Control: {context["control_mode"]}. '
              f'Weibull k={k:g}, c={scale:g} m/s; integración de {v[0]:g} a {v[-1]:g} m/s, '
              f'cobertura probabilística {coverage:.1%}. Energía eléctrica sin ajuste adicional por disponibilidad.')
    if context.get('qblade_mode'):
        method = ('Datos declarados QBlade CE 2.0.9.7 LLFVW en visualizador_resultados_V80.html. '
                  'Puntos e interpolación según el HTML; no se ejecuta QBlade. '
                  'Geometría V80 sin brazos ni torre; generador y pérdidas del simulador. '
                  f'Weibull k={k:g}, c={scale:g} m/s; integración limitada a 4–10 m/s, cobertura {coverage:.1%}. '
                  'La animación usa series azimutales del HTML cuando coinciden las rpm; si no existen se indica su ausencia.')
    parameters = {name: (int(context[name]) if name in ('poles_total','struts_per_blade') else float(context[name]))
                  for name,*_ in SPECS if name != 'rpm_limit'}
    parameters['rpm_limit'] = float(limit) if limit is not None else None
    for name in ('v_rated','v_cut_in','v_cut_out','mu'):
        parameters[name] = float(context[name])
    for name in ('tab_power_rpm','tab_power_kw','tab_volt_rpm','tab_volt_vll'):
        parameters[name] = list(args[name])
    selected_wind = st.session_state.get('visualizer_selected_wind',6)
    return {
        'config': f'{n}x{c:g}', 'params': parameters, 'parameterSpecs': SPECS,
        'reference': load_reference(), 'selectedWind': selected_wind, 'ui':st.session_state.get('visualizer_ui',{}),
        'generator': {'label':context['GEN']['label'],'I_nom':float(context['GEN']['I_nom'])},
        'source': 'qblade' if context.get('qblade_mode') else 'parametric',
        'scenarios' : scenarios, 'radius': float(context['D'])/2,
        'height': float(context['H']), 'profile': context['airfoil_name'],
        'thickness': float(context['t_rel'])/100, 'pitch': float(context['pitch_deg']),
        'stall': float(polar.loc[polar.Cl.idxmax(), 'alpha_deg']) if context.get('qblade_mode') else (12 if context['is_symmetric'] else 10),
        'limit': float(limit) if limit is not None else None, 'coverage': coverage,
        'polar': {'alpha': polar.alpha_deg.tolist(), 'cl': polar.Cl.tolist(),
                  'ymin': ymin-span*.1, 'ymax': ymax+span*.1, 'xmin':float(polar.alpha_deg.min()), 'xmax':float(polar.alpha_deg.max())},
        'method': method,
    }


def build_html(payload):
    # Escape HTML delimiters so profile labels cannot terminate the script.
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    data = data.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    data = data.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = Path(__file__).with_name('assets').joinpath('results_visualizer.html').read_text()
    assets = Path(__file__).with_name('assets')
    template = template.replace('__MODEL_JS__', assets.joinpath('qblade_model.js').read_text())
    template = template.replace('__DASHBOARD_JS__', assets.joinpath('interactive_dashboard.js').read_text())
    template = template.replace('__ROTOR_JS__', assets.joinpath('rotor_visualization.js').read_text())
    template = template.replace('__IFC_VIEWER_JS__', assets.joinpath('ifc_viewer.js').read_text())
    template = template.replace('__THREE_JS__', assets.joinpath('vendor/three.r158.min.js').read_text())
    model = Path(__file__).with_name('data').joinpath('v80_v5_mesh.json').read_text()
    model = model.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = template.replace('__IFC_DATA__', model)
    template = template.replace('__COST_JS__', assets.joinpath('cost_dashboard.js').read_text() + '\n' + assets.joinpath('cost_preview.js').read_text())
    costs = json.dumps(load_cost_reference(), ensure_ascii=False, allow_nan=False)
    costs = costs.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = template.replace('__COST_DATA__', costs)
    return template.replace('__PAYLOAD__', data)


def render_visualizer(context, compute):
    # One continuous workspace; controls and HTML export are inside the dashboard.
    payload = build_payload(context, compute)
    render_component(build_html(payload))
