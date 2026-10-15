# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Small Blender helpers for explicit meshes; no registration or import side effects.

Run in Blender with ``--background --factory-startup --python THIS.py -- COMMAND``.
audit/snapshot: --input MODEL.blend --objects MeshA MeshB [--rig Rig] --report NEW.json
normalize-copy: same, with --rig Rig and --output-blend NEW.blend (both required).
compare: --left OLD.json --right NEW.json --report DIFF.json; ordinary Python works.

Python API functions return reports without writing files. Only normalization
creates in-memory candidate objects. main() alone opens an explicitly named blend
and writes reports/candidate files. It never saves the input or user preferences.
Exit codes: 0 completed; 2 snapshot differences or unresolved normalization;
1 invalid input, I/O or execution error. Audit findings are observations, not an
appearance grade. Boundary edges, UV repeats and empty keys can be intentional.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile


SNAPSHOT_SCHEMA = "lida.model-tools.snapshot.v1"
REPORT_SCHEMA = "lida.model-tools.report.v1"
UNVERIFIED = [
    "armature rest/pose matrices and parent transforms",
    "drivers, constraints, Geometry Nodes and modifier configuration",
    "material nodes, texture image content and external dependencies",
    "non-deform/mask groups, vertex-group locks and shape playback settings in snapshots",
    "evaluated geometry, animation, contacts and appearance",
    "exported files and behavior in the target application",
]


def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("This command needs Blender Python; compare also works in ordinary Python") from error
    return bpy


def _finite_positive(value, name, allow_zero=False):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (not allow_zero and value == 0):
        raise ValueError(name + " must be finite and " + ("nonnegative" if allow_zero else "positive"))


def _meshes(objects):
    objects = list(objects)
    if not objects:
        raise ValueError("Choose at least one explicit mesh")
    names = set()
    for obj in objects:
        if obj is None or obj.type != "MESH":
            raise ValueError("Every target must be a mesh")
        if obj.mode != "OBJECT":
            raise ValueError("Targets must be in Object Mode")
        if obj.name in names:
            raise ValueError("Duplicate target: " + obj.name)
        names.add(obj.name)
    return sorted(objects, key=lambda obj: obj.name)


def _deform_names(armature):
    if armature is None:
        return None
    if armature.type != "ARMATURE":
        raise ValueError("The explicit rig must be an armature")
    return {bone.name for bone in armature.data.bones if bone.use_deform}


def _coordinates(items):
    return [tuple(float(value) for value in item.co) for item in items]


def _is_finite(values):
    return all(math.isfinite(value) for value in values)


def _stable(value):
    """Keep non-finite values explicit while producing strict, deterministic JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": "NaN" if math.isnan(value) else "+Infinity" if value > 0 else "-Infinity"}
    if isinstance(value, dict):
        return {str(key): _stable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_stable(item) for item in value]
    return value


def _hash(value):
    encoded = json.dumps(_stable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _component(value, count):
    return {"count": count, "sha256": _hash(value)}


def _triangle_area(a, b, c):
    ab = [b[index] - a[index] for index in range(3)]
    ac = [c[index] - a[index] for index in range(3)]
    cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
    return math.sqrt(sum(value * value for value in cross)) * 0.5


def _weight_rows(obj, names):
    groups = {group.index: group.name for group in obj.vertex_groups}
    return [sorted((groups[item.group], float(item.weight)) for item in vertex.groups
                   if groups.get(item.group) in names) for vertex in obj.data.vertices]


def _audit_weights(obj, names, tolerance, max_influences):
    if names is None:
        return {"status": "not_verified", "reason": "No explicit rig was supplied"}
    problems = {key: [] for key in ("unweighted", "invalid_values", "not_normalized", "over_limit")}
    maximum_error = 0.0
    maximum_influences = 0
    for index, row in enumerate(_weight_rows(obj, names)):
        values = [value for _, value in row]
        if any(not math.isfinite(value) or value < 0 or value > 1 for value in values):
            problems["invalid_values"].append(index)
            continue
        positive = [value for value in values if value > 0]
        count = len(positive)
        maximum_influences = max(maximum_influences, count)
        error = abs(sum(positive) - 1.0)
        maximum_error = max(maximum_error, error)
        if not positive:
            problems["unweighted"].append(index)
        elif error > tolerance:
            problems["not_normalized"].append(index)
        if count > max_influences:
            problems["over_limit"].append(index)
    return {"status": "inspected", "deform_bones_only": True,
            "counts": {key: len(value) for key, value in problems.items()}, "indices": problems,
            "max_sum_error": maximum_error, "max_influences_observed": maximum_influences,
            "requested_influence_limit": max_influences, "sum_tolerance": tolerance}


def audit_meshes(objects, armature=None, *, area_epsilon=1e-12, uv_epsilon=1e-12,
                 weight_tolerance=1e-4, max_influences=4):
    """Inspect base mesh data. Return observations, never an artistic pass/fail."""
    objects = _meshes(objects)
    names = _deform_names(armature)
    for value, label in ((area_epsilon, "area_epsilon"), (uv_epsilon, "uv_epsilon"), (weight_tolerance, "weight_tolerance")):
        _finite_positive(value, label, allow_zero=True)
    if not isinstance(max_influences, int) or isinstance(max_influences, bool) or max_influences < 1:
        raise ValueError("max_influences must be a positive integer")
    results = {}
    for obj in objects:
        mesh = obj.data
        coordinates = _coordinates(mesh.vertices)
        bad_positions = [index for index, point in enumerate(coordinates) if not _is_finite(point)]
        edge_uses = {}
        duplicate_faces = []
        seen_faces = set()
        for polygon in mesh.polygons:
            face = tuple(polygon.vertices)
            key = tuple(sorted(face))
            if key in seen_faces:
                duplicate_faces.append(polygon.index)
            seen_faces.add(key)
            for a, b in zip(face, face[1:] + face[:1]):
                edge = tuple(sorted((a, b)))
                edge_uses[edge] = edge_uses.get(edge, 0) + 1
        mesh.calc_loop_triangles()
        degenerate = []
        for triangle in mesh.loop_triangles:
            points = [coordinates[index] for index in triangle.vertices]
            if all(_is_finite(point) for point in points) and _triangle_area(*points) <= area_epsilon:
                degenerate.append(triangle.index)
        uv_results = {}
        for layer in mesh.uv_layers:
            uv = [tuple(float(value) for value in item.uv) for item in layer.data]
            bad = [index for index, point in enumerate(uv) if not _is_finite(point)]
            outside = [index for index, point in enumerate(uv) if _is_finite(point) and any(value < 0 or value > 1 for value in point)]
            collapsed = []
            for triangle in mesh.loop_triangles:
                a, b, c = [uv[index] for index in triangle.loops]
                if all(_is_finite(point) for point in (a, b, c)):
                    area = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) * 0.5
                    if area <= uv_epsilon:
                        collapsed.append(triangle.index)
            uv_results[layer.name] = {"loops": len(uv), "nonfinite_loops": bad,
                                      "outside_0_1_loops": outside, "degenerate_triangles": collapsed}
        shape_results = []
        keys = mesh.shape_keys
        if keys:
            key_blocks = list(keys.key_blocks)
            for key in key_blocks:
                points = _coordinates(key.data)
                invalid = [index for index, point in enumerate(points) if not _is_finite(point)]
                reference = key.relative_key
                valid_reference = reference is not None and any(reference == item for item in key_blocks)
                reference_points = _coordinates(reference.data) if valid_reference else []
                valid_lengths = len(points) == len(coordinates) and len(reference_points) == len(points)
                changes = None
                maximum = None
                if valid_lengths and not invalid and all(_is_finite(point) for point in reference_points):
                    deltas = [math.dist(point, base) for point, base in zip(points, reference_points)]
                    changes = sum(value > 1e-7 for value in deltas)
                    maximum = max(deltas, default=0.0)
                shape_results.append({"name": key.name, "is_basis": key == key_blocks[0],
                                      "vertices": len(points), "vertex_count_matches": len(points) == len(coordinates),
                                      "relative_key": reference.name if valid_reference else None,
                                      "relative_key_valid": valid_reference, "nonfinite_vertices": invalid,
                                      "changed_vertices": changes, "max_relative_delta": maximum,
                                      "empty_relative_key": changes == 0 if changes is not None and key != key_blocks[0] and keys.use_relative else None})
        boundary = sum(value == 1 for value in edge_uses.values())
        branch = sum(value > 2 for value in edge_uses.values())
        wire = sum(tuple(sorted(edge.vertices)) not in edge_uses for edge in mesh.edges)
        results[obj.name] = {
            "geometry": {"vertices": len(coordinates), "edges": len(mesh.edges), "faces": len(mesh.polygons),
                         "triangles": len(mesh.loop_triangles), "nonfinite_vertices": bad_positions,
                         "degenerate_triangles": degenerate, "duplicate_index_faces": duplicate_faces,
                         "boundary_edges": boundary, "branch_edges": branch, "wire_edges": wire},
            "uv_missing": not bool(mesh.uv_layers), "uv_layers": uv_results,
            "weights": _audit_weights(obj, names, weight_tolerance, max_influences),
            "shape_keys": shape_results, "shape_key_mode": "RELATIVE" if keys and keys.use_relative else "ABSOLUTE" if keys else None,
        }
    return {"schema": REPORT_SCHEMA, "command": "audit", "status": "inspected", "meshes": results,
            "rig": armature.name if armature else None,
            "tolerances": {"triangle_area_local_units_squared": area_epsilon, "uv_triangle_area": uv_epsilon},
            "notes": ["Base meshes only; no automatic appearance grade.",
                      "Boundary edges, UV ranges/repeats and empty keys can be intentional.",
                      "Degenerate areas use local object coordinates; object scale is not applied.",
                      "Duplicate faces mean the same vertex IDs, not spatially coincident separate vertices."],
            "unverified": list(UNVERIFIED)}


def snapshot_meshes(objects, armature=None, *, source_path=None):
    """Hash explicitly scoped base data. Importing this module never opens files."""
    objects = _meshes(objects)
    names = _deform_names(armature)
    if source_path is None:
        source_path = _bpy().data.filepath
    if not source_path or not Path(source_path).is_file():
        raise ValueError("Snapshot needs an existing source blend for its input SHA")
    results = {}
    for obj in objects:
        mesh = obj.data
        fields = {
            "coordinates": _component(_coordinates(mesh.vertices), len(mesh.vertices)),
            "topology": _component({"vertices": len(mesh.vertices),
                                    "edges": [tuple(edge.vertices) for edge in mesh.edges],
                                    "faces": [tuple(polygon.vertices) for polygon in mesh.polygons]}, len(mesh.polygons)),
            "uv": {layer.name: _component([tuple(float(value) for value in item.uv) for item in layer.data], len(layer.data))
                   for layer in mesh.uv_layers},
            "weights": {"status": "not_verified", "reason": "No explicit rig was supplied"},
            "shape_keys": {},
            "material_slots": _component({"slots": [(slot.material.name if slot.material else None, slot.link) for slot in obj.material_slots],
                                          "polygon_material_indices": [polygon.material_index for polygon in mesh.polygons]}, len(obj.material_slots)),
        }
        if names is not None:
            fields["weights"] = {"status": "captured", "deform_bones": sorted(names),
                                 **_component(_weight_rows(obj, names), len(mesh.vertices))}
        if mesh.shape_keys:
            if not mesh.shape_keys.use_relative:
                raise ValueError("Absolute shape key playback is not supported by this snapshot: " + obj.name)
            keys = list(mesh.shape_keys.key_blocks)
            for key in keys:
                points = _coordinates(key.data)
                reference = key.relative_key
                valid_reference = reference is not None and any(reference == item for item in keys)
                base = _coordinates(reference.data) if valid_reference else []
                if len(points) != len(mesh.vertices) or len(base) != len(points):
                    raise ValueError("Shape key count/reference mismatch: " + obj.name + "/" + key.name)
                deltas = [tuple(value - start for value, start in zip(point, initial)) for point, initial in zip(points, base)]
                fields["shape_keys"][key.name] = {"relative_key": reference.name, "is_basis": key == keys[0],
                                                   **_component({"coordinates": points, "relative_deltas": deltas}, len(points))}
        results[obj.name] = fields
    return {"schema": SNAPSHOT_SCHEMA, "source": {"name": Path(source_path).name, "sha256": _file_hash(source_path)},
            "rig": armature.name if armature else None, "meshes": results,
            "comparison": "Exact captured content, local coordinates and indexed connectivity; no rounding or name normalization.",
            "notes": ["Source SHA identifies the input file, not proof that current in-memory data was saved to it.",
                      "Material slots capture names/order/link mode and polygon assignments, not nodes or image content.",
                      "Shape hashes include key coordinates and deltas against their declared relative key, including Basis coordinates.",
                      "Shape values, mute flags and playback settings are not captured; absolute keys are refused.",
                      "Mesh names, vertex order, face order and group names remain significant."],
            "unverified": list(UNVERIFIED)}


def _validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("Expected " + SNAPSHOT_SCHEMA)
    if not isinstance(snapshot.get("meshes"), dict) or not snapshot["meshes"]:
        raise ValueError("Snapshot needs explicitly scoped meshes")
    source = snapshot.get("source", {})
    def is_sha(value):
        return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)

    def component(value, extra=()):
        return (isinstance(value, dict) and set(value) == {"count", "sha256"} | set(extra)
                and isinstance(value.get("count"), int) and not isinstance(value["count"], bool)
                and value["count"] >= 0 and is_sha(value.get("sha256")))

    if not isinstance(source, dict) or not isinstance(source.get("name"), str) or not is_sha(source.get("sha256")):
        raise ValueError("Snapshot source SHA is missing")
    required = {"coordinates", "topology", "uv", "weights", "shape_keys", "material_slots"}
    for name, fields in snapshot["meshes"].items():
        if not isinstance(name, str) or not isinstance(fields, dict) or set(fields) != required:
            raise ValueError("Unexpected or missing snapshot fields")
        for field in ("coordinates", "topology", "material_slots"):
            value = fields[field]
            if not component(value):
                raise ValueError("Invalid snapshot component: " + field)
        if not isinstance(fields["uv"], dict) or not isinstance(fields["shape_keys"], dict) or not isinstance(fields["weights"], dict):
            raise ValueError("Invalid snapshot collection")
        if any(not isinstance(key, str) or not component(value) for key, value in fields["uv"].items()):
            raise ValueError("Invalid UV snapshot component")
        for key, value in fields["shape_keys"].items():
            if (not isinstance(key, str) or not component(value, ("relative_key", "is_basis"))
                    or not isinstance(value["relative_key"], str) or not isinstance(value["is_basis"], bool)
                    or value["count"] != fields["coordinates"]["count"]):
                raise ValueError("Invalid shape key snapshot component")
        weights = fields["weights"]
        if weights.get("status") == "captured":
            bones = weights.get("deform_bones")
            if (not component(weights, ("status", "deform_bones")) or not isinstance(bones, list)
                    or not all(isinstance(bone, str) for bone in bones) or bones != sorted(set(bones))
                    or weights["count"] != fields["coordinates"]["count"]):
                raise ValueError("Invalid deform weight snapshot component")
        elif weights.get("status") == "not_verified":
            if set(weights) != {"status", "reason"} or not isinstance(weights["reason"], str):
                raise ValueError("Invalid unverified weight snapshot component")
        else:
            raise ValueError("Unknown deform weight snapshot status")


def compare_snapshots(left, right):
    """Pure Python exact field comparison. Source-file hashes are provenance only."""
    _validate_snapshot(left)
    _validate_snapshot(right)
    before, after = left["meshes"], right["meshes"]
    differences = []
    for name in sorted(set(before) | set(after)):
        if name not in before or name not in after:
            differences.append({"mesh": name, "field": "target", "change": "added" if name in after else "removed"})
            continue
        for field in sorted(before[name]):
            if before[name][field] != after[name][field]:
                differences.append({"mesh": name, "field": field, "before": before[name][field], "after": after[name][field]})
    if left.get("rig") != right.get("rig"):
        differences.append({"mesh": None, "field": "explicit_rig", "before": left.get("rig"), "after": right.get("rig")})
    unverified = list(UNVERIFIED)
    if any(fields["weights"].get("status") != "captured" for snapshot in (left, right) for fields in snapshot["meshes"].values()):
        unverified.append("deform weights on meshes without an explicit rig")
    return {"schema": REPORT_SCHEMA, "command": "compare", "status": "different" if differences else "equal_captured_fields",
            "equal": not differences, "differences": differences,
            "sources": [left["source"], right["source"]], "unverified": unverified,
            "notes": ["Equal means only captured fields; not all Blender data or visual equivalence.",
                      "Different input file SHA alone is not a mesh content difference."]}


def normalize_weights_copy(objects, armature, *, weight_tolerance=1e-4):
    """Return (candidate_objects, report); unresolved preflight creates no copies.

    Preserve all non-deform groups and locked entries. Scale only already positive
    unlocked deform entries into the remaining budget. Never invent a bone,
    transfer weights, reduce influences or save a file.
    """
    objects = _meshes(objects)
    if armature is None:
        raise ValueError("Normalization requires an explicit rig")
    names = _deform_names(armature)
    _finite_positive(weight_tolerance, "weight_tolerance")
    bpy = _bpy()
    plans = []
    unresolved = []
    for obj in objects:
        if not obj.is_editable or obj.library or obj.data.library:
            raise ValueError("Normalization requires a local editable mesh: " + obj.name)
        rigs = {modifier.object for modifier in obj.modifiers if modifier.type == "ARMATURE" and modifier.object}
        if rigs != {armature}:
            raise ValueError("Target must use exactly the explicit armature: " + obj.name)
        groups = {group.index: group for group in obj.vertex_groups if group.name in names}
        object_plan = []
        for vertex in obj.data.vertices:
            entries = [(entry.group, float(entry.weight)) for entry in vertex.groups if entry.group in groups]
            reason = None
            if any(not math.isfinite(value) or value < 0 or value > 1 for _, value in entries):
                reason = "invalid_deform_weight"
            elif sum(value for _, value in entries) <= 0:
                reason = "unweighted"
            locked = [(index, value) for index, value in entries if groups[index].lock_weight]
            unlocked = [(index, value) for index, value in entries if not groups[index].lock_weight and value > 0]
            locked_sum = sum(value for _, value in locked)
            total = sum(value for _, value in unlocked)
            if reason is None and locked_sum > 1.0 + 1e-7:
                reason = "locked_sum_exceeds_one"
            budget = max(0.0, 1.0 - locked_sum) if math.isfinite(locked_sum) else 0.0
            if reason is None and total == 0 and budget > 1e-7:
                reason = "locked_weights_leave_unfillable_budget"
            if reason:
                unresolved.append({"object": obj.name, "vertex": vertex.index, "reason": reason})
            object_plan.append([(index, budget * value / total) for index, value in unlocked] if total > 0 else [])
        plans.append((obj, object_plan))
    report = {"schema": REPORT_SCHEMA, "command": "normalize-copy", "status": "unresolved" if unresolved else "candidate",
              "unresolved": unresolved, "copies": [], "sum_tolerance": weight_tolerance,
              "notes": ["Only unlocked deform weights are normalized; masks and locked entries are retained.",
                        "No influence reduction, nearest-surface transfer or fallback assignment.",
                        "Source objects and candidates both remain at their original positions/visibility; isolate the named candidate for comparison.",
                        "Normalization is structural; motion and appearance need separate review."],
              "unverified": list(UNVERIFIED)}
    if unresolved:
        return [], report
    copies = []
    try:
        for source, plan in plans:
            result = source.copy()
            result.data = source.data.copy()
            result.name = source.name + "_NormalizedCandidate"
            (source.users_collection[0] if source.users_collection else bpy.context.collection).objects.link(result)
            copies.append(result)
            for vertex, entries in zip(result.data.vertices, plan):
                for index, value in entries:
                    result.vertex_groups[index].add([vertex.index], value, "REPLACE")
            inspected = _audit_weights(result, names, weight_tolerance, 2**31 - 1)
            if any(inspected["counts"][key] for key in ("unweighted", "invalid_values", "not_normalized")):
                raise RuntimeError("Normalized candidate failed weight verification")
            report["copies"].append({"source": source.name, "candidate": result.name, "weights": inspected})
    except Exception:
        for result in copies:
            data = result.data
            bpy.data.objects.remove(result, do_unlink=True)
            if data.users == 0:
                bpy.data.meshes.remove(data)
        raise
    return copies, report


def _new_output(path):
    path = Path(path).expanduser()
    if path.exists() or path.is_symlink():
        raise ValueError("Refusing to overwrite an existing output: " + path.name)
    path = path.resolve()
    if not path.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    return path


def _write_report(path, report):
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        json.dump(_stable(report), output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")


def _save_candidate(path):
    """Blender writes an owned temporary copy; final publication is exclusive."""
    bpy = _bpy()
    descriptor, temporary = tempfile.mkstemp(prefix=".lida-model-tools-", suffix=".blend", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    temporary.unlink()
    try:
        result = bpy.ops.wm.save_as_mainfile(filepath=str(temporary), check_existing=False, copy=True)
        if result != {"FINISHED"} or not temporary.is_file():
            raise RuntimeError("Blender did not save a candidate")
        with temporary.open("rb") as source, path.open("xb") as output:
            shutil.copyfileobj(source, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "snapshot", "normalize-copy"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
        sub.add_argument("--objects", nargs="+", required=True)
        sub.add_argument("--rig", required=command == "normalize-copy")
        sub.add_argument("--report", required=True, type=Path)
        if command == "normalize-copy":
            sub.add_argument("--output-blend", required=True, type=Path)
        if command == "audit":
            sub.add_argument("--max-influences", type=int, default=4)
    sub = commands.add_parser("compare")
    sub.add_argument("--left", required=True, type=Path)
    sub.add_argument("--right", required=True, type=Path)
    sub.add_argument("--report", required=True, type=Path)
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parser().parse_args(argv)
    report_path = None
    try:
        report_path = _new_output(args.report)
        if args.command == "compare":
            for path in (args.left, args.right):
                if report_path == path.resolve():
                    raise ValueError("Report must differ from input snapshots")
            left = json.loads(args.left.read_text(encoding="utf-8"))
            right = json.loads(args.right.read_text(encoding="utf-8"))
            report = compare_snapshots(left, right)
            code = 0 if report["equal"] else 2
        else:
            source = args.input.expanduser().resolve()
            if not source.is_file() or source.suffix.lower() != ".blend":
                raise ValueError("Input must be an existing .blend file")
            if source == report_path:
                raise ValueError("Report must differ from input")
            output = None
            if args.command == "normalize-copy":
                output = _new_output(args.output_blend)
                if output in (source, report_path) or output.suffix.lower() != ".blend":
                    raise ValueError("Candidate must be a distinct new .blend path")
            before_sha = _file_hash(source)
            bpy = _bpy()
            if not bpy.app.background:
                raise ValueError("Run the CLI in a separate Blender background process; use API functions in an interactive session")
            bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
            objects = []
            for name in args.objects:
                obj = bpy.context.scene.objects.get(name)
                if obj is None:
                    raise ValueError("Target mesh not found: " + name)
                objects.append(obj)
            armature = bpy.context.scene.objects.get(args.rig) if args.rig else None
            if args.rig and armature is None:
                raise ValueError("Explicit rig not found: " + args.rig)
            if args.command == "audit":
                report = audit_meshes(objects, armature, max_influences=args.max_influences)
                code = 0
            elif args.command == "snapshot":
                report = snapshot_meshes(objects, armature, source_path=source)
                code = 0
            else:
                _, report = normalize_weights_copy(objects, armature)
                code = 2 if report["unresolved"] else 0
                if code == 0:
                    _save_candidate(output)
                    report["output"] = {"name": output.name, "sha256": _file_hash(output)}
            after_sha = _file_hash(source)
            if before_sha != after_sha:
                raise RuntimeError("Input SHA changed during command")
            report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        _write_report(report_path, report)
        print(json.dumps({"command": args.command, "status": report["status"] if "status" in report else "captured",
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
