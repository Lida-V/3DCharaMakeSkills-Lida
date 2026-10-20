"""Read-only checks for an explicitly selected FBX upload file.

Copyright (c) 2026 Lida. Lida Attribution License 1.0; see ../LICENSE.
This standard-library helper does not parse FBX scenes, launch a 3D application,
contact a service, or decide whether a model looks or moves correctly. Importing
the module and requesting help do not read model files or create reports.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys


DEFAULT_MAX_BYTES = 150_000_000
HEADER_BYTES = 65_536
BINARY_MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
SCHEMA = "lida-fbx-file-check-1"
UNINSPECTED = [
    "Full FBX structure, scene parsing, and import/export compatibility",
    "Mesh geometry, topology, normals, and penetration",
    "Bones, hierarchy, bind pose, humanoid/VRM mapping, and skin weights",
    "Images, textures, materials, UVs, and shape keys",
    "Animation, intermediate poses, motion continuity, and saved-file playback",
    "Appearance, reference-image agreement, and artistic quality",
    "Service acceptance, account limits, and current upload requirements",
]


class FileCheckError(Exception):
    """An input/output error whose message contains no private absolute path."""


def positive_bytes(value):
    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer byte count") from error
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer byte count")
    return result


def ascii_header_version(block):
    """Read one root-level version from a closed header block, not later nodes."""
    # Quoted creator strings and comments can contain braces. This only walks the
    # identifying header, not FBX scene objects or properties.
    cleaned = re.sub(rb'"(?:\\.|[^"\\])*"|;[^\r\n]*',
                     lambda match: b'""' if match.group(0).startswith(b'"') else b"", block)
    depth = 1
    versions = []
    for line in cleaned.splitlines():
        if depth == 1:
            field = re.fullmatch(rb"[ \t]*FBXVersion[ \t]*:[ \t]*(\d+)[ \t]*", line)
            if field:
                versions.append(int(field.group(1)))
        for value in line:
            if value == ord("{"):
                depth += 1
            elif value == ord("}"):
                depth -= 1
                if depth == 0:
                    return versions[0] if len(versions) == 1 else None
    return None


def identify_header(header):
    """Recognize identifying header fields only; never validate the scene body."""
    if header.startswith(BINARY_MAGIC):
        if len(header) < len(BINARY_MAGIC) + 4:
            return {"condition_passed": False, "status": "incomplete_binary_header"}
        version = struct.unpack_from("<I", header, len(BINARY_MAGIC))[0]
        if not version:
            return {"condition_passed": False, "status": "invalid_binary_version", "version": version}
        return {"condition_passed": True, "status": "recognized_binary_header", "version": version}
    if header.startswith(b"Kaydara FBX Binary"):
        return {"condition_passed": False, "status": "binary_header_mismatch"}
    ascii_head = header.removeprefix(b"\xef\xbb\xbf").lstrip(b" \t\r\n")
    project = re.match(rb";[ \t]*FBX[ \t]+(\d+)\.(\d+)\.(\d+)[ \t]+project file(?:[ \t]*\r?\n|[ \t]*$)",
                       ascii_head, re.IGNORECASE)
    if project and b"\x00" not in ascii_head:
        extension = re.search(rb"(?:^|\n)[ \t]*FBXHeaderExtension[ \t]*:[ \t]*\{", ascii_head)
        version = ascii_header_version(ascii_head[extension.end():]) if extension else None
        expected_version = sum(int(part) * scale for part, scale in zip(project.groups(), (1000, 100, 10)))
        if version is not None:
            if version == expected_version and version > 0:
                return {"condition_passed": True, "status": "recognized_ascii_header", "version": version}
            return {"condition_passed": False, "status": "ascii_version_mismatch", "version": version}
        return {"condition_passed": False, "status": "incomplete_ascii_header"}
    return {"condition_passed": False, "status": "unrecognized_header_format_unverified"}


def read_fingerprint(path):
    """Hash the complete regular file while keeping only a bounded header."""
    digest = hashlib.sha256()
    size = 0
    header = bytearray()
    try:
        with path.open("rb") as stream:
            initial = os.fstat(stream.fileno())
            if not stat.S_ISREG(initial.st_mode):
                raise FileCheckError("Input must be a regular file.")
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                header.extend(chunk[:max(0, HEADER_BYTES - len(header))])
            final = os.fstat(stream.fileno())
    except OSError as error:
        raise FileCheckError("Could not read the selected input file.") from error
    identity = (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)
    final_identity = (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
    if identity != final_identity or size != final.st_size:
        raise FileCheckError("Input changed during reading; retry with a stable file.")
    return {"size_bytes": size, "sha256": digest.hexdigest(), "header": bytes(header), "identity": identity}


def check_file(input_path, report_path, max_bytes=DEFAULT_MAX_BYTES):
    """Write one new report; an existing output or an input alias is refused."""
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        raise FileCheckError("Maximum bytes must be a positive integer.")
    source = Path(input_path).expanduser()
    output = Path(report_path).expanduser()
    if ":" in output.name:
        raise FileCheckError("Report must be a normal file, not an alternate data stream.")
    try:
        source_resolved = source.resolve(strict=True)
        output_resolved = output.resolve(strict=False)
        if source_resolved == output_resolved:
            raise FileCheckError("Report must be a new file distinct from the input.")
        if output.exists() or output.is_symlink():
            raise FileCheckError("Report already exists; choose a new report file.")
        if not source_resolved.is_file():
            raise FileCheckError("Input must be an existing regular file.")
        if not output.parent.is_dir():
            raise FileCheckError("Report parent directory must already exist.")
    except (OSError, RuntimeError) as error:
        raise FileCheckError("Could not resolve the selected input or report location.") from error
    before = read_fingerprint(source)
    checks = {
        "fbx_extension": {"condition_passed": source.suffix.lower() == ".fbx"},
        "nonempty_file": {"condition_passed": before["size_bytes"] > 0},
        "size_limit": {"condition_passed": before["size_bytes"] <= max_bytes},
        "identifying_header_only": identify_header(before["header"]),
    }
    after = read_fingerprint(source)
    if before["identity"] != after["identity"] or before["sha256"] != after["sha256"]:
        raise FileCheckError("Input changed between checks; retry with a stable file.")
    file_checks_passed = all(item["condition_passed"] for item in checks.values())
    report = {
        "schema": SCHEMA,
        "tool": "lida_file_check",
        "file_checks_passed": file_checks_passed,
        "check_scope": "Only filename extension, nonempty size, byte limit, identifying header, and observed source preservation",
        "input": {"name": source.name, "size_bytes": before["size_bytes"], "sha256": before["sha256"]},
        "limits": {"max_bytes": max_bytes, "default_bytes_definition": "150 MB = 150,000,000 bytes; service requirements remain unchecked"},
        "checks": checks,
        "source_preservation": {"sha256_before": before["sha256"], "sha256_after": after["sha256"],
                                "equal_at_observed_reads": True},
        "uninspected": list(UNINSPECTED),
        "next_step": "Compare controlled reference images and inspect motion in a 3D application; do not treat these file checks as model approval.",
    }
    try:
        # Exclusive creation also refuses a report/symlink created after preflight.
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise FileCheckError("Report must be a regular file.")
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except OSError as error:
        raise FileCheckError("Could not create the new report; existing files were not overwritten.") from error
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="lida_file_check.py", description=__doc__)
    parser.add_argument("--input", required=True, help="Explicit FBX upload file; read only")
    parser.add_argument("--report", required=True, help="New JSON report file in an existing directory; never overwritten")
    parser.add_argument("--max-bytes", type=positive_bytes, default=DEFAULT_MAX_BYTES,
                        help="Positive byte limit (default: 150000000 decimal bytes)")
    args = parser.parse_args(argv)
    try:
        report = check_file(args.input, args.report, args.max_bytes)
    except FileCheckError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"file_checks_passed": report["file_checks_passed"],
                      "report_name": Path(args.report).name,
                      "model_quality": "not_inspected"}, ensure_ascii=False))
    return 0 if report["file_checks_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
