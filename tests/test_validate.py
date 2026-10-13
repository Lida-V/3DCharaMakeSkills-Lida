"""Check observable failures that would contaminate or break a distributed pack."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate import validate, EXCLUDED_NAMES
from build_package import build


class PublicationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "README.md").write_text("# Pack\n[Guide](guide.md#steps)\n", encoding="utf-8")
        (self.root / "guide.md").write_text("# Steps\nUse the same camera.\n", encoding="utf-8")
        (self.root / "VERSION").write_text("0.1.0-dev\n", encoding="utf-8")
        self.files = ["README.md", "guide.md", "VERSION", "publication-manifest.json"]
        self.manifest()

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, assets=None):
        (self.root / "publication-manifest.json").write_text(json.dumps(dict(files=self.files, asset_sha256=assets or {})), encoding="utf-8")

    def test_valid_pack_and_reproducible_archive(self):
        self.assertTrue(validate(self.root)["passed"])
        first = build(self.root)
        self.assertEqual(first["sha256"], build(self.root)["sha256"])

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
        self.manifest({"diagram.svg":digest})
        self.assertTrue(validate(self.root)["passed"])
        (self.root / "diagram.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/a.png"/></svg>', encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])


if __name__ == "__main__":
    unittest.main()
