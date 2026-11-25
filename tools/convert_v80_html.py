"""Extract embedded JSON and mesh buffers from the supplied V80 v5 HTML, without executing it."""
import argparse,base64,collections,hashlib,json,re
from pathlib import Path
import numpy as np

LAYER_ALIASES={'Torre reforzada':'Torre: montantes y riostras','Pernería torre':'Pernos y fijaciones de torre','Fundación':'Fundación y morteros'}
ROTATING=re.compile(r'^(Pala|Brazo|Carenado|Unión|Plancha de buje|Columna rotor|Tapa superior|Brida inferior|Eje corto de torque|Tirante|Tensor|Buje portavigas|Diafragma del buje|Oreja de brazo|Eje principal|Tambor de freno|Cruceta y brida|Tubo de cardán SWC|Barra del anillo|Tensor central|Silla de brazo|Flange de unión|Anillo de contracción|Acople flexible)')

def literal(text,name):
    match=re.search(r'const\s+'+re.escape(name)+r'\s*=\s*',text)
    if not match:raise ValueError('Dato no encontrado: '+name)
    return json.JSONDecoder().raw_decode(text[match.end():])[0]

def convert(source):
    raw=source.read_bytes();text=raw.decode('utf-8');meta=literal(text,'META');binary=base64.b64decode(literal(text,'GEO_B64'),validate=True);meshes=[]
    for pi,p in enumerate(meta['protos']):
        vertices=np.frombuffer(binary,dtype='<f4',count=p['vn']*3,offset=p['vo']).reshape(-1,3).astype(np.float64)
        faces=np.frombuffer(binary,dtype='<u2' if p['i16'] else '<u4',count=p['in'],offset=p['io']).astype('<u4')
        assert len(faces)%3==0 and faces.max()<len(vertices) and np.isfinite(vertices).all()
        layer=LAYER_ALIASES.get(p['layer'],p['layer'])
        if p['k'] in ('T:Suples y rellenos','T:Placas base y zapatas'):layer='Placas y conexiones de torre'
        color=[int(p['col'][i:i+2],16)/255 for i in (1,3,5)]
        offer=p['offer'];cards={k:meta['COMP'][k]['C'].get(p['k']) for k in ('A','B') if offer in (k,'AB')}
        card=next((c for c in cards.values() if c),None)
        for ii,a in enumerate(p['inst']):
            matrix=np.array(a[:9],dtype=float).reshape(3,3,order='F');world=(vertices@matrix.T+np.array(a[9:12])).astype('<f4')
            assert np.isfinite(world).all()
            props={k:v for k,v in (card['rows'] if card else [])}
            if p['k'].startswith('T:'):
                tower=meta['TOWER'].get(p['k'][2:],{})
                props.update({'Cantidad física declarada':tower.get('qty','Sin dato'),'Peso grupo declarado kg':tower.get('kg','Sin dato')})
            props.update({'Origen':'HTML V80 v5','Capa en HTML':p['layer'],'Variante':'Compartida A/B' if offer=='AB' else offer,'Instancia':f'{ii+1} de {len(p["inst"])}','Alcance ficha':'Propiedades y costos declarados del grupo; no de cada instancia'})
            meshes.append({'id':f'v5-{pi+1}-{ii+1}','sourceId':p['k'],'name':p['n']+f' · {ii+1}','type':'Malla HTML V5','layer':layer,'sourceLayer':p['layer'],'offer':offer,'rotating':bool(ROTATING.match(p['k'])),'props':props,'propsByOffer':{k:{**props,**dict(c['rows'])} for k,c in cards.items() if c},'bounds':[world.min(axis=0).tolist(),world.max(axis=0).tolist()],'vertices':base64.b64encode(world.tobytes()).decode(),'groups':[{'material':0,'indices':base64.b64encode(faces.tobytes()).decode()}],'materials':[{'rgb':color,'opacity':1}],'vertexCount':len(world),'triangleCount':len(faces)//3})
    layers=[]
    for layer,count in collections.Counter(m['layer'] for m in meshes).items():
        members=[m for m in meshes if m['layer']==layer]
        layers.append({'name':layer,'count':count,'rotating':any(m['rotating'] for m in members),'color':members[0]['materials'][0]['rgb'],'defaultVisible':True,'sourceLayers':sorted({m['sourceLayer'] for m in members})})
    # Retain the cost layer even though the recommended A configuration omits its ring.
    for k in ('A','B'):
        active=[m for m in meshes if m['offer'] in ('AB',k)]
        assert sum(m['layer']=='Rotor: palas' for m in active)==3
    bounds=np.array([m['bounds'] for m in meshes]);blade=[m for m in meshes if m['layer']=='Rotor: palas'];assert all(abs(m['bounds'][1][2]-m['bounds'][0][2]-14)<1e-5 for m in blade)
    metadata={'filename':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'schema':'HTML V5 · prototipos e instancias','sourceFormat':'HTML','revision':'V5','units':'m','products':len(meshes),'meshes':len(meshes),'prototypes':len(meta['protos']),'vertices':sum(m['vertexCount'] for m in meshes),'triangles':sum(m['triangleCount'] for m in meshes),'bounds':[bounds[:,0,:].min(axis=0).tolist(),bounds[:,1,:].max(axis=0).tolist()],'axis':[0,0,0],'diameter':14,'bladeHeight':14,'bladeCount':3,'chord':1.4,'sweptArea':196,'bladeZ':[6,20],'bladeProfile':'NACA 0018','bladeMassKG':400,'generatorDeclaredKW':100,'gearRatioDeclared':10,'defaultOffer':'A','offers':{'A':{'label':'A · Recomendada, sin anillo','description':'6 diagonales RHS 250×150×8 · carenados NACA 0022','meshes':sum(m['offer'] in ('AB','A') for m in meshes)},'B':{'label':'B · Con anillo de barras','description':'6 diagonales RHS 250×150×6 · barras Ø20 y tensores','meshes':sum(m['offer'] in ('AB','B') for m in meshes)}},'omitted':[],'conversion':'Extracción de GEO_B64/META, transformación de instancias a coordenadas originales Z vertical; sin ejecutar scripts','sourceLegacyTitle':'El title del HTML conserva D18; la ficha finalista, metadatos y geometría corresponden a D14 × H14.'}
    return {'metadata':metadata,'layers':layers,'meshes':meshes,'sourceCostSummaries':{k:v['resumen'] for k,v in meta['COMP'].items()}}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=convert(args.source);args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')));print(json.dumps(result['metadata'],ensure_ascii=False,indent=2))
