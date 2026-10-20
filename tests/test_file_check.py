"""CLI checks with synthesized identifying headers, never distributed model assets."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/lida-avatar-workflow/scripts/lida_file_check.py"
TEST_TEMP = Path(os.environ.get("LIDA_DISTRIBUTION_TEST_TEMP", str(Path(tempfile.gettempdir()) / "lida-distribution-tests")))


def binary_header(version=7400):
    return b"Kaydara FBX Binary  \x00\x1a\x00" + struct.pack("<I", version)


def ascii_header(version=7400):
    return ("; FBX 7.4.0 project file\nFBXHeaderExtension: {\n"
            f"    FBXHeaderVersion: 1003\n    FBXVersion: {version}\n}}\n").encode("ascii")


class FileCheckCliTests(unittest.TestCase):
    def setUp(self):
        TEST_TEMP.mkdir(parents=True, exist_ok=True)
        self.work = tempfile.TemporaryDirectory(prefix="lida-fbx-check-", dir=TEST_TEMP)
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        self.source = self.directory / "upload.fbx"
        self.report = self.directory / "report.json"

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)],
                              cwd=self.directory, capture_output=True, text=True, encoding="utf-8",
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})

    def check_fixture(self, data, expected_code, max_bytes=None, name="upload.fbx"):
        source = self.directory / name
        source.write_bytes(data)
        before = source.read_bytes()
        args = ["--input", source, "--report", self.report]
        if max_bytes is not None:
            args += ["--max-bytes", str(max_bytes)]
        proc = self.run_cli(*args)
        self.assertEqual(proc.returncode, expected_code, proc.stderr)
        self.assertEqual(source.read_bytes(), before)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(report["file_checks_passed"], expected_code == 0)
        self.assertEqual(report["input"]["size_bytes"], len(data))
        self.assertEqual(report["input"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(report["source_preservation"]["sha256_before"], report["source_preservation"]["sha256_after"])
        self.assertNotIn(str(self.directory), self.report.read_text(encoding="utf-8"))
        self.assertNotIn(str(self.directory), proc.stdout + proc.stderr)
        return report

    def test_binary_header_default_limit_and_scope_are_explicit(self):
        report = self.check_fixture(binary_header(), 0)
        self.assertEqual(report["limits"]["max_bytes"], 150_000_000)
        self.assertEqual(report["checks"]["identifying_header_only"]["status"], "recognized_binary_header")
        limitations = " ".join(report["uninspected"]).lower()
        for word in ("full fbx", "mesh", "bones", "images", "animation", "appearance", "service acceptance"):
            self.assertIn(word, limitations)
        self.assertNotIn("passed", report)

    def test_ascii_header_and_uppercase_extension(self):
        report = self.check_fixture(ascii_header(), 0, name="upload.FBX")
        self.assertEqual(report["checks"]["identifying_header_only"]["status"], "recognized_ascii_header")

    def test_exact_byte_limit_is_inclusive(self):
        data = binary_header()
        report = self.check_fixture(data, 0, max_bytes=len(data))
        self.assertTrue(report["checks"]["size_limit"]["condition_passed"])

    def test_one_byte_over_limit_is_not_approved(self):
        data = binary_header()
        report = self.check_fixture(data, 2, max_bytes=len(data) - 1)
        self.assertFalse(report["checks"]["size_limit"]["condition_passed"])

    def test_empty_input_is_not_approved(self):
        report = self.check_fixture(b"", 2)
        self.assertFalse(report["checks"]["nonempty_file"]["condition_passed"])

    def test_renamed_non_fbx_is_not_approved(self):
        report = self.check_fixture(b"this is not an FBX file", 2)
        self.assertEqual(report["checks"]["identifying_header_only"]["status"], "unrecognized_header_format_unverified")

    def test_missing_or_mismatched_extension_is_not_approved(self):
        report = self.check_fixture(binary_header(), 2, name="upload.txt")
        self.assertFalse(report["checks"]["fbx_extension"]["condition_passed"])

    def test_incomplete_or_mismatched_binary_headers(self):
        for index, data in enumerate((binary_header()[:-2], b"Kaydara FBX Binary wrong", binary_header(0))):
            with self.subTest(case=index):
                self.report = self.directory / f"binary-{index}.json"
                self.check_fixture(data, 2)

    def test_incomplete_or_mismatched_ascii_headers(self):
        for index, data in enumerate((b"; FBX 7.4.0 project file\n", ascii_header(7500),
                                      b"FBXHeaderExtension: {\nFBXVersion: 7400\n}\n")):
            with self.subTest(case=index):
                self.report = self.directory / f"ascii-{index}.json"
                self.check_fixture(data, 2)

    def test_ascii_version_must_be_in_closed_header_at_root_level(self):
        prefix = b"; FBX 7.4.0 project file\nFBXHeaderExtension: {\n"
        cases = (prefix + b"}\nFBXVersion: 7400\n",
                 prefix + b"FBXVersion: 7400\n",
                 prefix + b"FBXVersion: 7400\nFBXVersion: 7400\n}\n",
                 prefix + b"Nested: {\nFBXVersion: 7400\n}\n}\n")
        for index, data in enumerate(cases):
            with self.subTest(case=index):
                self.report = self.directory / f"ascii-scope-{index}.json"
                self.check_fixture(data, 2)

    def test_ascii_comments_bom_and_quoted_braces_do_not_change_header_scope(self):
        data = (b"\xef\xbb\xbf; FBX 7.4.0 project file\nFBXHeaderExtension: {\n"
                b"FBXVersion: 7400 ; version comment }\nCreator: \"example { }\"\n}\n")
        self.check_fixture(data, 0)

    def test_existing_report_is_preserved(self):
        self.source.write_bytes(binary_header())
        self.report.write_bytes(b"keep this report")
        proc = self.run_cli("--input", self.source, "--report", self.report)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.report.read_bytes(), b"keep this report")
        self.assertEqual(self.source.read_bytes(), binary_header())

    def test_alternate_stream_output_is_refused(self):
        self.source.write_bytes(binary_header())
        output = self.directory / "upload.fbx:report.json"
        proc = self.run_cli("--input", self.source, "--report", output)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.source.read_bytes(), binary_header())
        self.assertFalse(output.exists())

    def test_same_path_and_normalized_alias_are_refused(self):
        self.source.write_bytes(binary_header())
        child = self.directory / "child"
        child.mkdir()
        for output in (self.source, child / ".." / "upload.fbx"):
            with self.subTest(output=output.name):
                proc = self.run_cli("--input", self.source, "--report", output)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(self.source.read_bytes(), binary_header())

    def test_hard_link_alias_is_preserved_and_refused(self):
        self.source.write_bytes(binary_header())
        alias = self.directory / "hard-link.json"
        try:
            os.link(self.source, alias)
        except OSError:
            self.skipTest("Hard links unavailable on this filesystem")
        proc = self.run_cli("--input", self.source, "--report", alias)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.source.read_bytes(), binary_header())
        self.assertEqual(alias.read_bytes(), binary_header())

    def test_symlink_and_dangling_report_are_refused(self):
        self.source.write_bytes(binary_header())
        for index, target in enumerate((self.source, self.directory / "missing.json")):
            alias = self.directory / f"symlink-{index}.json"
            try:
                alias.symlink_to(target)
            except OSError:
                self.skipTest("Symbolic links unavailable on this filesystem")
            proc = self.run_cli("--input", self.source, "--report", alias)
            self.assertEqual(proc.returncode, 1)
            self.assertTrue(alias.is_symlink())
            self.assertEqual(self.source.read_bytes(), binary_header())

    def test_missing_input_directory_input_and_missing_report_parent(self):
        self.source.write_bytes(binary_header())
        cases = ((self.directory / "missing.fbx", self.report), (self.directory, self.report),
                 (self.source, self.directory / "missing-parent" / "report.json"))
        for source, report in cases:
            with self.subTest(source=source.name, report=report.name):
                proc = self.run_cli("--input", source, "--report", report)
                self.assertEqual(proc.returncode, 1)
                self.assertFalse(report.exists())
                self.assertNotIn(str(self.directory), proc.stdout + proc.stderr)

    def test_required_arguments_and_positive_integer_limits(self):
        for args in ([], ["--input", "missing.fbx"], ["--report", "new.json"],
                     ["--input", "missing.fbx", "--report", "new.json", "--max-bytes", "0"],
                     ["--input", "missing.fbx", "--report", "new.json", "--max-bytes", "-1"],
                     ["--input", "missing.fbx", "--report", "new.json", "--max-bytes", "1.5"]):
            with self.subTest(args=args):
                proc = self.run_cli(*args)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(list(self.directory.iterdir()), [])

    def test_import_and_help_have_no_model_reads_or_writes(self):
        code = ("import importlib.util, pathlib, sys; "
                "s=importlib.util.spec_from_file_location('file_helper',sys.argv[1]); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "assert 'bpy' not in sys.modules; assert not list(pathlib.Path.cwd().iterdir())")
        proc = subprocess.run([sys.executable, "-B", "-c", code, str(SCRIPT)], cwd=self.directory,
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = self.run_cli("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
