# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Before deleting or moving work files, find what still depends on them.

blend-refs: --inputs KEEP1.blend [KEEP2.blend ...] --report NEW.json       (Blender, background)
impact:     --targets PATH [PATH ...] [--refs REFS.json ...] [--scan DIR_OR_FILE ...] --report NEW.json
            (ordinary Python)

Cleaning up a work folder breaks things in two quiet ways: a kept blend reads an image from the
folder through a relative path, or a kept script reads a file there. blend-refs opens each blend you
intend to keep and lists every external file it reads (images, libraries, sounds, fonts, caches,
movie clips, volumes) with the resolved path, whether it exists and whether it is packed. impact
takes the paths you intend to delete or move and reports (a) external references of those blends
that fall inside the targets and (b) text files (scripts, notes, configs) outside the targets that
mention a target by path, by its last two path parts, or by the name of a file inside it.

Nothing is deleted, moved or modified; blends are opened read-only and never saved. Reports hold
local paths and are working notes, not material to publish. Exit codes: 0 nothing depends on the
targets (blend-refs: nothing missing); 2 dependencies or missing files found; 1 invalid input or
I/O error. A clean report covers the listed blends and scanned folders only.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys


REPORT_SCHEMA = "lida.reference-check.report.v1"
TEXT_SUFFIXES = {".py", ".sh", ".ps1", ".cmd", ".bat", ".json", ".md", ".txt", ".toml", ".yaml", ".yml", ".js", ".ts", ".cs", ".cfg", ".ini"}
SKIP_FOLDERS = {".git", "__pycache__", "node_modules", "Library", ".venv"}
UNVERIFIED = [
    "blends, scripts and folders that were not listed (other projects may read the targets too)",
    "paths built at run time from variables or arguments that never appear as text",
    "files read by applications other than Blender (engines, editors) unless their configs were scanned",
    "whether a mention is live code or a historical note; read the listed lines",
]


def _norm(path):
    return os.path.normcase(os.path.abspath(str(path))).replace("\\", "/")


def _inside(path, target):
    path, target = _norm(path), _norm(target)
    return path == target or path.startswith(target.rstrip("/") + "/")


def collect_names(targets, limit=4000, min_length=8):
    """File names inside the targets that are distinctive enough to search for."""
    names = {}
    for target in targets:
        target = Path(target)
        files = [target] if target.is_file() else (p for p in target.rglob("*") if p.is_file())
        for path in files:
            if len(names) >= limit:
                return names
            if len(path.name) >= min_length and path.suffix:
                names.setdefault(path.name.lower(), str(target))
    return names


def scan_text(path, text, targets, names):
    """Mentions of the targets in one text; returns a list of {target, kind, line, text}."""
    found = []
    lowered = re.sub("/+", "/", text.replace("\\", "/").lower())      # escaped and doubled separators count as one
    lines = None
    keys = []
    for target in targets:
        full = _norm(target).lower()
        parts = [p for p in full.split("/") if p]
        keys.append((str(target), "path", full))
        if len(parts) >= 2:
            keys.append((str(target), "last two parts", "/".join(parts[-2:])))
    for name, target in names.items():
        keys.append((target, "file name", name))
    seen = set()
    for target, kind, needle in keys:
        if needle not in lowered:
            continue
        if lines is None:
            lines = lowered.split("\n")
            raw = text.split("\n")
        for number, line in enumerate(lines):
            if needle in line and (target, number) not in seen:
                seen.add((target, number))
                found.append({"file": str(path), "target": target, "kind": kind, "line": number + 1, "text": raw[number].strip()[:200]})
                if len(found) >= 200:
                    return found
    return found


def analyse_impact(targets, refs=(), scan=(), max_bytes=4 * 1024 * 1024):
    """Core of impact. refs: reports of blend-refs (dicts). scan: folders or files to read as text."""
    targets = [Path(t).expanduser() for t in targets]
    if not targets:
        raise ValueError("Give at least one target")
    missing = [t.name for t in targets if not t.exists()]
    if missing:
        raise ValueError("Targets not found: " + ", ".join(missing))
    broken = []
    for report in refs:
        if report.get("schema") != REPORT_SCHEMA or report.get("command") != "blend-refs":
            raise ValueError("--refs must be reports of blend-refs")
        for blend in report.get("blends", []):
            if any(_inside(blend["path"], t) for t in targets):
                continue                                    # the blend itself goes away with the target
            for item in blend.get("external", []):
                if item["packed"]:
                    continue
                hit = [str(t) for t in targets if _inside(item["resolved"], t)]
                if hit:
                    broken.append({"blend": blend["path"], "kind": item["kind"], "name": item["name"], "resolved": item["resolved"], "target": hit[0]})
    names = collect_names(targets)
    mentions, scanned = [], 0
    for root in scan:
        root = Path(root).expanduser()
        if not root.exists():
            raise ValueError("Scan path not found: " + root.name)
        if root.is_file():
            files = [root]
        else:
            files = []
            for folder, folders, entries in os.walk(root):
                folders[:] = [f for f in folders if f not in SKIP_FOLDERS and not any(_inside(Path(folder) / f, t) for t in targets)]
                files.extend(Path(folder) / entry for entry in entries)
        for path in files:
            if path.suffix.lower() not in TEXT_SUFFIXES or any(_inside(path, t) for t in targets):
                continue
            try:
                if path.stat().st_size > max_bytes:
                    continue
                text = path.read_bytes().decode("utf-8", "replace")
            except OSError:
                continue
            scanned += 1
            mentions.extend(scan_text(path, text, targets, names))
    strong = [m for m in mentions if m["kind"] != "file name"]
    weak = [m for m in mentions if m["kind"] == "file name"]
    warnings = []
    if broken:
        warnings.append("%d external references of kept blends lie inside the targets and would break" % len(broken))
    if strong:
        warnings.append("%d lines in %d kept text files mention a target path" % (len(strong), len({m["file"] for m in strong})))
    if weak:
        warnings.append("%d lines mention the name of a file inside a target (weaker evidence; read them)" % len(weak))
    return {"targets": [str(t) for t in targets],
            "summary": {"would_break": len(broken), "path_mentions": len(strong), "name_mentions": len(weak), "text_files_scanned": scanned,
                        "blends_checked": sum(len(r.get("blends", [])) for r in refs), "safe": not warnings},
            "would_break": broken, "path_mentions": strong, "name_mentions": weak, "warnings": warnings}


# ---------------------------------------------------------------- Blender side

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("blend-refs needs Blender Python; impact works in ordinary Python") from error
    return bpy


def blend_refs(paths):
    """Open each blend read-only and list its external files. Returns the report body."""
    bpy = _bpy()
    blends, warnings = [], []
    for path in paths:
        path = Path(path).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".blend":
            raise ValueError("Input must be an existing .blend file: " + path.name)
        before = _file_hash(path)
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
        external = []

        def add(kind, block, raw, packed=False, library=None):
            if not raw:
                return
            resolved = os.path.abspath(bpy.path.abspath(raw, library=library))
            external.append({"kind": kind, "name": block.name, "raw": raw, "resolved": resolved.replace("\\", "/"),
                             "relative": raw.startswith("//"), "exists": os.path.exists(resolved), "packed": bool(packed)})

        for image in bpy.data.images:
            if image.source in ("FILE", "SEQUENCE", "MOVIE", "TILED"):
                add("image", image, image.filepath, image.packed_file is not None, image.library)
        for library in bpy.data.libraries:
            add("library", library, library.filepath, library.packed_file is not None)
        for sound in bpy.data.sounds:
            add("sound", sound, sound.filepath, sound.packed_file is not None, sound.library)
        for font in bpy.data.fonts:
            if font.filepath != "<builtin>":
                add("font", font, font.filepath, font.packed_file is not None, font.library)
        for clip in bpy.data.movieclips:
            add("movie clip", clip, clip.filepath, False, clip.library)
        for cache in bpy.data.cache_files:
            add("cache", cache, cache.filepath, False, cache.library)
        for volume in getattr(bpy.data, "volumes", []):
            add("volume", volume, volume.filepath, False, volume.library)
        lost = [e for e in external if not e["exists"] and not e["packed"]]
        if lost:
            warnings.append("%s: %d external files are already missing" % (path.name, len(lost)))
        if _file_hash(path) != before:
            raise RuntimeError("Input SHA changed during command: " + path.name)
        blends.append({"path": str(path).replace("\\", "/"), "name": path.name, "sha256": before,
                       "external_files": sum(1 for e in external if not e["packed"]), "packed_files": sum(1 for e in external if e["packed"]),
                       "missing": len(lost), "folders": sorted({os.path.dirname(e["resolved"]) for e in external if not e["packed"]}),
                       "external": external})
    return {"blends": blends, "summary": {"blends": len(blends), "external_files": sum(b["external_files"] for b in blends),
                                          "missing": sum(b["missing"] for b in blends)}, "warnings": warnings}


# ---------------------------------------------------------------- CLI

def _new_output(path):
    path = Path(path).expanduser()
    if path.exists() or path.is_symlink():
        raise ValueError("Refusing to overwrite an existing output: " + path.name)
    path = path.resolve()
    if not path.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    return path


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_report(path, report):
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("blend-refs")
    sub.add_argument("--inputs", nargs="+", required=True, type=Path, help="blends you intend to keep")
    sub.add_argument("--report", required=True, type=Path)
    sub = commands.add_parser("impact")
    sub.add_argument("--targets", nargs="+", required=True, type=Path, help="files or folders you intend to delete or move")
    sub.add_argument("--refs", nargs="+", default=[], type=Path, help="reports of blend-refs for the blends you keep")
    sub.add_argument("--scan", nargs="+", default=[], type=Path, help="folders or files with scripts and notes you keep")
    sub.add_argument("--report", required=True, type=Path)
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
    report_path = None
    try:
        report_path = _new_output(args.report)
        if args.command == "blend-refs":
            if not _bpy().app.background:
                raise ValueError("Run blend-refs in a separate Blender background process")
            report = blend_refs(args.inputs)
        else:
            refs = []
            for path in args.refs:
                with path.expanduser().resolve().open("r", encoding="utf-8") as stream:
                    refs.append(json.load(stream))
            report = analyse_impact(args.targets, refs, args.scan)
        report.update({"schema": REPORT_SCHEMA, "command": args.command, "unverified": list(UNVERIFIED),
                       "status": "completed_with_findings" if report["warnings"] else "completed"})
        code = 2 if report["warnings"] else 0
        _write_report(report_path, report)
        print(json.dumps({"command": args.command, "status": report["status"], "summary": report["summary"],
                          "report": report_path.name, "exit_code": code}, ensure_ascii=False))
        return code
    except Exception as error:
        report = {"schema": REPORT_SCHEMA, "command": args.command, "status": "error",
                  "error_type": type(error).__name__, "message": str(error)}
        if report_path is not None and not report_path.exists():
            try:
                _write_report(report_path, report)
            except OSError:
                pass
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
