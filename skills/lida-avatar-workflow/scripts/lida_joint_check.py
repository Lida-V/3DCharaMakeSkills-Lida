# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Measure how elbows, knees and other joints collapse when bent, and add half-turn helper bones to a copy.

Run in Blender with ``--background --factory-startup --python THIS.py -- COMMAND``.
check:   --input MODEL.blend --rig Armature --mesh Body [Body2 ...] --joint LowerBone[@AXIS] [...] --report NEW.json
         [--axis x|y|z|local-x|local-y|local-z] [--angles 90 130] [--radius-mm 50] [--render-dir NEW_FOLDER]
helpers: --input MODEL.blend --rig Armature --mesh Body [Body2 ...] --joint LowerBone[:BAND_MM] [...] --report NEW.json
         --output-blend NEW.blend [--band-mm 65] [--influence 0.5] [--suffix _Helper]

check bends each named lower bone (knee: the shin bone, elbow: the forearm bone) by each angle about an axis
through the joint centre: x, y or z of the rig space (for a T pose, knees bend about x and elbows about z), or
the bone's own local axis (local-x ...) when its roll is known to be clean. It evaluates the meshes as Blender deforms them (constraints and modifiers included), and reports,
for the points near the joint centre, the distance to the centre after the bend divided by the rest distance
(a low percentile and the minimum: 1 keeps the volume, 0.5 means half collapsed), the edges stretched past
1.6x or shrunk below 0.5x with their rest positions and the strongest bones at both ends. A negative angle
bends the other way; read the reported tail motion and the images to confirm the direction.

helpers adds, for each named lower bone, a deform bone at the joint centre, parented to the upper bone and
aligned with the lower one, that copies the lower bone's local rotation with the given influence
(Copy Rotation, local to local, Add; the VRM Add-on can export it as a VRMC_node_constraint rotation
constraint). Along the bone axis it hands the weight of the joint ring from the upper bone to the helper to
the lower bone over +/- band. Other bones' weights stay. The result is written to a new blend only.

The numeric core needs numpy only. The input blend is opened and never saved; check poses the scene in
memory only. Exit codes: 0 nothing found; 2 findings, warnings or a usage error; 1 invalid input, I/O or
execution error.
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

import numpy as np


REPORT_SCHEMA = "lida.joint-check.report.v1"
DEFAULTS = {"axis": "x", "angles": [90.0, 130.0], "radius_mm": 50.0, "percentile": 5.0, "stretch": 1.6, "shrink": 0.5,
            "min_edge_mm": 0.5, "collapse_warn": 0.7, "edges_listed": 20, "band_mm": 65.0, "influence": 0.5,
            "suffix": "_Helper", "reach_mm": 150.0}
UNVERIFIED = [
    "poses other than one lower bone bent about one local axis (combined poses, twists, real motion)",
    "contacts between the bent parts and with other meshes (use the penetration check)",
    "appearance in renders and in the destination application",
    "whether the destination plays node constraints (a helper bone without them follows its parent only)",
]


# ---------------------------------------------------------------- numeric core

def near_points(rest, centre, radius):
    """Indices of rest points within radius of centre; widened to 1.6x the nearest distance for parts far out."""
    distance = np.linalg.norm(np.asarray(rest, float) - np.asarray(centre, float), axis=1)
    reach = max(float(radius), float(np.percentile(distance, 0.05)) * 1.6) if len(distance) else float(radius)
    return np.nonzero(distance < reach)[0], reach


def collapse_ratio(rest, posed, rest_centre, posed_centre, index, percentile=5.0):
    """Distance to the joint centre after the bend / at rest for the chosen points: (low percentile, minimum)."""
    if len(index) == 0:
        return None, None
    r0 = np.linalg.norm(np.asarray(rest, float)[index] - np.asarray(rest_centre, float), axis=1)
    r1 = np.linalg.norm(np.asarray(posed, float)[index] - np.asarray(posed_centre, float), axis=1)
    ratio = r1 / np.maximum(r0, 1e-9)
    return float(np.percentile(ratio, percentile)), float(ratio.min())


def edge_changes(rest, posed, edges, stretch=1.6, shrink=0.5, min_edge=0.0005):
    """Ratios of edge lengths (posed / rest); returns (ratios for edges longer than min_edge, mask of those, bad mask)."""
    rest, posed, edges = np.asarray(rest, float), np.asarray(posed, float), np.asarray(edges, int).reshape(-1, 2)
    l0 = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    l1 = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
    usable = l0 > min_edge
    ratio = np.ones(len(edges))
    ratio[usable] = l1[usable] / l0[usable]
    bad = usable & ((ratio > stretch) | (ratio < shrink))
    return ratio, usable, bad


def band_weights(t, total, band):
    """Weights (upper, helper, lower) for points at axial position t from the joint centre.

    total is the point's upper + lower weight. |t| >= band keeps the side bone; at t = 0 the helper takes all.
    The hand-over follows a smoothstep, so the sum stays total.
    """
    t, total = np.asarray(t, float), np.asarray(total, float)
    u = np.clip(np.abs(t) / float(band), 0.0, 1.0)
    side = u * u * (3.0 - 2.0 * u)
    helper = total * (1.0 - side)
    upper = np.where(t < 0, total * side, 0.0)
    lower = np.where(t >= 0, total * side, 0.0)
    return upper, helper, lower


def axial_position(points, head, tail):
    """Signed distance of points along the bone axis from its head, and the distance from the axis."""
    head, tail = np.asarray(head, float), np.asarray(tail, float)
    axis = tail - head
    axis = axis / np.linalg.norm(axis)
    rel = np.asarray(points, float) - head
    t = rel @ axis
    radial = np.linalg.norm(rel - np.outer(t, axis), axis=1)
    return t, radial


AXES = ("x", "y", "z", "local-x", "local-y", "local-z")


def parse_check_joint(text, default_axis):
    """'Bone' or 'Bone@z' or 'Bone@local-x' -> (bone, axis). Plain x/y/z are axes of the rig space."""
    name, sep, axis = str(text).rpartition("@")
    if not sep:
        return str(text), default_axis
    if axis not in AXES:
        raise ValueError("Unknown axis in " + str(text) + " (use " + ", ".join(AXES) + ")")
    return name, axis


def parse_joint(text, default_band):
    """'Bone' or 'Bone:65' -> (bone, band in mm)."""
    name, sep, band = str(text).rpartition(":")
    if not sep:
        return str(text), float(default_band)
    try:
        value = float(band)
    except ValueError:
        return str(text), float(default_band)
    if value <= 0:
        raise ValueError("A band must be positive: " + str(text))
    return name, value


# ---------------------------------------------------------------- Blender side

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("This command needs Blender Python; the numeric core works in ordinary Python") from error
    return bpy


def _meshes_points(bpy, meshes, evaluated):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    out = []
    for obj in meshes:
        source = obj.evaluated_get(depsgraph) if evaluated else obj
        mesh = source.to_mesh() if evaluated else obj.data
        flat = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", flat)
        matrix = np.array(obj.matrix_world)
        out.append(flat.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3])
        if evaluated:
            source.to_mesh_clear()
    return out


def _weights_table(obj):
    names = [group.name for group in obj.vertex_groups]
    rows = []
    for vertex in obj.data.vertices:
        rows.append({names[g.group]: g.weight for g in vertex.groups if g.weight > 1e-6})
    return rows


def _top(row, count=3):
    return {name: round(weight, 3) for name, weight in sorted(row.items(), key=lambda kv: -kv[1])[:count]}


def _check_inputs(bpy, rig, meshes, joints):
    if rig is None or rig.type != "ARMATURE":
        raise ValueError("--rig must be an armature object")
    for obj in meshes:
        if obj.type != "MESH":
            raise ValueError("--mesh must name mesh objects: " + obj.name)
    for name in joints:
        bone = rig.data.bones.get(name)
        if bone is None:
            raise ValueError("Bone not found: " + name)
        if bone.parent is None:
            raise ValueError("The joint bone needs a parent (the upper bone): " + name)


def _render(bpy, meshes, folder, name, centre, side_dir, inner_dir, size):
    from mathutils import Vector
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_backface_culling = False
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.45, 0.5, 0.55)
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = scene.render.resolution_y = 700
    wires = []
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj not in meshes
    for obj in meshes:
        obj.color = (0.92, 0.88, 0.85, 1.0)
        wire = obj.copy()
        scene.collection.objects.link(wire)
        modifier = wire.modifiers.new("Wire", "WIREFRAME")
        modifier.thickness = 0.0006
        modifier.use_replace = True
        modifier.use_even_offset = False
        wire.color = (0.15, 0.15, 0.2, 1.0)
        wires.append(wire)
    camera_data = bpy.data.cameras.new("JointCheckCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = size
    camera_data.clip_end = 50.0
    camera = bpy.data.objects.new("JointCheckCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    written = []
    for tag, direction in (("side", side_dir), ("inner", inner_dir)):
        d = Vector(direction).normalized()
        camera.location = Vector(centre) + d * 5.0
        camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        path = folder / ("%s_%s.png" % (name, tag))
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path.name)
    for wire in wires:                                  # in memory only; the blend is never saved
        bpy.data.objects.remove(wire)
    bpy.data.objects.remove(camera)
    return written


def check(rig, meshes, joints, options=None, render_dir=None):
    """Bend each joint bone in memory and measure; returns the report. Nothing is saved."""
    bpy = _bpy()
    from mathutils import Matrix
    opt = dict(DEFAULTS)
    opt.update({k: v for k, v in (options or {}).items() if v is not None})
    if opt["axis"] not in AXES:
        raise ValueError("--axis must be one of " + ", ".join(AXES))
    joints = [parse_check_joint(text, opt["axis"]) for text in joints]
    _check_inputs(bpy, rig, meshes, [name for name, _ in joints])
    rig.data.pose_position = "POSE"
    pose = rig.pose.bones
    for bone in pose:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    rest = _meshes_points(bpy, meshes, True)
    edges = [np.array([e.vertices[:] for e in obj.data.edges], int).reshape(-1, 2) for obj in meshes]
    weights = [_weights_table(obj) for obj in meshes]
    world = rig.matrix_world
    scale = float(bpy.context.scene.unit_settings.scale_length) or 1.0
    to_mm = 1000.0 * scale
    results, warnings, images = [], [], []
    for name, axis in joints:
        centre0 = np.array(world @ pose[name].head)
        for angle in opt["angles"]:
            for bone in pose:
                bone.matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()
            if axis.startswith("local-"):
                pose[name].matrix_basis = Matrix.Rotation(math.radians(float(angle)), 4, axis[-1].upper())
            else:                                       # about an axis of the rig space, through the joint centre
                current = pose[name].matrix.copy()
                head = current.translation.copy()
                turn = Matrix.Rotation(math.radians(float(angle)), 4, axis.upper())
                pose[name].matrix = Matrix.Translation(head) @ turn @ Matrix.Translation(-head) @ current
            bpy.context.view_layer.update()
            posed = _meshes_points(bpy, meshes, True)
            centre1 = np.array(world @ pose[name].head)
            tail0 = np.array(world @ rig.data.bones[name].tail_local)
            tail1 = np.array(world @ pose[name].tail)
            entry = {"joint": name, "axis": axis, "angle": float(angle), "tail_motion": [round(float(x), 4) for x in tail1 - tail0],
                     "meshes": {}}
            for index, obj in enumerate(meshes):
                near, reach = near_points(rest[index], centre0, opt["radius_mm"] / to_mm)
                low, low_min = collapse_ratio(rest[index], posed[index], centre0, centre1, near, opt["percentile"])
                ratio, usable, bad = edge_changes(rest[index], posed[index], edges[index], opt["stretch"], opt["shrink"],
                                                  opt["min_edge_mm"] / to_mm)
                listed = []
                for edge_index in np.nonzero(bad)[0][np.argsort(-np.abs(np.log(ratio[bad])))][: int(opt["edges_listed"])]:
                    a, b = edges[index][edge_index]
                    listed.append({"ratio": round(float(ratio[edge_index]), 3),
                                   "rest_mid": [round(float(x), 4) for x in (rest[index][a] + rest[index][b]) / 2],
                                   "weights_a": _top(weights[index][a]), "weights_b": _top(weights[index][b])})
                record = {"points_near": int(len(near)), "reach_mm": round(reach * to_mm, 1),
                          "distance_ratio_low": None if low is None else round(low, 3),
                          "distance_ratio_min": None if low_min is None else round(low_min, 3),
                          "edges_out": int(bad.sum()), "edge_ratio_max": round(float(ratio[usable].max()), 3) if usable.any() else None,
                          "edge_ratio_min": round(float(ratio[usable].min()), 3) if usable.any() else None, "worst_edges": listed}
                entry["meshes"][obj.name] = record
                if low is not None and low < opt["collapse_warn"]:
                    warnings.append("%s %+g deg on %s: points near the joint keep %.2f of their distance to the centre (low %g%%)"
                                    % (name, angle, obj.name, low, opt["percentile"]))
                if record["edges_out"]:
                    warnings.append("%s %+g deg on %s: %d edges stretch past %gx or shrink below %gx"
                                    % (name, angle, obj.name, record["edges_out"], opt["stretch"], opt["shrink"]))
            if render_dir is not None:
                if axis.startswith("local-"):
                    axis_world = np.array(world.to_3x3() @ pose[name].matrix.to_3x3().col["xyz".index(axis[-1])])
                else:
                    axis_world = np.array(world.to_3x3().col["xyz".index(axis)])
                parent_head = np.array(world @ pose[name].parent.head)
                inner = (parent_head - centre1) / max(np.linalg.norm(parent_head - centre1), 1e-9) + \
                        (tail1 - centre1) / max(np.linalg.norm(tail1 - centre1), 1e-9)
                if np.linalg.norm(inner) < 1e-6:
                    inner = axis_world
                size = max(0.12, 2.6 * near_points(rest[0], centre0, opt["radius_mm"] / to_mm)[1])
                label = "%s_%+d" % (name, int(round(float(angle))))
                images += _render(bpy, meshes, render_dir, label.replace("+", "p").replace("-", "m"), centre1, axis_world, inner, size)
            results.append(entry)
    for bone in pose:
        bone.matrix_basis = Matrix.Identity(4)
    report = {"schema": REPORT_SCHEMA, "command": "check", "rig": rig.name, "meshes": [m.name for m in meshes], "unit": "mm",
              "options": opt, "joints": results, "images": images, "warnings": warnings, "unverified": list(UNVERIFIED),
              "status": "completed_with_findings" if warnings else "completed"}
    return report


def add_helpers(rig, meshes, joints, options=None):
    """Add half-turn helper bones and hand the joint ring weights over to them (in memory). Returns the report."""
    bpy = _bpy()
    from mathutils import Matrix
    opt = dict(DEFAULTS)
    opt.update({k: v for k, v in (options or {}).items() if v is not None})
    if not 0.0 < float(opt["influence"]) < 1.0:
        raise ValueError("--influence must be between 0 and 1")
    names = [name for name, _ in joints]
    _check_inputs(bpy, rig, meshes, names)
    for obj in meshes:
        if not any(m.type == "ARMATURE" and m.object == rig for m in obj.modifiers):
            raise ValueError(obj.name + " has no Armature modifier pointing to " + rig.name)
    for name in names:
        if rig.data.bones.get(name + opt["suffix"]) is not None:
            raise ValueError("A bone named " + name + opt["suffix"] + " already exists")
    rig.data.pose_position = "REST"
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    to_rig = np.linalg.inv(np.array(rig.matrix_world))
    scale = float(bpy.context.scene.unit_settings.scale_length) or 1.0
    to_m = 1.0 / (1000.0 * scale)
    report_joints = []
    plans = []
    for name, band in joints:
        bone = rig.data.bones[name]
        parent = bone.parent.name
        plans.append((name, parent, band))
    # weights first (rest data), bones after
    for obj in meshes:
        matrix = to_rig @ np.array(obj.matrix_world)
        flat = np.empty(len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get("co", flat)
        points = flat.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
        groups = {group.name: group for group in obj.vertex_groups}
        table = _weights_table(obj)
        for name, parent, band in plans:
            if name not in groups or parent not in groups:
                report_joints.append({"joint": name, "mesh": obj.name, "verts": 0, "note": "the mesh has no weights for both bones"})
                continue
            bone = rig.data.bones[name]
            t, radial = axial_position(points, np.array(bone.head_local), np.array(bone.tail_local))
            upper_w = np.array([row.get(parent, 0.0) for row in table])
            lower_w = np.array([row.get(name, 0.0) for row in table])
            total = upper_w + lower_w
            band_m = band * to_m
            chosen = np.nonzero((total > 0.3) & (np.abs(t) < band_m) & (radial < float(opt["reach_mm"]) * to_m))[0]
            up, helper, low = band_weights(t[chosen], total[chosen], band_m)
            helper_group = obj.vertex_groups.get(name + opt["suffix"]) or obj.vertex_groups.new(name=name + opt["suffix"])
            for k, vertex in enumerate(chosen):
                vertex = int(vertex)
                for group_name, value in ((parent, up[k]), (name, low[k]), (name + opt["suffix"], helper[k])):
                    group = obj.vertex_groups[group_name]
                    if value > 1e-5:
                        group.add([vertex], float(value), "REPLACE")
                    else:
                        group.remove([vertex])
            report_joints.append({"joint": name, "mesh": obj.name, "parent": parent, "band_mm": band, "verts": int(len(chosen))})
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == rig)
    bpy.context.view_layer.objects.active = rig
    with bpy.context.temp_override(active_object=rig, object=rig, selected_objects=[rig], selected_editable_objects=[rig]):
        bpy.ops.object.mode_set(mode="EDIT")
        edit = rig.data.edit_bones
        for name, parent, band in plans:
            lower = edit[name]
            helper = edit.new(name + opt["suffix"])
            helper.head = lower.head.copy()
            helper.tail = lower.head + (lower.tail - lower.head).normalized() * max(0.01, (lower.tail - lower.head).length * 0.2)
            helper.roll = lower.roll
            helper.parent = edit[parent]
            helper.use_connect = False
            helper.use_deform = True
        bpy.ops.object.mode_set(mode="OBJECT")
    for name, parent, band in plans:
        constraint = rig.pose.bones[name + opt["suffix"]].constraints.new("COPY_ROTATION")
        constraint.target = rig
        constraint.subtarget = name
        constraint.owner_space = "LOCAL"
        constraint.target_space = "LOCAL"
        constraint.mix_mode = "ADD"
        constraint.influence = float(opt["influence"])
    rig.data.pose_position = "POSE"
    return {"schema": REPORT_SCHEMA, "command": "helpers", "rig": rig.name, "meshes": [m.name for m in meshes],
            "options": opt, "helpers": [name + opt["suffix"] for name, _, _ in plans], "joints": report_joints,
            "warnings": [j["joint"] + " on " + j["mesh"] + ": " + j["note"] for j in report_joints if j.get("note")],
            "unverified": list(UNVERIFIED), "status": "completed"}


# ---------------------------------------------------------------- CLI

def _new_output(path, directory=False):
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


def _save_candidate(path):
    """Blender writes an owned temporary copy; final publication is exclusive."""
    bpy = _bpy()
    descriptor, temporary = tempfile.mkstemp(prefix=".lida-joint-", suffix=".blend", dir=path.parent)
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
    parser = argparse.ArgumentParser(prog="lida_joint_check.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "helpers"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
        sub.add_argument("--rig", required=True)
        sub.add_argument("--mesh", required=True, nargs="+")
        sub.add_argument("--joint", required=True, nargs="+", help="the lower bone of each joint (helpers: Bone or Bone:BAND_MM)")
        sub.add_argument("--report", required=True, type=Path)
        if command == "check":
            sub.add_argument("--axis", choices=AXES, help="default bend axis: x/y/z of the rig space or local-x/y/z of the bone; "
                                                          "a joint can override it as Bone@axis")
            sub.add_argument("--angles", type=float, nargs="+")
            sub.add_argument("--radius-mm", type=float)
            sub.add_argument("--render-dir", type=Path, help="a new folder for side and inner views of each bend")
        else:
            sub.add_argument("--output-blend", required=True, type=Path)
            sub.add_argument("--band-mm", type=float)
            sub.add_argument("--influence", type=float)
            sub.add_argument("--suffix")
    return parser


def _safe_console():
    """Names the console cannot encode are escaped instead of failing after the report is written."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


def _clean_argv(argv):
    """Drop a trailing CR/LF from each argument (names read from a Windows program's output keep the CR)."""
    return [text.rstrip("\r\n") if isinstance(text, str) else text for text in argv]


def main(argv=None):
    _safe_console()
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parser().parse_args(_clean_argv(argv))
    report_path = None
    try:
        report_path = _new_output(args.report)
        render_dir = _new_output(args.render_dir) if getattr(args, "render_dir", None) else None
        output_blend = _new_output(args.output_blend) if getattr(args, "output_blend", None) else None
        source = args.input.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".blend":
            raise ValueError("Input must be an existing .blend file")
        if output_blend is not None and (output_blend == source or output_blend.suffix.lower() != ".blend"):
            raise ValueError("--output-blend must be a new .blend path")
        before_sha = _file_hash(source)
        bpy = _bpy()
        if not bpy.app.background:
            raise ValueError("Run the CLI in a separate Blender background process")
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)

        def find(name):
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError("Object not found: " + name)
            return obj

        rig = find(args.rig)
        meshes = [find(name) for name in args.mesh]
        if args.command == "check":
            if render_dir is not None:
                render_dir.mkdir()
            options = {"axis": args.axis, "angles": args.angles, "radius_mm": args.radius_mm}
            report = check(rig, meshes, args.joint, options, render_dir)
        else:
            options = {"band_mm": args.band_mm, "influence": args.influence, "suffix": args.suffix}
            band = args.band_mm if args.band_mm is not None else DEFAULTS["band_mm"]
            report = add_helpers(rig, meshes, [parse_joint(text, band) for text in args.joint], options)
            _save_candidate(output_blend)
            report["output_blend"] = {"name": output_blend.name, "sha256": _file_hash(output_blend)}
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        code = 2 if report["warnings"] else 0
        _write_report(report_path, report)
        print(json.dumps({"command": args.command, "status": report["status"], "warnings": len(report["warnings"]),
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
