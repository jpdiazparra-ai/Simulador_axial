"""Convert IFC world geometry to a self-contained browser mesh payload.
Requires IfcOpenShell only when rebuilding the asset, not at app runtime.
"""
import base64,collections,hashlib,json,math,os,time
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import numpy as np

import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path)
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data')
args=parser.parse_args()
source=args.source
args.output.mkdir(parents=True,exist_ok=True)
f=ifcopenshell.open(str(source))
products={p.id():p for p in f.by_type('IfcProduct') if p.Representation}

def properties(p):
    result={}
    for rel in getattr(p,'IsDefinedBy',[]):
        if rel.is_a('IfcRelDefinesByProperties'):
            for prop in getattr(rel.RelatingPropertyDefinition,'HasProperties',[]):
                if prop.is_a('IfcPropertySingleValue') and prop.NominalValue is not None:
                    v=prop.NominalValue.wrappedValue
                    if isinstance(v,(str,int,float,bool)):result[prop.Name]=v
    return result

def layer_for(p,props):
    if props.get('Capa'):return props['Capa']
    name=(p.Name or '').lower()
    if p.is_a('IfcFooting') or any(t in name for t in ('mortero','hormig','fundaci')):return 'Fundación y morteros'
    if p.is_a('IfcMechanicalFastener'):return 'Pernos y fijaciones de torre'
    if p.is_a('IfcPlate'):return 'Placas y conexiones de torre'
    return 'Torre: montantes y riostras'

def encode(array,dtype):
    return base64.b64encode(np.asarray(array,dtype=dtype).tobytes()).decode('ascii')

settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
settings.set('mesher-linear-deflection',.0005)
iterator=ifcopenshell.geom.iterator(settings,f,min(4,os.cpu_count() or 1))
assert iterator.initialize()
meshes=[];failed=[];seen=set();bounds_min=np.full(3,np.inf);bounds_max=-bounds_min
start=time.time()
while True:
    shape=iterator.get();p=products.get(shape.id)
    if p is not None:
        seen.add(p.id());geom=shape.geometry
        vertices=np.array(geom.verts,dtype=np.float32).reshape(-1,3);faces=np.array(geom.faces,dtype=np.uint32).reshape(-1,3)
        if not len(vertices) or not len(faces):failed.append({'id':p.id(),'name':p.Name,'reason':'Empty triangulation'})
        else:
            props=properties(p);layer=layer_for(p,props)
            colors=[]
            for material in geom.materials:
                try:
                    diffuse=material.diffuse
                    rgb=[float(diffuse.r()),float(diffuse.g()),float(diffuse.b())]
                    transparency=float(material.transparency)
                    colors.append({'rgb':rgb,'opacity':1-min(1,max(0,transparency)) if math.isfinite(transparency) else 1})
                except Exception:colors.append({'rgb':[.55,.6,.64],'opacity':1})
            if not colors:colors=[{'rgb':[.55,.6,.64],'opacity':1}]
            ids=np.asarray(geom.material_ids,dtype=np.int32)
            groups=[]
            for index in sorted(set(ids.tolist())):
                subset=faces[ids==index]
                if len(subset):groups.append({'material':int(max(index,0)),'indices':encode(subset,'<u4')})
            if not groups:groups=[{'material':0,'indices':encode(faces,'<u4')}]
            lo=vertices.min(axis=0);hi=vertices.max(axis=0);bounds_min=np.minimum(bounds_min,lo);bounds_max=np.maximum(bounds_max,hi)
            meshes.append({'id':p.id(),'guid':p.GlobalId,'name':p.Name or p.is_a(),'type':p.is_a(),
                'layer':layer,'rotating':layer.startswith('Rotor:'),'props':props,
                'bounds':[lo.tolist(),hi.tolist()],'vertices':encode(vertices,'<f4'),'groups':groups,'materials':colors,
                'vertexCount':len(vertices),'triangleCount':len(faces)})
        if len(seen)%100==0:print('Processed',len(seen),'elapsed',round(time.time()-start,1),flush=True)
    if not iterator.next():break
for ident,p in products.items():
    if ident not in seen:failed.append({'id':ident,'name':p.Name,'reason':'Not produced by geometry iterator'})
meshes.sort(key=lambda x:x['id'])
blades=[m for m in meshes if m['layer']=='Rotor: palas']
assert len(blades)==3
shaft=next(m for m in meshes if m['name'].startswith('Eje principal macizo'))
shaft_bounds=np.array(shaft['bounds']);axis=((shaft_bounds[0]+shaft_bounds[1])/2).tolist();axis[2]=0
layers=[]
for layer,count in collections.Counter(m['layer'] for m in meshes).items():
    members=[m for m in meshes if m['layer']==layer]
    layers.append({'name':layer,'count':count,'rotating':members[0]['rotating'],'color':members[0]['materials'][0]['rgb'],
                   'defaultVisible':layer!='Pernos y fijaciones de torre'})
meta={'filename':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'schema':f.schema,'units':'m',
      'products':len(products),'meshes':len(meshes),'vertices':sum(m['vertexCount'] for m in meshes),'triangles':sum(m['triangleCount'] for m in meshes),
      'bounds':[bounds_min.tolist(),bounds_max.tolist()],'axis':axis,'diameter':14,'bladeHeight':14,'bladeCount':3,'chord':1.4,'sweptArea':196,
      'bladeZ':[min(m['bounds'][0][2] for m in blades),max(m['bounds'][1][2] for m in blades)],
      'generatorDeclaredKW':100,'gearRatioDeclared':8,'status':'Propuesta según propiedades del IFC; no validada por calculista',
      'projectName':f.by_type('IfcProject')[0].Name,'projectDescription':f.by_type('IfcProject')[0].Description,
      'converter':'IfcOpenShell '+ifcopenshell.version,'omitted':failed}
result={'metadata':meta,'layers':layers,'meshes':meshes}
(args.output/'ifc_v80_v4_mesh.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
(args.output/'ifc_v80_v4_audit.json').write_text(json.dumps({'metadata':meta,'layers':layers,'bladeBounds':[{'id':b['id'],'bounds':b['bounds']} for b in blades]},ensure_ascii=False,indent=2))
print(json.dumps(meta,ensure_ascii=False),flush=True)
print('Payload bytes',(args.output/'ifc_v80_v4_mesh.json').stat().st_size,flush=True)
