"""Portable checks of the VRM file check; it needs neither Blender nor numpy."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/lida-avatar-workflow/scripts/lida_vrm_check.py'
TEST_TEMP = Path(os.environ.get('LIDA_DISTRIBUTION_TEST_TEMP', str(Path(tempfile.gettempdir()) / 'lida-distribution-tests')))
spec = importlib.util.spec_from_file_location('portable_vrm_check', SCRIPT)
VRM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VRM)


def png(width, height):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IEND', b'')


def good_document(image_bytes):
    bones = {name: {'node': index} for index, name in enumerate(VRM.REQUIRED_BONES)}
    count = len(bones)                                      # nodes: 15 bones, face mesh, two hair joints and an end
    nodes = [{'name': name} for name in bones] + [{'name': 'Face', 'mesh': 0}, {'name': 'hair0'}, {'name': 'hair1'}, {'name': 'hair_end'}]
    presets = {name: {'morphTargetBinds': [{'node': count, 'index': 0, 'weight': 1.0}]} for name in VRM.EXPECTED_EXPRESSIONS}
    presets['happy']['overrideBlink'] = 'blend'
    presets['lookUp'] = {}
    return {
        'asset': {'version': '2.0'}, 'extensionsUsed': ['VRMC_vrm', 'VRMC_springBone', 'VRMC_materials_mtoon'],
        'nodes': nodes,
        'accessors': [{'count': 300}, {'count': 100}],
        'meshes': [{'name': 'Face', 'primitives': [{'attributes': {'POSITION': 1, 'TEXCOORD_0': 1, 'JOINTS_0': 1, 'WEIGHTS_0': 1},
                                                    'indices': 0, 'targets': [{'POSITION': 1}]}]}],
        'materials': [{'name': 'Skin', 'extensions': {'VRMC_materials_mtoon': {'outlineWidthMode': 'screenCoordinates'}}}],
        'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': len(image_bytes)}],
        'images': [{'name': 'Skin', 'bufferView': 0, 'mimeType': 'image/png'}],
        'extensions': {
            'VRMC_vrm': {'specVersion': '1.0', 'meta': {'name': 'Test', 'authors': ['Lida'], 'licenseUrl': 'https://vrm.dev/licenses/1.0/'},
                         'humanoid': {'humanBones': bones}, 'expressions': {'preset': presets},
                         'lookAt': {'type': 'bone', 'offsetFromHeadBone': [0.0, 0.07, 0.06]},
                         'firstPerson': {'meshAnnotations': [{'node': count, 'type': 'auto'}]}},
            'VRMC_springBone': {
                'colliders': [{'node': 2, 'shape': {'sphere': {'offset': [0, 0, 0], 'radius': 0.08}}}],
                'colliderGroups': [{'name': 'Head', 'colliders': [0]}],
                'springs': [{'name': 'Hair', 'colliderGroups': [0], 'joints': [
                    {'node': count + 1, 'hitRadius': 0.02, 'gravityPower': 0.2, 'gravityDir': [0, -1, 0]},
                    {'node': count + 2, 'hitRadius': 0.02, 'gravityPower': 0.2, 'gravityDir': [0, -1, 0]},
                    {'node': count + 3}]}]}}}


def glb(document, binary):
    text = json.dumps(document).encode('utf-8')
    text += b' ' * (-len(text) % 4)
    binary += b'\x00' * (-len(binary) % 4)
    body = struct.pack('<I4s', len(text), b'JSON') + text + struct.pack('<I4s', len(binary), b'BIN\x00') + binary
    return b'glTF' + struct.pack('<II', 2, 12 + len(body)) + body


def codes(document, binary, **options):
    return VRM.check_document(document, binary, options)['summary']['codes']


class VrmCheck(unittest.TestCase):
    def setUp(self):
        self.image = png(1024, 512)
        self.good = good_document(self.image)

    def variant(self):
        return copy.deepcopy(self.good)

    def test_a_sound_file_has_no_findings_and_counts_are_read(self):
        document, binary = VRM.read_glb(glb(self.good, self.image))
        report = VRM.check_document(document, binary)
        self.assertEqual(report['summary']['codes'], [])
        self.assertEqual(report['vrm_version'], '1.0 (specVersion 1.0)')
        self.assertEqual(report['images'], {'count': 1, 'largest_side': 1024, 'bytes': len(self.image), 'over_limit': 0})
        self.assertEqual(report['meshes']['triangles'], 100)
        self.assertEqual(report['springs']['joints'], 3)
        self.assertEqual(report['materials']['mtoon'], 1)
        self.assertEqual(report['expressions']['overrides'], {'happy': {'overrideBlink': 'blend'}})
        self.assertEqual(report['expressions']['empty'], [])                      # lookUp is normally empty with bone gaze

    def test_each_silent_export_fault_is_named(self):
        cases = {}
        d = self.variant()
        d['materials'][0].pop('extensions')
        cases['mtoon_missing'] = d
        d = self.variant()
        for joint in d['extensions']['VRMC_springBone']['springs'][0]['joints'][:2]:
            joint['gravityDir'] = [0, 0, 1]
        cases['gravity_direction'] = d
        d = self.variant()
        for joint in d['extensions']['VRMC_springBone']['springs'][0]['joints']:
            joint.pop('hitRadius', None)
        cases['hit_radius_zero'] = d
        d = self.variant()
        d['extensions']['VRMC_springBone']['colliderGroups'][0]['colliders'] = []
        cases['group_empty'] = d
        d = self.variant()
        d['extensions']['VRMC_springBone']['springs'][0]['colliderGroups'] = [3]
        cases['spring_group'] = d
        d = self.variant()
        d['extensions']['VRMC_vrm']['lookAt']['offsetFromHeadBone'] = [0.0, 0.06, -0.07]
        cases['lookat_axis'] = d
        d = self.variant()
        d['extensions']['VRMC_vrm']['humanoid']['humanBones'].pop('leftFoot')
        cases['humanoid_missing'] = d
        d = self.variant()
        d['extensions']['VRMC_vrm']['expressions']['preset'].pop('blinkLeft')
        cases['expression_missing'] = d
        d = self.variant()
        d['extensions']['VRMC_vrm']['expressions']['preset']['aa']['morphTargetBinds'][0]['index'] = 5
        cases['bind_index'] = d
        d = self.variant()
        d['extensions']['VRMC_vrm']['expressions']['preset']['sad'] = {}
        cases['expression_empty'] = d
        d = self.variant()
        d['meshes'][0]['primitives'][0]['attributes'].pop('TEXCOORD_0')
        cases['uv_missing'] = d
        d = self.variant()
        d['meshes'][0]['primitives'][0]['attributes'].pop('WEIGHTS_0')
        cases['skin_incomplete'] = d
        d = self.variant()
        d['extensionsRequired'] = ['KHR_texture_basisu']
        cases['extension_required'] = d
        d = self.variant()
        d['materials'][0]['alphaMode'] = 'BLEND'
        d['materials'][0]['extensions']['VRMC_materials_mtoon']['transparentWithZWrite'] = True
        cases['blend_zwrite'] = d
        d = self.variant()
        d['extensions']['VRMC_vrm']['meta'].pop('licenseUrl')
        cases['meta_incomplete'] = d
        for code, document in cases.items():
            with self.subTest(code):
                extra = ['group_unused'] if code == 'spring_group' else []    # the real group is then unused too
                self.assertEqual(codes(document, self.image), sorted(extra + [code]))

    def test_image_size_format_and_options(self):
        big = png(4096, 4096)
        self.assertEqual(codes(self.good, big), ['image_large'])
        self.assertEqual(codes(self.good, big, max_texture=4096), [])
        self.assertEqual(VRM.image_size(b'\xff\xd8\xff\xe0\x00\x04\x00\x00\xff\xc0\x00\x11\x08\x00\x20\x00\x40\x03'), ('jpeg', 64, 32))
        self.assertEqual(codes(self.good, b'\xabKTX 20\xbb\r\n\x1a\n' + b'\x00' * 40), ['image_format'])
        plain = self.variant()
        plain['materials'][0].pop('extensions')
        self.assertEqual(codes(plain, self.image, expect_mtoon='ignore'), [])
        self.assertEqual(codes(self.good, self.image, expect_expressions=['aa', 'custom_one']), ['expression_missing'])
        gaze = self.variant()
        gaze['extensions']['VRMC_vrm']['lookAt']['type'] = 'expression'
        self.assertEqual(codes(gaze, self.image), ['expression_empty'])            # lookUp needs binds for expression gaze
        self.assertEqual(codes({'asset': {}}, b''), ['not_vrm'])
        with self.assertRaises(ValueError):
            VRM.check_document(self.good, self.image, {'expect_mtoon': 'maybe'})

    def test_legacy_files_and_broken_containers(self):
        legacy = {'extensions': {'VRM': {'materialProperties': [{'name': 'a', 'shader': 'VRM/MToon'}, {'name': 'b', 'shader': 'Standard'}],
                                         'secondaryAnimation': {'boneGroups': [{'gravityPower': 1, 'gravityDir': {'x': 0, 'y': 0, 'z': 1},
                                                                                'colliderGroups': [0], 'hitRadius': 0}]}}}}
        report = VRM.check_document(legacy, b'')
        self.assertEqual(report['vrm_version'], '0.x')
        self.assertEqual(report['summary']['codes'], ['gravity_direction', 'hit_radius_zero', 'mtoon_missing'])
        for broken in (b'', b'not a glb file at all', b'glTF' + struct.pack('<II', 1, 20) + b'\x00' * 8):
            with self.assertRaises(ValueError):
                VRM.read_glb(broken)

    def test_cli_writes_new_reports_only_and_never_touches_the_input(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

        def run(*extra):
            return subprocess.run([sys.executable, '-B', str(SCRIPT), 'check', *extra], capture_output=True, text=True,
                                  encoding='utf-8', env=env)
        with tempfile.TemporaryDirectory(prefix='lida-vrm-', dir=TEST_TEMP) as work:
            work = Path(work)
            good, bad = work / 'good.vrm', work / 'bad.vrm'
            good.write_bytes(glb(self.good, self.image))
            broken = self.variant()
            broken['materials'][0].pop('extensions')
            bad.write_bytes(glb(broken, self.image))
            before = good.read_bytes()
            self.assertEqual(run('--input', str(good), '--report', str(work / 'good.json')).returncode, 0)
            self.assertEqual(run('--input', str(bad), '--report', str(work / 'bad.json')).returncode, 2)
            self.assertEqual(run('--input', str(good), '--report', str(work / 'good.json')).returncode, 1)     # existing report is kept
            self.assertEqual(run('--input', str(work / 'none.vrm'), '--report', str(work / 'none.json')).returncode, 1)
            self.assertEqual(json.loads((work / 'none.json').read_text(encoding='utf-8'))['status'], 'error')
            report = json.loads((work / 'bad.json').read_text(encoding='utf-8'))
            self.assertEqual(report['summary']['codes'], ['mtoon_missing'])
            self.assertTrue(report['unverified'])
            self.assertEqual(good.read_bytes(), before)

    def test_script_declares_gpl_is_ascii_and_imports_no_blender(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# SPDX-License-Identifier: GPL-3.0-or-later\n'))
        text.encode('ascii')
        self.assertNotIn('import bpy', text)
        self.assertNotIn('import numpy', text)


if __name__ == '__main__':
    unittest.main()
