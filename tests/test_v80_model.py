import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

class V80ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((ROOT/'data/v80_v5_mesh.json').read_text())

    def test_v5_provenance_and_declared_configuration(self):
        m=self.model['metadata']
        self.assertEqual(hashlib.sha256((ROOT/'data/rotor_v80_v5_source.html').read_bytes()).hexdigest(),m['sha256'])
        self.assertEqual(m['revision'],'V5')
        self.assertEqual((m['diameter'],m['bladeHeight'],m['bladeProfile'],m['bladeMassKG'],m['gearRatioDeclared']),(14,14,'NACA 0018',400,10))
        self.assertEqual(m['defaultOffer'],'A')
        self.assertEqual((m['prototypes'],len(self.model['meshes'])),(38,86))
        self.assertEqual(m['omitted'],[])

    def test_offer_exclusivity_and_real_ring(self):
        for offer,expected,rings in [('A',68,0),('B',80,12)]:
            with self.subTest(offer=offer):
                active=[p for p in self.model['meshes'] if p['offer'] in ('AB',offer)]
                self.assertEqual(len(active),expected)
                self.assertEqual(sum(p['layer']=='Rotor: anillo' for p in active),rings)
                blades=[p for p in active if p['layer']=='Rotor: palas']
                self.assertEqual(len(blades),3)
                for blade in blades:self.assertAlmostEqual(blade['bounds'][1][2]-blade['bounds'][0][2],14)
                arms=[p for p in active if p['layer']=='Rotor: brazos']
                self.assertEqual(len(arms),6)
                self.assertTrue(all(('×8' if offer=='A' else '×6') in p['name'] for p in arms))

    def test_offer_specific_properties_are_preserved(self):
        gearbox=next(m for m in self.model['meshes'] if m['sourceId']=='Caja planetaria 1:10.0')
        self.assertIn('20.043',gearbox['propsByOffer']['A']['Costo unitario'])
        self.assertIn('19.789',gearbox['propsByOffer']['B']['Costo unitario'])

    def test_mesh_buffers_and_rotation_assignment(self):
        for mesh in self.model['meshes']:
            verts=np.frombuffer(base64.b64decode(mesh['vertices']),dtype='<f4')
            self.assertTrue(np.isfinite(verts).all())
            self.assertEqual(len(verts),mesh['vertexCount']*3)
            for group in mesh['groups']:
                indices=np.frombuffer(base64.b64decode(group['indices']),dtype='<u4')
                self.assertEqual(len(indices)%3,0)
                self.assertLess(indices.max(),mesh['vertexCount'])
            if mesh['sourceId'].startswith('T:') or mesh['name'].startswith('Generador'):
                self.assertFalse(mesh['rotating'])
            if mesh['layer']=='Rotor: palas':self.assertTrue(mesh['rotating'])
        self.assertTrue(next(m for m in self.model['meshes'] if m['sourceId']=='Acople flexible eje-caja')['rotating'])

    def test_safe_extraction_reproduces_embedded_instances(self):
        spec=importlib.util.spec_from_file_location('convert_v80_html',ROOT/'tools/convert_v80_html.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        rebuilt=module.convert(ROOT/'data/rotor_v80_v5_source.html')
        self.assertEqual(rebuilt['meshes'],self.model['meshes'])
        self.assertEqual(rebuilt['sourceCostSummaries'],self.model['sourceCostSummaries'])
        self.assertEqual({l['name'] for l in rebuilt['layers']},{l['name'] for l in self.model['layers']})
        self.assertIn('Pernos y fijaciones de torre',{l['name'] for l in rebuilt['layers']})
        self.assertIn('Fundación y morteros',{l['name'] for l in rebuilt['layers']})
