"""10 kW project isolates its source geometry, engine assumptions and nominal generator."""
import ast,base64,hashlib,json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from turbine10_view import default_inputs,engine_inputs,build_payload10,build_html10,validate_inputs


def engine_namespace():
    tree=ast.parse((ROOT/'app.py').read_text());nodes=[]
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef)):nodes.append(node)
        elif isinstance(node,ast.Assign):
            selected=any(isinstance(target,ast.Name) and (target.id.startswith('GDG_') or target.id=='GENERATORS') for target in node.targets)
            try:ast.literal_eval(node.value);selected=True
            except (ValueError,TypeError):pass
            if selected:nodes.append(node)
    scope={'__file__':str(ROOT/'app.py')};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/'app.py'),'exec'),scope);return scope

class Turbine10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((ROOT/'data/ifc_10kw_mesh.json').read_text());cls.engine=engine_namespace();cls.inputs=default_inputs(cls.model['metadata']);cls.generator=cls.engine['GENERATORS']['GDG_10k']

    def test_actual_ifc_geometry_and_counts(self):
        model=self.model;self.assertEqual(model['metadata']['meshes'],133);self.assertEqual(model['metadata']['assemblies'],26);self.assertEqual(model['metadata']['bladeCount'],3);self.assertEqual(model['metadata']['omitted'],[])
        self.assertEqual(len({m['guid'] for m in model['meshes']}),133)
        self.assertAlmostEqual(model['metadata']['diameterEnvelope'],5.679039,places=5);self.assertAlmostEqual(model['metadata']['bladeHeight'],4.014891,places=5)
        for mesh in model['meshes']:
            vertices=np.frombuffer(base64.b64decode(mesh['vertices']),dtype='<f4').reshape(-1,3);self.assertTrue(np.isfinite(vertices).all());np.testing.assert_allclose(vertices.min(0),mesh['bounds'][0],atol=1e-5);np.testing.assert_allclose(vertices.max(0),mesh['bounds'][1],atol=1e-5)
            for group in mesh['groups']:
                indices=np.frombuffer(base64.b64decode(group['indices']),dtype='<u4');self.assertEqual(len(indices)%3,0);self.assertLess(indices.max(),len(vertices));self.assertLess(group['material'],len(mesh['materials']))

    def test_engine_output_is_10kw_and_unknown_structural_results_are_masked(self):
        p=dict(self.inputs);self.assertEqual(p['chord'],.8);args=engine_inputs(p,self.generator);self.assertFalse(args['qblade_reference_mode']);self.assertEqual(args['P_nom_kW'],10);self.assertEqual(args['poles_total'],20)
        result=build_payload10(self.engine['compute_base_results'],self.generator,self.engine['build_lift_drag_polar'],p,self.model['metadata'])
        for case in result['cases']:
            self.assertTrue(all(0<=value<=10+1e-8 for value in case['electric']));self.assertTrue(all(e<=a+1e-8 for e,a in zip(case['electric'],case['aero'])));self.assertTrue(all(value is None for value in case['rootStress']));self.assertTrue(all(value is None for value in case['centrifugal']))
            np.testing.assert_allclose(np.array(case['torque'])*np.array(case['rpm'])*np.pi/30,np.array(case['aero'])*1000,atol=1e-7)
            self.assertGreaterEqual(case['aep'],0);self.assertLessEqual(case['cf'],1)
        self.assertEqual(p,self.inputs);self.assertEqual(result['source'],'parametric-10kw');self.assertEqual(len(result['cases']),3)
        html=build_html10(result,self.model)
        for i in range(1,6):self.assertIn('id="step10-'+str(i)+'"',html)
        self.assertNotIn('__PAYLOAD10__',html);self.assertNotIn('qblade_v80_reference',html);self.assertIn('SIN ESTUDIO QBlade PROPIO',html)

    def test_loads_require_explicit_activation(self):
        p=dict(self.inputs,mass_enabled=True,structural_enabled=True)
        result=build_payload10(self.engine['compute_base_results'],self.generator,self.engine['build_lift_drag_polar'],p,self.model['metadata'])
        self.assertTrue(result['structuralActive']);self.assertTrue(any(value>0 for value in result['cases'][0]['rootStress']))
        with self.assertRaises(ValueError):validate_inputs(dict(p,mass_enabled=False))
        with self.assertRaises(ValueError):validate_inputs(dict(p,diameter=float('nan')))
        with self.assertRaises(ValueError):validate_inputs(dict(p,blades=3.5))

if __name__=='__main__':unittest.main()
