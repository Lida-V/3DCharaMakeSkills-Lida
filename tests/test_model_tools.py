"""Portable regression checks; Blender integration fixtures remain outside this package."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_model_tools.py'
spec = importlib.util.spec_from_file_location('portable_model_tools', SCRIPT)
TOOLS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TOOLS)
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))


def snapshot():
    component = {'count': 4, 'sha256': 'a' * 64}
    return {'schema': TOOLS.SNAPSHOT_SCHEMA,
            'source': {'name': 'fixture.blend', 'sha256': 'b' * 64}, 'rig': 'Rig',
            'meshes': {'Body': {'coordinates': deepcopy(component), 'topology': deepcopy(component),
                                'uv': {'Main': deepcopy(component)},
                                'weights': {'status': 'captured', 'deform_bones': ['Bone'], **deepcopy(component)},
                                'shape_keys': {'Basis': {'relative_key': 'Basis', 'is_basis': True, **deepcopy(component)}},
                                'material_slots': deepcopy(component)}}}


class ModelToolChecks(unittest.TestCase):
    def setUp(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)

    def test_import_and_help_need_no_blender_or_file_writes(self):
        with tempfile.TemporaryDirectory(prefix='lida-model-import-', dir=TEST_TEMP) as work:
            code = ('import importlib.util,sys,pathlib; '
                    'p=pathlib.Path(sys.argv[1]); '
                    's=importlib.util.spec_from_file_location("model_helpers",p); '
                    'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                    'assert "bpy" not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())')
            env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
            proc = subprocess.run([sys.executable, '-B', '-c', code, str(SCRIPT)], cwd=work,
                                  capture_output=True, text=True, encoding='utf-8', env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = subprocess.run([sys.executable, '-B', str(SCRIPT), '--help'], cwd=work,
                                  capture_output=True, text=True, encoding='utf-8', env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(list(Path(work).iterdir()), [])

    def test_file_sha_is_provenance_not_mesh_change(self):
        left = snapshot()
        right = deepcopy(left)
        right['source'] = {'name': 'saved-again.blend', 'sha256': 'c' * 64}
        report = TOOLS.compare_snapshots(left, right)
        self.assertTrue(report['equal'])
        self.assertEqual(report['status'], 'equal_captured_fields')
        self.assertTrue(any('drivers' in value for value in report['unverified']))

    def test_equal_counts_do_not_hide_connectivity_change(self):
        left = snapshot()
        right = deepcopy(left)
        right['meshes']['Body']['topology']['sha256'] = 'd' * 64
        report = TOOLS.compare_snapshots(left, right)
        self.assertFalse(report['equal'])
        self.assertEqual([(r['mesh'], r['field']) for r in report['differences']], [('Body', 'topology')])

    def test_missing_and_added_meshes_are_reported(self):
        left = snapshot()
        right = deepcopy(left)
        right['meshes']['Cloth'] = right['meshes'].pop('Body')
        report = TOOLS.compare_snapshots(left, right)
        self.assertEqual({(r['mesh'], r['change']) for r in report['differences']},
                         {('Body', 'removed'), ('Cloth', 'added')})

    def test_unverified_weights_remain_unverified_when_equal(self):
        item = snapshot()
        item['rig'] = None
        item['meshes']['Body']['weights'] = {'status': 'not_verified', 'reason': 'No explicit rig'}
        report = TOOLS.compare_snapshots(item, deepcopy(item))
        self.assertTrue(report['equal'])
        self.assertTrue(any('without an explicit rig' in value for value in report['unverified']))

    def test_corrupt_snapshot_is_rejected_before_comparison(self):
        malformed = []
        item = snapshot(); del item['meshes']['Body']['uv']; malformed.append(item)
        item = snapshot(); item['meshes']['Body']['coordinates']['count'] = True; malformed.append(item)
        item = snapshot(); item['meshes']['Body']['topology']['sha256'] = 'z' * 64; malformed.append(item)
        item = snapshot(); item['meshes']['Body']['shape_keys']['Basis']['count'] = 3; malformed.append(item)
        item = snapshot(); item['meshes']['Body']['weights']['count'] = 3; malformed.append(item)
        for index, item in enumerate(malformed):
            with self.subTest(case=index), self.assertRaises(ValueError):
                TOOLS.compare_snapshots(snapshot(), item)

    def test_compare_cli_can_run_without_blender(self):
        with tempfile.TemporaryDirectory(prefix='lida-model-compare-', dir=TEST_TEMP) as work:
            directory = Path(work)
            left = directory / 'left.json'
            right = directory / 'right.json'
            report = directory / 'difference.json'
            left.write_text(json.dumps(snapshot()), encoding='utf-8')
            changed = snapshot()
            changed['meshes']['Body']['coordinates']['sha256'] = 'e' * 64
            right.write_text(json.dumps(changed), encoding='utf-8')
            proc = subprocess.run([sys.executable, '-B', str(SCRIPT), 'compare', '--left', str(left),
                                  '--right', str(right), '--report', str(report)],
                                  capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'different')
            original = report.read_bytes()
            proc = subprocess.run([sys.executable, '-B', str(SCRIPT), 'compare', '--left', str(left),
                                  '--right', str(right), '--report', str(report)],
                                  capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(report.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
