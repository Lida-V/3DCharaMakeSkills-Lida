"""Portable checks of the penetration-check numeric core; Blender runs stay outside this package."""
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
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_penetration_check.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
PEN = None
if np is not None:
    spec = importlib.util.spec_from_file_location('portable_penetration_check', SCRIPT)
    PEN = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PEN)

HALF = 0.05                                             # the solid partner is a cube of 100 mm


def ribbon(x0, x1, width=0.02, step=0.005, y=0.0007, z=0.0):
    """A flat strip along X (a lock of hair seen as a ribbon)."""
    xs = np.linspace(x0, x1, max(2, int(round((x1 - x0) / step)) + 1))
    ys = np.array([y - width / 2, y, y + width / 2])
    points = np.array([(a, b, z) for a in xs for b in ys])
    triangles = []
    for i in range(len(xs) - 1):
        for j in range(2):
            a, b, c, d = i * 3 + j, i * 3 + j + 1, (i + 1) * 3 + j, (i + 1) * 3 + j + 1
            triangles += [(a, c, b), (b, c, d)]
    return points, np.array(triangles)


def cube():
    points = np.array([(x, y, z) for x in (-HALF, HALF) for y in (-HALF, HALF) for z in (-HALF, HALF)])
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return points, np.array([t for a, b, c, d in quads for t in ((a, b, c), (a, c, d))])


def inside_cube(_name, points):
    margin = HALF - np.abs(points).max(1)
    return (margin > 0).astype(float), np.abs(margin)


def all_seen(points):
    return np.ones((len(points), 48), bool)


def none_seen(points):
    return np.zeros((len(points), 48), bool)


def contacts(strips, visible=all_seen, allowed=False, **options):
    parts = {name: mesh for name, mesh in strips.items()}
    box = cube()
    partners = {'cube': (box[0], box[1], 'solid', allowed)}
    overlap = lambda part, partner: PEN.brute_pairs(*parts[part], box[0], box[1])
    report, marks = PEN.analyse_contacts(parts, partners, overlap, inside_cube, visible, options)
    report.update({'schema': PEN.REPORT_SCHEMA, 'command': 'check'})
    return report, marks


def buried(x0, x1, visible=all_seen, **options):
    options.setdefault('levels', 1)
    info, items, marks = PEN.analyse_buried('strip', *ribbon(x0, x1), ['cube'], inside_cube, visible, options)
    return PEN.finish_advice([info], items, options, 1000.0), marks


@unittest.skipIf(np is None, 'numpy is not installed')
class PenetrationCore(unittest.TestCase):
    def test_triangle_pair_gives_the_exact_crossing_segment(self):
        a = np.array([(-1, -1, 0), (1, -1, 0), (0, 1, 0)], float)
        b = np.array([(0, -0.5, -1), (0, -0.5, 1), (0, 0.5, -1)], float)
        tri = np.array([[0, 1, 2]])
        segments = PEN.tri_tri_segments(a, tri, b, tri, [(0, 0)])
        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(float(np.linalg.norm(segments[0, 1] - segments[0, 0])), 0.5, places=9)
        self.assertLess(float(np.abs(segments[0][:, [0, 2]]).max()), 1e-12)        # on both planes
        apart = PEN.tri_tri_segments(a, tri, b + np.array([3.0, 0, 0]), tri, [(0, 0)])
        self.assertEqual(len(apart), 0)                                            # boxes may overlap, triangles do not

    def test_subdivide_weld_and_cluster(self):
        points = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], float)
        triangles = np.array([(0, 1, 2), (3, 4, 5)])
        welded, joined = PEN.weld(points, triangles, 1e-6)
        self.assertEqual(len(welded), 4)                                           # the seam is merged
        fine, split = PEN.subdivide(welded, joined)
        self.assertEqual(len(split), 8)
        area = np.linalg.norm(np.cross(fine[split[:, 1]] - fine[split[:, 0]], fine[split[:, 2]] - fine[split[:, 0]]), axis=1).sum() / 2
        self.assertAlmostEqual(float(area), 1.0, places=12)
        self.assertEqual(PEN.clean_triangles(welded, joined)[1], 4)                # a square has four open edges
        cloud = np.array([(0, 0, 0), (0.004, 0, 0), (0.008, 0, 0), (0.1, 0, 0), (0.103, 0, 0)])
        label = PEN.cluster_points(cloud, 0.005)
        self.assertEqual(len(set(label[:3])), 1)                                   # chained through the middle point
        self.assertEqual(len(set(label)), 2)

    def test_check_lists_entry_and_exit_of_a_strip_through_a_solid(self):
        report, marks = contacts({'strip': ribbon(-0.1013, 0.1013)})
        summary = report['summary']
        self.assertEqual(summary['spots'], 2)                                      # where it enters and where it leaves
        self.assertEqual(summary['visible_spots'], 2)
        self.assertAlmostEqual(summary['visible_curve_mm'], 40.0, delta=0.5)       # two cuts of the 20 mm width
        self.assertTrue(report['warnings'])
        self.assertGreater(report['pairs'][0]['deepest_mm'], 40.0)
        self.assertGreater(report['spots'][0]['depth_mm'], 40.0)
        self.assertEqual([s['id'] for s in report['spots']], [1, 2])
        self.assertEqual(sum(len(segments) for _, segments in marks) > 0, True)

    def test_hidden_or_allowed_crossings_are_not_counted_as_findings(self):
        hidden, _ = contacts({'strip': ribbon(-0.1013, 0.1013)}, visible=none_seen)
        self.assertEqual(hidden['summary']['visible_spots'], 0)
        self.assertAlmostEqual(hidden['summary']['hidden_curve_mm'], 40.0, delta=0.5)
        self.assertEqual(hidden['warnings'], [])
        allowed, _ = contacts({'strip': ribbon(-0.1013, 0.1013)}, allowed=True)
        self.assertEqual(allowed['summary']['spots'], 0)
        self.assertEqual(allowed['summary']['allowed_spots'], 2)                   # still listed, apart
        self.assertEqual(allowed['warnings'], [])
        clear, _ = contacts({'strip': ribbon(0.0613, 0.2013)})
        self.assertEqual(clear['summary']['spots'], 0)

    def test_advice_follows_depth_extent_entries_and_visibility(self):
        cases = {'reroute_or_cut': (-0.1013, 0.1013),                              # through: two entries, deep
                 'trim': (-0.1013, 0.0),                                           # goes in and stays, 50 mm buried
                 'pull_tip': (-0.1013, -0.03),                                     # only a short tip, 20 mm deep
                 'push': (-0.1013, -0.047),                                        # 3 mm deep
                 'delete': (-0.02, 0.02)}                                          # the whole island is inside
        for expected, (x0, x1) in cases.items():
            with self.subTest(expected):
                report, marks = buried(x0, x1)
                self.assertEqual([i['advice'] for i in report['items']], [expected])
                self.assertEqual(report['summary'], {expected: 1})
                self.assertTrue(report['warnings'])
        through = buried(-0.1013, 0.1013)[0]['items'][0]
        self.assertEqual(through['entries'], 2)
        self.assertAlmostEqual(through['entry_width_mm'], 20.0, delta=0.6)
        self.assertAlmostEqual(through['depth_mm'], 49.3, delta=1.5)
        tip = buried(-0.1013, -0.03)[0]['items'][0]
        self.assertEqual(tip['entries'], 1)
        self.assertAlmostEqual(tip['depth_mm'], 20.0, delta=1.0)
        unseen, marks = buried(-0.1013, 0.0, visible=none_seen)
        self.assertEqual(unseen['items'][0]['advice'], 'leave')
        self.assertEqual(unseen['warnings'], [])                                   # nothing to do
        self.assertEqual(buried(0.0613, 0.2013)[0]['items'], [])

    def test_thresholds_are_options_and_small_flakes_are_reported(self):
        self.assertEqual(buried(-0.1013, -0.047, shallow_mm=1.0)[0]['items'][0]['advice'], 'pull_tip')
        self.assertEqual(buried(-0.1013, 0.0, tip_extent_mm=80.0)[0]['items'][0]['advice'], 'pull_tip')
        report, _ = buried(-0.0523, 0.02)                                          # 2 mm of the strip shows outside the solid
        self.assertEqual(sorted(i['advice'] for i in report['items']), ['delete', 'delete_scrap'])
        flake = [i for i in report['items'] if i['advice'] == 'delete_scrap'][0]
        self.assertLess(flake['scrap_area_cm2'], 1.5)
        coarse = buried(-0.1013, 0.1013)[0]
        self.assertEqual(coarse['notes'], [])                                      # 5 mm edges are not coarse
        for bad in ({'nope': 1}, {'levels': 9}, {'tolerance_mm': -1}, {'view_directions': 2}):
            with self.assertRaises(ValueError):
                PEN.resolve_options(bad)

    def test_compare_names_new_gone_and_grown_spots(self):
        before, _ = contacts({'strip': ribbon(-0.1013, 0.1013)})
        same = PEN.compare_reports(before, before)
        self.assertEqual(same['summary']['changes'], {'same': 2})
        self.assertEqual(same['warnings'], [])
        second = ribbon(-0.1013, 0.1013, y=0.0307)
        after, _ = contacts({'strip': ribbon(-0.1013, 0.1013), 'other': second})
        worse = PEN.compare_reports(before, after)
        self.assertEqual(worse['summary']['changes'], {'same': 2, 'new': 2})
        self.assertTrue(worse['warnings'])
        fixed, _ = contacts({'strip': ribbon(0.0613, 0.2013)})
        better = PEN.compare_reports(before, fixed)
        self.assertEqual(better['summary']['changes'], {'gone': 2})
        self.assertEqual(better['warnings'], [])
        wide, _ = contacts({'strip': ribbon(-0.1013, 0.1013, width=0.04)})
        grown = PEN.compare_reports(before, wide)
        self.assertEqual(grown['summary']['changes'], {'worse': 2})
        with self.assertRaises(ValueError):
            PEN.compare_reports({'schema': 'other'}, before)

    def test_import_help_compare_and_errors_need_no_blender_or_extra_files(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
        run = lambda command, work: subprocess.run(command, cwd=work, capture_output=True, text=True, encoding='utf-8', env=env)
        with tempfile.TemporaryDirectory(prefix='lida-penetration-', dir=TEST_TEMP) as work:
            code = ('import importlib.util,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                    's=importlib.util.spec_from_file_location("pen",p); m=importlib.util.module_from_spec(s); '
                    's.loader.exec_module(m); assert "bpy" not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())')
            self.assertEqual(run([sys.executable, '-B', '-c', code, str(SCRIPT)], work).returncode, 0)
            self.assertEqual(run([sys.executable, '-B', str(SCRIPT), 'advise', '--help'], work).returncode, 0)
            self.assertEqual(list(Path(work).iterdir()), [])
            work = Path(work)
            blend = work / 'model.blend'
            blend.write_bytes(b'BLENDER')
            existing = work / 'old.json'
            existing.write_text('{}', encoding='utf-8')
            base = [sys.executable, '-B', str(SCRIPT), 'check', '--input', str(blend), '--parts', 'A', '--solid', 'B', '--report']
            self.assertEqual(run(base + [str(existing)], work).returncode, 1)
            self.assertEqual(existing.read_text(encoding='utf-8'), '{}')          # existing output is kept
            self.assertEqual(run(base + [str(work / 'new.json')], work).returncode, 1)   # no Blender here: an error report
            self.assertEqual(json.loads((work / 'new.json').read_text(encoding='utf-8'))['status'], 'error')
            self.assertEqual(blend.read_bytes(), b'BLENDER')
            before, _ = contacts({'strip': ribbon(-0.1013, 0.1013)})
            after, _ = contacts({'strip': ribbon(-0.1013, 0.1013), 'other': ribbon(-0.1013, 0.1013, y=0.0307)})
            for name, report in (('before.json', before), ('after.json', after)):
                (work / name).write_text(json.dumps(report), encoding='utf-8')
            compare = [sys.executable, '-B', str(SCRIPT), 'compare', '--before', str(work / 'before.json'), '--after']
            self.assertEqual(run(compare + [str(work / 'before.json'), '--report', str(work / 'c0.json')], work).returncode, 0)
            self.assertEqual(run(compare + [str(work / 'after.json'), '--report', str(work / 'c2.json')], work).returncode, 2)
            result = json.loads((work / 'c2.json').read_text(encoding='utf-8'))
            self.assertEqual(result['command'], 'compare')
            self.assertEqual(result['summary']['changes']['new'], 2)


class PenetrationPackaging(unittest.TestCase):
    def test_script_declares_gpl_is_ascii_and_registers_nothing(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        for word in ('register_class', 'bpy.app.handlers', 'save_mainfile', 'save_as_mainfile'):
            self.assertNotIn(word, text)                                           # read-only on the model


if __name__ == '__main__':
    unittest.main()
