"""Validated bidirectional state for the HTML dashboard and Streamlit widgets."""
from pathlib import Path
import math

import streamlit as st
import streamlit.components.v1 as components
from qblade_reference import configurations, config_id, preset, reference_point

# Engine field, user label, min, max, step. Keys are shared with sidebar widgets.
SPECS = [
 ('rpm_limit','Máximo rotor [rpm]',1,200,1),
 ('k_w','Weibull · forma k',1,10,.1),('c_w','Weibull · escala c [m/s]',2,40,.1),
 ('G','Relación de transmisión G',1,100,.05),
 ('eta_bear','Eficiencia rodamientos',.90,1,.005),('eta_gear','Eficiencia transmisión',.85,1,.005),
 ('eta_gen_max','Eficiencia máxima generador',.80,1,.005),('eta_elec','Eficiencia electrónica',.90,1,.005),
 ('P_nom_kW','Potencia nominal eléctrica [kW]',1,10000,1),('T_gen_max','Torque máximo generador [N·m]',0,1000000,50),
 ('poles_total','Número de polos',4,200,2),('pf_setpoint','Factor de potencia',.8,1,.01),
 ('Ke_vsr_default','Ke [V·s/rad]',1,10000,.1),('Kt_nm_per_A','Kt [N·m/A]',1,10000,.1),
 ('V_dc_nom','Tensión DC [V]',400,5000,10),('I_dc_nom','Corriente DC nominal [A]',20,10000,5),
 ('m_blade','Masa por pala [kg]',10,100000,10),('lever_arm_pala','Brazo efectivo [m]',.1,100,.1),
 ('struts_per_blade','Brazos por pala',1,20,1),('section_modulus_root','Módulo resistente raíz [m³]',.001,100,.005),
 ('sigma_y_pala_mpa','Admisible pala antes de FS [MPa]',50,10000,5),('strut_area_cm2','Área efectiva brazo [cm²]',5,100000,1),
 ('sigma_allow_strut_mpa','Admisible brazo antes de FS [MPa]',50,10000,5),('safety_target','Factor de seguridad',1,20,.1),
 ('rpm_rotor_max_iec','Umbral estructural [rpm]',10,1000,1),('T_rotor_max_iec','Límite torque rotor [N·m]',1000,10000000,500),
 ('g_max_pala_iec','Límite aceleración radial [g]',5,10000,1),('M_base_max_iec','Límite momento raíz [kN·m]',10,1000000,10),
 ('I_inv_thermal_A','Corriente térmica inversor [A]',50,10000,1),
]
KEYS = {name:'html_'+name for name,*_ in SPECS if name not in ('rpm_limit','lever_arm_pala')}
INTEGER_FIELDS={'poles_total','struts_per_blade'}


def validate_update(update):
    if not isinstance(update,dict) or update.get('source')!='qblade':
        raise ValueError('Actualización HTML no válida')
    ident=str(update.get('config',''))
    if ident not in {config_id(n,c) for n,c in configurations()}:
        raise ValueError('La configuración no pertenece al estudio V80')
    params=update.get('params',{})
    if not isinstance(params,dict):raise ValueError('Parámetros no válidos')
    clean={}
    for name,_label,minimum,maximum,_step in SPECS:
        value=params.get(name)
        if name=='rpm_limit' and value is None:
            clean[name]=None;continue
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f'Parámetro no válido: {name}')
        if not minimum<=value<=maximum:raise ValueError(f'Fuera de rango: {name}')
        if name in INTEGER_FIELDS:
            if value!=int(value):raise ValueError(f'{name} debe ser entero')
            value=int(value)
        if name=='poles_total' and value%2:raise ValueError('El número de polos debe ser par')
        clean[name]=value
    n,c=ident.split('x')
    for wind in (4,6,8,10):reference_point(int(n),float(c),wind,clean['rpm_limit'])
    return ident,clean


def synchronize():
    update=st.session_state.get('vawt_html_component')
    if not update:return
    if isinstance(update, dict) and update.get('action') == 'refresh_costs':
        from cost_reference import load_cost_reference
        load_cost_reference.clear()
        st.session_state.pop('visualizer_sync_error', None)
        return
    try:
        ident,params=validate_update(update)
    except ValueError as exc:
        st.session_state['visualizer_sync_error']=str(exc);return
    if st.session_state.get('aerodynamic_source')!='QBlade · V80 (HTML)':preset(st.session_state)
    st.session_state['aerodynamic_source']='QBlade · V80 (HTML)'
    st.session_state['reference_config']=ident
    n,c=ident.split('x');st.session_state['rotor_n']=int(n);st.session_state['rotor_c']=float(c)
    for name,key in KEYS.items():st.session_state[key]=params[name]
    st.session_state['apply_rotor_rpm_limit']=params['rpm_limit'] is not None
    if params['rpm_limit'] is not None:st.session_state['rotor_rpm_limit_value']=params['rpm_limit']
    st.session_state['html_auto_G']=False
    count=params['struts_per_blade']
    st.session_state['strut_dist_input']=', '.join([str(params['lever_arm_pala'])]*count)
    st.session_state['strut_dist_count']=count
    st.session_state['strut_weight_input']=', '.join(['1']*count)
    st.session_state['strut_weight_count']=count
    wind=update.get('wind',6)
    if wind in (4,6,8,10):st.session_state['visualizer_selected_wind']=wind
    ui=update.get('ui',{})
    if isinstance(ui,dict) and isinstance(ui.get('theta'),(int,float)) and math.isfinite(ui['theta']) and isinstance(ui.get('play'),bool):
        st.session_state['visualizer_ui']={'theta':float(ui['theta'])%360,'play':ui['play']}
        if ui.get('powerView') in ('power','cp','losses'):
            st.session_state['visualizer_ui']['powerView']=ui['powerView']
        if ui.get('riskMetric') in ('rpm','torque','tGen','current','currentInv','accel','moment','sigmaRoot','sigmaStrut'):
            st.session_state['visualizer_ui']['riskMetric']=ui['riskMetric']
    st.session_state.pop('visualizer_sync_error',None)


@st.cache_resource
def component():
    return components.declare_component('vawt_interactive_dashboard_v3',path=str(Path(__file__).with_name('assets')/'visualizer_component'))


def render_component(html):
    value=st.session_state.get('vawt_html_component') or {}
    component()(html=html,ack_nonce=value.get('nonce'),key='vawt_html_component',default=None,on_change=synchronize)
    if st.session_state.get('visualizer_sync_error'):
        st.error(st.session_state['visualizer_sync_error'])
