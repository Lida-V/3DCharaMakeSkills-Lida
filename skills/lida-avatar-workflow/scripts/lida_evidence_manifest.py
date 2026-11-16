# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Tie review images and videos to the exact saved model they were made from. Ordinary Python only.

record: --sources MODEL.blend [MODEL.vrm ...] --media SHEET.jpg TURN.mp4 [...] --manifest NEW.json [--note TEXT]
verify: --manifest MANIFEST.json [--report NEW.json]

A model is saved again under the same name, and an older video is then shown as proof of the new
version. record writes, next to the media, a manifest with the size and SHA-256 of every source
model and every image or video made from it. verify hashes the files again and says which media
are stale (their source changed after they were made), replaced or missing. Paths are stored
relative to the manifest, never absolute, so a moved folder still verifies and no local path leaks.

Nothing is modified except the new manifest or report. Exit codes: 0 recorded, or everything still
matches; 2 something changed, is stale or is missing; 1 invalid input or I/O error. A matching hash
proves which file was shown, not that the review covered what matters.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys


MANIFEST_SCHEMA = "lida.evidence-manifest.v1"
REPORT_SCHEMA = "lida.evidence-manifest.report.v1"


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _entry(path, base):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError("File not found: " + path.name)
    try:
        relative = Path(os.path.relpath(path, base)).as_posix()
    except ValueError as error:
        raise ValueError("Keep the manifest on the same drive as " + path.name + " so that a relative path can be stored") from error
    return {"path": relative, "name": path.name, "bytes": path.stat().st_size, "sha256": file_hash(path)}


def build_manifest(sources, media, manifest_path, note=None):
    """Return the manifest dict for the given files; paths are relative to the manifest's folder."""
    base = Path(manifest_path).expanduser().resolve().parent
    if not sources or not media:
        raise ValueError("Give at least one source and one media file")
    manifest = {"schema": MANIFEST_SCHEMA,
                "recorded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sources": [_entry(p, base) for p in sources], "media": [_entry(p, base) for p in media]}
    if note:
        manifest["note"] = note
    overlap = {e["path"] for e in manifest["sources"]} & {e["path"] for e in manifest["media"]}
    if overlap:
        raise ValueError("A file is listed both as source and as media: " + ", ".join(sorted(overlap)))
    return manifest


def verify_manifest(manifest, manifest_path):
    """Hash the listed files again; return the report body."""
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("Not an evidence manifest of this tool")
    base = Path(manifest_path).expanduser().resolve().parent

    def state(entry):
        path = base / entry["path"]
        if not path.is_file():
            return "missing"
        return "same" if path.stat().st_size == entry["bytes"] and file_hash(path) == entry["sha256"] else "changed"

    sources = [{"path": e["path"], "state": state(e)} for e in manifest["sources"]]
    source_moved = [s["path"] for s in sources if s["state"] != "same"]
    media = []
    for entry in manifest["media"]:
        now = state(entry)
        if now == "same" and source_moved:
            now = "stale"                                   # the picture is intact, but it no longer shows the current model
        media.append({"path": entry["path"], "state": now})
    counts = {}
    for item in sources + media:
        counts[item["state"]] = counts.get(item["state"], 0) + 1
    warnings = []
    if source_moved:
        warnings.append("Sources changed or missing since the media were recorded: " + ", ".join(source_moved)
                        + ". Render the media again from the current version or label them as the old version.")
    replaced = [m["path"] for m in media if m["state"] in ("changed", "missing")]
    if replaced:
        warnings.append("Media changed or missing since they were recorded: " + ", ".join(replaced))
    return {"recorded_utc": manifest.get("recorded_utc"), "note": manifest.get("note"),
            "summary": {"sources": len(sources), "media": len(media), "states": counts, "all_match": not warnings},
            "sources": sources, "media": media, "warnings": warnings}


def _new_output(path):
    path = Path(path).expanduser()
    if path.exists() or path.is_symlink():
        raise ValueError("Refusing to overwrite an existing output: " + path.name)
    path = path.resolve()
    if not path.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    return path


def _write_json(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        json.dump(data, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("record")
    sub.add_argument("--sources", nargs="+", required=True, type=Path, help="saved models the media were made from")
    sub.add_argument("--media", nargs="+", required=True, type=Path, help="images and videos made from those models")
    sub.add_argument("--manifest", required=True, type=Path)
    sub.add_argument("--note")
    sub = commands.add_parser("verify")
    sub.add_argument("--manifest", required=True, type=Path)
    sub.add_argument("--report", type=Path)
    return parser


def _safe_console():
    """Names the console cannot encode are escaped instead of failing after the report is written."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None):
    _safe_console()
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parser().parse_args(argv)
    try:
        if args.command == "record":
            target = _new_output(args.manifest)
            manifest = build_manifest(args.sources, args.media, target, args.note)
            _write_json(target, manifest)
            print(json.dumps({"command": "record", "status": "completed", "manifest": target.name,
                              "sources": len(manifest["sources"]), "media": len(manifest["media"]), "exit_code": 0}, ensure_ascii=False))
            return 0
        report_path = _new_output(args.report) if args.report else None
        source = args.manifest.expanduser().resolve()
        if not source.is_file():
            raise ValueError("Manifest not found: " + source.name)
        with source.open("r", encoding="utf-8") as stream:
            report = verify_manifest(json.load(stream), source)
        report.update({"schema": REPORT_SCHEMA, "command": "verify", "manifest": source.name,
                       "status": "completed_with_findings" if report["warnings"] else "completed"})
        code = 2 if report["warnings"] else 0
        if report_path is not None:
            _write_json(report_path, report)
        print(json.dumps({"command": "verify", "status": report["status"], "summary": report["summary"],
                          "warnings": report["warnings"], "exit_code": code}, ensure_ascii=False))
        return code
    except Exception as error:
        print(json.dumps({"schema": REPORT_SCHEMA, "command": args.command, "status": "error",
                          "error_type": type(error).__name__, "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
