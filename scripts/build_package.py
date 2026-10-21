"""Build a deterministic allowlisted ZIP and audit its completed contents."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import stat
import urllib.request
from urllib.parse import urlsplit
import zipfile
from validate import (ROOT, validate, check_file_bytes, safe_relative, reference_declaration,
                      check_reference_bytes, safe_file_path)


class ReferenceHttpsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if (parsed.scheme != "https" or parsed.hostname not in {
                "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
                or parsed.username or parsed.password or parsed.port not in {None, 443}):
            raise ValueError("Reference download redirect is outside official HTTPS hosts")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch_reference_model(root=ROOT):
    """Explicit acquisition only: verify the pinned archive before creating one file."""
    root = Path(root).resolve()
    source = validate(root)
    if not source["passed"]:
        raise RuntimeError(json.dumps(source, ensure_ascii=False))
    manifest = json.loads((root / "publication-manifest.json").read_text(encoding="utf-8"))
    reference, errors = reference_declaration(manifest)
    if errors or reference is None:
        raise RuntimeError("No valid bundled reference model declaration")
    target = root / reference["path"]
    if not safe_file_path(target, root):
        raise RuntimeError("Reference model target is outside the source folder or a symlink")
    if target.exists():
        if not target.is_file() or check_reference_bytes(reference, target.read_bytes()):
            raise RuntimeError("Existing reference model differs; it will not be overwritten")
        return dict(acquired=False, present=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), ReferenceHttpsOnly())
    request = urllib.request.Request(reference["archive_url"], headers={"User-Agent": "Lida-Skills-Reference-Build/1.0"})
    with opener.open(request, timeout=30) as response:
        raw = response.read(reference["archive_bytes"] + 1)
    if len(raw) != reference["archive_bytes"] or hashlib.sha256(raw).hexdigest() != reference["archive_sha256"]:
        raise RuntimeError("Reference archive size or SHA256 mismatch")
    prefix = reference["archive_member"].rsplit("/", 1)[0] + "/"
    allowed = {prefix + name for name in ("README.md", "README.en.md", "MODEL-TERMS.md",
                "MODEL-TERMS.en.md", "reference-manifest.json", "SHA256SUMS.txt")}
    allowed.add(reference["archive_member"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if (set(info.filename for info in infos) != allowed or len(infos) != len(allowed)
                or any(not safe_relative(info.filename) or info.is_dir()
                       or stat.S_ISLNK(info.external_attr >> 16) for info in infos)):
            raise RuntimeError("Reference archive contains unexpected or unsafe files")
        info = archive.getinfo(reference["archive_member"])
        if info.file_size != reference["bytes"]:
            raise RuntimeError("Reference model member has the wrong byte size")
        data = archive.read(info)
    errors = check_reference_bytes(reference, data)
    if errors:
        raise RuntimeError(json.dumps(errors))
    target.parent.mkdir(parents=True, exist_ok=True)
    if not safe_file_path(target, root):
        raise RuntimeError("Reference model target changed or is a symlink")
    # x prevents accidental replacement even if another process created the target.
    with target.open("xb") as output:
        output.write(data)
    return dict(acquired=True, present=True, bytes=len(data), sha256=reference["sha256"])


def package_files(manifest):
    reference, errors = reference_declaration(manifest)
    if errors:
        raise RuntimeError(json.dumps(errors))
    return sorted([*manifest["files"], *([reference["path"]] if reference else [])])


def audit_archive(archive, root=ROOT):
    """Read only: compare the finished archive against the validated source."""
    root = Path(root).resolve()
    report = validate(root, require_reference_model=True)
    if not report["passed"]:
        return dict(passed=False, files=0, errors=["Source pack is invalid", *report["errors"]])
    manifest = json.loads((root / "publication-manifest.json").read_text(encoding="utf-8"))
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    prefix = f"3DCharaMakeSkills-Lida-{version}/"
    expected = {prefix + name: name for name in package_files(manifest)}
    reference, _ = reference_declaration(manifest)
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
                is_reference = reference and relative == reference["path"]
                limit = reference["bytes"] if is_reference else 5 * 1024 * 1024
                if info.file_size > limit:
                    errors.append(f"{relative}: ZIP file too large")
                    continue
                data = pack.read(info)
                errors.extend(check_reference_bytes(reference, data) if is_reference else check_file_bytes(relative, data))
                if hashlib.sha256(data).digest() != hashlib.sha256((root / relative).read_bytes()).digest():
                    errors.append(f"{relative}: ZIP content differs from source")
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        errors.append(f"ZIP is unreadable: {type(exc).__name__}")
    return dict(passed=not errors, files=count, errors=errors)


def build(root=ROOT, fetch_reference=False):
    root = Path(root).resolve()
    if fetch_reference:
        fetch_reference_model(root)
    report = validate(root, require_reference_model=True)
    if not report["passed"]:
        raise RuntimeError(json.dumps(report, ensure_ascii=False))
    manifest = json.loads((root / "publication-manifest.json").read_text(encoding="utf-8"))
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    output = root / "dist"
    output.mkdir(exist_ok=True)
    archive = output / f"3DCharaMakeSkills-Lida-{version}.zip"
    prefix = f"3DCharaMakeSkills-Lida-{version}/"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as pack:
        for relative in package_files(manifest):
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
    return dict(archive=archive.name, files=len(package_files(manifest)),
                bytes=archive.stat().st_size, sha256=digest, audit=audit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, help="Audit an existing ZIP without writing")
    parser.add_argument("--fetch-reference-model", action="store_true",
                        help="Explicitly fetch the pinned official reference asset if missing, then build")
    args = parser.parse_args()
    if args.audit and args.fetch_reference_model:
        parser.error("--audit is read-only and cannot be combined with acquisition")
    result = audit_archive(args.audit) if args.audit else build(fetch_reference=args.fetch_reference_model)
    print(json.dumps(result, ensure_ascii=False))
    if args.audit and not result["passed"]:
        raise SystemExit(1)
