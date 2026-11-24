"""Bounded interpolation of the numerical reference supplied in the V80 HTML.

This module replays results declared as QBlade in the source; it is not an LLFVW solver.
Power interpolation follows the source HTML's exact/azimuthal/parabolic/PCHIP policy.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np


class ReferenceDomainError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_reference():
    return json.loads(Path(__file__).with_name('data').joinpath('qblade_v80_reference.json').read_text())


def configurations():
    return sorted({(int(x['nb']), float(x['c'])) for x in load_reference()['casos'] if x['g']=='palas'})


def config_id(n,c):
    return f'{int(n)}x{float(c):g}'


def pchip_value(xs,ys,x):
    xs=np.asarray(xs,dtype=float);ys=np.asarray(ys,dtype=float)
    if x<xs[0]-1e-8 or x>xs[-1]+1e-8:
        raise ReferenceDomainError(f'Giro {x:.2f} rpm fuera del intervalo simulado {xs[0]:.2f}–{xs[-1]:.2f} rpm.')
    if len(xs)==1:return float(ys[0])
    h=np.diff(xs);d=np.diff(ys)/h;m=np.zeros(len(xs));m[0]=d[0];m[-1]=d[-1]
    for i in range(1,len(xs)-1):
        if d[i-1]*d[i]>0:
            m[i]=3*(h[i-1]+h[i])/((2*h[i]+h[i-1])/d[i-1]+(h[i]+2*h[i-1])/d[i])
    i=min(int(np.searchsorted(xs,x,side='right'))-1,len(xs)-2);i=max(i,0)
    t=(x-xs[i])/h[i]
    return float((2*t**3-3*t**2+1)*ys[i]+(t**3-2*t**2+t)*h[i]*m[i]+(-2*t**3+3*t**2)*ys[i+1]+(t**3-t**2)*h[i]*m[i+1])


def reference_point(n,c,wind,limit=30):
    d=load_reference();ident=config_id(n,c)
    q=sorted([x for x in d['casos'] if x['g']=='palas' and x['id']==ident and x['V']==wind],key=lambda x:x['rpm'])
    op=next((x for x in d['op'] if x['g']=='palas' and x['id']==ident and x['V']==wind),None)
    if not q or not op:raise ReferenceDomainError(f'No hay datos V80 para {ident} con viento {wind:g} m/s.')
    rpm=min(float(op['rpm_opt']),float(limit)) if limit is not None else float(op['rpm_opt'])
    # Never extrapolate at a lower operating limit, even if an exact-series tolerance matches.
    if rpm<q[0]['rpm']-1e-8 or rpm>q[-1]['rpm']+1e-8:
        raise ReferenceDomainError(f'{ident}, {wind:g} m/s: {rpm:.2f} rpm fuera de {q[0]["rpm"]:.2f}–{q[-1]["rpm"]:.2f} rpm. Cambia el límite o utiliza el modelo paramétrico.')
    az=d['az'].get(f'palas|{ident}|{wind:g}')
    exact=next((x for x in q if abs(x['rpm']-rpm)<.3),None)
    if az and abs(az['rpm']-rpm)<.3:
        power=float(az['P']);method='Serie azimutal del HTML'
    elif exact:
        power=float(exact['P']);method='Punto tabulado del HTML'
    else:
        k=int(np.argmax([x['P'] for x in q]));power=None
        if abs(rpm-op['rpm_opt'])<1e-8 and 0<k<len(q)-1:
            tri=q[k-1:k+2];coef=np.polyfit([x['rpm'] for x in tri],[x['P'] for x in tri],2)
            power=float(np.polyval(coef,rpm));method='Ajuste parabólico interior del HTML'
        if power is None:
            power=pchip_value([x['rpm'] for x in q],[x['P'] for x in q],rpm);method='Interpolación PCHIP entre puntos del HTML'
    omega=rpm*np.pi/30
    return {'V':wind,'rpm':rpm,'P':power,'Cp':power*1000/(.5*1.225*192*wind**3),'T':power*1000/omega,
            'method':method,'az':az if az and abs(az['rpm']-rpm)<.3 else None}


def reference_operation(D,H,N,c,pitch,helical,rho,limit,vmin,vmax,t_rel,symmetric,endplates,trips,struts_perf):
    valid=(np.isclose(D,12) and np.isclose(H,16) and np.isclose(rho,1.225) and
           np.isclose(pitch,0) and not helical and np.isclose(t_rel,15) and symmetric and
           not endplates and not trips and not struts_perf and (int(N),float(c)) in configurations())
    if not valid:raise ReferenceDomainError('La referencia V80 requiere D=12 m, H=16 m, NACA 0015, pala recta, calaje 0°, ρ=1,225 y una combinación de palas/cuerda del estudio, sin modificadores. Usa «Cargar geometría del estudio» o el modelo paramétrico.')
    if not np.isclose(vmin,4) or not np.isclose(vmax,10):
        raise ReferenceDomainError('La referencia dispone de vientos 4, 6, 8 y 10 m/s. Usa rango 4–10 m/s; no se extrapolan resultados.')
    points=[reference_point(N,c,v,limit) for v in (4.,6.,8.,10.)]
    return points


def preset(state):
    """Write widget state before Streamlit instantiates the dependent controls."""
    for key,value in {'rotor_d':12.,'rotor_h':16.,'rotor_n':3,'rotor_c':1.,'profile_name':'NACA 0015',
        'control_mode_widget':'MPPT (λ constante)','source_cut_in':3.,'source_rated':12.,'source_cut_out':20.,'profile_mode':'Catálogo NACA','profile_pitch':0.,'rotor_helical':False,'rotor_endplates':False,
        'rotor_trips':False,'rotor_struts_perf':False,'air_density':1.225,'wind_min':4.,'wind_max':10.,
        'apply_rotor_rpm_limit':True,'rotor_rpm_limit_value':30.,'reference_config':'3x1'}.items():state[key]=value


def initialize_source(state):
    """Start fresh sessions on the V80 reference, preserving deliberate in-session edits."""
    if 'aerodynamic_source' not in state:
        preset(state)
        state['aerodynamic_source']='QBlade · V80 (HTML)'


def source_changed():
    import streamlit as st
    if st.session_state.get('aerodynamic_source')=='QBlade · V80 (HTML)':preset(st.session_state)


def config_changed():
    import streamlit as st
    n,c=st.session_state['reference_config'].split('x')
    st.session_state['rotor_n']=int(n);st.session_state['rotor_c']=float(c)


def render_sidebar_source():
    import streamlit as st
    initialize_source(st.session_state)
    css=Path(__file__).with_name('assets').joinpath('sidebar_design.css').read_text()
    st.markdown('<style>'+css+'</style>',unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="sidebar-hero"><span>LABORATORIO VAWT</span><h2>Diseña. Compara.<br>Comprende.</h2><p>Geometría, control y energía conectados en un solo modelo.</p></div>',unsafe_allow_html=True)
        source=st.radio('Base aerodinámica',['Modelo paramétrico','QBlade · V80 (HTML)'],key='aerodynamic_source',on_change=source_changed)
        active=source=='QBlade · V80 (HTML)'
        if active:
            st.selectbox('Configuración del estudio',[config_id(n,c) for n,c in configurations()],key='reference_config',on_change=config_changed)
            st.button('Cargar geometría del estudio',on_click=lambda:preset(st.session_state),use_container_width=True)
            st.caption('V80 · 12 × 16 m · NACA 0015 · pala recta. Potencia del HTML y operación óptima tabulada con límite de rpm; generador y pérdidas se calculan aquí.')
        else:
            st.caption('Exploración libre con Cp–TSR aproximado. Selecciona QBlade para respetar los puntos del estudio V80.')
    return active


def render_sidebar_summary(context):
    import streamlit as st
    from html import escape
    r=context['base_results'];j=int(np.argmin(np.abs(r['v_grid']-st.session_state.get('visualizer_selected_wind',6))))
    mode='Referencia V80' if context.get('qblade_mode') else 'Modelo paramétrico'
    with st.sidebar:
        st.markdown(f'''<div class="sidebar-summary"><span>{mode} · a {r['v_grid'][j]:g} m/s</span><strong>{r['P_out_W'][j]/1000:.2f} <small>kW eléctricos</small></strong><div>{r['rpm_rotor'][j]:.1f} rpm · Cp aero {r['Cp_aero'][j]:.3f}</div><p>{escape(context['airfoil_name'])} · {context['N']} palas</p></div>''',unsafe_allow_html=True)
        with st.expander('Relaciones físicas del modelo'):
            st.latex(r'A=D\,H\qquad\lambda=\omega R/V')
            st.latex(r'P_{aero}=\tfrac12\rho A V^3 C_p')
            st.latex(r'T_{rotor}=P_{aero}/\omega')
            st.caption('La potencia eléctrica incorpora límites del generador y pérdidas. La fuente QBlade se restringe a los casos y vientos del HTML.')


def bounded_interp(wind, grid, values):
    """Return unavailable rather than silently extending a curve beyond its wind range."""
    if wind < grid[0] or wind > grid[-1]:
        return float('nan')
    return float(np.interp(wind, grid, values))
