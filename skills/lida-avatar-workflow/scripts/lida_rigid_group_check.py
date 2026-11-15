# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Check that hard ornaments (a gem and its setting, a star and its stone) move as one piece on a rig.

Run in Blender with ``--background --factory-startup --python THIS.py -- check``.
check: --input MODEL.blend --rig Armature --group Gem Setting [--group Bodice@GemMaterial ...] --report NEW.json
       [--angle 30] [--tolerance-mm 0.3]

A hard ornament splits when its parts, or its vertices, carry different bone weights: bend the
joint and the stone leaves the setting. This command reads the weights of every object in a group,
turns each influencing bone by +/- angle about its three axes with linear blend skinning, fits the
best rigid motion to the whole group and reports how far any vertex strays from it (mm). It also
counts the distinct weight rows and proposes the mean row as a single shared weight. A group with
one row on one bone is exactly rigid; one row over several bones still shears a little, and the
residual says how much.

The numeric core needs numpy only. The blend is opened read-only and never saved; poses are computed
from rest data, so the scene is not posed. Exit codes: 0 every group stays within tolerance; 2 a group
splits, has unweighted vertices or another warning; 1 invalid input, I/O or execution error.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


REPORT_SCHEMA = "lida.rigid-group.report.v1"
DEFAULTS = {"angle": 30.0, "tolerance_mm": 0.3, "row_digits": 4}
UNVERIFIED = [
    "real poses and animation (each influencing bone is turned alone by a fixed angle)",
    "dual-quaternion or volume-preserving skinning, shape keys, constraints and other modifiers",
    "whether the ornament sinks into or floats off the surface under it",
    "appearance in renders",
]


def kabsch_residual(rest, moved):
    """Distance of every moved point from the best rigid motion of rest; returns (residuals, rotation)."""
    rest, moved = np.asarray(rest, float), np.asarray(moved, float)
    a, b = rest - rest.mean(0), moved - moved.mean(0)
    u, _, vt = np.linalg.svd(a.T @ b)
    sign = np.sign(np.linalg.det(u @ vt)) or 1.0
    rotation = (u * np.array([1.0, 1.0, sign])) @ vt
    return np.linalg.norm(a @ rotation - b, axis=1), rotation


def rotation_about(point, axis, degrees):
    """4x4 rotation by degrees about the unit axis through point."""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    angle = math.radians(degrees)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    rotation = np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = np.asarray(point, float) - rotation @ np.asarray(point, float)
    return matrix


def descendants(parents, bone):
    """Indices of bone and every bone below it; parents[i] is the parent index or -1."""
    chosen = {bone}
    changed = True
    while changed:
        changed = False
        for index, parent in enumerate(parents):
            if parent in chosen and index not in chosen:
                chosen.add(index)
                changed = True
    return chosen


def skin(points, weights, matrices):
    """Linear blend skinning: points (n,3), weights (n,b), matrices (b,4,4)."""
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    moved = np.einsum("bij,nj->nbi", matrices, homogeneous)[:, :, :3]
    return (moved * weights[:, :, None]).sum(1)


def analyse_group(points, weights, bone_names, parents, heads, axes, options=None, unit_mm=1000.0):
    """Core. weights (n, bones) for the rig's deform bones; heads (b,3) and axes (b,3,3 rows = bone X,Y,Z)."""
    opt = dict(DEFAULTS)
    opt.update({k: v for k, v in (options or {}).items() if v is not None})
    if opt["angle"] <= 0 or opt["tolerance_mm"] < 0:
        raise ValueError("angle must be positive and tolerance_mm non-negative")
    points, weights = np.asarray(points, float), np.asarray(weights, float)
    total = weights.sum(1)
    unweighted = int((total < 1e-6).sum())
    normal = weights / np.maximum(total, 1e-12)[:, None]
    used = np.nonzero(normal.max(0) > 1e-6)[0]
    rows = np.unique(np.round(normal[total >= 1e-6], int(opt["row_digits"])), axis=0)
    bones = [{"bone": bone_names[i], "min": round(float(normal[:, i].min()), 4), "max": round(float(normal[:, i].max()), 4)} for i in used]
    worst = {"residual_mm": 0.0}
    for bone in used:
        below = descendants(parents, int(bone))
        for axis_index, axis_name in enumerate("XYZ"):
            for sign in (1.0, -1.0):
                turn = rotation_about(heads[bone], axes[bone][axis_index], sign * opt["angle"])
                matrices = np.stack([turn if i in below else np.eye(4) for i in range(len(bone_names))])
                residual = kabsch_residual(points, skin(points, normal, matrices))[0] * unit_mm
                if residual.max() > worst["residual_mm"]:
                    worst = {"residual_mm": float(residual.max()), "bone": bone_names[bone], "axis": axis_name,
                             "degrees": sign * opt["angle"], "vertex": int(residual.argmax())}
    mean = normal[total >= 1e-6].mean(0) if unweighted < len(points) else np.zeros(len(bone_names))
    result = {"vertices": int(len(points)), "unweighted_vertices": unweighted, "weight_rows": int(len(rows)), "bones": bones,
              "largest_deviation_mm": round(worst["residual_mm"], 3), "worst_pose": {k: v for k, v in worst.items() if k != "residual_mm"},
              "rigid": bool(worst["residual_mm"] <= opt["tolerance_mm"] and unweighted == 0),
              "mean_row": {bone_names[i]: round(float(mean[i]), 4) for i in np.nonzero(mean > 1e-4)[0]}}
    if len(used) == 1 and len(rows) == 1:
        result["note"] = "one bone, one row: exactly rigid"
    elif len(rows) == 1:
        result["note"] = "one shared row over several bones: the piece keeps together but shears slightly when those bones move apart"
    else:
        result["note"] = "several weight rows: parts or vertices follow different bones and separate when the joint bends"
    return result


# ---------------------------------------------------------------- Blender side

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("check needs Blender Python; the numeric core works in ordinary Python") from error
    return bpy


def check(rig, groups, options=None):
    """Return a report for groups = [[objects...], ...] on the armature object rig. Nothing changes."""
    bpy = _bpy()
    if rig is None or rig.type != "ARMATURE":
        raise ValueError("--rig must be an armature object")
    if not groups:
        raise ValueError("Give at least one group")
    scale = float(bpy.context.scene.unit_settings.scale_length) or 1.0
    world = np.array(rig.matrix_world)
    unit_mm = scale * 1000.0 * float(np.mean(np.linalg.norm(world[:3, :3], axis=0)))
    to_rig = np.linalg.inv(world)
    deform = [bone for bone in rig.data.bones if bone.use_deform]
    names = [bone.name for bone in deform]
    index = {name: i for i, name in enumerate(names)}
    parents = []
    for bone in deform:
        parent = bone.parent
        while parent is not None and parent.name not in index:
            parent = parent.parent
        parents.append(index[parent.name] if parent is not None else -1)
    heads = np.array([list(bone.head_local) for bone in deform])
    axes = np.array([np.array(bone.matrix_local)[:3, :3].T for bone in deform])
    results, warnings = [], []
    for members in groups:
        all_points, all_weights, labels = [], [], []
        for member in members:
            obj, material = member if isinstance(member, tuple) else (member, None)
            if obj is None or obj.type != "MESH":
                raise ValueError("Group members must be mesh objects")
            if not any(m.type == "ARMATURE" and m.object == rig for m in obj.modifiers):
                warnings.append(obj.name + " has no Armature modifier pointing to " + rig.name)
            if any(m.type == "ARMATURE" and m.use_deform_preserve_volume for m in obj.modifiers):
                warnings.append(obj.name + " uses preserve volume; this check assumes linear blend skinning")
            count = len(obj.data.vertices)
            flat = np.empty(count * 3)
            obj.data.vertices.foreach_get("co", flat)
            matrix = to_rig @ np.array(obj.matrix_world)
            keep = np.ones(count, bool)
            if material is not None:
                slots = [i for i, slot in enumerate(obj.material_slots) if slot.material is not None and slot.material.name == material]
                if not slots:
                    raise ValueError("Material not found on " + obj.name + ": " + material)
                keep[:] = False
                for polygon in obj.data.polygons:
                    if polygon.material_index in slots:
                        keep[list(polygon.vertices)] = True
                if not keep.any():
                    raise ValueError("No faces of " + obj.name + " use " + material)
            all_points.append((flat.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3])[keep])
            table = np.zeros((count, len(names)))
            slot = {group.index: index[group.name] for group in obj.vertex_groups if group.name in index}
            for vertex in obj.data.vertices:
                for element in vertex.groups:
                    if element.group in slot:
                        table[vertex.index, slot[element.group]] = element.weight
            all_weights.append(table[keep])
            labels.append(obj.name + ("@" + material if material else ""))
        result = analyse_group(np.concatenate(all_points), np.concatenate(all_weights), names, parents, heads, axes, options, unit_mm)
        result["objects"] = labels
        results.append(result)
        if not result["rigid"]:
            warnings.append("%s: strays %.2f mm from a rigid motion (%s)" % (" + ".join(labels), result["largest_deviation_mm"], result["note"]))
    opt = dict(DEFAULTS)
    opt.update({k: v for k, v in (options or {}).items() if v is not None})
    return {"schema": REPORT_SCHEMA, "command": "check", "rig": rig.name, "unit": "mm", "options": opt,
            "summary": {"groups": len(results), "rigid": sum(1 for r in results if r["rigid"]),
                        "split": sum(1 for r in results if not r["rigid"]),
                        "largest_deviation_mm": max(r["largest_deviation_mm"] for r in results)},
            "groups": results, "warnings": warnings, "unverified": list(UNVERIFIED),
            "status": "completed_with_findings" if warnings else "completed"}


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
    sub = commands.add_parser("check")
    sub.add_argument("--input", required=True, type=Path)
    sub.add_argument("--rig", required=True)
    sub.add_argument("--group", nargs="+", action="append", required=True, metavar="OBJECT",
                     help="objects that must move as one piece (Object or Object@Material for the faces of one material); "
                          "repeat --group for more groups")
    sub.add_argument("--report", required=True, type=Path)
    sub.add_argument("--angle", type=float)
    sub.add_argument("--tolerance-mm", type=float)
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parser().parse_args(argv)
    report_path = None
    try:
        report_path = _new_output(args.report)
        source = args.input.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".blend":
            raise ValueError("Input must be an existing .blend file")
        before_sha = _file_hash(source)
        bpy = _bpy()
        if not bpy.app.background:
            raise ValueError("Run the CLI in a separate Blender background process; use check() in an interactive session")
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)

        def find(name):
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError("Object not found: " + name)
            return obj

        def member(text):
            name, _, material = text.partition("@")
            return (find(name), material or None)

        report = check(find(args.rig), [[member(name) for name in group] for group in args.group],
                       {"angle": args.angle, "tolerance_mm": args.tolerance_mm})
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        code = 2 if report["warnings"] else 0
        _write_report(report_path, report)
        print(json.dumps({"command": "check", "status": report["status"], "summary": report["summary"],
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
