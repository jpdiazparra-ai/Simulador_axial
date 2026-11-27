"""Convert the supplied SolidWorks 80 kW IFC to audited, self-contained meshes (offline build)."""
import argparse,base64,collections,hashlib,json,os,time
from pathlib import Path
import ifcopenshell,ifcopenshell.geom
import numpy as np

def ancestry(p):
 chain=[];seen=set()
 while p and p.id() not in seen:
  seen.add(p.id());chain.append(p);parents=getattr(p,'Decomposes',[]);p=parents[0].RelatingObject if parents else None
 return chain

def classify(p):
 chain=ancestry(p);names=[(x.Name or '').upper() for x in chain];parents=' / '.join(names[1:]);name=names[0]
 if name.startswith('NSK_'):return 'Tren de potencia',False,chain
 if any(n.startswith('NACA0018') for n in names[1:]):return 'Rotor: palas',True,chain
 if 'EJE 12IN' in parents:return 'Rotor: buje y eje',True,chain
 if 'ACOPLE BRAZO-ASPA' in parents:return 'Rotor: uniones',True,chain
 if any(n.startswith('BRAZO ') for n in names[1:]):return 'Rotor: brazos',True,chain
 if 'PLATO APERNADO' in parents or 'TRABA TUERCAS' in parents or 'ENSAMBLE ASPA' in parents:return 'Rotor: uniones',True,chain
 return 'Otros componentes IFC',False,chain

def enc(a,dtype):return base64.b64encode(np.asarray(a,dtype=dtype).tobytes()).decode('ascii')

def convert(source,output):
 f=ifcopenshell.open(str(source));products={p.id():p for p in f.by_type('IfcProduct') if p.Representation};settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
 iterator=ifcopenshell.geom.iterator(settings,f,min(4,os.cpu_count() or 1));assert iterator.initialize();meshes=[];seen=set();failures=[];blade_points=[];shaft_points=[];axis_points=[];blade_sections={};blade_ids=set();start=time.time()
 while True:
  shape=iterator.get();p=products[shape.id];seen.add(p.id());g=shape.geometry;v=np.asarray(g.verts,dtype=np.float64).reshape(-1,3);faces=np.asarray(g.faces,dtype=np.uint32).reshape(-1,3)
  if not len(v) or not len(faces):failures.append({'id':p.id(),'reason':'Empty geometry'})
  else:
   layer,rotating,chain=classify(p);materials=[]
   for material in g.materials:
    try:rgb=[material.diffuse.r(),material.diffuse.g(),material.diffuse.b()]
    except Exception:rgb=[.6,.65,.68]
    materials.append({'rgb':rgb,'opacity':1})
   if not materials:materials=[{'rgb':[.6,.65,.68],'opacity':1}]
   ids=np.asarray(g.material_ids);groups=[{'material':max(0,int(index)),'indices':enc(faces[ids==index],'<u4')} for index in sorted(set(ids.tolist()))]
   parent=chain[1].Name if len(chain)>1 else p.Name
   meshes.append({'id':p.id(),'guid':p.GlobalId,'name':str(parent)+' · '+str(p.Name),'type':p.is_a(),'assembly':parent,'layer':layer,'rotating':rotating,'props':{'Nombre IFC':p.Name,'Conjunto IFC':parent,'Cantidad':'No declarada','Peso total':'Sin dato'},'vertices':v,'groups':groups,'materials':materials,'vertexCount':len(v),'triangleCount':len(faces)})
   if layer=='Rotor: palas':
    blade_points.append(v)
    blade_id=next(x.id() for x in chain if (x.Name or '').upper().startswith('ENSAMBLE ASPA'));blade_ids.add(blade_id);blade_sections.setdefault(blade_id,[]).append(v)
   if layer=='Rotor: buje y eje':
    shaft_points.append(v)
    if '12IN SCH80' in (p.Name or '').upper():axis_points.append(v)
  if len(seen)%50==0:print('Converted',len(seen),'of',len(products),'seconds',round(time.time()-start,1),flush=True)
  if not iterator.next():break
 failures.extend({'id':ident,'reason':'Missing geometry'} for ident in products if ident not in seen)
 if failures:raise ValueError(json.dumps(failures))
 blades=np.concatenate(blade_points);shaft=np.concatenate(shaft_points);vertical=int(np.argmax(np.ptp(np.concatenate(blade_sections[min(blade_sections)]),axis=0)));transform=np.eye(3)
 if vertical==1:transform=np.array([[1,0,0],[0,0,-1],[0,1,0]],float)
 elif vertical==0:transform=np.array([[0,0,-1],[0,1,0],[1,0,0]],float)
 shaft=np.concatenate(axis_points) if axis_points else shaft;shaft=shaft@transform.T;axis=(shaft.min(0)+shaft.max(0))/2
 # Normalize only the rotor's horizontal axis; retain the source elevation and audit the transform.
 translation=np.array([-axis[0],-axis[1],0])
 for mesh in meshes:
  v=mesh['vertices']@transform.T+translation;mesh['bounds']=[v.min(0).tolist(),v.max(0).tolist()];mesh['vertices']=enc(v,'<f4')
 blades=blades@transform.T+translation;diameter=2*np.max(np.linalg.norm(blades[:,:2],axis=1));height=np.ptp(blades[:,2]);bounds=[np.min([m['bounds'][0] for m in meshes],axis=0).tolist(),np.max([m['bounds'][1] for m in meshes],axis=0).tolist()]
 counts=collections.Counter(m['layer'] for m in meshes);layers=[{'name':name,'count':count,'rotating':next(m['rotating'] for m in meshes if m['layer']==name),'color':next(m['materials'][0]['rgb'] for m in meshes if m['layer']==name),'defaultVisible':True} for name,count in counts.items()]
 previous=json.loads((output/'v80_v5_mesh.json').read_text())['metadata']['sha256']
 meta={'filename':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'previousModelSha':previous,'schema':f.schema,'sourceType':'IFC','label':'Ensamble 80 kW · IFC','units':'m','products':len(products),'meshes':len(meshes),'vertices':sum(m['vertexCount'] for m in meshes),'triangles':sum(m['triangleCount'] for m in meshes),'bounds':bounds,'axis':[0,0,0],'diameter':float(diameter),'bladeHeight':float(height),'bladeCount':len(blade_ids),'chord':None,'sweptArea':float(diameter*height),'generatorDeclaredKW':None,'gearRatioDeclared':None,'defaultOffer':'IFC','offers':{'IFC':{'label':'IFC · Ensamble turbina 80 kW','description':'SolidWorks · archivo suministrado · sin torre ni fundación y sin pesos declarados','meshes':len(meshes)}},'converter':'IfcOpenShell '+ifcopenshell.version,'coordinateTransform':{'rotation':transform.tolist(),'translation':translation.tolist(),'sourceVerticalAxis':vertical},'omitted':failures,'missingGeometryGroups':['tower','foundation'],'weightStatus':'No mass quantities or property sets are provided by this IFC'}
 result={'metadata':meta,'layers':layers,'meshes':sorted(meshes,key=lambda m:m['id'])}
 (output/'ifc_80kw_mesh.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 (output/'ifc_80kw_audit.json').write_text(json.dumps({'metadata':meta,'layers':layers,'products':[{'id':m['id'],'guid':m['guid'],'name':m['name'],'assembly':m['assembly'],'layer':m['layer'],'rotating':m['rotating'],'bounds':m['bounds']} for m in result['meshes']]},ensure_ascii=False,indent=2))
 print(json.dumps(meta,ensure_ascii=False),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();convert(args.source,args.output)
