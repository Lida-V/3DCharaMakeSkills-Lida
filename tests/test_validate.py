"""Regression checks for publication scope, portable attribution, and finished ZIPs."""
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))
from validate import validate, EXCLUDED_NAMES, SKILL_DIR, ATTRIBUTION_HELPER
from build_package import build, audit_archive

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
        (self.root / "publication-manifest.json").write_text(
            json.dumps(dict(version=version, files=self.files, asset_sha256=assets or {})),
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
