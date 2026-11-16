"""Portable checks of the hand-rig numeric core on a synthetic hand; Blender runs stay outside this package."""
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
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_hand_rig.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
HAND = None
if np is not None:
    spec = importlib.util.spec_from_file_location('portable_hand_rig', SCRIPT)
    HAND = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(HAND)

# A left hand in metres: wrist at the origin, fingers along +X (fanned a little), back of the hand +Z, thumb toward -Y.
FINGER_DESIGN = {   # name: (knuckle, PIP, DIP, tip, radius)
    'Index': ((0.085, -0.024, 0.0), (0.125, -0.030, 0.0), (0.150, -0.033, 0.0), (0.172, -0.036, 0.0), 0.0085),
    'Middle': ((0.088, -0.006, 0.0), (0.130, -0.006, 0.0), (0.158, -0.006, 0.0), (0.181, -0.006, 0.0), 0.0088),
    'Ring': ((0.093, 0.012, 0.0), (0.131, 0.017, 0.0), (0.157, 0.020, 0.0), (0.178, 0.023, 0.0), 0.0082),
    'Little': ((0.088, 0.028, 0.0), (0.118, 0.037, 0.0), (0.137, 0.043, 0.0), (0.155, 0.048, 0.0), 0.0072),
}
THUMB = ((0.020, -0.030, -0.006), (0.045, -0.050, -0.010), (0.070, -0.062, -0.012), (0.090, -0.070, -0.012), 0.010)


def _segment_distance(p, a, b):
    ab = np.asarray(b) - np.asarray(a)
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def hand_field(p):
    """Signed distance-like field (negative inside): palm slab plus five capsule fingers with joint creases."""
    palm_centre = np.array([0.045, 0.0, 0.0])
    q = (p - palm_centre) / np.array([0.060, 0.050, 0.016])
    field = (np.linalg.norm(q, axis=1) - 1.0) * 0.016
    for knuckle, pip, dip, tip, radius in list(FINGER_DESIGN.values()) + [THUMB]:
        points = [np.array(knuckle), np.array(pip), np.array(dip), np.array(tip)]
        lengths = [np.linalg.norm(points[k + 1] - points[k]) for k in range(3)]
        start = np.concatenate([[0.0], np.cumsum(lengths)])
        for k in range(3):
            d, t = _segment_distance(p, points[k], points[k + 1])
            u = (start[k] + t * lengths[k]) / start[-1]              # smooth taper along the whole finger
            r = radius * (1 - 0.3 * u)
            direction = (points[k + 1] - points[k]) / lengths[k]
            centre = points[k] + t[:, None] * (points[k + 1] - points[k])
            side = np.clip((p[:, 2] - centre[:, 2]) / np.maximum(d, 1e-9), -1, 1)   # +1 back of the hand, -1 palm
            for joint in points[1:3]:       # at PIP and DIP: a palm crease and a small knuckle on the back
                g = np.exp(-0.5 * (((p - joint) @ direction) / (0.6 * radius)) ** 2)
                r = r * (1 - 0.45 * g * np.clip(-side, 0, 1) + 0.2 * g * np.clip(side, 0, 1))
            field = np.minimum(field, d - r)
    return field


def marching_tetrahedra(field, low, high, step):
    """Triangles of the zero level of field on a grid (each cube split into six tetrahedra)."""
    axes = [np.arange(low[i], high[i] + step, step) for i in range(3)]
    nx, ny, nz = (len(a) for a in axes)
    grid = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
    values = field(grid)
    index = np.arange(len(grid)).reshape(nx, ny, nz)
    corners = [index[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k].ravel() for i, j, k in
               ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))]
    tets = []
    for a, b, c, d in ((0, 5, 1, 6), (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6)):
        tets.append(np.stack([corners[a], corners[b], corners[c], corners[d]], 1))
    tets = np.concatenate(tets)
    inside = values[tets] < 0
    tets = tets[(inside.sum(1) > 0) & (inside.sum(1) < 4)]
    inside = values[tets] < 0
    vertex_of = {}
    points = []

    def vertex(a, b):
        key = (a, b) if a < b else (b, a)
        if key not in vertex_of:
            va, vb = values[a], values[b]
            t = va / (va - vb)
            vertex_of[key] = len(points)
            points.append(grid[a] + t * (grid[b] - grid[a]))
        return vertex_of[key]

    triangles = []
    for tet, mask in zip(tets, inside):
        ins, outs = tet[mask], tet[~mask]
        if len(ins) == 1 or len(outs) == 1:
            one, rest = (ins[0], outs) if len(ins) == 1 else (outs[0], ins)
            triangles.append([vertex(one, rest[0]), vertex(one, rest[1]), vertex(one, rest[2])])
        else:
            a, b = ins
            c, d = outs
            ac, ad, bc, bd = vertex(a, c), vertex(a, d), vertex(b, c), vertex(b, d)
            triangles.append([ac, ad, bd])
            triangles.append([ac, bd, bc])
    return np.array(points), np.array(triangles, np.int64)


SYNTH = {}


def synthetic_hand():
    if not SYNTH:
        points, triangles = marching_tetrahedra(hand_field, (-0.030, -0.085, -0.030), (0.195, 0.055, 0.030), 0.0035)
        # add a short forearm so the wrist plane cuts skin
        SYNTH['points'], SYNTH['triangles'] = points, triangles
    return SYNTH['points'], SYNTH['triangles']


@unittest.skipIf(np is None, 'numpy is not installed')
class HandRigCoreTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.points, cls.triangles = synthetic_hand()
        cls.hand = HAND.measure_hand(cls.points, cls.triangles, np.zeros(3), np.array([1.0, 0, 0]), 'left')

    def test_fingers_are_split_by_connectivity_and_named_from_the_thumb_side(self):
        hand = self.hand
        self.assertEqual(sorted(hand['fingers']), sorted(HAND.FINGERS))
        np.testing.assert_allclose(hand['back'], [0, 0, 1], atol=0.15)
        for name in FINGER_DESIGN:
            tip = hand['fingers'][name]['joints'][3]
            self.assertLess(np.linalg.norm(tip[:2] - np.array(FINGER_DESIGN[name][3][:2])), 0.012, name)
        self.assertLess(hand['fingers']['Thumb']['joints'][3][1], -0.05)
        labels = hand['labels']
        for slot in range(1, 6):
            self.assertGreater((labels == slot).sum(), 20)

    def test_mirrored_right_hand_gives_the_same_back(self):
        mirrored = self.points * np.array([-1.0, 1.0, 1.0])
        right = HAND.measure_hand(mirrored, self.triangles[:, ::-1], np.zeros(3), np.array([-1.0, 0, 0]), 'right')
        np.testing.assert_allclose(right['back'], [0, 0, 1], atol=0.15)
        for name in HAND.FINGERS:
            left_joints = self.hand['fingers'][name]['joints'] * np.array([-1.0, 1.0, 1.0])
            np.testing.assert_allclose(right['fingers'][name]['joints'], left_joints, atol=0.004)

    def test_creases_place_pip_and_dip_near_the_design(self):
        for name, (knuckle, pip, dip, tip, radius) in FINGER_DESIGN.items():
            joints = self.hand['fingers'][name]['joints']
            methods = [m[0] for m in self.hand['fingers'][name]['methods']]
            self.assertEqual(methods[1:3], ['mesh', 'mesh'], name)
            self.assertLess(np.linalg.norm(joints[1][:2] - np.array(pip[:2])), 0.004, name + ' PIP')
            self.assertLess(np.linalg.norm(joints[2][:2] - np.array(dip[:2])), 0.004, name + ' DIP')
            self.assertLess(joints[0][0], 0.10, name + ' MCP lies inside the palm')

    def test_bend_axes_curl_toward_the_palm(self):
        axes = HAND.hinge_axes(self.hand)
        for name in HAND.FINGERS:
            joints = self.hand['fingers'][name]['joints']
            for k in range(3):
                d = joints[k + 1] - joints[k]
                moved = HAND.rotation(axes[name][k], 20.0) @ d
                self.assertLess(moved[2] - d[2], 0, '%s %d' % (name, k))
        straight = HAND.hinge_axes(self.hand, converge=0.0)
        tilted = HAND.hinge_axes(self.hand, converge=1.0)
        self.assertGreater(np.degrees(np.arccos(np.clip(abs(straight['Little'][2] @ tilted['Little'][2]), -1, 1))), 2.0)
        self.assertLess(np.degrees(np.arccos(np.clip(abs(straight['Middle'][2] @ tilted['Middle'][2]), -1, 1))), 2.0)

    def test_weights_sum_to_one_and_follow_each_finger(self):
        names, weights = HAND.hand_weights(self.hand)
        region = self.hand['mask']
        np.testing.assert_allclose(weights[region].sum(1), 1.0, atol=1e-9)
        labels = self.hand['labels']
        for slot, name in enumerate(HAND.FINGERS):
            verts = np.nonzero(labels == slot + 1)[0]
            own = [names.index(name + s) for s in HAND.SEGMENTS[name]]
            self.assertGreater(weights[verts][:, own].sum(1).mean(), 0.9, name)
            tip = verts[np.argmax(self.hand['distance'][verts])]
            self.assertGreater(weights[tip, own[2]], 0.9, name + ' tip follows the distal bone')

    def test_skinning_rest_is_identity_and_a_bend_keeps_lengths(self):
        names, weights = HAND.hand_weights(self.hand)
        joints = {n: self.hand['fingers'][n]['joints'] for n in HAND.FINGERS}
        model = HAND.HandModel(self.hand, joints, HAND.hinge_axes(self.hand), weights)
        np.testing.assert_allclose(model.pose('fist', 0.0), self.points, atol=1e-12)
        matrices = HAND.chain_matrices(self.hand, joints, model.axes, HAND.pose_angles('fist', 1.0))
        index = names.index('IndexDistal')
        a, b = joints['Index'][2], joints['Index'][3]
        moved = matrices[index][:3, :3] @ (b - a)
        self.assertAlmostEqual(np.linalg.norm(moved), np.linalg.norm(b - a), places=9)

    def test_check_reports_grips_and_a_forced_crossing(self):
        names, weights = HAND.hand_weights(self.hand)
        joints = {n: self.hand['fingers'][n]['joints'] for n in HAND.FINGERS}
        model = HAND.HandModel(self.hand, joints, HAND.hinge_axes(self.hand), weights)
        options = HAND.resolve_options({'steps': 2})
        result, warnings, _marks = HAND.check_poses(model, ['relax', 'spread'], options)
        self.assertEqual([p['pose'] for p in result['poses']], ['relax', 'spread'])
        moved = self.points.copy()
        middle = self.hand['labels'] == 3
        moved[middle] += np.array([0.0, -0.018, 0.0])                     # push the middle finger into the index
        groups, _stretched, _found = model.metrics(moved, options)
        self.assertIn('Index-Middle', groups)
        self.assertEqual(groups['Index-Middle']['kind'], 'fingers')

    def test_thumb_search_returns_a_roll_from_the_table(self):
        names, weights = HAND.hand_weights(self.hand)
        joints = {n: self.hand['fingers'][n]['joints'] for n in HAND.FINGERS}
        model = HAND.HandModel(self.hand, joints, HAND.hinge_axes(self.hand), weights)
        roll, rows = HAND.thumb_search(model, self.hand['options'], angles=(-20, 20))
        self.assertIn(roll, (-20.0, 20.0))
        self.assertEqual(len(rows), 2)

    def test_thumb_is_solved_as_one_arc_and_stays_out_of_the_fingers(self):
        names, weights = HAND.hand_weights(self.hand)
        joints = {n: self.hand['fingers'][n]['joints'] for n in HAND.FINGERS}
        model = HAND.HandModel(self.hand, joints, HAND.hinge_axes(self.hand), weights)
        table = HAND.fit_thumb_poses(model, ['relax', 'fist', 'pinch'])
        self.assertEqual(sorted(table), ['fist', 'pinch'])
        for row in table.values():
            self.assertLessEqual(row['crossing_mm'], 1.0)
            self.assertLessEqual(row['oppose'], HAND.THUMB_OPPOSE)
            if row['proximal'] > 0:                                   # fixed shares: the thumb folds as one arc
                self.assertAlmostEqual(row['distal'] / row['proximal'], HAND.THUMB_CURL[2] / HAND.THUMB_CURL[1], places=2)
        self.assertEqual(model.spec('fist')[0]['Thumb'], [table['fist'][k] for k in ('metacarpal', 'proximal', 'distal')])
        tip_rest = HAND._thumb_tip(model, model.points)
        tip_bent = HAND._thumb_tip(model, model.pose('fist', 1.0, thumb=HAND.thumb_from(1.0, 0.0)))
        self.assertGreater((tip_bent - tip_rest)[1], 0, 'the thumb curls across the palm, toward the little finger')
        self.assertLess((tip_bent - tip_rest)[2], 0, 'and toward the palm')

    def test_rigid_followers_take_the_bone_under_them_and_skip_far_pieces(self):
        names, weights = HAND.hand_weights(self.hand)
        tip = np.array(FINGER_DESIGN['Index'][3])
        nail = tip + np.array([[-0.010, -0.003, 0.007], [-0.002, -0.003, 0.007], [-0.002, 0.003, 0.007], [-0.010, 0.003, 0.007]])
        far = nail + np.array([0.0, 1.0, 0.0])
        points = np.concatenate([nail, far])
        triangles = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]])
        self.assertEqual(len(set(HAND.pieces(8, triangles))), 2)
        label, chosen, near = HAND.rigid_follower_bones(points, triangles, self.hand, weights)
        self.assertEqual(list(chosen.values()), [names.index('IndexDistal')])
        joints = {n: self.hand['fingers'][n]['joints'] for n in HAND.FINGERS}
        region = np.nonzero(self.hand['mask'])[0]
        bed = np.unique(region[HAND.nearest_k(nail, self.points[region])[0]])
        seated = weights.copy()
        seated[bed] = 0.0
        seated[bed, names.index('IndexDistal')] = 1.0
        rigid = np.zeros((4, len(names)))
        rigid[:, names.index('IndexDistal')] = 1.0
        model = HAND.HandModel(self.hand, joints, HAND.hinge_axes(self.hand), seated)
        self.assertLess(HAND.follower_drift(model, 'fist', nail, rigid).max(), 1e-9)
        loose = np.zeros((4, len(names)))
        loose[:, names.index('IndexProximal')] = 1.0                 # a nail left on the wrong bone slides
        self.assertGreater(HAND.follower_drift(model, 'fist', nail, loose).max(), 0.002)

    def test_proportions_inside_the_hand_and_against_the_body(self):
        inside = HAND.hand_proportions(self.hand)
        self.assertAlmostEqual(inside['hand_length_mm'], 181.0, delta=6.0)             # the middle fingertip of the design
        self.assertTrue(0.5 < inside['palm_share'] < 0.66, inside['palm_share'])
        self.assertAlmostEqual(inside['palm_share'], inside['palm_length_mm'] / inside['hand_length_mm'], places=2)
        self.assertGreater(inside['palm_width_mm'], 50.0)
        body = HAND.body_ratios(inside['hand_length_mm'], forearm_mm=250.0, head_mm=230.0, height_mm=1700.0)
        self.assertAlmostEqual(body['heads'], 1700.0 / 230.0, places=2)
        self.assertAlmostEqual(body['hand_per_forearm'], inside['hand_length_mm'] / 250.0, places=2)
        self.assertIsNone(body['hand_per_upper_arm'])
        options = HAND.resolve_options({})
        calm = dict(inside, palm_share=0.57, palm_length_per_width=1.25, thumb_reach=1.15)
        self.assertEqual(HAND.proportion_warnings(calm, body, options), [])
        long_palm = dict(calm, palm_share=0.67, palm_length_per_width=1.6, thumb_reach=0.96)
        found = HAND.proportion_warnings(long_palm, HAND.body_ratios(170.0, forearm_mm=170.0, head_mm=316.0), options)
        self.assertEqual(len(found), 4)
        self.assertIn('long palm', found[0])
        relaxed = HAND.resolve_options({'palm_share_max': 0.7, 'palm_aspect_max': 2.0, 'thumb_reach_min': 0.9, 'hand_forearm_max': 1.1})
        self.assertEqual(HAND.proportion_warnings(long_palm, HAND.body_ratios(170.0, forearm_mm=170.0, head_mm=316.0), relaxed), [])

    def test_hand_size_table_by_head_count_can_be_shifted_replaced_and_bypassed(self):
        human = HAND.table_expectation(HAND.PROPORTION_TABLE, 7.5, 0.15, head_mm=230.0)
        self.assertAlmostEqual(human['expected_hand_per_head'], HAND.HUMAN_REFERENCE['hand_per_height'] * 7.5, delta=0.02)
        self.assertAlmostEqual(human['expected_hand_mm'], human['expected_hand_per_head'] * 230.0, delta=0.1)
        between = HAND.table_expectation(HAND.PROPORTION_TABLE, 5.5, 0.15)
        self.assertTrue(0.42 < between['expected_hand_per_head'] < 0.46)
        self.assertEqual(len(between['basis']), 2)                    # both neighbouring rows are named
        self.assertTrue(HAND.table_expectation(HAND.PROPORTION_TABLE, 2.0, 0.15)['outside_table'])
        mine = [{'heads': 5, 'hand_per_head': 0.5, 'basis': 'my design sheet'}, {'heads': 7, 'hand_per_head': 0.6}]
        self.assertAlmostEqual(HAND.table_expectation(mine, 6.0, 0.1)['expected_hand_per_head'], 0.55, places=3)
        self.assertEqual(HAND.read_proportion_table({'rows': mine})[1]['basis'], 'not stated')
        for bad in ([], [{'heads': 5}], [{'heads': 5, 'hand_per_head': -1}], [{'heads': 5, 'hand_per_head': 0.4}] * 2):
            with self.assertRaises(ValueError):
                HAND.read_proportion_table(bad)
        options = HAND.resolve_options({})
        inside = dict(HAND.hand_proportions(self.hand), palm_share=0.57, palm_length_per_width=1.25, thumb_reach=1.15)
        body = HAND.body_ratios(170.0, head_mm=316.0)                  # 0.54 of the head
        tight = HAND.table_expectation(HAND.PROPORTION_TABLE, 5.3, 0.15, head_mm=316.0)
        found = HAND.proportion_warnings(dict(inside, hand_length_mm=170.0), body, options, tight)
        self.assertEqual(len(found), 1)
        self.assertIn('rule of thumb', found[0])
        loose = HAND.table_expectation(HAND.PROPORTION_TABLE, 5.3, 0.3, head_mm=316.0)
        self.assertEqual(HAND.proportion_warnings(dict(inside, hand_length_mm=170.0), body, options, loose), [])

    def test_too_few_fingers_and_bad_options_are_refused(self):
        with self.assertRaises(ValueError):
            HAND.resolve_options({'converge': -1})
        with self.assertRaises(ValueError):
            HAND.resolve_options({'unknown': 1})
        keep = self.points[:, 0] < 0.06                      # cut the fingers off: a mitten
        index = -np.ones(len(self.points), np.int64)
        index[keep] = np.arange(keep.sum())
        tris = self.triangles[keep[self.triangles].all(1)]
        with self.assertRaises(ValueError):
            HAND.measure_hand(self.points[keep], index[tris], np.zeros(3), np.array([1.0, 0, 0]), 'left')

    def test_import_help_and_errors_need_no_blender_or_extra_files(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
            env = dict(os.environ, PYTHONIOENCODING='utf-8')
            shown = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True, env=env)
            self.assertEqual(shown.returncode, 0)
            for command in ('measure', 'place', 'check'):
                self.assertIn(command, shown.stdout)
            blend = Path(folder) / 'model.blend'
            blend.write_bytes(b'BLENDER-v300')
            report = Path(folder) / 'r.json'
            ran = subprocess.run([sys.executable, str(SCRIPT), 'measure', '--input', str(blend), '--mesh', 'Body', '--side', 'left',
                                  '--wrist', '0', '0', '0', '--toward', '1', '0', '0', '--report', str(report)],
                                 capture_output=True, text=True, env=env)
            self.assertEqual(ran.returncode, 1)
            self.assertIn('Blender Python', json.loads(report.read_text(encoding='utf-8'))['message'])
            again = subprocess.run([sys.executable, str(SCRIPT), 'measure', '--input', str(blend), '--mesh', 'Body', '--side', 'left',
                                    '--wrist', '0', '0', '0', '--toward', '1', '0', '0', '--report', str(report)],
                                   capture_output=True, text=True, env=env)
            self.assertEqual(again.returncode, 1)
            self.assertIn('Refusing to overwrite', again.stderr)

    def test_script_declares_gpl_is_ascii_and_saves_only_a_new_copy(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        for word in ('register_class', 'bpy.app.handlers', 'save_mainfile('):
            self.assertNotIn(word, text)
        self.assertEqual(text.count('save_as_mainfile('), 1)
        self.assertIn('save_as_mainfile(filepath=str(temporary), check_existing=False, copy=True)', text)


if __name__ == '__main__':
    unittest.main()
