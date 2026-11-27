"""The active 80 kW IFC replaces historical geometry without inventing absent properties."""
import base64,hashlib,json,subprocess,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

class ActiveIfc80Tests(unittest.TestCase):
    def test_all_geometry_and_provenance_are_preserved(self):
        model=json.loads((ROOT/'data/ifc_80kw_mesh.json').read_text())
        audit=json.loads((ROOT/'data/ifc_80kw_audit.json').read_text())
        meta=model['metadata']
        self.assertEqual(meta['sha256'],hashlib.sha256((ROOT/'data/ENSAMBLE TURBINA 80KW_1.IFC').read_bytes()).hexdigest())
        self.assertEqual((meta['products'],len(model['meshes']),len(audit['products'])),(378,378,378))
        self.assertEqual(meta['omitted'],[])
        self.assertEqual(meta['bladeCount'],3)
        self.assertEqual(meta['missingGeometryGroups'],['tower','foundation'])
        self.assertIsNone(meta['generatorDeclaredKW']);self.assertIsNone(meta['gearRatioDeclared'])
        self.assertEqual(sum(m['rotating'] for m in model['meshes']),376)
        for mesh in model['meshes']:
            vertices=np.frombuffer(base64.b64decode(mesh['vertices']),dtype='<f4').reshape(-1,3)
            self.assertTrue(np.isfinite(vertices).all())
            np.testing.assert_allclose([vertices.min(0),vertices.max(0)],mesh['bounds'],atol=1e-5)
            self.assertEqual(mesh['props']['Peso total'],'Sin dato')
            for group in mesh['groups']:
                indices=np.frombuffer(base64.b64decode(group['indices']),dtype='<u4')
                self.assertLess(int(indices.max()),len(vertices))
                self.assertLess(group['material'],len(mesh['materials']))
        pipe=next(m for m in model['meshes'] if m['id']==42)
        np.testing.assert_allclose(np.mean(pipe['bounds'],axis=0)[:2],[0,0],atol=1e-6)

    def test_absent_tower_keeps_its_costs_and_no_geometry(self):
        js=r'''
const fs=require('fs'),vm=require('vm');class El{constructor(){this.children=[];this.style={};this.dataset={};}setAttribute(){}replaceChildren(){this.children=[];}append(...x){this.children.push(...x);}}
const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,new El());return nodes.get(id);};
const scope={console,$,matchMedia:()=>({matches:false}),localStorage:{setItem(){}},f:(n,d)=>n.toFixed(d)};vm.createContext(scope);
for(const file of ['ifc_viewer','cost_dashboard','cost_preview'])vm.runInContext(fs.readFileSync('assets/'+file+'.js','utf8'),scope);
scope.model=JSON.parse(fs.readFileSync('data/ifc_80kw_mesh.json'));scope.costs=JSON.parse(fs.readFileSync('data/cost_reference_snapshot.json'));
vm.runInContext(`IFCView.data=model;IFCView.offer='IFC';CostView.data=costs;renderCostDashboard=()=>{};
const inputs=model.layers.map(l=>({dataset:{layer:l.name},checked:true,onchange(){notifyIfcLayerCosts();}}));$('ifc-layers').querySelectorAll=()=>inputs;
applyCostDockGroups(['tower']);
if(!costChartRows().length||costChartRows().some(r=>turbineLayerGroup(costLayer(r))!=='tower'))throw Error('tower costs lost');
if(costPreviewProducts(model,CostView,'IFC').length)throw Error('absent tower geometry invented');
if(costSectionTitle()!=='Costos de la torre')throw Error('cost title');
applyCostDockGroups(['rotor','tower']);if(costDockGroups().join()!=='rotor,tower'||costPreviewProducts(model,CostView,'IFC').length!==378)throw Error('combined budget/geometry scope');
if(modelWeightGroups(model.meshes,'IFC').some(g=>g.totalKg!==null))throw Error('historic mass carried into new model');`,scope);
'''
        result=subprocess.run(['node','-e',js],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
