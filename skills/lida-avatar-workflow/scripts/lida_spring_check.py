# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Run the VRM Add-on's spring bone simulation on a test motion and measure each chain.

Run in Blender with ``--background --factory-startup --python THIS.py -- check``.
check: --input MODEL.blend --rig Armature --report NEW.json [--vrm-addon bl_ext.user_default.vrm]
       [--values VALUES.json] [--render-dir NEW_FOLDER]

The motion (30 fps, in memory only): frames 1-30 stand still; 30-60 lower both arms 60 deg while the hips
and head sway +/-25 and +/-30 deg; 60-75 raise the left leg 45 deg forward; 75-110 hold. The humanoid bones
come from the VRM humanoid assignment of the armature; the model must face -Y (the VRM Add-on convention).

For the tip of every spring (its last joint) the report gives:
- drift at rest: how far the tip moves in the first 30 frames without motion (gravity or colliders
  collapsing the shape);
- lag: the distance between the tip and where it would be if fixed rigidly to the parent bone of the chain
  root. The raw distance moved includes the parent's motion, so the lag is the measure of sway;
- after stopping: the tip's motion in the last frame and the lag left at the end, to read next to the drift
  at rest and to how far colliders push the chain.
The report also says whether the leg went forward (the foot moved toward -Y), so the direction is not taken
from the sign of an angle.

--values replaces stiffness, gravity power, drag force and hit radius in memory for springs whose name starts
with a given prefix: {"kind": {"Hair_": [stiffness, gravity, drag, hit_radius], ...}}. Nothing is saved.

The numeric core needs numpy only. Exit codes: 0 nothing found; 2 findings, warnings or a usage error;
1 invalid input, I/O or execution error.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


REPORT_SCHEMA = "lida.spring-check.report.v1"
DEFAULTS = {"fps": 30, "frames": 110, "rest_frames": 30, "motion": [30, 75], "drift_warn_mm": 10.0, "still_warn_mm": 1.0,
            "arms_down": 60.0, "hips_sway": 25.0, "head_sway": 30.0, "leg_forward": 45.0}
UNVERIFIED = [
    "motions other than the built-in test motion (walking, turning, the production's own animation)",
    "contacts with meshes; only the VRM colliders take part in the simulation",
    "the simulation in other applications (only the Blender VRM Add-on was run)",
    "appearance in renders",
]


# ---------------------------------------------------------------- numeric core

def chain_metrics(track, rigid, rest_frames=30, motion=(30, 75)):
    """track, rigid: (frames, 3) positions of a chain tip (simulated) and of the same point fixed to the root parent.

    Returns drift at rest, the largest motion and lag during the motion, the motion in the last frame and the
    lag left at the end, all in the units of the input, and whether any value is not finite.
    """
    track, rigid = np.asarray(track, float), np.asarray(rigid, float)
    if track.shape != rigid.shape or track.ndim != 2 or track.shape[1] != 3 or len(track) < 2:
        raise ValueError("track and rigid must be (frames, 3) arrays of the same shape")
    finite = bool(np.isfinite(track).all() and np.isfinite(rigid).all())
    rest_frames = int(min(max(rest_frames, 1), len(track)))
    start, stop = int(max(motion[0], 0)), int(min(motion[1], len(track)))
    lag = np.linalg.norm(track - rigid, axis=1)
    moved = np.linalg.norm(track - track[0], axis=1)
    return {"drift_at_rest": float(moved[rest_frames - 1]),
            "moved_max": float(moved[start:stop].max()) if stop > start else 0.0,
            "lag_max": float(lag[start:stop].max()) if stop > start else 0.0,
            "last_frame_motion": float(np.linalg.norm(track[-1] - track[-2])),
            "lag_end": float(lag[-1]), "finite": finite}


def smoothstep(x):
    x = min(1.0, max(0.0, float(x)))
    return x * x * (3.0 - 2.0 * x)


def motion_angles(frame, opt):
    """Angles (degrees) of the test motion at a frame: arms, hips, head, leg."""
    start, stop = opt["motion"]
    arms = opt["arms_down"] * smoothstep((frame - start) / 20.0)
    wave = math.sin((frame - start) / 30.0 * 2.0 * math.pi) if start <= frame <= start + 30 else 0.0
    leg = opt["leg_forward"] * smoothstep((frame - (start + 30)) / 12.0)
    return {"arms": arms, "hips": opt["hips_sway"] * wave, "head": opt["head_sway"] * wave, "leg": leg}


def load_values(text):
    """{"kind": {prefix: [stiffness, gravity, drag, hit_radius]}} -> dict; checks the shape."""
    data = json.loads(text) if isinstance(text, str) else text
    kind = data.get("kind") if isinstance(data, dict) else None
    if not isinstance(kind, dict) or not kind:
        raise ValueError('--values must hold {"kind": {"Prefix": [stiffness, gravity, drag, hit_radius]}}')
    out = {}
    for prefix, values in kind.items():
        if not isinstance(values, list) or len(values) < 4 or not all(isinstance(v, (int, float)) for v in values[:4]):
            raise ValueError("Values for " + str(prefix) + " must be four numbers")
        out[str(prefix)] = [float(v) for v in values[:4]]
    return out


# ---------------------------------------------------------------- Blender side

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("This command needs Blender Python; the numeric core works in ordinary Python") from error
    return bpy


def check(rig, options=None, values=None, render_dir=None):
    """Simulate the test motion in memory and measure every spring. Nothing is saved."""
    bpy = _bpy()
    from mathutils import Matrix, Vector
    opt = dict(DEFAULTS)
    opt.update({k: v for k, v in (options or {}).items() if v is not None})
    if rig is None or rig.type != "ARMATURE":
        raise ValueError("--rig must be an armature object")
    extension = getattr(rig.data, "vrm_addon_extension", None)
    if extension is None:
        raise ValueError("The VRM Add-on is not active in this Blender")
    springs = extension.spring_bone1
    if not len(springs.springs):
        raise ValueError(rig.name + " has no VRM 1.0 springs")
    humanoid = {}
    for name, prop in extension.vrm1.humanoid.human_bones.human_bone_name_to_human_bone().items():
        if prop.node.bone_name:
            humanoid[name.value] = prop.node.bone_name
    needed = ["hips", "head", "leftUpperArm", "rightUpperArm", "leftUpperLeg", "leftFoot"]
    missing = [name for name in needed if name not in humanoid or humanoid[name] not in rig.data.bones]
    if missing:
        raise ValueError("The VRM humanoid assignment lacks: " + ", ".join(missing))
    applied = {}
    if values:
        for spring in springs.springs:
            prefix = next((p for p in values if spring.vrm_name.startswith(p)), None)
            if prefix:
                stiffness, gravity, drag, hit = values[prefix]
                for joint in spring.joints:
                    joint.stiffness, joint.gravity_power, joint.drag_force, joint.hit_radius = stiffness, gravity, drag, hit
                applied[spring.vrm_name] = values[prefix]
    chains = []
    for spring in springs.springs:
        names = [joint.node.bone_name for joint in spring.joints if joint.node.bone_name in rig.data.bones]
        if not names:
            continue
        root = rig.data.bones[names[0]]
        parent = root.parent.name if root.parent else None
        chains.append({"name": spring.vrm_name, "tip": names[-1], "parent": parent, "joints": len(names)})
    scene = bpy.context.scene
    scene.render.fps = int(opt["fps"])
    scene.frame_start, scene.frame_end = 1, int(opt["frames"])
    rig.data.pose_position = "POSE"
    pose = rig.pose.bones
    for bone in pose:
        bone.matrix_basis = Matrix.Identity(4)

    def key(name, axis, degrees, frame):
        bone = pose[name]
        rest = bone.bone.matrix_local.to_3x3()
        turn = Matrix.Rotation(math.radians(degrees), 3, Vector(axis))
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (rest.inverted() @ turn @ rest).to_quaternion()
        bone.keyframe_insert("rotation_quaternion", frame=frame)

    for frame in range(1, int(opt["frames"]) + 1):
        a = motion_angles(frame, opt)
        key(humanoid["leftUpperArm"], (0, 1, 0), a["arms"], frame)
        key(humanoid["rightUpperArm"], (0, 1, 0), -a["arms"], frame)
        key(humanoid["hips"], (0, 0, 1), a["hips"], frame)
        key(humanoid["head"], (0, 0, 1), a["head"], frame)
        key(humanoid["leftUpperLeg"], (1, 0, 0), -a["leg"], frame)   # -X raises the leg toward -Y (front)
    world = rig.matrix_world
    rest_tip = {c["name"]: world @ rig.data.bones[c["tip"]].head_local for c in chains}
    foot0 = None
    springs.enable_animation = True
    track = {c["name"]: [] for c in chains}
    rigid = {c["name"]: [] for c in chains}
    shots = {1, 30, 45, 60, 75, int(opt["frames"])}
    images = []
    for frame in range(1, int(opt["frames"]) + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for c in chains:
            track[c["name"]].append(list(world @ pose[c["tip"]].head))
            if c["parent"]:
                p = pose[c["parent"]]
                follow = world @ p.matrix @ p.bone.matrix_local.inverted() @ world.inverted()
                rigid[c["name"]].append(list(follow @ rest_tip[c["name"]]))
            else:
                rigid[c["name"]].append(list(rest_tip[c["name"]]))
        foot = world @ pose[humanoid["leftFoot"]].head
        if frame == 1:
            foot0 = foot.copy()
        if render_dir is not None and frame in shots:
            images += _render(bpy, rig, render_dir, frame)
    foot_motion = foot - foot0
    springs.enable_animation = False
    scale = float(scene.unit_settings.scale_length) or 1.0
    to_mm = 1000.0 * scale
    results, warnings = [], []
    for c in chains:
        m = chain_metrics(track[c["name"]], rigid[c["name"]], opt["rest_frames"], opt["motion"])
        row = {"spring": c["name"], "tip": c["tip"], "root_parent": c["parent"], "joints": c["joints"], "finite": m["finite"]}
        for k in ("drift_at_rest", "moved_max", "lag_max", "last_frame_motion", "lag_end"):
            row[k + "_mm"] = round(m[k] * to_mm, 2)
        results.append(row)
        if not m["finite"]:
            warnings.append(c["name"] + ": the simulation gave a value that is not finite")
        if row["drift_at_rest_mm"] > opt["drift_warn_mm"]:
            warnings.append("%s: the tip moves %.1f mm at rest (gravity or colliders change the shape)" % (c["name"], row["drift_at_rest_mm"]))
        if row["last_frame_motion_mm"] > opt["still_warn_mm"]:
            warnings.append("%s: still moving %.2f mm per frame at the end" % (c["name"], row["last_frame_motion_mm"]))
    leg = "forward" if foot_motion.y < -0.01 else ("backward" if foot_motion.y > 0.01 else "unclear")
    if leg != "forward":
        warnings.append("The leg went " + leg + " (foot moved %.3f in Y); check the model faces -Y" % foot_motion.y)
    return {"schema": REPORT_SCHEMA, "command": "check", "rig": rig.name, "unit": "mm", "options": opt,
            "values_applied": applied, "leg_raise_direction": leg, "springs": results, "images": images,
            "warnings": warnings, "unverified": list(UNVERIFIED),
            "status": "completed_with_findings" if warnings else "completed"}


def _render(bpy, rig, folder, frame):
    from mathutils import Vector
    scene = bpy.context.scene
    if scene.camera is None or scene.camera.name != "SpringCheckCamera":
        scene.render.engine = "BLENDER_WORKBENCH"
        shading = scene.display.shading
        shading.light = "STUDIO"
        shading.color_type = "OBJECT"
        shading.show_backface_culling = False
        shading.background_type = "VIEWPORT"
        shading.background_color = (0.45, 0.5, 0.55)
        scene.view_settings.view_transform = "Standard"
        scene.render.resolution_x = scene.render.resolution_y = 700
        for obj in bpy.data.objects:
            if obj.type in ("EMPTY", "ARMATURE"):
                obj.hide_render = True
        data = bpy.data.cameras.new("SpringCheckCamera")
        data.type = "ORTHO"
        data.clip_end = 50.0
        camera = bpy.data.objects.new("SpringCheckCamera", data)
        scene.collection.objects.link(camera)
        scene.camera = camera
    camera = scene.camera
    corners = [rig.matrix_world @ Vector(c) for c in rig.bound_box]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render]
    points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box] or corners
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centre = (low + high) / 2
    camera.data.ortho_scale = max(high.x - low.x, high.z - low.z) * 1.1
    written = []
    for tag, direction in (("front", (0, -1, 0)), ("side", (1, 0, 0)), ("back", (0, 1, 0))):
        d = Vector(direction)
        camera.location = centre + d * 10.0
        camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        path = folder / ("frame%03d_%s.png" % (frame, tag))
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path.name)
    return written


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
    parser = argparse.ArgumentParser(prog="lida_spring_check.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("check")
    sub.add_argument("--input", required=True, type=Path)
    sub.add_argument("--rig", required=True)
    sub.add_argument("--report", required=True, type=Path)
    sub.add_argument("--vrm-addon", default="bl_ext.user_default.vrm", help="module name of the installed VRM Add-on")
    sub.add_argument("--values", type=Path, help="spring values to try in memory, by name prefix")
    sub.add_argument("--render-dir", type=Path, help="a new folder for front, side and back views at a few frames")
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
        render_dir = _new_output(args.render_dir) if args.render_dir else None
        source = args.input.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".blend":
            raise ValueError("Input must be an existing .blend file")
        values = None
        if args.values is not None:
            with args.values.expanduser().resolve().open("r", encoding="utf-8") as stream:
                values = load_values(json.load(stream))
        before_sha = _file_hash(source)
        bpy = _bpy()
        if not bpy.app.background:
            raise ValueError("Run the CLI in a separate Blender background process")
        bpy.ops.preferences.addon_enable(module=args.vrm_addon)
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
        rig = bpy.data.objects.get(args.rig)
        if rig is None:
            raise ValueError("Object not found: " + args.rig)
        if render_dir is not None:
            render_dir.mkdir()
        report = check(rig, None, values, render_dir)
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        code = 2 if report["warnings"] else 0
        _write_report(report_path, report)
        print(json.dumps({"command": "check", "status": report["status"], "springs": len(report["springs"]),
                          "warnings": len(report["warnings"]), "report": report_path.name, "exit_code": code}, ensure_ascii=False))
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
