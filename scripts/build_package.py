"""Build a deterministic ZIP from the publication allowlist, after validation."""
from pathlib import Path
import hashlib
import json
import zipfile
from validate import ROOT, validate


def build(root=ROOT):
    root = Path(root)
    report = validate(root)
    if not report["passed"]:
        raise RuntimeError(json.dumps(report, ensure_ascii=False))
    manifest = json.loads((root / "publication-manifest.json").read_text(encoding="utf-8"))
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    output = root / "dist"
    output.mkdir(exist_ok=True)
    archive = output / f"3DCharaMakeSkills-Lida-{version}.zip"
    prefix = f"3DCharaMakeSkills-Lida-{version}/"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as pack:
        for relative in sorted(manifest["files"]):
            info = zipfile.ZipInfo(prefix + relative, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            pack.writestr(info, (root / relative).read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return dict(archive=archive.name, files=len(manifest["files"]), bytes=archive.stat().st_size, sha256=digest)


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
