"""Portable checks of the evidence manifest; it needs neither Blender nor numpy."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_evidence_manifest.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
spec = importlib.util.spec_from_file_location('portable_evidence_manifest', SCRIPT)
EVIDENCE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EVIDENCE)


class EvidenceManifest(unittest.TestCase):
    def setUp(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        self.holder = tempfile.TemporaryDirectory(prefix='lida-evidence-', dir=TEST_TEMP)
        self.work = Path(self.holder.name)
        (self.work / 'model').mkdir()
        (self.work / 'review').mkdir()
        self.model = self.work / 'model' / 'avatar.blend'
        self.sheet = self.work / 'review' / 'sheet.jpg'
        self.video = self.work / 'review' / 'turn.mp4'
        self.model.write_bytes(b'model version one')
        self.sheet.write_bytes(b'picture of version one')
        self.video.write_bytes(b'video of version one')
        self.manifest = self.work / 'review' / 'evidence.json'

    def tearDown(self):
        self.holder.cleanup()

    def record(self):
        data = EVIDENCE.build_manifest([self.model], [self.sheet, self.video], self.manifest, 'first look')
        self.manifest.write_text(json.dumps(data), encoding='utf-8')
        return data

    def test_record_stores_relative_paths_sizes_and_hashes(self):
        data = self.record()
        self.assertEqual(data['sources'][0]['path'], '../model/avatar.blend')
        self.assertEqual([m['path'] for m in data['media']], ['sheet.jpg', 'turn.mp4'])
        self.assertEqual(data['sources'][0]['bytes'], len(b'model version one'))
        self.assertEqual(len(data['media'][0]['sha256']), 64)
        self.assertNotIn(str(self.work), json.dumps(data))                         # no absolute path leaks
        self.assertNotIn(self.work.name, json.dumps(data))
        with self.assertRaises(ValueError):
            EVIDENCE.build_manifest([self.model], [self.model], self.manifest)
        with self.assertRaises(ValueError):
            EVIDENCE.build_manifest([self.work / 'none.blend'], [self.sheet], self.manifest)
        with self.assertRaises(ValueError):
            EVIDENCE.build_manifest([], [self.sheet], self.manifest)

    def test_verify_names_stale_changed_and_missing_files(self):
        data = self.record()
        fresh = EVIDENCE.verify_manifest(data, self.manifest)
        self.assertTrue(fresh['summary']['all_match'])
        self.assertEqual(fresh['summary']['states'], {'same': 3})
        self.model.write_bytes(b'model version two')                               # saved again under the same name
        stale = EVIDENCE.verify_manifest(data, self.manifest)
        self.assertEqual([m['state'] for m in stale['media']], ['stale', 'stale'])
        self.assertEqual(stale['sources'][0]['state'], 'changed')
        self.assertIn('Render the media again', stale['warnings'][0])
        self.model.write_bytes(b'model version one')                               # back to the recorded bytes
        self.sheet.write_bytes(b'another picture altogether')
        self.video.unlink()
        mixed = EVIDENCE.verify_manifest(data, self.manifest)
        self.assertEqual([m['state'] for m in mixed['media']], ['changed', 'missing'])
        self.assertEqual(mixed['sources'][0]['state'], 'same')
        with self.assertRaises(ValueError):
            EVIDENCE.verify_manifest({'schema': 'other'}, self.manifest)

    def test_a_moved_folder_still_verifies(self):
        data = self.record()
        moved = self.work.parent / (self.work.name + '-moved')
        self.work.rename(moved)
        try:
            self.assertTrue(EVIDENCE.verify_manifest(data, moved / 'review' / 'evidence.json')['summary']['all_match'])
        finally:
            moved.rename(self.work)

    def test_cli_exit_codes_and_existing_outputs(self):
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

        def run(*extra):
            return subprocess.run([sys.executable, '-B', str(SCRIPT), *extra], capture_output=True, text=True, encoding='utf-8', env=env)
        record = ['record', '--sources', str(self.model), '--media', str(self.sheet), str(self.video), '--manifest', str(self.manifest)]
        self.assertEqual(run(*record).returncode, 0)
        self.assertEqual(run(*record).returncode, 1)                               # the manifest is never overwritten
        self.assertEqual(run('verify', '--manifest', str(self.manifest)).returncode, 0)
        self.model.write_bytes(b'model version two')
        report = self.work / 'review' / 'verify.json'
        self.assertEqual(run('verify', '--manifest', str(self.manifest), '--report', str(report)).returncode, 2)
        self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['summary']['states'], {'changed': 1, 'stale': 2})
        self.assertEqual(run('verify', '--manifest', str(self.work / 'none.json')).returncode, 1)
        self.assertEqual(self.sheet.read_bytes(), b'picture of version one')       # inputs are never touched

    def test_script_declares_gpl_is_ascii_and_imports_no_blender(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        self.assertNotIn('import bpy', text)
        self.assertNotIn('import numpy', text)


if __name__ == '__main__':
    unittest.main()
