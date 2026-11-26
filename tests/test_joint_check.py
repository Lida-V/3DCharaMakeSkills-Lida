"""Portable checks of the joint-check numeric core; Blender runs stay outside this package."""
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
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_joint_check.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
JOINT = None
if np is not None:
    spec = importlib.util.spec_from_file_location('portable_joint_check', SCRIPT)
    JOINT = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(JOINT)


def tube(radius=0.04, length=0.3, rings=31, around=16):
    """Points of a straight tube along +Z centred on the joint at z = 0, and its ring/row edges."""
    points, edges = [], []
    for i in range(rings):
        z = -length / 2 + length * i / (rings - 1)
        for j in range(around):
            a = 2 * math.pi * j / around
            points.append((radius * math.cos(a), radius * math.sin(a), z))
            here = i * around + j
            edges.append((here, i * around + (j + 1) % around))
            if i + 1 < rings:
                edges.append((here, here + around))
    return np.array(points), np.array(edges)


def bend(points, degrees, blend):
    """Linear blend skinning of the tube: the upper half stays, the lower half turns about X at the origin."""
    angle = math.radians(degrees)
    rot = np.array([[1, 0, 0], [0, math.cos(angle), -math.sin(angle)], [0, math.sin(angle), math.cos(angle)]])
    weight = np.clip((points[:, 2] + blend) / (2 * blend), 0, 1)[:, None] if blend > 0 else (points[:, 2] >= 0)[:, None] * 1.0
    return points * (1 - weight) + (points @ rot.T) * weight


@unittest.skipIf(JOINT is None, 'numpy is not installed')
class JointCore(unittest.TestCase):
    def test_collapse_grows_with_angle_and_a_half_turn_helper_keeps_volume(self):
        points, edges = tube()
        near, reach = JOINT.near_points(points, (0, 0, 0), 0.05)
        self.assertGreater(len(near), 0)
        ratios = []
        for degrees in (0, 90, 130):
            low, low_min = JOINT.collapse_ratio(points, bend(points, degrees, 0.03), (0, 0, 0), (0, 0, 0), near, 5.0)
            ratios.append(low)
        self.assertAlmostEqual(ratios[0], 1.0, places=6)
        self.assertGreater(ratios[1], ratios[2])                     # deeper bend, more collapse
        # the helper: the ring at the joint turns half way, so the joint ring keeps its radius
        upper, helper, lower = JOINT.band_weights(points[:, 2], np.ones(len(points)), 0.05)
        angle = math.radians(130)
        rot = lambda a: np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        posed = points * upper[:, None] + (points @ rot(angle / 2).T) * helper[:, None] + (points @ rot(angle).T) * lower[:, None]
        low_helper, _ = JOINT.collapse_ratio(points, posed, (0, 0, 0), (0, 0, 0), near, 5.0)
        self.assertGreater(low_helper, ratios[2])

    def test_near_points_widen_for_parts_far_from_the_centre(self):
        points, _ = tube(radius=0.09)
        near, reach = JOINT.near_points(points, (0, 0, 0), 0.05)
        self.assertGreater(reach, 0.05)
        self.assertGreater(len(near), 0)

    def test_edge_changes_flags_stretch_and_shrink_and_skips_tiny_edges(self):
        rest = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 0.0001)])
        posed = np.array([(0, 0, 0), (2, 0, 0), (0, 0.3, 0), (0, 0, 0.01)])
        ratio, usable, bad = JOINT.edge_changes(rest, posed, [(0, 1), (0, 2), (0, 3)], 1.6, 0.5, 0.001)
        self.assertEqual(list(bad), [True, True, False])
        self.assertFalse(usable[2])

    def test_band_weights_sum_and_ends(self):
        t = np.array([-0.1, -0.05, -0.02, 0.0, 0.02, 0.05, 0.1])
        upper, helper, lower = JOINT.band_weights(t, np.full(len(t), 0.8), 0.05)
        self.assertTrue(np.allclose(upper + helper + lower, 0.8))
        self.assertAlmostEqual(helper[3], 0.8)
        self.assertAlmostEqual(upper[0], 0.8)
        self.assertAlmostEqual(lower[-1], 0.8)
        self.assertEqual(float(lower[0]), 0.0)
        self.assertEqual(float(upper[-1]), 0.0)

    def test_axial_position_and_joint_parsing(self):
        t, radial = JOINT.axial_position([(0.03, 0, 0.1), (0, 0.02, -0.05)], (0, 0, 0), (0, 0, 1))
        self.assertTrue(np.allclose(t, [0.1, -0.05]))
        self.assertTrue(np.allclose(radial, [0.03, 0.02]))
        self.assertEqual(JOINT.parse_joint('Shin.L:80', 65), ('Shin.L', 80.0))
        self.assertEqual(JOINT.parse_joint('Shin.L', 65), ('Shin.L', 65.0))
        self.assertEqual(JOINT.parse_joint('Bone:Left', 65), ('Bone:Left', 65.0))
        with self.assertRaises(ValueError):
            JOINT.parse_joint('Shin.L:0', 65)
        self.assertEqual(JOINT.parse_check_joint('Forearm.L@z', 'x'), ('Forearm.L', 'z'))
        self.assertEqual(JOINT.parse_check_joint('Forearm.L', 'local-x'), ('Forearm.L', 'local-x'))
        with self.assertRaises(ValueError):
            JOINT.parse_check_joint('Forearm.L@w', 'x')

    def test_import_help_and_errors_need_no_blender_or_extra_files(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

        def call(command, work):
            return subprocess.run(command, cwd=work, capture_output=True, text=True, encoding='utf-8', env=env)
        with tempfile.TemporaryDirectory(prefix='lida-joint-', dir=TEST_TEMP) as work:
            code = ('import importlib.util,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                    's=importlib.util.spec_from_file_location("j",p); m=importlib.util.module_from_spec(s); '
                    's.loader.exec_module(m); assert "bpy" not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())')
            self.assertEqual(call([sys.executable, '-B', '-c', code, str(SCRIPT)], work).returncode, 0)
            for command in ('check', 'helpers'):
                self.assertEqual(call([sys.executable, '-B', str(SCRIPT), command, '--help'], work).returncode, 0)
            work = Path(work)
            blend = work / 'model.blend'
            blend.write_bytes(b'BLENDER')
            existing = work / 'old.json'
            existing.write_text('{}', encoding='utf-8')
            base = [sys.executable, '-B', str(SCRIPT), 'check', '--input', str(blend), '--rig', 'Rig', '--mesh', 'Body',
                    '--joint', 'Shin.L@x', '--report']
            self.assertEqual(call(base + [str(existing)], work).returncode, 1)
            self.assertEqual(existing.read_text(encoding='utf-8'), '{}')          # existing output is kept
            self.assertEqual(call(base + [str(work / 'new.json')], work).returncode, 1)   # no Blender here: an error report
            self.assertEqual(json.loads((work / 'new.json').read_text(encoding='utf-8'))['status'], 'error')
            helpers = [sys.executable, '-B', str(SCRIPT), 'helpers', '--input', str(blend), '--rig', 'Rig\r', '--mesh', 'Body',
                       '--joint\r', 'Shin.L:65', '--report', str(work / 'h.json'), '--output-blend', str(work / 'out.blend')]
            result = call(helpers, work)
            self.assertEqual(result.returncode, 1)                                  # parsed despite the CR; stops for lack of Blender
            self.assertNotIn('required', result.stderr)
            self.assertFalse((work / 'out.blend').exists())
            self.assertEqual(blend.read_bytes(), b'BLENDER')


class JointPackaging(unittest.TestCase):
    def test_script_declares_gpl_is_ascii_registers_nothing_and_writes_only_a_copy(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        for word in ('register_class', 'bpy.app.handlers', 'save_mainfile('):
            self.assertNotIn(word, text)
        self.assertEqual(text.count('save_as_mainfile('), 1)
        self.assertIn('save_as_mainfile(filepath=str(temporary), check_existing=False, copy=True)', text)


if __name__ == '__main__':
    unittest.main()
