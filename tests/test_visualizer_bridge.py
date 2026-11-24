import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import visualizer_bridge as bridge

FIXTURES=json.loads(Path(__file__).with_name('html_model_fixtures.json').read_text())

class BridgeTests(unittest.TestCase):
    def update(self):
        return {'source':'qblade','config':'4x1.2','wind':8,'params':dict(FIXTURES[0]['params'],G=7.5)}

    def test_applies_validated_state_before_sidebar(self):
        state={'vawt_html_component':self.update()}
        with patch.object(bridge.st,'session_state',state):bridge.synchronize()
        self.assertEqual(state['aerodynamic_source'],'QBlade · V80 (HTML)')
        self.assertEqual(state['rotor_n'],4)
        self.assertEqual(state['rotor_c'],1.2)
        self.assertEqual(state['html_G'],7.5)
        self.assertFalse(state['html_auto_G'])
        self.assertEqual(state['visualizer_selected_wind'],8)

    def test_invalid_update_keeps_model_unchanged(self):
        update=self.update();update['params']['eta_elec']=1.5
        state={'vawt_html_component':update,'html_G':6}
        with patch.object(bridge.st,'session_state',state):bridge.synchronize()
        self.assertEqual(state['html_G'],6)
        self.assertIn('visualizer_sync_error',state)

    def test_rejects_unavailable_rpm(self):
        update=self.update();update['params']['rpm_limit']=1
        with self.assertRaises(ValueError):bridge.validate_update(update)

    def test_rejects_odd_poles(self):
        update=self.update();update['params']['poles_total']=7
        with self.assertRaises(ValueError):bridge.validate_update(update)

    @unittest.skipUnless(shutil.which('node'),'Node is required for HTML/Python numerical parity')
    def test_html_python_parity(self):
        subprocess.run([shutil.which('node'),str(Path(__file__).with_name('test_html_model.js'))],check=True)
