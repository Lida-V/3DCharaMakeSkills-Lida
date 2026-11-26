"""Portable checks of the spring-check numeric core; Blender runs stay outside this package."""
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import numpy as np
except ImportError:                                     # the core needs numpy; Blender bundles it
    np = None

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_spring_check.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
SPRING = None
if np is not None:
    spec = importlib.util.spec_from_file_location('portable_spring_check', SCRIPT)
    SPRING = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(SPRING)


def swing(frames=110, lag=0.0, sag=0.0):
    """A tip carried by a parent that swings in X during frames 30-60; the tip trails by lag and sags at rest."""
    rigid = np.zeros((frames, 3))
    for f in range(frames):
        rigid[f, 0] = 0.2 * math.sin((f - 30) / 30 * 2 * math.pi) if 30 <= f <= 60 else 0.0
    track = rigid.copy()
    track[1:, 0] = rigid[:-1, 0] * (1 - lag) + rigid[1:, 0] * lag if lag else rigid[1:, 0]
    track[:, 2] -= sag * np.minimum(np.arange(frames) / 10.0, 1.0)
    return track, rigid


@unittest.skipIf(SPRING is None, 'numpy is not installed')
class SpringCore(unittest.TestCase):
    def test_rigid_tip_has_no_lag_and_a_trailing_tip_does(self):
        track, rigid = swing()
        m = SPRING.chain_metrics(track, rigid)
        self.assertAlmostEqual(m['lag_max'], 0.0)
        self.assertGreater(m['moved_max'], 0.1)                 # it moves with the parent, which is not sway
        trailing, rigid = swing(lag=0.5)
        self.assertGreater(SPRING.chain_metrics(trailing, rigid)['lag_max'], 0.005)

    def test_drift_at_rest_and_the_end(self):
        track, rigid = swing(sag=0.02)
        m = SPRING.chain_metrics(track, rigid, rest_frames=30)
        self.assertAlmostEqual(m['drift_at_rest'], 0.02, places=6)
        self.assertAlmostEqual(m['lag_end'], 0.02, places=6)
        self.assertAlmostEqual(m['last_frame_motion'], 0.0)
        self.assertTrue(m['finite'])
        track[50, 1] = float('nan')
        self.assertFalse(SPRING.chain_metrics(track, rigid)['finite'])
        with self.assertRaises(ValueError):
            SPRING.chain_metrics(track[:, :2], rigid[:, :2])

    def test_motion_angles_follow_the_schedule(self):
        opt = dict(SPRING.DEFAULTS)
        self.assertEqual(SPRING.motion_angles(10, opt), {'arms': 0.0, 'hips': 0.0, 'head': 0.0, 'leg': 0.0})
        self.assertAlmostEqual(SPRING.motion_angles(50, opt)['arms'], opt['arms_down'])
        self.assertAlmostEqual(SPRING.motion_angles(100, opt)['leg'], opt['leg_forward'])
        self.assertAlmostEqual(SPRING.motion_angles(100, opt)['hips'], 0.0)

    def test_values_are_checked(self):
        self.assertEqual(SPRING.load_values({'kind': {'Hair_': [1.5, 0, 0.5, 0.02]}}), {'Hair_': [1.5, 0.0, 0.5, 0.02]})
        for bad in ({}, {'kind': {}}, {'kind': {'Hair_': [1, 2]}}, {'kind': {'Hair_': ['a', 1, 2, 3]}}):
            with self.assertRaises(ValueError):
                SPRING.load_values(bad)

    def test_import_help_and_errors_need_no_blender_or_extra_files(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

        def call(command, work):
            return subprocess.run(command, cwd=work, capture_output=True, text=True, encoding='utf-8', env=env)
        with tempfile.TemporaryDirectory(prefix='lida-spring-', dir=TEST_TEMP) as work:
            code = ('import importlib.util,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                    's=importlib.util.spec_from_file_location("s",p); m=importlib.util.module_from_spec(s); '
                    's.loader.exec_module(m); assert "bpy" not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())')
            self.assertEqual(call([sys.executable, '-B', '-c', code, str(SCRIPT)], work).returncode, 0)
            self.assertEqual(call([sys.executable, '-B', str(SCRIPT), 'check', '--help'], work).returncode, 0)
            work = Path(work)
            blend = work / 'model.blend'
            blend.write_bytes(b'BLENDER')
            existing = work / 'old.json'
            existing.write_text('{}', encoding='utf-8')
            base = [sys.executable, '-B', str(SCRIPT), 'check', '--input', str(blend), '--rig', 'Rig', '--report']
            self.assertEqual(call(base + [str(existing)], work).returncode, 1)
            self.assertEqual(existing.read_text(encoding='utf-8'), '{}')
            self.assertEqual(call(base + [str(work / 'new.json')], work).returncode, 1)
            self.assertEqual(json.loads((work / 'new.json').read_text(encoding='utf-8'))['status'], 'error')
            values = work / 'values.json'
            values.write_text('{"kind": {"Hair_": [1, 2]}}', encoding='utf-8')
            self.assertEqual(call(base + [str(work / 'bad.json'), '--values', str(values)], work).returncode, 1)
            self.assertIn('four numbers', json.loads((work / 'bad.json').read_text(encoding='utf-8'))['message'])
            self.assertEqual(blend.read_bytes(), b'BLENDER')


class SpringPackaging(unittest.TestCase):
    def test_script_declares_gpl_is_ascii_and_never_saves(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        for word in ('register_class', 'bpy.app.handlers', 'save_mainfile', 'save_as_mainfile'):
            self.assertNotIn(word, text)


if __name__ == '__main__':
    unittest.main()
