"""Regression checks for publication scope, portable attribution, and finished ZIPs."""
from pathlib import Path
import base64
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))
from validate import (validate, EXCLUDED_NAMES, SKILL_DIR, ATTRIBUTION_HELPER,
                      REFERENCE_PATH, REFERENCE_TERMS, REFERENCE_ARCHIVE_URL, REFERENCE_MEMBER)
from build_package import build, audit_archive, fetch_reference_model

DEFAULT_TEST_TEMP = Path(tempfile.gettempdir()) / "lida-distribution-tests"
TEST_TEMP = Path(os.environ.get("LIDA_DISTRIBUTION_TEST_TEMP", str(DEFAULT_TEST_TEMP)))
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB1cAAAAASUVORK5CYII=")


class PublicationChecks(unittest.TestCase):
    def setUp(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="pack-", dir=TEST_TEMP)
        self.outer = Path(self.temp.name)
        self.root = self.outer / "source"
        self.root.mkdir()
        (self.root / "README.md").write_text("# Pack\n[Guide](guide.md#steps)\n", encoding="utf-8")
        (self.root / "guide.md").write_text("# Steps\nUse the same camera.\n", encoding="utf-8")
        (self.root / "VERSION").write_text("0.1.0-dev\n", encoding="utf-8")
        skill = self.root / SKILL_DIR
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: lida-avatar-workflow\ndescription: Fixture workflow.\n---\n"
            "# Fixture\n[Terms](LICENSE) [Source](NOTICE.md)\n", encoding="utf-8")
        # Fixtures satisfy the same portable-file requirements without defining production terms.
        for name, value in (("LICENSE", "Fixture terms.\n"), ("NOTICE.md", "# Fixture source\n")):
            (self.root / name).write_text(value, encoding="utf-8")
            (skill / name).write_text(value, encoding="utf-8")
        shutil.copyfile(PACKAGE_ROOT / ATTRIBUTION_HELPER, self.root / ATTRIBUTION_HELPER)
        self.files = ["README.md", "guide.md", "VERSION", "publication-manifest.json",
                      "LICENSE", "NOTICE.md", SKILL_DIR + "/SKILL.md",
                      SKILL_DIR + "/LICENSE", SKILL_DIR + "/NOTICE.md", ATTRIBUTION_HELPER]
        self.manifest()

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, assets=None, version="0.1.0-dev"):
        pairs = []
        for source, target in [("README.md", "README.en.md"),
                               (SKILL_DIR + "/SKILL.md", SKILL_DIR + "/SKILL.en.md")]:
            if target not in self.files:
                (self.root / target).write_text("# English fixture\nUse matching images.\n", encoding="utf-8")
                self.files.append(target)
            pairs.append(dict(source=source, translation=target,
                              source_sha256=hashlib.sha256((self.root / source).read_bytes()).hexdigest()))
        (self.root / "publication-manifest.json").write_text(
            json.dumps(dict(version=version, files=self.files, asset_sha256=assets or {},
                            language_support=dict(primary="ja", available=["ja", "en"], pairs=pairs))),
            encoding="utf-8")

    def helper(self, *args, script=None, cwd=None):
        return subprocess.run(
            [sys.executable, "-B", str(script or self.root / ATTRIBUTION_HELPER), *args],
            cwd=cwd or self.outer, capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
            check=False)

    def project(self):
        directory = self.outer / "publishing-project"
        directory.mkdir(exist_ok=True)
        return directory

    def test_valid_pack_and_reproducible_archive(self):
        self.assertTrue(validate(self.root)["passed"], validate(self.root))
        first = build(self.root)
        self.assertTrue(first["audit"]["passed"])
        self.assertEqual(first["sha256"], build(self.root)["sha256"])
        self.assertTrue(audit_archive(self.root / "dist" / first["archive"], self.root)["passed"])

    def reference(self, present=True, external=False, animation=False, binary_size=4):
        document = dict(asset=dict(version="2.0"), buffers=[dict(byteLength=binary_size)], images=[],
                        extensions={"VRMC_vrm":dict(specVersion="1.0", meta=dict(
                            authors=["Lida"], allowRedistribution=False, modification="allowModification",
                            commercialUsage="corporation", avatarPermission="onlySeparatelyLicensedPerson"))})
        if external:
            document["images"] = [dict(uri="https://example.invalid/image.png")]
        if animation:
            document["animations"] = [dict(name="reference-motion")]
        raw = json.dumps(document).encode("utf-8")
        raw += b" " * (-len(raw) % 4)
        chunks = struct.pack("<II",len(raw),0x4E4F534A) + raw + struct.pack("<II",binary_size,0x004E4942) + b"\0"*binary_size
        data = struct.pack("<4sII",b"glTF",2,len(chunks)+12)+chunks
        for name in REFERENCE_TERMS:
            target = self.root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Model-only terms\nNo redistribution or modified-model sales.\n",encoding="utf-8")
            self.files.append(name)
        self.manifest()
        path, manifest = self.english_pack()
        declaration = dict(path=REFERENCE_PATH, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                           archive_url=REFERENCE_ARCHIVE_URL, archive_sha256="0"*64, archive_bytes=1,
                           archive_member=REFERENCE_MEMBER, terms=REFERENCE_TERMS)
        manifest["bundled_reference_model"] = declaration
        path.write_text(json.dumps(manifest),encoding="utf-8")
        if present:
            (self.root/REFERENCE_PATH).write_bytes(data)
        return data, declaration

    def reference_archive(self, data, extra=None):
        contents = io.BytesIO()
        prefix = REFERENCE_MEMBER.rsplit("/",1)[0]+"/"
        with zipfile.ZipFile(contents,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(REFERENCE_MEMBER,data)
            for name in ("README.md","README.en.md","MODEL-TERMS.md","MODEL-TERMS.en.md",
                         "reference-manifest.json","SHA256SUMS.txt"):
                archive.writestr(prefix+name,b"Fixture guide")
            if extra:
                archive.writestr(*extra)
        raw = contents.getvalue()
        path, manifest = self.english_pack()
        declaration = manifest["bundled_reference_model"]
        declaration.update(archive_sha256=hashlib.sha256(raw).hexdigest(), archive_bytes=len(raw))
        path.write_text(json.dumps(manifest),encoding="utf-8")
        return raw

    def test_bundled_reference_is_physically_in_complete_zip_and_portable_skill(self):
        data, _ = self.reference(binary_size=5*1024*1024+4)
        result = build(self.root)
        self.assertTrue(result['audit']['passed'])
        archive = self.root/'dist'/result['archive']
        with zipfile.ZipFile(archive) as pack:
            prefix = '3DCharaMakeSkills-Lida-0.1.0-dev/'
            self.assertEqual(pack.read(prefix+REFERENCE_PATH),data)
            for name in REFERENCE_TERMS:
                self.assertIn(prefix+name,pack.namelist())
        portable = self.outer/'portable-with-model'
        shutil.copytree(self.root/SKILL_DIR,portable)
        relative = Path(REFERENCE_PATH).relative_to(SKILL_DIR)
        self.assertEqual((portable/relative).read_bytes(),data)

    def test_missing_reference_is_allowed_in_source_but_not_in_complete_build_or_audit(self):
        self.reference(present=False)
        self.assertTrue(validate(self.root)['passed'])
        self.assertFalse(validate(self.root,require_reference_model=True)['passed'])
        with patch('build_package.urllib.request.build_opener') as network:
            with self.assertRaisesRegex(RuntimeError,'reference model is missing'):
                build(self.root)
            network.assert_not_called()
        self.assertFalse(audit_archive(self.outer/'absent.zip',self.root)['passed'])

    def test_reference_hash_structure_animation_and_external_dependencies_are_enforced(self):
        data, _ = self.reference()
        target = self.root/REFERENCE_PATH
        target.write_bytes(data+b'changed')
        self.assertFalse(validate(self.root)['passed'])
        target.write_bytes(data[:-1]+b'x')
        self.assertFalse(validate(self.root)['passed'])
        for external, animation in ((True,False),(False,True)):
            bad_doc = dict(asset=dict(version='2.0'), buffers=[],images=[dict(uri='private.png')] if external else [],
                           extensions={'VRMC_vrm':dict(specVersion='1.0',meta=dict(authors=['Lida'],
                               allowRedistribution=False,modification='allowModification',
                               commercialUsage='corporation',avatarPermission='onlySeparatelyLicensedPerson'))})
            if animation:
                bad_doc['animations'] = [dict(name='motion')]
            raw = json.dumps(bad_doc).encode(); raw += b' '*(-len(raw)%4)
            chunks = struct.pack('<II',len(raw),0x4E4F534A)+raw+struct.pack('<II',4,0x004E4942)+b'\0'*4
            candidate = struct.pack('<4sII',b'glTF',2,len(chunks)+12)+chunks
            target.write_bytes(candidate)
            path, manifest = self.english_pack()
            manifest['bundled_reference_model'].update(bytes=len(candidate),sha256=hashlib.sha256(candidate).hexdigest())
            path.write_text(json.dumps(manifest),encoding='utf-8')
            self.assertFalse(validate(self.root)['passed'])

    def test_bundled_reference_does_not_permit_other_models_or_missing_terms(self):
        self.reference()
        other = self.root/'unexpected.vrm'
        other.write_bytes(b'other model')
        self.assertFalse(validate(self.root)['passed'])
        other.unlink()
        (self.root/REFERENCE_TERMS[1]).unlink()
        self.assertFalse(validate(self.root)['passed'])

    def test_reference_exception_does_not_raise_regular_file_size_limit(self):
        self.reference()
        (self.root/'guide.md').write_bytes(b'# Steps\n'+b'x'*(5*1024*1024))
        self.assertFalse(validate(self.root)['passed'])

    def test_reference_terms_cannot_be_empty_or_disagree_with_root_copy(self):
        self.reference()
        terms = self.root/REFERENCE_TERMS[0]
        terms.write_text(' \n',encoding='utf-8')
        self.assertFalse(validate(self.root)['passed'])
        terms.write_text('# Model terms\nNo redistribution.\n',encoding='utf-8')
        root_copy = self.root/'model-reference/china-wafuku/MODEL-TERMS.md'
        root_copy.parent.mkdir(parents=True)
        root_copy.write_text('Different permission.\n',encoding='utf-8')
        self.files.append(root_copy.relative_to(self.root).as_posix())
        path, manifest = self.english_pack()
        manifest['files'] = self.files
        path.write_text(json.dumps(manifest),encoding='utf-8')
        self.assertFalse(validate(self.root)['passed'])

    def test_reference_declaration_cannot_widen_path_host_or_remove_terms(self):
        self.reference()
        path, manifest = self.english_pack()
        original = dict(manifest['bundled_reference_model'])
        for key,value in (('path','../escape.vrm'),('path','other.vrm'),
                          ('archive_url','https://example.invalid/model.zip'),('terms',[]),
                          ('bytes',True),('archive_sha256','not-a-hash')):
            manifest['bundled_reference_model'] = {**original,key:value}
            path.write_text(json.dumps(manifest),encoding='utf-8')
            self.assertFalse(validate(self.root)['passed'])

    def test_release_181_requires_reference_declaration(self):
        self.manifest(version='1.8.1')
        (self.root/'VERSION').write_text('1.8.1\n',encoding='utf-8')
        self.assertFalse(validate(self.root)['passed'])

    def test_reference_fetch_requires_explicit_build_flag_and_never_overwrites(self):
        data, _ = self.reference(present=False)
        raw = self.reference_archive(data)
        with patch('build_package.urllib.request.build_opener') as network:
            network.return_value.open.return_value.__enter__.return_value.read.return_value = raw
            result = build(self.root,fetch_reference=True)
            self.assertTrue(result['audit']['passed'])
            self.assertEqual(network.call_count,1)
            self.assertEqual((self.root/REFERENCE_PATH).read_bytes(),data)
            fetch_reference_model(self.root)
            self.assertEqual(network.call_count,1)
            (self.root/REFERENCE_PATH).write_bytes(b'keep this local candidate')
            with self.assertRaises(RuntimeError):
                fetch_reference_model(self.root)
            self.assertEqual((self.root/REFERENCE_PATH).read_bytes(),b'keep this local candidate')
            self.assertEqual(network.call_count,1)

    def test_reference_fetch_rejects_wrong_archive_hash_and_unexpected_motion(self):
        data, _ = self.reference(present=False)
        raw = self.reference_archive(data)
        for payload in (raw+b'tampered', self.reference_archive(data,('ChinaWafuku-Reference-r35/reference.fbx',b'motion'))):
            if payload.endswith(b'tampered'):
                path,manifest=self.english_pack()
                manifest['bundled_reference_model'].update(archive_sha256=hashlib.sha256(raw).hexdigest(),archive_bytes=len(raw))
                path.write_text(json.dumps(manifest),encoding='utf-8')
            else:
                path,manifest=self.english_pack()
                manifest['bundled_reference_model'].update(archive_sha256=hashlib.sha256(payload).hexdigest(),archive_bytes=len(payload))
                path.write_text(json.dumps(manifest),encoding='utf-8')
            with patch('build_package.urllib.request.build_opener') as network:
                network.return_value.open.return_value.__enter__.return_value.read.return_value=payload
                with self.assertRaises(RuntimeError):
                    fetch_reference_model(self.root)
            self.assertFalse((self.root/REFERENCE_PATH).exists())

    def test_complete_zip_rejects_missing_changed_and_additional_reference_models(self):
        self.reference()
        result = build(self.root)
        with zipfile.ZipFile(self.root/'dist'/result['archive']) as reader:
            entries = [(i.filename,reader.read(i)) for i in reader.infolist()]
        prefix = '3DCharaMakeSkills-Lida-0.1.0-dev/'
        cases = [
            [(n,d) for n,d in entries if n != prefix+REFERENCE_PATH],
            [(n,b'changed' if n==prefix+REFERENCE_PATH else d) for n,d in entries],
            entries+[(prefix+'another.vrm',b'model')],
            entries+[(prefix+'reference.fbx',b'motion')],
        ]
        for index,entries in enumerate(cases):
            archive = self.outer/f'tampered-{index}.zip'
            with zipfile.ZipFile(archive,'w') as writer:
                for n,d in entries:
                    writer.writestr(n,d)
            self.assertFalse(audit_archive(archive,self.root)['passed'])

    def test_english_attribution_is_usable_and_does_not_replace_existing_blocks(self):
        project = self.project()
        args = ['--target', 'skill', '--component', 'skills', '--project-dir', str(project)]
        created = self.helper(*args, '--language', 'en', '--changes', 'Adapted the rig review workflow.')
        self.assertEqual(created.returncode, 0, created.stderr)
        notice = project / 'THIRD_PARTY_NOTICES.md'
        original = notice.read_bytes()
        self.assertIn(b'- Author: Lida', original)
        self.assertIn(b'- Changes: Adapted the rig review workflow.', original)
        checked = self.helper(*args, '--language', 'ja', '--check')
        self.assertEqual(checked.returncode, 0, checked.stderr)
        repeated = self.helper(*args, '--language', 'ja')
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(notice.read_bytes(), original)

    def test_english_model_target_does_not_create_notice(self):
        project = self.project()
        result = self.helper('--target', 'model', '--language', 'en', '--project-dir', str(project))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['required'])
        self.assertFalse((project / 'THIRD_PARTY_NOTICES.md').exists())

    def english_pack(self):
        path = self.root / 'publication-manifest.json'
        return path, json.loads(path.read_text(encoding='utf-8'))

    def test_translation_declaration_cannot_be_removed(self):
        path, value = self.english_pack()
        for mode in ('missing', 'null'):
            candidate = dict(value)
            if mode == 'missing':
                candidate.pop('language_support')
            else:
                candidate['language_support'] = None
            path.write_text(json.dumps(candidate), encoding='utf-8')
            self.assertFalse(validate(self.root)['passed'])

    def test_translation_coverage_and_reviewed_source_version(self):
        _, _ = self.english_pack()
        self.assertTrue(validate(self.root)['passed'], validate(self.root))
        source = self.root / 'README.md'
        source.write_text(source.read_text(encoding='utf-8') + 'Changed workflow.\n', encoding='utf-8')
        report = validate(self.root)
        self.assertFalse(report['passed'])
        self.assertTrue(any('source version is stale' in item for item in report['errors']))

    def test_registered_translation_must_exist_and_be_nonempty(self):
        self.english_pack()
        target = self.root / 'README.en.md'
        for whitespace in ('  \n', '\ufeff', '\ufeff \u3000\n'):
            target.write_text(whitespace, encoding='utf-8')
            self.assertFalse(validate(self.root)['passed'])
        target.unlink()
        self.assertFalse(validate(self.root)['passed'])

    def test_new_reference_requires_english_pair(self):
        self.english_pack()
        reference = SKILL_DIR + '/references/new-stage.md'
        path = self.root / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# New stage\nUse matching evidence.\n', encoding='utf-8')
        manifest_path = self.root / 'publication-manifest.json'
        value = json.loads(manifest_path.read_text(encoding='utf-8'))
        value['files'].append(reference)
        manifest_path.write_text(json.dumps(value), encoding='utf-8')
        report = validate(self.root)
        self.assertFalse(report['passed'])
        self.assertTrue(any('English document is not registered' in item for item in report['errors']))

    def test_unlisted_model_is_rejected(self):
        (self.root / ("raw"+".blend")).write_bytes(b"private model")
        self.assertFalse(validate(self.root)["passed"])

    def test_missing_guide_or_heading_is_rejected(self):
        (self.root / "guide.md").write_text("# Other\n", encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_personal_path_is_rejected(self):
        value = "Q" + chr(58) + chr(92) + "Users" + chr(92) + "someone"
        (self.root / "guide.md").write_text("# Steps\n"+value, encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_https_is_allowed_but_local_file_uri_is_rejected(self):
        (self.root / "guide.md").write_text("# Steps\n[Source](https://example.invalid/guide)", encoding="utf-8")
        self.assertTrue(validate(self.root)["passed"])
        value = "file:" + "/" * 3 + "private/model"
        (self.root / "guide.md").write_text("# Steps\n"+value, encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_excluded_term_is_rejected_without_exposing_it(self):
        (self.root / "guide.md").write_text("# Steps\n"+EXCLUDED_NAMES[0], encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_credential_is_rejected(self):
        value = "gh" + "p" + "_" + "A" * 25
        (self.root / "guide.md").write_text("# Steps\n"+value, encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_modified_or_external_svg_is_rejected(self):
        (self.root / "diagram.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        self.files.append("diagram.svg")
        digest = hashlib.sha256((self.root / "diagram.svg").read_bytes()).hexdigest()
        self.manifest({"diagram.svg": digest})
        self.assertTrue(validate(self.root)["passed"])
        (self.root / "diagram.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/a.png"/></svg>', encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_missing_or_unlisted_portable_files_are_rejected(self):
        (self.root / SKILL_DIR / "NOTICE.md").unlink()
        self.assertFalse(validate(self.root)["passed"])
        self.files.remove("LICENSE")
        self.manifest()
        self.assertFalse(validate(self.root)["passed"])

    def test_mismatched_or_empty_portable_terms_are_rejected(self):
        (self.root / SKILL_DIR / "LICENSE").write_text("Different terms.\n", encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])
        for rel in ("LICENSE", SKILL_DIR + "/LICENSE"):
            (self.root / rel).write_text("", encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_extensionless_license_content_is_checked(self):
        value = "gh" + "p" + "_" + "B" * 25
        for rel in ("LICENSE", SKILL_DIR + "/LICENSE"):
            (self.root / rel).write_text(value, encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_manifest_version_must_match(self):
        self.manifest(version="0.2.0")
        self.assertFalse(validate(self.root)["passed"])

    def test_unsafe_or_duplicate_manifest_paths_are_rejected(self):
        for path in ("../outside.txt", "/absolute.txt", "folder\\file.md", "README.md"):
            with self.subTest(path=path):
                self.files.append(path)
                self.manifest()
                self.assertFalse(validate(self.root)["passed"])
                self.files.pop()

    def test_fbx_extension_and_renamed_ascii_binary_are_rejected(self):
        payloads = [
            ("motion.FBX", b"not a distributable reference"),
            ("renamed.md", b"; FBX 7.4.0 project file\nFBXHeaderExtension: {\n}"),
            ("renamed.png", b"Kaydara FBX Binary  \x00\x1a\x00payload"),
            ("renamed.txt", b"FBXHeaderExtension: {\n}"),
        ]
        for name, data in payloads:
            with self.subTest(name=name):
                (self.root / name).write_bytes(data)
                self.files.append(name)
                assets = {name: hashlib.sha256(data).hexdigest()} if name.endswith(".png") else {}
                self.manifest(assets)
                result = validate(self.root)
                self.assertFalse(result["passed"])
                self.assertTrue(any("FBX" in error for error in result["errors"]))
                self.files.pop()
                (self.root / name).unlink()

    def test_images_require_signature_and_approved_hash(self):
        name = "image.png"
        self.files.append(name)
        (self.root / name).write_bytes(PNG)
        self.manifest()
        self.assertFalse(validate(self.root)["passed"])
        self.manifest({name: hashlib.sha256(PNG).hexdigest()})
        self.assertTrue(validate(self.root)["passed"])
        (self.root / name).write_bytes(b"fake image")
        self.manifest({name: hashlib.sha256(b"fake image").hexdigest()})
        self.assertFalse(validate(self.root)["passed"])

    def test_zip_missing_extra_duplicate_and_changed_contents_are_rejected(self):
        report = build(self.root)
        archive = self.root / "dist" / report["archive"]
        with zipfile.ZipFile(archive) as reader:
            entries = [(info.filename, reader.read(info)) for info in reader.infolist()]
        prefix = entries[0][0].split("/")[0] + "/"
        scenarios = {
            "missing": [(name, data) for name, data in entries if name != prefix + SKILL_DIR + "/NOTICE.md"],
            "extra": entries + [(prefix + "reference.fbx", b"forbidden")],
            "duplicate": entries + [entries[0]],
            "changed": [(name, b"changed" if name == prefix + "LICENSE" else data) for name, data in entries],
            "unsafe": entries + [("../escape.txt", b"not allowed")],
        }
        for case, data in scenarios.items():
            with self.subTest(case=case):
                altered = self.root / "dist" / (case + ".zip")
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with zipfile.ZipFile(altered, "w") as writer:
                        for name, contents in data:
                            writer.writestr(name, contents)
                self.assertFalse(audit_archive(altered, self.root)["passed"])

    def test_standalone_skill_preserves_terms_links_and_helper(self):
        portable = self.outer / "portable-skill"
        shutil.copytree(self.root / SKILL_DIR, portable)
        self.assertEqual((portable / "LICENSE").read_bytes(), (self.root / "LICENSE").read_bytes())
        self.assertEqual((portable / "NOTICE.md").read_bytes(), (self.root / "NOTICE.md").read_bytes())
        for link in re.findall(r"\]\(([^)]+)\)", (portable / "SKILL.md").read_text(encoding="utf-8")):
            self.assertTrue((portable / link).is_file())
        project = self.project()
        result = self.helper("--target", "skill", "--component", "skills", "--project-dir", str(project),
                             script=portable / "scripts" / "ensure_attribution.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("3DCharaMakeSkills-Lida", (project / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"))

    def test_skill_links_cannot_depend_on_repository_root(self):
        path = self.root / SKILL_DIR / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n[Root-only terms](../../LICENSE)\n", encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_model_target_and_module_import_never_write(self):
        project = self.project()
        result = self.helper("--target", "model", "--project-dir", str(project))
        self.assertEqual(result.returncode, 0, result.stdout)
        code = "import runpy,sys; runpy.run_path(sys.argv[1], run_name='helper_import')"
        imported = subprocess.run([sys.executable, "-B", "-c", code, str(self.root / ATTRIBUTION_HELPER)],
                                  cwd=project, capture_output=True, check=False)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(list(project.iterdir()), [])

    def test_app_requires_explicit_component_and_destination(self):
        project = self.project()
        for args in (("--target", "app"), ("--target", "app", "--component", "both"),
                     ("--target", "app", "--project-dir", str(project))):
            self.assertNotEqual(self.helper(*args).returncode, 0)
        self.assertEqual(list(project.iterdir()), [])

    def test_helper_check_is_read_only_and_repeated_use_preserves_notes(self):
        project = self.project()
        notice = project / "THIRD_PARTY_NOTICES.md"
        original = b"# Existing notices\r\n\r\nKeep these exact bytes.\r\n"
        notice.write_bytes(original)
        args = ("--target", "app", "--component", "skills", "--project-dir", str(project))
        self.assertEqual(self.helper(*args, "--check").returncode, 1)
        self.assertEqual(notice.read_bytes(), original)
        result = self.helper(*args, "--changes", "Only the mesh diagnosis was adapted.")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        first = notice.read_bytes()
        self.assertTrue(first.startswith(original))
        self.assertIn(b"Only the mesh diagnosis was adapted.", first)
        self.assertEqual(self.helper(*args, "--changes", "Do not replace the earlier note.").returncode, 0)
        self.assertEqual(notice.read_bytes(), first)
        self.assertEqual(self.helper(*args, "--check").returncode, 0)
        self.assertEqual(notice.read_bytes(), first)
        both = ("--target", "app", "--component", "both", "--project-dir", str(project))
        self.assertEqual(self.helper(*both, "--check").returncode, 1)
        self.assertEqual(self.helper(*both).returncode, 0)
        final = notice.read_text(encoding="utf-8")
        self.assertEqual(final.count("<!-- lida-attribution:skills:start -->"), 1)
        self.assertEqual(final.count("<!-- lida-attribution:shader:start -->"), 1)
        self.assertIn("LidaAngelToon", final)
        self.assertIn("https://github.com/Lida-V/LidaAngelToon", final)
        self.assertIn("Only the mesh diagnosis was adapted.", final)
        self.assertEqual(self.helper(*both, "--check").returncode, 0)
        self.assertEqual({item.name for item in project.iterdir()}, {"THIRD_PARTY_NOTICES.md"})

    def test_helper_keeps_valid_manual_entry_and_rejects_incomplete_block(self):
        project = self.project()
        notice = project / "THIRD_PARTY_NOTICES.md"
        manual = ("# Sources\n\n## 3DCharaMakeSkills-Lida\n- Author: Lida\n"
                  "- URL: https://github.com/Lida-V/3DCharaMakeSkills-Lida\n"
                  "- Changes: Custom existing changes note.\n")
        notice.write_text(manual, encoding="utf-8")
        args = ("--target", "skill", "--component", "skills", "--project-dir", str(project))
        self.assertEqual(self.helper(*args).returncode, 0)
        self.assertEqual(notice.read_text(encoding="utf-8"), manual)
        broken = "<!-- lida-attribution:skills:start -->\nIncomplete"
        notice.write_text(broken, encoding="utf-8")
        self.assertEqual(self.helper(*args).returncode, 2)
        self.assertEqual(notice.read_text(encoding="utf-8"), broken)

    def test_helper_rejects_missing_portable_license(self):
        project = self.project()
        (self.root / SKILL_DIR / "LICENSE").unlink()
        result = self.helper("--target", "app", "--component", "skills", "--project-dir", str(project))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(project.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
