# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Sweep shape keys and their combinations through intermediate values and report where the mesh breaks.

Run in Blender with ``--background --factory-startup --python THIS.py -- sweep``.
sweep: --input MODEL.blend --object Face [--keys blink aa ... | --all] [--combo happy+blink happy=1+blink ...]
       [--partners Eye_L Eye_R Teeth] [--steps 20] --report NEW.json

A key that looks right at 0 and 1 can fold, collapse or let the eyeball through at 0.35, and two
keys that are fine alone can fight when mixed. This command evaluates basis + sum(weight * key
offset) at evenly spaced values and reports, for every key and combination, the worst value and
where it happens: faces folded back onto a neighbour, collapsed faces, edge stretch, and new
crossing spots against partner meshes (eyeballs, teeth) compared with the resting state. A lid rim
always touches the eyeball along one loop, so the number of separate crossing spots is counted, not
the length: a poke-through adds a spot. In a combination "a+b" both run 0..1 together; "a=1+b"
holds a at 1 while b runs. --accept OLD.json takes an earlier report of an approved model as the
baseline: only values worse than the accepted ones are reported as problems.

The numeric core needs numpy only. The blend is opened read-only and never saved; key values in the
file are not changed (offsets are read and combined in memory). Drivers, key slider limits and the
destination's own blending rules are not applied. Exit codes: 0 nothing over the limits; 2 a key or
combination exceeds a limit; 1 invalid input, I/O or execution error. Numbers do not grade the look
of an expression.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


REPORT_SCHEMA = "lida.shape-key-sweep.report.v1"
DEFAULTS = {
    "steps": 20,                # values between 0 and 1 (inclusive ends are added)
    "moved_mm": 0.01,           # a vertex that moves more than this belongs to the key
    "fold_degrees": 150.0,      # neighbouring faces at more than this angle count as folded back ...
    "fold_from_degrees": 120.0,  # ... when they were below this angle at rest
    "collapse_ratio": 0.05,     # a face whose area falls below this share of its rest area collapses
    "stretch_limit": 3.0,       # warn when an edge grows beyond this multiple of its rest length
    "min_edge_mm": 1.0,         # edges shorter than this at rest are left out of the stretch measure (lip slits, lid rims)
    "spot_mm": 3.0,             # crossing curves closer than this belong to one spot
    "fold_limit": 0,            # warn when more new folds than this appear
    "collapse_limit": 0,
    "spot_limit": 0,            # warn when more new crossing spots than this appear against a partner
}
UNVERIFIED = [
    "the look of each expression and whether it matches the reference art",
    "drivers, slider limits, relative-key chains other than the stored reference, and corrective keys",
    "blending rules of the destination (VRM overrides, engine-side clamps) unless given as combinations",
    "gaps: a closed eye that leaves a slit is not detected, only new crossings with partners are",
    "modifiers after the keys (subdivision can pull thin lid edges) and custom normals",
]


def _penetration():
    """The triangle-crossing helpers of the sibling penetration tool."""
    path = Path(__file__).resolve().with_name("lida_penetration_check.py")
    spec = importlib.util.spec_from_file_location("lida_penetration_check_for_sweep", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_options(options=None):
    resolved = dict(DEFAULTS)
    for key, value in (options or {}).items():
        if key not in DEFAULTS:
            raise ValueError("Unknown option: " + str(key))
        if value is not None:
            resolved[key] = value
    resolved["steps"] = int(resolved["steps"])
    if not 2 <= resolved["steps"] <= 200:
        raise ValueError("steps must be between 2 and 200")
    return resolved


def parse_recipe(text):
    """'a+b' -> [('a', None), ('b', None)]; 'a=1+b' -> [('a', 1.0), ('b', None)]."""
    recipe = []
    for part in text.split("+"):
        name, mark, value = part.partition("=")
        if not name:
            raise ValueError("Empty key name in combination: " + text)
        recipe.append((name, float(value) if mark else None))
    if all(value is not None for _, value in recipe):
        raise ValueError("A combination needs at least one key that runs: " + text)
    return recipe


class Topology:
    """Rest measures of a triangle mesh that every step is compared with."""

    def __init__(self, points, triangles):
        self.triangles = np.asarray(triangles, np.int64)
        self.edges, inverse = np.unique(np.sort(np.concatenate([self.triangles[:, [0, 1]], self.triangles[:, [1, 2]],
                                                                 self.triangles[:, [2, 0]]]), axis=1), axis=0, return_inverse=True)
        inverse = inverse.ravel()
        order = np.argsort(inverse, kind="stable")
        owner = np.tile(np.arange(len(self.triangles)), 3)[order]
        start = np.searchsorted(inverse[order], np.arange(len(self.edges)))
        count = np.diff(np.append(start, len(order)))
        inner = count == 2                                   # edges shared by exactly two faces
        self.pair = np.stack([owner[start[inner]], owner[start[inner] + 1]], axis=1)
        self.area0 = self.areas(points)
        self.length0 = self.lengths(points)
        self.angle0 = self.angles(points)

    def normals(self, points):
        t = self.triangles
        return np.cross(points[t[:, 1]] - points[t[:, 0]], points[t[:, 2]] - points[t[:, 0]])

    def areas(self, points):
        return np.linalg.norm(self.normals(points), axis=1) / 2

    def lengths(self, points):
        return np.linalg.norm(points[self.edges[:, 0]] - points[self.edges[:, 1]], axis=1)

    def angles(self, points):
        """Angle in degrees between the normals of the two faces at every inner edge (0 = flat)."""
        normal = self.normals(points)
        normal = normal / np.maximum(np.linalg.norm(normal, axis=1), 1e-300)[:, None]
        cosine = np.clip((normal[self.pair[:, 0]] * normal[self.pair[:, 1]]).sum(1), -1.0, 1.0)
        return np.degrees(np.arccos(cosine))


def step_metrics(topology, rest, moved, opt, unit_mm):
    shift = np.linalg.norm(moved - rest, axis=1) * unit_mm
    area = topology.areas(moved)
    alive = topology.area0 > 1e-14
    length = topology.lengths(moved)
    long_enough = topology.length0 * unit_mm >= opt["min_edge_mm"]
    ratio = np.where(long_enough, length / np.maximum(topology.length0, 1e-300), 1.0)
    angle = topology.angles(moved)
    return {"moved_vertices": int((shift > opt["moved_mm"]).sum()), "max_move_mm": float(shift.max()) if len(shift) else 0.0,
            "folds": int(((angle > opt["fold_degrees"]) & (topology.angle0 < opt["fold_from_degrees"])).sum()),
            "collapsed": int((alive & (area < opt["collapse_ratio"] * topology.area0)).sum()),
            "stretch": float(ratio.max()) if len(ratio) else 1.0}


def sweep(name, recipe, rest, topology, offsets, crossing=None, options=None, unit_mm=1000.0, accepted=None):
    """Run one key or combination.

    offsets: {key: (n,3)}; crossing(weights, points) -> {partner: (spots, mm)} or None; accepted: the
    record of the same name from an approved report, or None.
    """
    opt = resolve_options(options)
    values = np.linspace(0.0, 1.0, opt["steps"] + 1)
    worst = {"folds": (0, 0.0), "collapsed": (0, 0.0), "stretch": (1.0, 0.0)}
    cross_worst, base, moved_vertices, max_move = {}, None, 0, 0.0
    for value in values:
        weights = {key: (fixed if fixed is not None else float(value)) for key, fixed in recipe}
        points = rest + sum(weights[key] * offsets[key] for key, _ in recipe)
        metrics = step_metrics(topology, rest, points, opt, unit_mm)
        moved_vertices, max_move = max(moved_vertices, metrics["moved_vertices"]), max(max_move, metrics["max_move_mm"])
        for key in worst:
            if metrics[key] > worst[key][0]:
                worst[key] = (metrics[key], float(value))
        if crossing is not None:
            now = crossing(weights, points)
            if base is None:
                base = crossing({key: 0.0 for key, _ in recipe}, rest)
            for partner, (spots, amount) in now.items():
                extra = max(0, spots - base.get(partner, (0, 0.0))[0])
                if partner not in cross_worst or extra > cross_worst[partner][0]:
                    cross_worst[partner] = (extra, float(value), amount)
    record = {"name": name, "keys": [key for key, _ in recipe], "moved_vertices": moved_vertices, "max_move_mm": round(max_move, 3),
              "folds": {"count": int(worst["folds"][0]), "at": round(worst["folds"][1], 3)},
              "collapsed": {"count": int(worst["collapsed"][0]), "at": round(worst["collapsed"][1], 3)},
              "stretch": {"ratio": round(float(worst["stretch"][0]), 3), "at": round(worst["stretch"][1], 3)},
              "new_crossing_spots": {partner: {"spots": int(extra), "at": round(at, 3), "curve_mm": round(amount, 2)}
                                     for partner, (extra, at, amount) in sorted(cross_worst.items())},
              "resting_crossing": {partner: {"spots": int(spots), "curve_mm": round(amount, 2)}
                                   for partner, (spots, amount) in sorted((base or {}).items())}}
    old = accepted or {}
    limit = {"folds": max(opt["fold_limit"], (old.get("folds") or {}).get("count", 0)),
             "collapsed": max(opt["collapse_limit"], (old.get("collapsed") or {}).get("count", 0)),
             "stretch": max(opt["stretch_limit"], (old.get("stretch") or {}).get("ratio", 0.0) * 1.05)}
    problems = []
    if record["folds"]["count"] > limit["folds"]:
        problems.append("%d faces fold back at %.2f" % (record["folds"]["count"], record["folds"]["at"]))
    if record["collapsed"]["count"] > limit["collapsed"]:
        problems.append("%d faces collapse at %.2f" % (record["collapsed"]["count"], record["collapsed"]["at"]))
    if record["stretch"]["ratio"] > limit["stretch"]:
        problems.append("an edge stretches %.1f times at %.2f" % (record["stretch"]["ratio"], record["stretch"]["at"]))
    for partner, entry in record["new_crossing_spots"].items():
        allowed = max(opt["spot_limit"], ((old.get("new_crossing_spots") or {}).get(partner) or {}).get("spots", 0))
        if entry["spots"] > allowed:
            problems.append("%d new crossing spots with %s at %.2f" % (entry["spots"], partner, entry["at"]))
    record["compared_with_accepted"] = accepted is not None
    if moved_vertices == 0:
        problems.append("the key moves nothing")
    record["problems"] = problems
    return record


def crossing_spots(points, triangles, partner_points, partner_triangles, pairs, spot_mm=3.0, unit_mm=1000.0):
    """(number of separate crossing spots, total curve length in mm) between two triangle meshes."""
    pen = _penetration()
    segments = pen.tri_tri_segments(points, triangles, partner_points, partner_triangles, pairs)
    if not len(segments):
        return 0, 0.0
    spots = len(np.unique(pen.cluster_segments(segments, spot_mm / unit_mm)))
    return int(spots), float(np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1).sum() * unit_mm)


# ---------------------------------------------------------------- Blender side

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("sweep needs Blender Python; the numeric core works in ordinary Python") from error
    return bpy


def _key_data(obj):
    """World-space rest points, triangles and {key: offset} of a mesh with shape keys."""
    mesh = obj.data
    if mesh.shape_keys is None:
        return None
    matrix = np.array(obj.matrix_world)
    count = len(mesh.vertices)

    def read(block):
        flat = np.empty(count * 3)
        block.data.foreach_get("co", flat)
        return flat.reshape(-1, 3) @ matrix[:3, :3].T

    blocks = mesh.shape_keys.key_blocks
    rest_local = read(mesh.shape_keys.reference_key)
    offsets = {}
    for block in blocks:
        if block == mesh.shape_keys.reference_key:
            continue
        delta = read(block) - read(block.relative_key)
        if block.vertex_group and block.vertex_group in obj.vertex_groups:
            index = obj.vertex_groups[block.vertex_group].index
            mask = np.zeros(count)
            for vertex in mesh.vertices:
                for element in vertex.groups:
                    if element.group == index:
                        mask[vertex.index] = element.weight
            delta = delta * mask[:, None]
        offsets[block.name] = delta
    mesh.calc_loop_triangles()
    corners = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", corners)
    return rest_local + matrix[:3, 3], corners.reshape(-1, 3), offsets


def _plain_mesh(obj):
    mesh = obj.data
    matrix = np.array(obj.matrix_world)
    flat = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", flat)
    mesh.calc_loop_triangles()
    corners = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", corners)
    return flat.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3], corners.reshape(-1, 3), {}


def run(obj, keys=None, combos=(), partners=(), options=None, accepted=None):
    """Return a report for the mesh object obj. Nothing in the file changes."""
    from mathutils.bvhtree import BVHTree
    bpy = _bpy()
    opt = resolve_options(options)
    if obj is None or obj.type != "MESH" or obj.data.shape_keys is None:
        raise ValueError("--object must be a mesh with shape keys")
    scale = float(bpy.context.scene.unit_settings.scale_length) or 1.0
    unit_mm = scale * 1000.0
    rest, triangles, offsets = _key_data(obj)
    pen = _penetration()
    triangles = pen.clean_triangles(rest, triangles)[0]
    topology = Topology(rest, triangles)
    names = list(offsets) if keys is None else list(keys)
    for name in names:
        if name not in offsets:
            raise ValueError("Shape key not found on " + obj.name + ": " + name)
    recipes = [(name, [(name, None)]) for name in names] + [(text, parse_recipe(text)) for text in combos]
    for text, recipe in recipes:
        for key, _ in recipe:
            if key not in offsets:
                raise ValueError("Shape key not found on " + obj.name + ": " + key + " (in " + text + ")")
    others = []
    for partner in partners:
        if partner is None or partner.type != "MESH":
            raise ValueError("Partners must be mesh objects")
        data = _key_data(partner) or _plain_mesh(partner)
        others.append((partner.name, data[0], pen.clean_triangles(data[0], data[1])[0], data[2]))
    trees = {}

    def crossing(weights, points):
        own = BVHTree.FromPolygons(points.tolist(), triangles.tolist())
        result = {}
        for name, partner_rest, partner_triangles, partner_offsets in others:
            follow = tuple(sorted((key, weights[key]) for key in weights if key in partner_offsets and weights[key] != 0.0))
            if (name, follow) not in trees:                 # a partner with the same key names follows the same weights
                moved = partner_rest + sum(value * partner_offsets[key] for key, value in follow) if follow else partner_rest
                trees[(name, follow)] = (moved, BVHTree.FromPolygons(moved.tolist(), partner_triangles.tolist()))
            moved, tree = trees[(name, follow)]
            result[name] = crossing_spots(points, triangles, moved, partner_triangles, own.overlap(tree), opt["spot_mm"], unit_mm)
        return result

    known = {}
    if accepted is not None:
        if accepted.get("schema") != REPORT_SCHEMA or accepted.get("object") != obj.name:
            raise ValueError("--accept must be a sweep report of the same object")
        known = {record["name"]: record for record in accepted.get("sweeps", [])}
    records = [sweep(text, recipe, rest, topology, offsets, crossing if others else None, opt, unit_mm, known.get(text))
               for text, recipe in recipes]
    bad = [r for r in records if r["problems"]]
    driven = []
    animation = obj.data.shape_keys.animation_data
    if animation is not None:
        driven = sorted({d.data_path.split('"')[1] for d in animation.drivers if d.data_path.startswith('key_blocks["')})
    return {"schema": REPORT_SCHEMA, "command": "sweep", "object": obj.name, "partners": [p.name for p in partners], "unit": "mm",
            "options": opt, "vertices": int(len(rest)), "keys_on_object": len(offsets), "driven_keys": driven,
            "summary": {"swept": len(records), "with_problems": len(bad), "names_with_problems": [r["name"] for r in bad],
                        "compared_with_accepted": sum(1 for r in records if r["compared_with_accepted"])},
            "sweeps": records,
            "warnings": ["%s: %s" % (r["name"], "; ".join(r["problems"])) for r in bad],
            "unverified": list(UNVERIFIED), "status": "completed_with_findings" if bad else "completed"}


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
    sub = commands.add_parser("sweep")
    sub.add_argument("--input", required=True, type=Path)
    sub.add_argument("--object", required=True)
    which = sub.add_mutually_exclusive_group()
    which.add_argument("--keys", nargs="+")
    which.add_argument("--all", action="store_true", help="every key of the object (the default when --keys is absent)")
    sub.add_argument("--combo", nargs="+", default=[], help="combinations such as happy+blink or happy=1+blink")
    sub.add_argument("--partners", nargs="+", default=[], help="meshes that must not be crossed (eyeballs, teeth)")
    sub.add_argument("--report", required=True, type=Path)
    sub.add_argument("--accept", type=Path, help="an earlier sweep report of an approved model; only worse values are problems")
    for key, value in DEFAULTS.items():
        sub.add_argument("--" + key.replace("_", "-"), type=int if isinstance(value, int) else float)
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
        options = {key: getattr(args, key) for key in DEFAULTS if getattr(args, key, None) is not None}
        for text in args.combo:
            parse_recipe(text)
        accepted = None
        if args.accept is not None:
            with args.accept.expanduser().resolve().open("r", encoding="utf-8") as stream:
                accepted = json.load(stream)
        before_sha = _file_hash(source)
        bpy = _bpy()
        if not bpy.app.background:
            raise ValueError("Run the CLI in a separate Blender background process; use run() in an interactive session")
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)

        def find(name):
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError("Object not found: " + name)
            return obj

        report = run(find(args.object), args.keys, args.combo, [find(name) for name in args.partners], options, accepted)
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        code = 2 if report["warnings"] else 0
        _write_report(report_path, report)
        print(json.dumps({"command": "sweep", "status": report["status"], "summary": report["summary"],
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
