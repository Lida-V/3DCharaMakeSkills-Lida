"""Portable checks of the accessory-fit numeric core; Blender runs stay outside this package."""
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
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_accessory_fit.py'
PANEL = ROOT / 'skills/lida-avatar-workflow/scripts/lida_accessory_fit_panel.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
FIT = None
if np is not None:
    spec = importlib.util.spec_from_file_location('portable_accessory_fit', SCRIPT)
    FIT = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(FIT)


def ellipse_cast(a, b, center=(0.0, 0.0, 0.0)):
    """Analytic partner: an elliptic cylinder along +Z with half axes a (X) and b (Y)."""
    def cast(origins, directions, limit):
        o = origins - np.asarray(center)
        qa = (directions[:, 0] / a) ** 2 + (directions[:, 1] / b) ** 2
        qb = 2 * (o[:, 0] * directions[:, 0] / a ** 2 + o[:, 1] * directions[:, 1] / b ** 2)
        qc = (o[:, 0] / a) ** 2 + (o[:, 1] / b) ** 2 - 1
        disc = qb * qb - 4 * qa * qc
        t = np.where(disc >= 0, (-qb - np.sqrt(np.maximum(disc, 0))) / (2 * qa), np.nan)
        t = np.where((t >= 0) & (t <= limit), t, np.nan)
        return t, np.zeros(len(t), bool)
    return cast


def ring_points(radius, thickness=0.004, height=0.012, span=(-180.0, 180.0), count=720, seed=7):
    rng = np.random.default_rng(seed)
    theta = np.radians(rng.uniform(span[0], span[1], count * 6))
    r = radius + rng.uniform(0, thickness, len(theta))
    z = rng.uniform(0, height, len(theta))
    return np.column_stack([-r * np.sin(theta), -r * np.cos(theta), z])   # azimuth 0 faces -Y


@unittest.skipIf(np is None, 'numpy is not installed')
class AccessoryFitCore(unittest.TestCase):
    frame = None

    def setUp(self):
        self.frame = FIT.ring_frame((0, 0, 1))

    def run_fit(self, points, cast, **options):
        return FIT.analyse(points, cast, self.frame, np.zeros(3), options, fit=True)

    def test_ring_coordinates_round_trip(self):
        frame = FIT.ring_frame((0.0, 0.2588, 0.9659))
        for vector in frame:
            self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=9)
        self.assertAlmostEqual(float(frame[0] @ frame[2]), 0.0, places=9)
        points = np.random.default_rng(1).normal(size=(50, 3))
        center = np.array([0.1, -0.2, 0.3])
        back = FIT.from_ring(*FIT.to_ring(points, center, frame), center, frame)
        self.assertLess(float(np.abs(back - points).max()), 1e-12)

    def test_outline_encloses_the_partner(self):
        outline = FIT.build_outline(ellipse_cast(0.04, 0.03), np.zeros(3), self.frame, 0.0, 0.02, 0.1)
        theta = np.linspace(-np.pi, np.pi, 200, endpoint=False)
        true = 1.0 / np.sqrt((np.sin(theta) / 0.04) ** 2 + (np.cos(theta) / 0.03) ** 2)
        got = outline.sample(theta, np.full(200, 0.01))
        self.assertGreaterEqual(float((got - true).min()), -1e-6)        # never inside the real surface
        self.assertLess(float((got - true).max()), 0.0008)

    def test_closed_ring_reaches_target_gap_without_axial_change(self):
        points = ring_points(0.036)                                       # inside the ellipse along X, loose along Y
        fitted, report = self.run_fit(points, ellipse_cast(0.04, 0.03), gap_mm=1.0, stretch_limit=1.0)
        self.assertTrue(report['frame']['closed_ring'])
        self.assertGreater(report['before']['all_points_inside_ratio'], 0.2)
        self.assertEqual(report['after']['all_points_inside_ratio'], 0.0)
        self.assertLess(float(np.abs(fitted[:, 2] - points[:, 2]).max()), 1e-12)
        before = np.arctan2(points[:, 0], -points[:, 1])
        after = np.arctan2(fitted[:, 0], -fitted[:, 1])
        self.assertLess(float(np.abs(np.angle(np.exp(1j * (after - before)))).max()), 1e-9)
        for row in report['after']['per_azimuth_band']:
            self.assertGreater(row['min_mm'], 0.3)
            self.assertLess(row['median_mm'], 4.0)

    def test_open_arc_is_detected_and_upper_part_is_only_pushed_out(self):
        base = ring_points(0.05, span=(-100.0, 100.0), height=0.01)       # band clear of a 0.04 cylinder
        spikes = ring_points(0.036, thickness=0.002, span=(-100.0, 100.0), count=200, seed=3)
        spikes[:, 2] += 0.02                                              # upper part leaning into the partner
        points = np.vstack([base, spikes])
        fitted, report = self.run_fit(points, ellipse_cast(0.04, 0.04), gap_mm=10.0, band_axial=0.3, stretch_limit=1.0)
        self.assertFalse(report['frame']['closed_ring'])
        self.assertAlmostEqual(report['frame']['arc_span_deg'], 200.0, delta=10.0)
        self.assertEqual(report['after']['all_points_inside_ratio'], 0.0)
        low = points[:, 2] < 0.012
        r0, r1 = np.hypot(points[:, 0], points[:, 1]), np.hypot(fitted[:, 0], fitted[:, 1])
        self.assertLess(float(np.abs(r1[low] - r0[low]).max()), 0.0005)   # band already at the target: stays
        self.assertGreater(float((r1[~low] - r0[~low]).min()), 0.003)     # the leaning part moves out

    def test_push_only_leaves_a_loose_ring_alone(self):
        points = ring_points(0.05)
        fitted, report = self.run_fit(points, ellipse_cast(0.04, 0.04), push_only=True)
        self.assertLess(report['move']['max_mm'], 1e-6)
        pulled, report = self.run_fit(points, ellipse_cast(0.04, 0.04), stretch_limit=1.0)
        self.assertGreater(report['move']['max_mm'], 5.0)                 # default pulls the band to the gap

    def test_small_islands_move_rigidly(self):
        ring = ring_points(0.037, count=400)
        pearl = np.array([[0.0, -0.0385, 0.02], [0.002, -0.0385, 0.02], [0.0, -0.0365, 0.02], [0.0, -0.0385, 0.022]])
        points = np.vstack([ring, pearl])
        n = len(ring)
        edges = np.array([[n, n + 1], [n, n + 2], [n, n + 3], [n + 1, n + 2]])
        fitted, report = FIT.analyse(points, ellipse_cast(0.04, 0.04), self.frame, np.zeros(3),
                                     {'rigid_islands_mm': 6.0, 'stretch_limit': 1.0}, edges=edges, fit=True)
        self.assertGreaterEqual(report['move']['rigid_islands']['moved_rigidly'], 1)
        shift = fitted[n:] - points[n:]
        self.assertLess(float(np.abs(shift - shift[0]).max()), 1e-12)
        self.assertGreater(float(np.hypot(fitted[n:, 0], fitted[n:, 1]).min()), 0.04)

    def test_large_stretch_warns_and_refuses(self):
        points = ring_points(0.02)                                        # far too small for a 0.04 partner
        fitted, report = self.run_fit(points, ellipse_cast(0.04, 0.04))
        self.assertTrue(report['refused'])
        self.assertTrue(any('Refused' in text for text in report['warnings']))
        fitted, report = self.run_fit(points, ellipse_cast(0.04, 0.04), stretch_limit=2.0)
        self.assertFalse(report['refused'])
        self.assertTrue(any('stretched' in text for text in report['warnings']))

    def test_measure_reports_backface_and_miss_doubts(self):
        def doubtful(origins, directions, limit):
            return np.full(len(origins), 0.01), np.ones(len(origins), bool)
        _, report = FIT.analyse(ring_points(0.05), doubtful, self.frame, np.zeros(3), {})
        self.assertTrue(any('from behind' in text for text in report['warnings']))
        def empty(origins, directions, limit):
            return np.full(len(origins), np.nan), np.zeros(len(origins), bool)
        _, report = FIT.analyse(ring_points(0.05), empty, self.frame, np.zeros(3), {})
        self.assertTrue(any('hit nothing' in text for text in report['warnings']))
        self.assertNotIn('after', report)

    def test_invalid_options_are_rejected(self):
        for bad in ({'gap_mm': -1}, {'band_axial': 0}, {'unknown': 1}, {'backfaces': 'maybe'}, {'sectors': 3}):
            with self.assertRaises(ValueError):
                FIT.resolve_options(bad)

    def test_import_help_and_errors_need_no_blender_or_extra_files(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
        with tempfile.TemporaryDirectory(prefix='lida-accessory-', dir=TEST_TEMP) as work:
            code = ('import importlib.util,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                    's=importlib.util.spec_from_file_location("fit",p); m=importlib.util.module_from_spec(s); '
                    's.loader.exec_module(m); assert "bpy" not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())')
            proc = subprocess.run([sys.executable, '-B', '-c', code, str(SCRIPT)], cwd=work, capture_output=True,
                                  text=True, encoding='utf-8', env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = subprocess.run([sys.executable, '-B', str(SCRIPT), 'fit', '--help'], cwd=work, capture_output=True,
                                  text=True, encoding='utf-8', env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(list(Path(work).iterdir()), [])
            blend = Path(work) / 'model.blend'
            blend.write_bytes(b'BLENDER')
            existing = Path(work) / 'old.json'
            existing.write_text('{}', encoding='utf-8')
            base = [sys.executable, '-B', str(SCRIPT), 'measure', '--input', str(blend), '--accessory', 'A',
                    '--partners', 'B', '--axis', '0', '0', '1', '--report']
            proc = subprocess.run(base + [str(existing)], cwd=work, capture_output=True, text=True, encoding='utf-8', env=env)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(existing.read_text(encoding='utf-8'), '{}')          # existing output is kept
            report = Path(work) / 'new.json'
            proc = subprocess.run(base + [str(report)], cwd=work, capture_output=True, text=True, encoding='utf-8', env=env)
            self.assertEqual(proc.returncode, 1)                                  # no Blender here: an error report
            self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'error')
            self.assertEqual(blend.read_bytes(), b'BLENDER')


class AccessoryFitPackaging(unittest.TestCase):
    def test_scripts_declare_gpl_and_the_panel_only_registers_when_run(self):
        for path in (SCRIPT, PANEL):
            text = path.read_text(encoding='utf-8')
            self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
            text.encode('ascii')
        panel = PANEL.read_text(encoding='utf-8')
        self.assertIn('if __name__ == "__main__":\n    register()', panel)
        core = SCRIPT.read_text(encoding='utf-8')
        self.assertNotIn('register_class', core)
        self.assertNotIn('bpy.app.handlers', core)


if __name__ == '__main__':
    unittest.main()
