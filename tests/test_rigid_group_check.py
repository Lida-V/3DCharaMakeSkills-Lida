"""Portable checks of the rigid-group numeric core; Blender runs stay outside this package."""
import importlib.util
import json
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
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_rigid_group_check.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
RIG = None
if np is not None:
    spec = importlib.util.spec_from_file_location('portable_rigid_group_check', SCRIPT)
    RIG = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(RIG)

NAMES = ['forearm', 'hand']                             # a wrist: the hand hangs below the forearm
PARENTS = [-1, 0]


def wrist():
    heads = np.array([(0.0, 0.0, 0.0), (0.2, 0.0, 0.0)])
    axes = np.stack([np.eye(3), np.eye(3)])
    return heads, axes


def ornament(count=60, seed=3):
    """Points of a small star sitting on the wrist joint."""
    rng = np.random.default_rng(seed)
    return np.array([0.2, 0.0, 0.02]) + rng.uniform(-0.012, 0.012, (count, 3))


def run(points, weights, **options):
    heads, axes = wrist()
    return RIG.analyse_group(points, weights, NAMES, PARENTS, heads, axes, options)


@unittest.skipIf(np is None, 'numpy is not installed')
class RigidGroupCore(unittest.TestCase):
    def test_kabsch_ignores_rigid_motion_and_measures_the_rest(self):
        points = np.random.default_rng(1).normal(size=(40, 3))
        turn = RIG.rotation_about((0.3, -0.2, 0.1), (1.0, 2.0, 0.5), 47.0)
        moved = points @ turn[:3, :3].T + turn[:3, 3]
        self.assertLess(float(RIG.kabsch_residual(points, moved)[0].max()), 1e-12)
        moved[0] += (0.0, 0.0, 0.01)
        self.assertGreater(float(RIG.kabsch_residual(points, moved)[0].max()), 0.005)
        self.assertEqual(RIG.descendants([-1, 0, 1, 0], 1), {1, 2})
        self.assertAlmostEqual(float(np.linalg.det(turn[:3, :3])), 1.0, places=12)

    def test_one_bone_is_rigid_and_two_parts_on_two_bones_split(self):
        points = ornament()
        on_hand = np.tile([0.0, 1.0], (len(points), 1))
        whole = run(points, on_hand)
        self.assertTrue(whole['rigid'])
        self.assertEqual(whole['weight_rows'], 1)
        self.assertLess(whole['largest_deviation_mm'], 1e-6)
        self.assertEqual(whole['mean_row'], {'hand': 1.0})
        split = on_hand.copy()
        split[: len(points) // 2] = [1.0, 0.0]            # the stone stays on the forearm, the star follows the hand
        broken = run(points, split)
        self.assertFalse(broken['rigid'])
        self.assertEqual(broken['weight_rows'], 2)
        self.assertGreater(broken['largest_deviation_mm'], 3.0)
        self.assertEqual(broken['worst_pose']['bone'], 'hand')
        self.assertEqual(broken['mean_row'], {'forearm': 0.5, 'hand': 0.5})
        self.assertIn('several weight rows', broken['note'])

    def test_one_shared_row_over_two_bones_keeps_together_but_shears(self):
        points = ornament()
        shared = run(points, np.tile([0.5, 0.5], (len(points), 1)))
        self.assertEqual(shared['weight_rows'], 1)
        self.assertIn('shears', shared['note'])
        self.assertGreater(shared['largest_deviation_mm'], 0.01)
        self.assertLess(shared['largest_deviation_mm'], 2.0)                       # far smaller than a split
        gentle = run(points, np.tile([0.08, 0.92], (len(points), 1)))
        self.assertLess(gentle['largest_deviation_mm'], shared['largest_deviation_mm'])
        self.assertTrue(run(points, np.tile([0.5, 0.5], (len(points), 1)), tolerance_mm=5.0)['rigid'])
        self.assertGreater(run(points, np.tile([0.5, 0.5], (len(points), 1)), angle=60.0)['largest_deviation_mm'],
                           shared['largest_deviation_mm'])

    def test_unweighted_vertices_and_bad_options_are_reported(self):
        points = ornament()
        weights = np.tile([0.0, 1.0], (len(points), 1))
        weights[3] = 0.0
        result = run(points, weights)
        self.assertEqual(result['unweighted_vertices'], 1)
        self.assertFalse(result['rigid'])
        unnormalised = run(points, np.tile([0.0, 0.4], (len(points), 1)))          # sums are normalised before the test
        self.assertTrue(unnormalised['rigid'])
        with self.assertRaises(ValueError):
            run(points, weights, angle=0.0)

    def test_import_help_and_errors_need_no_blender_or_extra_files(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

        def call(command, work):
            return subprocess.run(command, cwd=work, capture_output=True, text=True, encoding='utf-8', env=env)
        with tempfile.TemporaryDirectory(prefix='lida-rigid-', dir=TEST_TEMP) as work:
            code = ('import importlib.util,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                    's=importlib.util.spec_from_file_location("rig",p); m=importlib.util.module_from_spec(s); '
                    's.loader.exec_module(m); assert "bpy" not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())')
            self.assertEqual(call([sys.executable, '-B', '-c', code, str(SCRIPT)], work).returncode, 0)
            self.assertEqual(call([sys.executable, '-B', str(SCRIPT), 'check', '--help'], work).returncode, 0)
            work = Path(work)
            blend = work / 'model.blend'
            blend.write_bytes(b'BLENDER')
            existing = work / 'old.json'
            existing.write_text('{}', encoding='utf-8')
            base = [sys.executable, '-B', str(SCRIPT), 'check', '--input', str(blend), '--rig', 'Rig', '--group', 'A', 'B', '--report']
            self.assertEqual(call(base + [str(existing)], work).returncode, 1)
            self.assertEqual(existing.read_text(encoding='utf-8'), '{}')          # existing output is kept
            self.assertEqual(call(base + [str(work / 'new.json')], work).returncode, 1)   # no Blender here: an error report
            self.assertEqual(json.loads((work / 'new.json').read_text(encoding='utf-8'))['status'], 'error')
            self.assertEqual(blend.read_bytes(), b'BLENDER')
            # arguments read from a Windows program's output keep the CR of the line end
            crlf = [sys.executable, '-B', str(SCRIPT), 'check', '--input', str(blend), '--rig', 'Rig\r', '--group\r', 'A\r', 'B',
                    '--report', str(work / 'crlf.json')]
            result = call(crlf, work)
            self.assertEqual(result.returncode, 1)                                  # parsed; stops only for lack of Blender
            self.assertNotIn('required', result.stderr)
            self.assertEqual(json.loads((work / 'crlf.json').read_text(encoding='utf-8'))['status'], 'error')

    @unittest.skipIf(RIG is None, 'numpy is not installed')
    def test_clean_argv_drops_only_the_line_end(self):
        self.assertEqual(RIG._clean_argv(['--group\r', 'Gem\r\n', 'Set ting', 'a\rb']), ['--group', 'Gem', 'Set ting', 'a\rb'])


class RigidGroupPackaging(unittest.TestCase):
    def test_script_declares_gpl_is_ascii_and_registers_nothing(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        for word in ('register_class', 'bpy.app.handlers', 'save_mainfile', 'save_as_mainfile'):
            self.assertNotIn(word, text)


if __name__ == '__main__':
    unittest.main()
