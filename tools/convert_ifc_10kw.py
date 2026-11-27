"""Build the 10 kW browser asset from the supplied SolidWorks IFC. Offline rebuild only."""
import argparse,base64,collections,hashlib,json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom


def encode(values,dtype):return base64.b64encode(np.asarray(values,dtype=dtype).tobytes()).decode('ascii')

def ancestry(product):
    result=[];seen=set()
    while product and product.id() not in seen:
        seen.add(product.id());result.append(product)
        parents=list(getattr(product,'Decomposes',[]));product=parents[0].RelatingObject if parents else None
    return result

def classify(product):
    chain=ancestry(product);text=' / '.join(str(item.Name or '') for item in chain).upper()
    for token,layer in [('ASPA FRP','Palas FRP'),('GENERADOR 10KW','Generador 10 kW'),('MASTIL HEXAGONAL','Mástil'),('CALIPER','Freno y caliper'),('DISCO FRENO','Freno y caliper'),('TENSOR','Tensores'),('ACOPLE','Acoples y transmisión'),('COLUMNA','Columna y soportes'),('PIÑON','Acoples y transmisión')]:
        if token in text:return layer,chain
    return 'Otros componentes',chain


def convert(source,output):
    f=ifcopenshell.open(str(source));settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    meshes=[];failures=[];blade_points=[];mast_points=[];blade_ids=set()
    for product in f.by_type('IfcProduct'):
        if not product.Representation:continue
        try:
            shape=ifcopenshell.geom.create_shape(settings,product);g=shape.geometry
            verts=np.asarray(g.verts,dtype=np.float64).reshape(-1,3);faces=np.asarray(g.faces,dtype=np.uint32).reshape(-1,3)
            if not len(faces):raise ValueError('No triangulation')
            layer,chain=classify(product);assembly=next((item for item in chain if item.is_a('IfcElementAssembly')),product)
            materials=[]
            for material in g.materials:
                try:rgb=[material.diffuse.r(),material.diffuse.g(),material.diffuse.b()]
                except Exception:rgb=[.6,.66,.7]
                materials.append({'rgb':rgb,'opacity':1})
            if not materials:materials=[{'rgb':[.6,.66,.7],'opacity':1}]
            ids=np.asarray(g.material_ids);groups=[]
            for ident in sorted(set(ids.tolist())):
                groups.append({'material':max(0,int(ident)),'indices':encode(faces[ids==ident],'<u4')})
            lo=verts.min(0);hi=verts.max(0)
            meshes.append({'id':product.id(),'guid':product.GlobalId,'name':product.Name or 'Componente IFC','assembly':assembly.Name or '', 'assemblyId':assembly.id(), 'layer':layer,
                'vertices':encode(verts,'<f4'),'groups':groups,'materials':materials,'bounds':[lo.tolist(),hi.tolist()], 'triangles':len(faces)})
            if layer=='Palas FRP':
                blade_points.append(verts);blade_ids.add(assembly.id())
            if layer=='Mástil':mast_points.append(verts)
        except Exception as exc:failures.append({'id':product.id(),'name':product.Name,'reason':str(exc)})
    if failures:raise ValueError('Unconverted products: '+json.dumps(failures,ensure_ascii=False))
    blades=np.concatenate(blade_points);all_points=np.array([m['bounds'] for m in meshes]).reshape(-1,3)
    # Determine the long direction from the blades, then rotate into Z-up for the viewer.
    span=np.ptp(np.concatenate(mast_points) if mast_points else blade_points[0],axis=0);vertical=int(np.argmax(span))
    transform=np.eye(3)
    if vertical==1:transform=np.array([[1,0,0],[0,0,-1],[0,1,0]],dtype=float)
    elif vertical==0:transform=np.array([[0,0,-1],[0,1,0],[1,0,0]],dtype=float)
    for mesh in meshes:
        v=np.frombuffer(base64.b64decode(mesh['vertices']),dtype='<f4').reshape(-1,3).astype(float)@transform.T
        mesh['vertices']=encode(v,'<f4');mesh['bounds']=[v.min(0).tolist(),v.max(0).tolist()]
    blades=blades@transform.T
    mast=np.concatenate(mast_points)@transform.T if mast_points else blades
    axis=(mast.min(0)+mast.max(0))/2
    diameter=float(2*np.max(np.linalg.norm(blades[:,:2]-axis[:2],axis=1)))
    height=float(np.ptp(blades[:,2]));chords=[]
    for ident in sorted(blade_ids):
        points=np.concatenate([np.frombuffer(base64.b64decode(m['vertices']),dtype='<f4').reshape(-1,3) for m in meshes if m['assemblyId']==ident])
        mid=(points[:,2].min()+points[:,2].max())/2;cuts=[]
        for mesh in [m for m in meshes if m['assemblyId']==ident]:
            vertices=np.frombuffer(base64.b64decode(mesh['vertices']),dtype='<f4').reshape(-1,3)
            for group in mesh['groups']:
                triangles=vertices[np.frombuffer(base64.b64decode(group['indices']),dtype='<u4').reshape(-1,3)]
                for a,b in [(0,1),(1,2),(2,0)]:
                    first=triangles[:,a];second=triangles[:,b];dz=second[:,2]-first[:,2]
                    mask=(np.abs(dz)>1e-8)&((first[:,2]-mid)*(second[:,2]-mid)<=0)
                    t=(mid-first[mask,2])/dz[mask];cuts.extend((first[mask,:2]+t[:,None]*(second[mask,:2]-first[mask,:2])).tolist())
        section=np.unique(np.round(cuts,6),axis=0) if cuts else np.empty((0,2))
        if len(section)>3:
            _,basis=np.linalg.eigh(np.cov(section.T));chords.append(float(np.ptp(section@basis[:,-1])))
    bounds=[np.min([m['bounds'][0] for m in meshes],axis=0).tolist(),np.max([m['bounds'][1] for m in meshes],axis=0).tolist()]
    metadata={'filename':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'schema':f.schema,'units':'m','generatorDeclaredKW':10,
        'meshes':len(meshes),'assemblies':len(f.by_type('IfcElementAssembly')),'triangles':sum(m['triangles'] for m in meshes),'bounds':bounds,'axis':axis.tolist(),
        'bladeCount':len(blade_ids),'diameterEnvelope':diameter,'bladeHeight':height,'chordEstimate':float(np.median(chords)) if chords else None,
        'dimensionMethod':'Diámetro envolvente de las palas respecto del centro del mástil; altura de las palas y cuerda aproximada de sección central por PCA. Confirmar cotas de diseño.',
        'massStatus':'No hay cantidades de peso estructuradas; 158 kg aparece en el nombre de los conjuntos de pala, sin validar su alcance.',
        'qbladeStatus':'Sin resultados QBlade de esta geometría. Análisis paramétrico separado del IFC.', 'converter':'IfcOpenShell '+ifcopenshell.version,'originalVerticalAxis':vertical,'omitted':failures}
    layers=[{'name':name,'count':count} for name,count in collections.Counter(m['layer'] for m in meshes).items()]
    output.mkdir(parents=True,exist_ok=True);(output/'ifc_10kw_mesh.json').write_text(json.dumps({'metadata':metadata,'layers':layers,'meshes':meshes},ensure_ascii=False,separators=(',',':')))
    (output/'ifc_10kw_audit.json').write_text(json.dumps({'metadata':metadata,'layers':layers},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(metadata,ensure_ascii=False,indent=2));print('Bytes:',(output/'ifc_10kw_mesh.json').stat().st_size)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();convert(args.source,args.output)
