"""Regression against the supplied HTML's original JavaScript, at a 30 rpm cap."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qblade_reference import reference_point, reference_operation, ReferenceDomainError, bounded_interp, initialize_source


class ReferenceTests(unittest.TestCase):
    def test_fresh_session_starts_with_qblade_geometry(self):
        state={}
        initialize_source(state)
        self.assertEqual(state['aerodynamic_source'],'QBlade · V80 (HTML)')
        self.assertEqual((state['rotor_d'],state['rotor_h'],state['rotor_n'],state['rotor_c']),(12.,16.,3,1.))
        self.assertEqual(state['wind_min'],4.)
        self.assertEqual(state['wind_max'],10.)
        self.assertTrue(state['apply_rotor_rpm_limit'])
        self.assertEqual(state['rotor_rpm_limit_value'],30.)

    def test_existing_selection_and_parameters_survive_reruns(self):
        state={'aerodynamic_source':'Modelo paramétrico','rotor_d':17.,'rotor_c':1.6}
        expected=dict(state)
        initialize_source(state)
        self.assertEqual(state,expected)
        state={'aerodynamic_source':'QBlade · V80 (HTML)','rotor_c':1.4,'reference_config':'3x1.4'}
        expected=dict(state)
        initialize_source(state)
        self.assertEqual(state,expected)

    def test_original_operating_points(self):
        points=json.loads(Path(__file__).with_name('qblade_original_points.json').read_text())
        for p in points:
            with self.subTest(configuration=p['id'],wind=p['V']):
                n,c=p['id'].split('x')
                actual=reference_point(int(n),float(c),p['V'],30)
                for key in ('rpm','P','Cp','T'):
                    self.assertAlmostEqual(actual[key],p[key],places=8)
                omega=actual['rpm']*np.pi/30
                self.assertAlmostEqual(actual['T']*omega,actual['P']*1000,places=8)
                self.assertAlmostEqual(actual['P']*1000,.5*1.225*192*p['V']**3*actual['Cp'],places=8)

    def test_no_rpm_extrapolation(self):
        with self.assertRaises(ReferenceDomainError):
            reference_point(3,1,10,1)

    def test_unavailable_geometry_is_rejected(self):
        with self.assertRaises(ReferenceDomainError):
            reference_operation(11,16,3,1,0,False,1.225,30,4,10,15,True,False,False,False)

    def test_nominal_indicator_does_not_extend_curve(self):
        self.assertTrue(np.isnan(bounded_interp(12,[4,6,8,10],[1,2,3,4])))
        self.assertEqual(bounded_interp(6,[4,6,8,10],[1,2,3,4]),2)

    def test_unavailable_wind_is_rejected(self):
        with self.assertRaises(ReferenceDomainError):
            reference_point(3,1,12,30)

if __name__=='__main__':unittest.main()
