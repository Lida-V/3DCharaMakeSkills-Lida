"""Portable checks of the shape-key sweep numeric core; Blender runs stay outside this package."""
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
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_shape_key_sweep.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
SWEEP = None
if np is not None:
    spec = importlib.util.spec_from_file_location('portable_shape_key_sweep', SCRIPT)
    SWEEP = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(SWEEP)


def sheet(nx=9, ny=5, step=0.005):
    """A flat patch of skin in the XZ plane facing -Y, 40 mm x 20 mm."""
    points = np.array([(i * step, 0.0, j * step) for i in range(nx) for j in range(ny)])
    triangles = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d = i * ny + j, (i + 1) * ny + j, i * ny + j + 1, (i + 1) * ny + j + 1
            triangles += [(a, b, c), (c, b, d)]
    return points, np.array(triangles)


def plate(y, size=0.012, center=(0.02, 0.01)):
    """A small square partner (an eyeball seen as a plate) parallel to the skin at depth y."""
    cx, cz = center
    points = np.array([(cx - size, y, cz - size), (cx + size, y, cz - size), (cx - size, y, cz + size), (cx + size, y, cz + size)])
    return points, np.array([(0, 1, 2), (2, 1, 3)])


def run(offsets, recipe, crossing=None, accepted=None, **options):
    points, triangles = sheet()
    topology = SWEEP.Topology(points, triangles)
    name = '+'.join(key if value is None else '%s=%g' % (key, value) for key, value in recipe)
    return SWEEP.sweep(name, recipe, points, topology, offsets, crossing, options, 1000.0, accepted)


@unittest.skipIf(np is None, 'numpy is not installed')
class ShapeKeySweepCore(unittest.TestCase):
    def setUp(self):
        self.points, self.triangles = sheet()
        count = len(self.points)
        x, z = self.points[:, 0], self.points[:, 2]
        bump = np.exp(-(((x - 0.02) / 0.008) ** 2 + ((z - 0.01) / 0.006) ** 2))
        self.push = np.zeros((count, 3))
        self.push[:, 1] = 0.006 * bump                              # a smooth dent of 6 mm into the head
        self.fold = np.zeros((count, 3))
        self.fold[x > 0.021, 0] = -0.03                              # the right part slides back over the left part
        self.squash = np.zeros((count, 3))
        self.squash[:, 2] = -(z - 0.01) * 0.99                       # everything is pressed onto one line
        self.none = np.zeros((count, 3))

    def test_recipes_and_options(self):
        self.assertEqual(SWEEP.parse_recipe('happy+blink'), [('happy', None), ('blink', None)])
        self.assertEqual(SWEEP.parse_recipe('happy=1+blink'), [('happy', 1.0), ('blink', None)])
        for bad in ('a=1', '+a', ''):
            with self.assertRaises(ValueError):
                SWEEP.parse_recipe(bad)
        for bad in ({'steps': 1}, {'nope': 3}):
            with self.assertRaises(ValueError):
                SWEEP.resolve_options(bad)

    def test_a_smooth_key_passes_and_broken_keys_are_named_with_their_value(self):
        smooth = run({'dent': self.push}, [('dent', None)])
        self.assertEqual(smooth['problems'], [])
        self.assertAlmostEqual(smooth['max_move_mm'], 6.0, delta=0.05)
        self.assertGreater(smooth['moved_vertices'], 10)
        folded = run({'fold': self.fold}, [('fold', None)])
        self.assertGreater(folded['folds']['count'], 0)
        self.assertTrue(0.0 < folded['folds']['at'] <= 1.0)
        self.assertTrue(any('fold back' in p for p in folded['problems']))
        squashed = run({'squash': self.squash}, [('squash', None)])
        self.assertGreater(squashed['collapsed']['count'], 0)
        self.assertGreaterEqual(squashed['collapsed']['at'], 0.95)                # only near the full value
        self.assertEqual(run({'none': self.none}, [('none', None)])['problems'], ['the key moves nothing'])
        stretch = np.zeros_like(self.push)
        stretch[self.points[:, 0] > 0.021, 0] = 0.02                               # one column of edges grows five times
        self.assertTrue(any('stretches' in p for p in run({'s': stretch}, [('s', None)])['problems']))
        self.assertEqual(run({'s': stretch}, [('s', None)], stretch_limit=6.0, min_edge_mm=1.0)['problems'], [])
        self.assertEqual(run({'s': stretch}, [('s', None)], min_edge_mm=20.0)['stretch']['ratio'], 1.0)   # short edges left out

    def test_a_combination_can_break_where_single_keys_do_not(self):
        half = self.fold * 0.1                                                     # key a alone slides 3 mm: no fold yet
        offsets = {'a': half, 'b': half * 2.5}
        self.assertEqual(run(offsets, [('a', None)])['folds']['count'], 0)
        both = run(offsets, [('a', None), ('b', None)])
        self.assertGreater(both['folds']['count'], 0)
        held = run(offsets, [('b', 1.0), ('a', None)])
        self.assertEqual(held['keys'], ['b', 'a'])
        self.assertGreater(held['folds']['count'], 0)

    def test_new_crossing_spots_are_counted_against_the_resting_state(self):
        pen = SWEEP._penetration()
        partner_points, partner_triangles = plate(0.003)                           # 3 mm behind the skin

        def crossing(weights, points):
            pairs = pen.brute_pairs(points, self.triangles, partner_points, partner_triangles)
            return {'eye': SWEEP.crossing_spots(points, self.triangles, partner_points, partner_triangles, pairs)}
        record = run({'dent': self.push}, [('dent', None)], crossing)
        self.assertEqual(record['resting_crossing']['eye']['spots'], 0)
        self.assertEqual(record['new_crossing_spots']['eye']['spots'], 1)          # the dent goes through the plate
        self.assertGreater(record['new_crossing_spots']['eye']['at'], 0.5)         # only past half way
        self.assertTrue(any('crossing spots with eye' in p for p in record['problems']))
        shallow = run({'dent': self.push * 0.4}, [('dent', None)], crossing)
        self.assertEqual(shallow['problems'], [])

    def test_an_accepted_report_turns_known_values_into_a_baseline(self):
        first = run({'fold': self.fold}, [('fold', None)])
        self.assertTrue(first['problems'])
        again = run({'fold': self.fold}, [('fold', None)], accepted=first)
        self.assertEqual(again['problems'], [])
        self.assertTrue(again['compared_with_accepted'])
        worse = run({'fold': self.fold * 1.6}, [('fold', None)], accepted=first)
        self.assertTrue(worse['problems'])

    def test_import_help_and_errors_need_no_blender_or_extra_files(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

        def call(command, work):
            return subprocess.run(command, cwd=work, capture_output=True, text=True, encoding='utf-8', env=env)
        with tempfile.TemporaryDirectory(prefix='lida-sweep-', dir=TEST_TEMP) as work:
            code = ('import importlib.util,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                    's=importlib.util.spec_from_file_location("sweep",p); m=importlib.util.module_from_spec(s); '
                    's.loader.exec_module(m); assert "bpy" not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())')
            self.assertEqual(call([sys.executable, '-B', '-c', code, str(SCRIPT)], work).returncode, 0)
            self.assertEqual(call([sys.executable, '-B', str(SCRIPT), 'sweep', '--help'], work).returncode, 0)
            work = Path(work)
            blend = work / 'model.blend'
            blend.write_bytes(b'BLENDER')
            existing = work / 'old.json'
            existing.write_text('{}', encoding='utf-8')
            base = [sys.executable, '-B', str(SCRIPT), 'sweep', '--input', str(blend), '--object', 'Face', '--report']
            self.assertEqual(call(base + [str(existing)], work).returncode, 1)
            self.assertEqual(existing.read_text(encoding='utf-8'), '{}')          # existing output is kept
            self.assertEqual(call(base + [str(work / 'new.json')], work).returncode, 1)   # no Blender here: an error report
            self.assertEqual(json.loads((work / 'new.json').read_text(encoding='utf-8'))['status'], 'error')
            self.assertEqual(blend.read_bytes(), b'BLENDER')


class ShapeKeySweepPackaging(unittest.TestCase):
    def test_script_declares_gpl_is_ascii_and_registers_nothing(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        for word in ('register_class', 'bpy.app.handlers', 'save_mainfile', 'save_as_mainfile', '.value ='):
            self.assertNotIn(word, text)                                           # key values in the file are never set


if __name__ == '__main__':
    unittest.main()
