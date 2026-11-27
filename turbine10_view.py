"""Independent 10 kW workspace: measured IFC, explicit hypotheses, existing parametric engine."""
import json
from pathlib import Path
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

ROOT=Path(__file__).parent

@st.cache_data(show_spinner=False)
def load_model10():
    return json.loads((ROOT/'data/ifc_10kw_mesh.json').read_text())

def default_inputs(metadata):
    return dict(diameter=round(metadata['diameterEnvelope'],3),height=round(metadata['bladeHeight'],3),blades=metadata['bladeCount'],chord=.8,profile='NACA 0018',pitch=0.,G=1.,tsr=2.6,rpm_limit=70.,rho=1.225,k=2.,wind_scale=6.,mass=158.,mass_enabled=False,structural_enabled=False,root_modulus=.0001,strut_area=10.,yield_mpa=250.,safety=2.,rpm_threshold=70.,torque_threshold=2000.,root_threshold=10.)

def validate_inputs(p):
    ranges={'diameter':(.5,100.),'height':(.5,100.),'blades':(2,8),'chord':(.05,10.),'pitch':(-20,20),'G':(1,100),'tsr':(.5,8),'rpm_limit':(1,300),'rho':(.8,1.5),'k':(1,5),'wind_scale':(2,20),'mass':(.1,5000),'root_modulus':(1e-6,1),'strut_area':(.1,10000),'yield_mpa':(10,3000),'safety':(1,10),'rpm_threshold':(1,300),'torque_threshold':(1,100000),'root_threshold':(.01,10000)}
    for key,(lo,hi) in ranges.items():
        value=p.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value) or not lo<=value<=hi:raise ValueError('Revisa '+key)
    if p['blades']!=int(p['blades']):raise ValueError('El número de palas debe ser entero.')
    if p['profile'] not in ['NACA 0015','NACA 0018','NACA 0021']:raise ValueError('Perfil de cálculo no disponible.')
    if p['structural_enabled'] and not p['mass_enabled']:raise ValueError('Activa la masa ingresada antes de evaluar tensiones.')
    return p

def engine_inputs(p,generator):
    validate_inputs(p)
    return dict(D=p['diameter'],H=p['height'],N=int(p['blades']),c=p['chord'],eta_bear=.98,eta_gear=.96,helical=False,helix_angle_deg=0.,endplates=False,trips=False,struts_perf=False,t_rel=float(p['profile'][-2:]),is_symmetric=True,pitch_deg=p['pitch'],control_mode='MPPT (λ constante)',lam_opt_ctrl=p['tsr'],v_cut_in=3.,v_rated=12.,v_cut_out=20.,rpm_rotor_rated=generator['rpm_nom']/p['G'],G=p['G'],rpm_gen_rated=generator['rpm_nom'],rpm_v_exp=1.,rho=p['rho'],mu=1.81e-5,m_blade=p['mass'] if p['mass_enabled'] else 0.,lever_arm_pala=p['diameter']/2,struts_per_blade=2,section_modulus_root=p['root_modulus'],sigma_y_pala_mpa=p['yield_mpa'],strut_area_cm2=p['strut_area'],sigma_allow_strut_mpa=p['yield_mpa'],safety_target=p['safety'],T_gen_max=generator['T_nom'],eta_gen_max=.93,eta_elec=.975,P_nom_kW=10.,poles_total=generator['poles'],pf_setpoint=.95,Kt_nm_per_A=generator['Kt_default'],Ke_vsr_default=generator['Ke_default'],V_dc_nom=600.,I_dc_nom=25.,use_noise=False,Lw_ref_dB=0.,r_obs=50.,n_noise=5.,v_min=1.,v_max=20.,tab_power_rpm=tuple(generator['power_table']['rpm']),tab_power_kw=tuple(generator['power_table']['P_kW']),tab_volt_rpm=tuple(generator['volt_table']['rpm']),tab_volt_vll=tuple(generator['volt_table']['V_LL']),rpm_limit=p['rpm_limit'],qblade_reference_mode=False)

def build_payload10(compute,generator,polar_fn,p,metadata):
    base=engine_inputs(p,generator);cases=[]
    for label,factor in [('Configuración actual',1.),('Cuerda −20 %',.8),('Cuerda +20 %',1.2)]:
        result=compute(**dict(base,c=base['c']*factor));v=np.asarray(result['v_grid']);power=np.asarray(result['P_out_W'])/1000
        pdf=(p['k']/p['wind_scale'])*(v/p['wind_scale'])**(p['k']-1)*np.exp(-(v/p['wind_scale'])**p['k'])
        energy=float(np.trapz(power*pdf,v)*8760)
        fields={'aero':('P_aero_W',1000),'electric':('P_out_W',1000),'rpm':('rpm_rotor',1),'rpmGen':('rpm_gen',1),'tsr':('lambda_eff',1),'cp':('Cp_aero',1),'torque':('T_rotor_Nm',1),'torqueGen':('T_gen_Nm',1),'voltage':('V_LL_curve',1),'current':('I_A',1),'frequency':('f_e_Hz',1),'re':('Re_mid',1),'mechanicalLoss':('P_loss_mec_W',1000),'generatorLoss':('P_loss_gen_W',1000),'electricalLoss':('P_loss_elec_W',1000),'clipping':('P_loss_clip_W',1000)}
        row={'name':label,'chord':base['c']*factor,'wind':v.tolist(),'aep':energy,'cf':energy/(10*8760)}
        for name,(key,scale) in fields.items():row[name]=(np.asarray(result[key])/scale).tolist()
        for name,key,scale,enabled in [('centrifugal','F_centripetal_series',1000,p['mass_enabled']),('rootMoment','M_root_series_Nm',1000,p['mass_enabled']),('rootStress','sigma_root_MPa',1,p['structural_enabled']),('strutStress','sigma_strut_MPa',1,p['structural_enabled'])]:row[name]=(np.asarray(result[key])/scale).tolist() if enabled else [None]*len(v)
        # The shared Cp model has an epsilon at zero TSR; a stopped rotor delivers no rotational power.
        for index,rpm in enumerate(row['rpm']):
            if rpm<=0:
                for name in ['aero','electric','cp','torque','torqueGen','voltage','current','frequency','mechanicalLoss','generatorLoss','electricalLoss','clipping','centrifugal','rootMoment','rootStress','strutStress']:
                    if row[name][index] is not None:row[name][index]=0.
        cases.append(row)
    polar=polar_fn(float(p['profile'][-2:]),True)
    coverage=float(np.exp(-(1/p['wind_scale'])**p['k'])-np.exp(-(20/p['wind_scale'])**p['k']))
    result={'params':dict(p),'metadata':metadata,'cases':cases,'generator':{'label':generator['label'],'ratedKW':10,'ratedRPM':generator['rpm_nom'],'ratedCurrent':generator['I_nom'],'ratedTorque':generator['T_nom']},'polar':{'alpha':polar['alpha_deg'].tolist(),'cl':polar['Cl'].tolist()},'coverage':coverage,'source':'parametric-10kw','structuralActive':bool(p['structural_enabled']),'massActive':bool(p['mass_enabled'])}
    # Reject invalid numerical output instead of serializing NaN into an offline report.
    json.dumps(result,allow_nan=False)
    return result

def build_html10(payload,model):
    assets=ROOT/'assets'
    safe=lambda value:json.dumps(value,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=(assets/'turbine10.html').read_text()
    return template.replace('__STYLE__',(assets/'turbine10.css').read_text()).replace('__THREE__',(assets/'vendor/three.r158.min.js').read_text()).replace('__PAYLOAD10__',safe(payload)).replace('__MODEL10__',safe(model)).replace('__SCRIPT10__',(assets/'page_refresh.js').read_text()+'\n'+(assets/'turbine10.js').read_text())

def render_turbine10(compute,generator,polar_fn):
    model=load_model10();defaults=default_inputs(model['metadata']);saved=dict(st.session_state.get('_t10_inputs',defaults))
    if not st.session_state.get('_t10_chord08_confirmed'):
        saved['chord']=.8;st.session_state['_t10_inputs']=dict(saved);st.session_state['t10_chord']=.8;st.session_state['_t10_chord08_confirmed']=True
    for key,value in saved.items():
        widget='t10_'+key
        if widget not in st.session_state:st.session_state[widget]=value
    with st.sidebar:
        st.markdown('### Proyecto 10 kW')
        st.caption('IFC propio · parámetros independientes del V80.')
        st.write('Generador de cálculo: '+generator['label'])
        st.caption('Edita las hipótesis en «Parámetros de la turbina de 10 kW», sobre el informe HTML.')
    st.markdown('<div class="t10-intro"><span>PROYECTO INDEPENDIENTE · 10 kW</span><h2>De la geometría al comportamiento</h2><p>IFC propio y estimación paramétrica. Las hipótesis se editan aquí; el estudio V80 conserva sus parámetros.</p></div>',unsafe_allow_html=True)
    with st.expander('Parámetros de la turbina de 10 kW',expanded=False):
        with st.form('t10_parameters'):
            a,b,c,d=st.columns(4)
            fields={}
            for box,key,label,lo,hi,step in [(a,'diameter','Diámetro de análisis [m]',.5,100.,.05),(b,'height','Altura de pala [m]',.5,100.,.05),(c,'chord','Cuerda de cálculo [m]',.05,10.,.05),(d,'blades','Número de palas',2,8,1)]:
                with box:fields[key]=st.number_input(label,min_value=lo,max_value=hi,step=step,key='t10_'+key)
            st.caption('D y H parten de envolventes del IFC. Cuerda de referencia confirmada por el usuario: 0,8 m; el perfil sigue supuesto; las dimensiones de cálculo no deforman el modelo 3D.')
            a,b,c,d=st.columns(4)
            with a:fields['profile']=st.selectbox('Perfil supuesto',['NACA 0015','NACA 0018','NACA 0021'],key='t10_profile')
            for box,key,label,lo,hi,step in [(b,'pitch','Calaje [°]',-20.,20.,.5),(c,'G','Relación de transmisión',1.,100.,.1),(d,'tsr','TSR de control',.5,8.,.1),(a,'rpm_limit','Límite rotor [rpm]',1.,300.,1.),(b,'rho','Densidad del aire [kg/m³]',.8,1.5,.005),(c,'k','Weibull · k',1.,5.,.1),(d,'wind_scale','Weibull · c [m/s]',2.,20.,.1)]:
                with box:fields[key]=st.number_input(label,min_value=lo,max_value=hi,step=step,key='t10_'+key)
            st.caption('Generador de cálculo: '+generator['label']+'. Confirmar que esta ficha representa al generador fluxial del IFC. Recurso Weibull supuesto; rango integrado 1–20 m/s.')
            a,b=st.columns(2)
            with a:fields['mass']=st.number_input('Masa por pala ingresada [kg]',min_value=.1,max_value=5000.,step=1.,key='t10_mass');fields['mass_enabled']=st.checkbox('Usar esta masa para estimar cargas',key='t10_mass_enabled')
            with b:fields['structural_enabled']=st.checkbox('Evaluar tensiones con las propiedades indicadas',key='t10_structural_enabled');st.caption('158 kg procede del nombre del conjunto, no de una propiedad de masa validada. Las tensiones quedan pendientes hasta activar las hipótesis.')
            a,b,c=st.columns(3)
            for box,key,label,lo,hi,step,fmt in [(a,'root_modulus','Módulo resistente raíz [m³]',1e-6,1.,.00001,'%.6f'),(b,'strut_area','Área efectiva del brazo [cm²]',.1,10000.,1.,'%.2f'),(c,'yield_mpa','Admisible antes de FS [MPa]',10.,3000.,5.,'%.1f'),(a,'safety','Factor de seguridad',1.,10.,.1,'%.1f'),(b,'rpm_threshold','Umbral rotor [rpm]',1.,300.,1.,'%.1f'),(c,'torque_threshold','Umbral torque rotor [N·m]',1.,100000.,100.,'%.1f'),(a,'root_threshold','Umbral momento raíz [kN·m]',.01,10000.,1.,'%.2f')]:
                with box:fields[key]=st.number_input(label,min_value=lo,max_value=hi,step=step,format=fmt,key='t10_'+key)
            submitted=st.form_submit_button('Actualizar análisis de 10 kW',use_container_width=True)
    if submitted:
        try:validate_inputs(fields);st.session_state['_t10_inputs']=dict(fields);saved=dict(fields)
        except ValueError as exc:st.error(str(exc));return
    try:payload=build_payload10(compute,generator,polar_fn,saved,model['metadata'])
    except (ValueError,KeyError) as exc:st.error('No se pudo calcular esta configuración: '+str(exc));return
    components.html(build_html10(payload,model),height=1400,scrolling=True)
