"""Build a deterministic allowlisted ZIP and audit its completed contents."""
from pathlib import Path
import argparse
import hashlib
import json
import stat
import zipfile
from validate import ROOT, validate, check_file_bytes, safe_relative


def audit_archive(archive, root=ROOT):
    """Read only: compare the finished archive against the validated source."""
    root = Path(root).resolve()
    report = validate(root)
    if not report["passed"]:
        return dict(passed=False, files=0, errors=["Source pack is invalid", *report["errors"]])
    manifest = json.loads((root / "publication-manifest.json").read_text(encoding="utf-8"))
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    prefix = f"3DCharaMakeSkills-Lida-{version}/"
    expected = {prefix + name: name for name in manifest["files"]}
    errors = []
    count = 0
    try:
        with zipfile.ZipFile(archive) as pack:
            infos = pack.infolist()
            count = len(infos)
            names = [info.filename for info in infos]
            if len(names) != len({name.casefold() for name in names}):
                errors.append("ZIP contains duplicate paths")
            if set(names) != set(expected):
                errors.append("ZIP contains missing or extra paths")
            for info in infos:
                if not safe_relative(info.filename) or info.filename not in expected:
                    errors.append("ZIP contains a non-allowlisted or unsafe path")
                    continue
                relative = expected[info.filename]
                if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                    errors.append(f"{relative}: ZIP file entry required")
                    continue
                if info.file_size > 5 * 1024 * 1024:
                    errors.append(f"{relative}: ZIP file too large")
                    continue
                data = pack.read(info)
                errors.extend(check_file_bytes(relative, data))
                if hashlib.sha256(data).digest() != hashlib.sha256((root / relative).read_bytes()).digest():
                    errors.append(f"{relative}: ZIP content differs from source")
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        errors.append(f"ZIP is unreadable: {type(exc).__name__}")
    return dict(passed=not errors, files=count, errors=errors)


def build(root=ROOT):
    root = Path(root).resolve()
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
    audit = audit_archive(archive, root)
    if not audit["passed"]:
        raise RuntimeError(json.dumps(audit, ensure_ascii=False))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return dict(archive=archive.name, files=len(manifest["files"]),
                bytes=archive.stat().st_size, sha256=digest, audit=audit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, help="Audit an existing ZIP without writing")
    args = parser.parse_args()
    result = audit_archive(args.audit) if args.audit else build()
    print(json.dumps(result, ensure_ascii=False))
    if args.audit and not result["passed"]:
        raise SystemExit(1)
