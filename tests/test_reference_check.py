"""Portable checks of the reference check before clean-up; the impact part needs neither Blender nor numpy."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_reference_check.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
spec = importlib.util.spec_from_file_location('portable_reference_check', SCRIPT)
REF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(REF)


class ReferenceCheck(unittest.TestCase):
    def setUp(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        self.holder = tempfile.TemporaryDirectory(prefix='lida-refs-', dir=TEST_TEMP)
        self.work = Path(self.holder.name)
        for folder in ('stage/work/v01', 'stage/tex', 'stage/scripts', 'final', 'notes'):
            (self.work / folder).mkdir(parents=True)
        (self.work / 'stage/work/v01/dance_pose_cache.npz').write_bytes(b'cache')
        (self.work / 'stage/work/v01/a.png').write_bytes(b'png')
        (self.work / 'stage/tex/T_Body_BaseColor.png').write_bytes(b'png')
        (self.work / 'final/model.blend').write_bytes(b'BLENDER')
        self.target = self.work / 'stage/work'

    def tearDown(self):
        self.holder.cleanup()

    def refs(self, *items):
        return {'schema': REF.REPORT_SCHEMA, 'command': 'blend-refs',
                'blends': [{'path': str(self.work / 'final/model.blend'), 'name': 'model.blend',
                            'external': [{'kind': 'image', 'name': name, 'raw': '//x', 'resolved': str(path), 'relative': True,
                                          'exists': True, 'packed': packed} for name, path, packed in items]}]}

    def test_a_kept_blend_reading_from_the_target_would_break(self):
        report = REF.analyse_impact([self.target], [self.refs(('in work', self.work / 'stage/work/v01/a.png', False),
                                                              ('in tex', self.work / 'stage/tex/T_Body_BaseColor.png', False),
                                                              ('packed', self.work / 'stage/work/v01/a.png', True))])
        self.assertEqual([b['name'] for b in report['would_break']], ['in work'])   # tex is outside, packed data travels with the blend
        self.assertFalse(report['summary']['safe'])
        safe = REF.analyse_impact([self.target], [self.refs(('in tex', self.work / 'stage/tex/T_Body_BaseColor.png', False))])
        self.assertTrue(safe['summary']['safe'])
        self.assertEqual(safe['warnings'], [])
        inside = self.refs(('in work', self.work / 'stage/work/v01/a.png', False))
        inside['blends'][0]['path'] = str(self.work / 'stage/work/old.blend')
        self.assertEqual(REF.analyse_impact([self.target], [inside])['would_break'], [])   # the blend goes away with the target

    def test_kept_scripts_that_mention_the_target_are_listed_with_lines(self):
        (self.work / 'stage/scripts/render.py').write_text('import numpy\nPOSE = D + "/work/v01/x.npz"\n', encoding='utf-8')
        (self.work / 'stage/scripts/run.sh').write_text('blender --python a.py -- "$D\\\\stage\\\\work\\\\v01"\n', encoding='utf-8')
        (self.work / 'notes/plan.md').write_text('reads dance_pose_cache.npz every run\n', encoding='utf-8')
        (self.work / 'notes/other.md').write_text('nothing here about the folder\n', encoding='utf-8')
        (self.work / 'stage/work/v01/self.py').write_text('"/work/v01/" inside the target itself\n', encoding='utf-8')
        report = REF.analyse_impact([self.work / 'stage/work/v01'], scan=[self.work / 'stage', self.work / 'notes'])
        paths = {(Path(m['file']).name, m['kind'], m['line']) for m in report['path_mentions']}
        self.assertEqual(paths, {('render.py', 'last two parts', 2), ('run.sh', 'last two parts', 1)})
        self.assertEqual([(Path(m['file']).name, m['kind']) for m in report['name_mentions']], [('plan.md', 'file name')])
        self.assertEqual(report['summary']['text_files_scanned'], 4)               # the file inside the target is not read
        self.assertEqual(len(report['warnings']), 2)
        clean = REF.analyse_impact([self.work / 'stage/work/v01'], scan=[self.work / 'notes/other.md'])
        self.assertTrue(clean['summary']['safe'])

    def test_bad_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            REF.analyse_impact([])
        with self.assertRaises(ValueError):
            REF.analyse_impact([self.work / 'nowhere'])
        with self.assertRaises(ValueError):
            REF.analyse_impact([self.target], [{'schema': 'other'}])
        with self.assertRaises(ValueError):
            REF.analyse_impact([self.target], scan=[self.work / 'nowhere'])

    def test_cli_exit_codes_and_nothing_is_touched(self):
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

        def run(*extra):
            return subprocess.run([sys.executable, '-B', str(SCRIPT), *extra], capture_output=True, text=True, encoding='utf-8', env=env)
        refs = self.work / 'refs.json'
        refs.write_text(json.dumps(self.refs(('in work', self.work / 'stage/work/v01/a.png', False))), encoding='utf-8')
        before = sorted(p.as_posix() for p in self.work.rglob('*'))
        self.assertEqual(run('impact', '--targets', str(self.target), '--refs', str(refs), '--report', str(self.work / 'r2.json')).returncode, 2)
        self.assertEqual(run('impact', '--targets', str(self.target), '--report', str(self.work / 'r0.json')).returncode, 0)
        self.assertEqual(run('impact', '--targets', str(self.target), '--report', str(self.work / 'r0.json')).returncode, 1)
        self.assertEqual(run('blend-refs', '--inputs', str(self.work / 'final/model.blend'), '--report', str(self.work / 'b.json')).returncode, 1)
        self.assertEqual(json.loads((self.work / 'b.json').read_text(encoding='utf-8'))['status'], 'error')   # no Blender here
        after = sorted(p.as_posix() for p in self.work.rglob('*'))
        self.assertEqual(set(after) - set(before), {(self.work / n).as_posix() for n in ('r2.json', 'r0.json', 'b.json')})
        self.assertEqual(json.loads((self.work / 'r2.json').read_text(encoding='utf-8'))['summary']['would_break'], 1)

    def test_script_declares_gpl_is_ascii_and_never_removes_files(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        for word in ('unlink(', 'rmtree', 'os.remove', 'shutil', 'save_mainfile', 'save_as_mainfile', '.rename('):
            self.assertNotIn(word, text)


if __name__ == '__main__':
    unittest.main()
