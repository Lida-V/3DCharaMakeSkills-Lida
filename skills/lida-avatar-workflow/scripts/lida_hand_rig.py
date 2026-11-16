# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Measure a hand mesh, place the finger joints, rolls and weights from it, and check the grips.

Run in Blender with ``--background --factory-startup --python THIS.py -- COMMAND``.

measure: --input MODEL.blend --mesh Body --side left (--rig Armature --bones MAP.json | --wrist X Y Z --toward X Y Z)
         --report NEW.json [--render-dir NEW_FOLDER]
place:   --input MODEL.blend --mesh Body --rig Armature --bones MAP.json --side left|right|both
         --report NEW.json --output-blend NEW.blend [--keep-weights] [--thumb-roll auto|DEGREES] [--z-toward palm|back]
         [--rigid-followers Nails ...]
check:   --input MODEL.blend --mesh Body --rig Armature --bones MAP.json --side left|right|both
         --report NEW.json [--render-dir NEW_FOLDER] [--poses relax grip fist point pinch spread opposition]
         [--followers Nails ...]

measure splits the hand into five fingers by surface connectivity (a merge tree of the distance
along the surface from the wrist), so a ray or a nearest point never picks up a neighbouring finger.
Each finger's joints are read from the mesh where it shows them (a palmar crease, a dorsal knuckle,
a gathering of edge loops) inside a window around an anatomical prior; where the mesh is silent the
prior is used and the report says so. The back of the hand follows from the side, the finger
direction and the thumb, so no axis is guessed from names.

place writes the measured joints into the finger bones of a copy, rolls each bone so that bending it
curls the finger toward the palm and, more and more along the finger, toward the wrist centre, and
(unless --keep-weights) replaces the hand weights by chains along each finger with smooth bands at
the joints, faded into the old weights over the wrist. The thumb bends across the palm (between "toward
the palm" and "toward the little finger"); its roll is searched so that the thumb can both rest on the
curled fingers in a fist and meet the index fingertip in a pinch without passing through a finger.

check bends the fingers through standard grips in steps with linear blend skinning computed from the
rest data. The thumb angles of each grip are solved for this hand (tip on the curled fingers, tip to the
index fingertip, ...) instead of using fixed numbers, and reported. It counts crossing curves between fingers, folds inside a finger, fingertips entering
the palm and stretched edges. One pose is also evaluated in Blender to confirm the skinning matches.

The numeric core needs numpy only. The input blend is never saved; place writes a new blend. Exit
codes: 0 nothing to report; 2 findings, warnings or a usage error; 1 invalid input or execution error.
"""

import argparse
import hashlib
import heapq
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np


REPORT_SCHEMA = "lida.hand-rig.report.v1"
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Little")
SEGMENTS = {"Thumb": ("Metacarpal", "Proximal", "Distal")}
SEGMENTS.update({name: ("Proximal", "Intermediate", "Distal") for name in FINGERS[1:]})
JOINT_NAMES = {"Thumb": ("cmc", "mcp", "ip", "tip")}
JOINT_NAMES.update({name: ("mcp", "pip", "dip", "tip") for name in FINGERS[1:]})
DEFAULTS = {
    "min_finger": 0.12,         # a branch shorter than this share of the wrist-to-tip distance is a bump, not a finger
    "window": 0.10,             # joints are searched within +/- this share of the finger length around the prior
    "feature_floor": 0.12,      # combined feature score needed to trust the mesh over the prior (see pick())
    "mcp_prior": 0.25,          # MCP lies this share of the visible finger length before the web
    "pip_prior": 0.49,          # PIP and DIP as shares of the MCP-to-tip length (phalanges about 1 : 0.6 : 0.45)
    "dip_prior": 0.78,
    "thumb_mcp_prior": 0.02,    # thumb MCP and IP as shares of the visible thumb length from its web
    "thumb_ip_prior": 0.55,
    "thumb_metacarpal": 1.35,   # thumb metacarpal length as a multiple of the proximal phalanx
    "converge": 0.3,            # 0 curls straight toward the palm; 1 aims the fingertip at the wrist centre (strong values push ring into middle)
    "fade_mm": 15.0,            # new hand weights fade in over this distance past the wrist plane
    "joint_band": 1.0,          # weight transition half-width at a joint, times the finger radius (narrow bands fold the knuckle)
    "smooth": 4,                # Laplacian passes over the new weights
    "steps": 4,                 # in-between steps per pose (0.25, 0.5, ...)
    "stretch": 1.5,             # an edge longer than this multiple of its rest length ...
    "stretch_mm": 3.0,          # ... and longer by more than this counts as stretched
    "cross_tolerance_mm": 1.0,  # crossing curves shorter than this are not warned about
    "spot_mm": 3.0,
    "follower_drift_mm": 1.0,   # a nail or other follower moving more than this against the skin under it is warned about
}
POSES = {   # degrees: fingers (proximal, middle, distal), thumb (metacarpal, proximal, distal); oppose turns the
            # thumb metacarpal about the hand's long axis toward the palm before it bends
    "relax": {"fingers": (20, 30, 15), "thumb": (10, 15, 10), "oppose": 10},
    "grip": {"fingers": (60, 70, 40), "thumb": (15, 35, 40), "oppose": 10},
    "fist": {"fingers": (85, 95, 60), "thumb": (20, 45, 50), "oppose": 10},
    "point": {"fingers": (85, 95, 60), "thumb": (20, 45, 50), "oppose": 10, "Index": (0, 0, 0)},
    "pinch": {"fingers": (20, 30, 15), "thumb": (15, 25, 30), "oppose": 45, "Index": (35, 45, 30)},
    "spread": {"fingers": (0, 0, 0), "thumb": (0, 0, 0), "spread": 12.0},
    "opposition": {"fingers": (20, 30, 15), "thumb": (25, 30, 30), "oppose": 70},
}
UNVERIFIED = [
    "whether the grips look right: fist shape, how far the thumb wraps, knuckle shape (render and look)",
    "the shape of the hand itself (a short thumb or thin fingers are not fixed by joints or weights)",
    "joints marked 'prior' in the report: the mesh showed no crease, knuckle or loop gathering there",
    "gloves, rings and other soft or shared meshes on the finger bones (only --rigid-followers pieces are re-weighted)",
    "dual-quaternion or volume-preserving skinning, corrective shape keys and the destination application",
]


# ---------------------------------------------------------------- numeric core (numpy only)

def resolve_options(options=None):
    resolved = dict(DEFAULTS)
    for key, value in (options or {}).items():
        if key not in DEFAULTS:
            raise ValueError("Unknown option: " + str(key))
        if value is not None:
            resolved[key] = value
    for key, value in resolved.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError(key + " must be a finite non-negative number")
    resolved["steps"] = max(1, int(resolved["steps"]))
    resolved["smooth"] = int(resolved["smooth"])
    if not 0 < resolved["min_finger"] < 1:
        raise ValueError("min_finger must be between 0 and 1")
    return resolved


def _unit(vector):
    vector = np.asarray(vector, float)
    length = np.linalg.norm(vector)
    if not length > 1e-12:
        raise ValueError("A direction has zero length")
    return vector / length


def _perp(vector, axis):
    return vector - axis * float(vector @ axis)


def rotation(axis, degrees):
    """Rotation matrix about a unit axis (right hand)."""
    axis = _unit(axis)
    angle = math.radians(degrees)
    x, y, z = axis
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)


def edge_neighbours(count, triangles):
    """Undirected edge lists per vertex from triangles."""
    triangles = np.asarray(triangles, np.int64).reshape(-1, 3)
    edges = np.unique(np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1), axis=0)
    neighbours = [[] for _ in range(count)]
    for a, b in edges:
        neighbours[a].append(b)
        neighbours[b].append(a)
    return [np.array(n, np.int64) for n in neighbours], edges


def geodesic(points, neighbours, sources, allowed=None):
    """Distance along the edges from the source vertices (Dijkstra). Unreached vertices are inf."""
    points = np.asarray(points, float)
    distance = np.full(len(points), np.inf)
    heap = []
    for s in sources:
        distance[s] = 0.0
        heap.append((0.0, int(s)))
    heapq.heapify(heap)
    while heap:
        d, v = heapq.heappop(heap)
        if d > distance[v]:
            continue
        for u in neighbours[v]:
            if allowed is not None and not allowed[u]:
                continue
            nd = d + float(np.linalg.norm(points[u] - points[v]))
            if nd < distance[u]:
                distance[u] = nd
                heapq.heappush(heap, (nd, int(u)))
    return distance


def hand_region(points, neighbours, wrist, toward):
    """Vertices past the wrist plane that are connected to the hand: (mask, along, sources)."""
    points = np.asarray(points, float)
    toward = _unit(toward)
    along = (points - wrist) @ toward
    past = along > 0
    if not past.any():
        raise ValueError("No vertices lie past the wrist plane; check --wrist and --toward")
    radial = np.linalg.norm(points - wrist - np.outer(along, toward), axis=1)
    near = past & (along <= np.quantile(along[past], 0.3))
    seed = int(np.argmin(np.where(near, radial, np.inf)))           # the skin closest to the forearm axis, just past the wrist
    mask = np.zeros(len(points), bool)
    mask[seed] = True
    stack = [seed]
    while stack:
        v = stack.pop()
        for u in neighbours[v]:
            if past[u] and not mask[u]:
                mask[u] = True
                stack.append(u)
    reach = along[mask].max()
    sources = np.nonzero(mask & (along < max(reach * 0.04, 1e-6)))[0]
    if not len(sources):
        sources = np.array([int(np.argmin(np.where(mask, along, np.inf)))])
    return mask, along, sources


def finger_branches(distance, neighbours, mask, min_extent):
    """Merge tree of the distance from the wrist, swept from the fingertips down.

    A branch is recorded when it meets another branch at least min_extent long; a branch formed by
    merging two such branches is never recorded. Returns a list of dicts: members, web, tip, extent.
    """
    order = [int(v) for v in np.argsort(-distance) if mask[v] and np.isfinite(distance[v])]
    parent = {}
    members, top, tip, leaf = {}, {}, {}, {}

    def find(v):
        root = v
        while parent[root] != root:
            root = parent[root]
        while parent[v] != root:
            parent[v], v = root, parent[v]
        return root

    branches = []
    for v in order:
        roots = {find(int(u)) for u in neighbours[v] if int(u) in parent}
        parent[v] = v
        members[v], top[v], tip[v], leaf[v] = [v], distance[v], v, True
        if not roots:
            continue
        roots = list(roots)
        big = [r for r in roots if top[r] - distance[v] >= min_extent]
        if len(big) >= 2:
            for r in big:
                if leaf[r]:
                    branches.append({"members": np.array(members[r], np.int64), "web": float(distance[v]),
                                     "tip": int(tip[r]), "extent": float(top[r] - distance[v])})
        roots.append(v)
        roots.sort(key=lambda r: -len(members[r]))
        keep = roots[0]
        is_leaf = len(big) < 2 and all(leaf[r] for r in big)
        for r in roots[1:]:
            parent[r] = keep
            members[keep].extend(members[r])
            if top[r] > top[keep]:
                top[keep], tip[keep] = top[r], tip[r]
            del members[r]
        leaf[keep] = is_leaf
    return branches


def _moving(values, width):
    width = max(1, int(width))
    kernel = np.ones(2 * width + 1) / (2 * width + 1)
    padded = np.pad(values, width, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def _robust_z(values):
    finite = np.isfinite(values)
    if finite.sum() < 3:
        return np.zeros_like(values)
    median = np.median(values[finite])
    spread = 1.4826 * np.median(np.abs(values[finite] - median)) + 1e-12
    return np.where(finite, (values - median) / spread, 0.0)


def profile(points, triangles, origin, axis, back, start, stop, step, loop_sigma):
    """Plane sections across the axis (exact on the triangles, however coarse the mesh).

    Rows: (s, centre, mean radius, dorsal height, palmar depth, loop density, axis centre). The centre is the
    length-weighted centre of the section outline. Dorsal height and palmar depth are measured from the
    axis line, not from the centre: a palm crease moves the centre too, and against the centre the crease
    and the knuckle would cancel. The loop density is a smoothed count of mesh vertices near s (edge loops
    gather at joints on a quad mesh).
    """
    points = np.asarray(points, float)
    triangles = np.asarray(triangles, np.int64).reshape(-1, 3)
    s_point = (points - origin) @ axis
    vertex_s = np.unique(s_point[triangles].ravel())
    rows = []
    for s in np.arange(start, stop + step * 0.5, step):
        signed = s_point[triangles] - s
        cut = (signed.min(1) < 0) & (signed.max(1) > 0)
        density = float(np.exp(-0.5 * ((vertex_s - s) / loop_sigma) ** 2).sum())
        if cut.sum() < 3:
            rows.append((float(s), None, np.nan, np.nan, np.nan, density, None))
            continue
        corners = points[triangles[cut]]
        signs = signed[cut]
        ends = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            crossing = signs[:, i] * signs[:, j] < 0
            share = signs[:, i] / np.where(crossing, signs[:, i] - signs[:, j], 1.0)
            ends.append(np.where(crossing[:, None], corners[:, i] + share[:, None] * (corners[:, j] - corners[:, i]), np.nan))
        ends = np.stack(ends, 1)
        pieces = np.array([e[~np.isnan(e[:, 0])][:2] for e in ends if (~np.isnan(e[:, 0])).sum() >= 2])
        if not len(pieces):
            rows.append((float(s), None, np.nan, np.nan, np.nan, density, None))
            continue
        middle = pieces.mean(1)
        weight = np.linalg.norm(pieces[:, 1] - pieces[:, 0], axis=1) + 1e-12
        centre = (middle * weight[:, None]).sum(0) / weight.sum()
        radius = float((np.linalg.norm(middle - centre, axis=1) * weight).sum() / weight.sum())
        on_axis = origin + axis * s
        level = (middle - on_axis) @ back
        thick_centre = on_axis + back * float((level.max() + level.min()) / 2)   # on the axis line, halfway through the thickness
        rows.append((float(s), centre, radius, float(level.max()), float(-level.min()), density, thick_centre))
    return rows


def feature_scores(rows, radius, use=("knuckle", "crease", "loops"), width_share=0.15):
    """Per-row joint features, each against its own moving average over width_share of the profile:
    a dorsal knuckle and a palmar crease (in units of the finger radius) and a gathering of edge loops (relative)."""
    dorsal = np.array([r[3] for r in rows])
    palmar = np.array([r[4] for r in rows])
    density = np.array([r[5] for r in rows], float)
    width = max(2, int(len(rows) * width_share / 2))
    dorsal_f = np.nan_to_num(dorsal, nan=float(np.nanmean(dorsal)))
    palmar_f = np.nan_to_num(palmar, nan=float(np.nanmean(palmar)))
    features = {"knuckle": (dorsal_f - _moving(dorsal_f, width)) / radius,
                "crease": (_moving(palmar_f, width) - palmar_f) / radius,
                "loops": (density - _moving(density, width)) / np.maximum(_moving(density, width), 1e-9)}
    return sum(features[k] for k in use), features


def pick_pair(rows, pip_prior, dip_prior, low, high, floor, radius, pull=0.5, ratio=(0.3, 0.65)):
    """PIP and DIP together: the two feature peaks with the best combined score, judged by how far each sits
    from its prior (pull per length of the search range) and whether the distal part keeps a finger-like
    share, (tip - DIP) / (tip - PIP) inside ratio. Returns None when no pair clears the floor."""
    at = np.array([r[0] for r in rows])
    score, features = feature_scores(rows, radius)
    filled = np.array([r[1] is not None for r in rows])
    peak = np.zeros(len(rows), bool)
    peak[1:-1] = (score[1:-1] >= score[:-2]) & (score[1:-1] >= score[2:])
    candidates = np.nonzero(peak & filled & (score >= floor) & (at >= low) & (at <= high))[0]
    span = max(high - low, 1e-12)
    best, choice = None, None
    for i in candidates:
        for j in candidates:
            if at[j] <= at[i]:
                continue
            share = (high - at[j]) / max(high - at[i], 1e-12)
            if not ratio[0] <= share <= ratio[1]:
                continue
            value = score[i] + score[j] - pull * (abs(at[i] - pip_prior) + abs(at[j] - dip_prior)) / span
            if best is None or value > best:
                best, choice = value, (i, j)
    if choice is None:
        return None
    return [(float(at[k]), "mesh", round(float(score[k]), 3), {n: round(float(features[n][k]), 3) for n in features})
            for k in choice]


def pick(rows, prior, window, floor, radius, use=("knuckle", "crease", "loops"), width_share=0.15):
    """Choose a joint along a profile: the strongest feature near the prior, else the prior (features: feature_scores)."""
    at = np.array([r[0] for r in rows])
    dorsal = np.array([r[3] for r in rows])
    palmar = np.array([r[4] for r in rows])
    density = np.array([r[5] for r in rows], float)
    width = max(2, int(len(rows) * width_share / 2))
    dorsal_f = np.nan_to_num(dorsal, nan=float(np.nanmean(dorsal)))
    palmar_f = np.nan_to_num(palmar, nan=float(np.nanmean(palmar)))
    features = {"knuckle": (dorsal_f - _moving(dorsal_f, width)) / radius,
                "crease": (_moving(palmar_f, width) - palmar_f) / radius,
                "loops": (density - _moving(density, width)) / np.maximum(_moving(density, width), 1e-9)}
    score = sum(features[k] for k in use)
    near = (np.abs(at - prior) <= window) & np.array([r[1] is not None for r in rows])
    if not near.any():
        return float(prior), "prior", None, {}
    best = int(np.argmax(np.where(near, score, -np.inf)))
    best_score = round(float(score[best]), 3)
    if score[best] >= floor:
        return float(at[best]), "mesh", best_score, {k: round(float(features[k][best]), 3) for k in use}
    return float(prior), "prior", best_score, {}


def _centre_at(rows, s):
    filled = [(r[0], r[1]) for r in rows if r[1] is not None]
    if not filled:
        raise ValueError("A finger has no cross-sections")
    at = np.array([f[0] for f in filled])
    centres = np.array([f[1] for f in filled])
    if s <= at[0]:
        return centres[0]
    if s >= at[-1]:
        return centres[-1]
    return np.array([np.interp(s, at, centres[:, k]) for k in range(3)])


def _extend_line(rows, s):
    """The knuckle inside the palm: the line through the proximal finger's section centres, extended back to s."""
    filled = [(r[0], r[1]) for r in rows if r[1] is not None]
    at = np.array([f[0] for f in filled])
    centres = np.array([f[1] for f in filled])
    slope, intercept = np.polyfit(at, centres, 1)
    return intercept + slope * s


def _axis_centre_at(rows, s):
    """Inside the palm: on the finger's axis line, halfway through the palm thickness (steadier than the slab centroid)."""
    filled = [(r[0], r[6]) for r in rows if r[6] is not None]
    if not filled:
        return _centre_at(rows, s)
    at = np.array([f[0] for f in filled])
    centres = np.array([f[1] for f in filled])
    return np.array([np.interp(s, at, centres[:, k]) for k in range(3)])


def _radius_at(rows, s):
    filled = [(r[0], r[2]) for r in rows if r[1] is not None and np.isfinite(r[2])]
    at = np.array([f[0] for f in filled])
    return float(np.interp(s, at, [f[1] for f in filled]))


def measure_hand(points, triangles, wrist, toward, side, back=None, options=None, unit_mm=1000.0):
    """Fingers, joints, back-of-hand direction and vertex labels of one hand. Pure numpy; nothing changes."""
    opt = resolve_options(options)
    if side not in ("left", "right"):
        raise ValueError("side must be left or right")
    points = np.asarray(points, float)
    wrist = np.asarray(wrist, float)
    toward = _unit(toward)
    neighbours, edges = edge_neighbours(len(points), triangles)
    mask, along, sources = hand_region(points, neighbours, wrist, toward)
    distance = geodesic(points, neighbours, sources, allowed=mask)
    reach = float(np.nanmax(np.where(mask & np.isfinite(distance), distance, np.nan)))
    branches = finger_branches(distance, neighbours, mask, opt["min_finger"] * reach)
    warnings = []
    if len(branches) < 5:
        raise ValueError("Found %d fingers instead of 5; the fingers may be fused, or the wrist point is wrong" % len(branches))
    if len(branches) > 5:
        warnings.append("Found %d branches; kept the five longest (spikes or loose pieces on the hand?)" % len(branches))
        branches = sorted(branches, key=lambda b: -b["extent"])[:5]
    thumb = min(range(5), key=lambda i: branches[i]["web"])
    base = [points[b["members"][distance[b["members"]] < b["web"] + 0.08 * b["extent"]]].mean(0) for b in branches]
    middle_line = _unit(np.mean([points[b["tip"]] for i, b in enumerate(branches) if i != thumb], axis=0) - wrist)
    thumb_side = _unit(_perp(base[thumb] - wrist, middle_line))
    # anatomy fixes the back of the hand: left hand thumb_side = finger direction x back; right hand back x direction
    derived_back = _unit(np.cross(thumb_side, middle_line) if side == "left" else np.cross(middle_line, thumb_side))
    palm_points = points[mask & ~np.isin(np.arange(len(points)), np.concatenate([b["members"] for b in branches]))]
    if len(palm_points) >= 10:                     # refine with the palm's own plane; keep the sign from the anatomy
        normal = np.linalg.svd(palm_points - palm_points.mean(0), full_matrices=False)[2][2]
        normal = _unit(_perp(normal, middle_line))
        if abs(float(normal @ derived_back)) > 0.6:
            derived_back = normal if float(normal @ derived_back) > 0 else -normal
    if back is not None:
        given = _unit(_perp(np.asarray(back, float), middle_line))
        if float(given @ derived_back) < 0.5:
            warnings.append("The given --back differs from the one the thumb implies (is --side right?)")
        back = given
        back_method = "given"
    else:
        back, back_method = derived_back, "side + thumb + finger direction"
    lateral = _unit(np.cross(middle_line, back) if side == "left" else np.cross(back, middle_line))  # points to the thumb
    others = sorted([i for i in range(5) if i != thumb], key=lambda i: -float((base[i] - wrist) @ lateral))
    order = [thumb] + others
    if float((base[order[1]] - wrist) @ lateral) < float((base[order[4]] - wrist) @ lateral):
        warnings.append("Finger order across the palm looks reversed; check --side")
    labels = np.full(len(points), -1, np.int64)
    labels[mask] = 0                                                   # palm
    fingers = {}
    finger_vertices = {}
    for slot, index in enumerate(order):
        name = FINGERS[slot]
        branch = branches[index]
        verts = branch["members"]
        labels[verts] = slot + 1
        finger_vertices[name] = verts
        fingers[name] = {"branch": branch, "base": base[index]}
    for slot, name in enumerate(FINGERS):
        data = fingers[name]
        branch = data["branch"]
        verts = finger_vertices[name]
        tip_point = points[branch["tip"]]
        axis = _unit(tip_point - data["base"])
        visible = float((tip_point - data["base"]) @ axis)          # web to tip along the finger axis
        local_back = _unit(_perp(back, axis))
        across = _unit(np.cross(axis, local_back))
        step = max(visible / 60.0, 1e-6)
        # the lane: palm vertices behind the web that sit in this finger's line (for the knuckle inside the palm)
        neighbours_base = [fingers[n]["base"] for n in FINGERS if n != name]
        spacing = min(abs(float((b - data["base"]) @ across)) for b in neighbours_base) or visible * 0.3
        in_finger = np.zeros(len(points), bool)
        in_finger[verts] = True
        finger_tris = np.asarray(triangles, np.int64).reshape(-1, 3)
        rows_fin = profile(points, finger_tris[in_finger[finger_tris].all(1)], data["base"], axis, local_back,
                           0.08 * visible, 0.45 * visible, step, visible / 25.0)
        radius = float(np.nanmedian([r[2] for r in rows_fin if r[1] is not None]))
        lane_radius = min(0.5 * spacing, 1.6 * radius)
        palm = np.nonzero(labels == 0)[0]
        rel = points[palm] - data["base"]
        s_lane_axis = rel @ axis
        off = np.abs(rel @ across)                     # a slab through the whole palm thickness, as wide as the finger lane
        reach_back = 0.55 * visible if name != "Thumb" else 0.25 * visible
        lane = palm[(off < lane_radius) & (s_lane_axis < 0.05 * visible) & (s_lane_axis > -reach_back)]
        in_both = in_finger.copy()
        in_both[lane] = True
        both_tris = finger_tris[in_both[finger_tris].all(1)]
        rows = profile(points, both_tris, data["base"], axis, local_back, -reach_back, visible, step, visible / 25.0)
        joints, methods = [], []
        window = opt["window"] * visible
        if name == "Thumb":
            mcp_s, mcp_m, mcp_score, mcp_parts = pick(rows, opt["thumb_mcp_prior"] * visible, window * 1.5, opt["feature_floor"], radius, use=("knuckle", "crease"))
            ip_s, ip_m, ip_score, ip_parts = pick(rows, opt["thumb_ip_prior"] * visible, window * 1.2, opt["feature_floor"], radius)
            mcp, ip = _centre_at(rows, mcp_s), _centre_at(rows, ip_s)
            tip = _centre_at(rows, visible * 0.97)
            proximal = float(np.linalg.norm(ip - mcp))
            toward_wrist = _unit(wrist - mcp)
            direction = _unit(0.5 * _unit(mcp - ip) + 0.5 * toward_wrist)
            cmc = mcp + direction * opt["thumb_metacarpal"] * proximal
            if float((cmc - wrist) @ toward) < 0.05 * reach:              # keep the base of the thumb inside the hand
                cmc = cmc + toward * (0.05 * reach - float((cmc - wrist) @ toward))
            joints = [cmc, mcp, ip, tip]
            methods = [("estimated", None, {}), (mcp_m, mcp_score, mcp_parts), (ip_m, ip_score, ip_parts), ("tip", None, {})]
            positions = [None, mcp_s, ip_s, visible * 0.97]
        else:
            # the knuckle sits inside the palm: search behind the prior more than toward the web, and ask for a clear bump
            mcp_s, mcp_m, mcp_score, mcp_parts = pick(rows, -(opt["mcp_prior"] + 0.03) * visible, 0.09 * visible,
                                                      3 * opt["feature_floor"], radius, use=("knuckle", "crease"))
            if mcp_m == "prior":
                mcp_s = -opt["mcp_prior"] * visible
            length = visible * 0.97 - mcp_s
            pip_s, pip_m, pip_score, pip_parts = pick(rows, mcp_s + opt["pip_prior"] * length, window, opt["feature_floor"], radius)
            dip_s, dip_m, dip_score, dip_parts = pick(rows, mcp_s + opt["dip_prior"] * length, window, opt["feature_floor"], radius)
            if "prior" in (pip_m, dip_m) or mcp_m == "prior":
                # an unsure knuckle shifts both priors; look for the PIP/DIP pair over the whole visible finger instead
                pair = pick_pair(rows, mcp_s + opt["pip_prior"] * length, mcp_s + opt["dip_prior"] * length,
                                 0.1 * visible, visible * 0.97, opt["feature_floor"], radius)
                if pair is not None:
                    (pip_s, pip_m, pip_score, pip_parts), (dip_s, dip_m, dip_score, dip_parts) = pair
            if not mcp_s < pip_s < dip_s < visible * 0.97:
                warnings.append(name + ": joints out of order from the mesh; used the priors")
                pip_s, dip_s = mcp_s + opt["pip_prior"] * length, mcp_s + opt["dip_prior"] * length
                pip_m = dip_m = "prior"
            joints = [_extend_line(rows_fin, mcp_s), _centre_at(rows, pip_s), _centre_at(rows, dip_s), _centre_at(rows, visible * 0.97)]
            methods = [(mcp_m, mcp_score, mcp_parts), (pip_m, pip_score, pip_parts), (dip_m, dip_score, dip_parts), ("tip", None, {})]
            positions = [mcp_s, pip_s, dip_s, visible * 0.97]
        lane_set = lane[~np.isin(lane, np.concatenate([finger_vertices[n] for n in FINGERS]))]
        data.update({"joints": np.array(joints), "methods": methods, "positions": positions, "radius": radius,
                     "visible": visible, "axis": axis, "lane": lane_set, "rows": rows})
        for joint_name, (method, _score, _parts) in zip(JOINT_NAMES[name], methods):
            if method == "prior":
                warnings.append("%s %s: no clear mesh feature; placed at the prior" % (name, joint_name.upper()))
    thumb_share = fingers["Thumb"]["visible"] / max(fingers["Index"]["visible"], 1e-12)
    if thumb_share < 0.55:
        warnings.append("Thumb: its free length is %d%% of the index finger's (roughly two thirds on a human hand); "
                        "it cannot reach across the fingers, which joints and weights do not fix" % round(thumb_share * 100))
    return {"points": points, "triangles": np.asarray(triangles, np.int64).reshape(-1, 3), "edges": edges,
            "neighbours": neighbours, "mask": mask, "along": along, "distance": distance, "labels": labels,
            "fingers": fingers, "back": back, "back_method": back_method, "lateral": lateral, "wrist": wrist,
            "spread_axis": _unit(np.cross(middle_line, lateral)),   # +angle about it turns a finger toward the thumb
            "oppose_axis": _oppose_axis(points, branches[thumb], middle_line, back),
            "toward": toward, "side": side, "reach": reach, "warnings": warnings, "unit_mm": unit_mm, "options": opt}


def _oppose_axis(points, thumb_branch, long_axis, back):
    """The hand's long axis, signed so that +angle swings the thumb tip toward the palm."""
    tip = points[thumb_branch["tip"]]
    lever = _perp(tip - points[thumb_branch["members"]].mean(0), long_axis)
    if np.linalg.norm(lever) < 1e-12:
        return long_axis
    swing = np.cross(long_axis, lever)
    return long_axis if float(swing @ -back) >= 0 else -long_axis


def hinge_axes(hand, converge=None, thumb_roll=0.0):
    """Bend axis per bone: bending +angle about it curls the finger toward the palm and toward the wrist centre."""
    opt = hand["options"]
    converge = opt["converge"] if converge is None else converge
    back, wrist = hand["back"], hand["wrist"]
    palm = -back
    fingers = hand["fingers"]
    middle = fingers["Middle"]["joints"]
    centre_line = _unit(middle[0] - wrist)
    side_axis = _unit(_perp(hand["lateral"], centre_line))
    axes = {}
    for name in FINGERS:
        joints = fingers[name]["joints"]
        rows = []
        if name == "Thumb":
            # the thumb bends across the palm, not into it: its curl direction lies between "toward the palm"
            # and "toward the little finger" (45 degrees, plus thumb_roll toward the little finger)
            little = fingers["Little"]["joints"][0]
            theta = math.radians(45.0 + thumb_roll)
            for k in range(3):
                d = _unit(joints[k + 1] - joints[k])
                to_palm = _unit(_perp(palm, d))
                across = _perp(_perp(little - joints[1], d), to_palm)
                across = _unit(across) if np.linalg.norm(across) > 1e-9 else np.cross(d, to_palm)
                target = to_palm * math.cos(theta) + across * math.sin(theta)
                rows.append(_unit(np.cross(d, target)))
        else:
            length = float(np.linalg.norm(joints[3] - joints[0]))
            offset = float((joints[0] - wrist) @ side_axis)
            phi = math.atan2(offset, length)
            for k, share in enumerate((0.5, 0.8, 1.0)):
                d = _unit(joints[k + 1] - joints[k])
                a = converge * share * phi
                target = _unit(palm * math.cos(a) - side_axis * math.sin(a))
                rows.append(_unit(np.cross(d, _unit(_perp(target, d)))))
        axes[name] = np.array(rows)
    return axes


def _smoothstep(x, low, high):
    t = np.clip((x - low) / max(high - low, 1e-12), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def bone_list():
    return ["Hand"] + [name + segment for name in FINGERS for segment in SEGMENTS[name]]


def hand_weights(hand):
    """New weights over the hand region: columns follow bone_list(). Fingers are chains with smooth joint bands."""
    opt = hand["options"]
    points, labels = hand["points"], hand["labels"]
    region = np.nonzero(hand["mask"])[0]
    names = bone_list()
    weights = np.zeros((len(points), len(names)))
    weights[region, 0] = 1.0
    claimed = np.full(len(points), np.inf)
    for slot, name in enumerate(FINGERS):
        data = hand["fingers"][name]
        joints = data["joints"]
        verts = np.concatenate([np.nonzero(labels == slot + 1)[0], data["lane"]])
        if name == "Thumb":                                         # the thenar pad follows the thumb metacarpal
            palm = np.nonzero(labels == 0)[0]
            a, b = joints[0], joints[1]
            ab = b - a
            t = np.clip(((points[palm] - a) @ ab) / (ab @ ab), 0, 1)
            gap = np.linalg.norm(points[palm] - (a + t[:, None] * ab), axis=1)
            verts = np.concatenate([verts, palm[gap < 1.8 * data["radius"]]])
        verts = np.unique(verts)
        lengths = np.linalg.norm(np.diff(joints, axis=0), axis=1)
        knots = np.concatenate([[0.0], np.cumsum(lengths)])
        best_u = np.full(len(verts), -np.inf)
        best_gap = np.full(len(verts), np.inf)
        for k in range(3):
            a, b = joints[k], joints[k + 1]
            ab = b - a
            t = ((points[verts] - a) @ ab) / (ab @ ab)
            t_clip = np.clip(t, 0 if k else -np.inf, 1 if k < 2 else np.inf)
            gap = np.linalg.norm(points[verts] - (a + t_clip[:, None] * ab), axis=1)
            better = gap < best_gap
            best_gap[better] = gap[better]
            best_u[better] = knots[k] + t_clip[better] * lengths[k]
        own = best_gap < claimed[verts]
        verts, u = verts[own], best_u[own]
        claimed[verts] = best_gap[own]
        band = opt["joint_band"] * data["radius"]
        column = names.index(name + SEGMENTS[name][0])
        if name == "Thumb":
            start = _smoothstep(u, -0.1 * lengths[0], 0.6 * lengths[0])     # wide: the thenar pad blends into the hand
        else:
            start = _smoothstep(u, -band, band)
        second = _smoothstep(u, knots[1] - band, knots[1] + band)
        third = _smoothstep(u, knots[2] - band, knots[2] + band)
        row = np.zeros((len(verts), len(names)))
        row[:, 0] = 1 - start
        row[:, column] = start - second
        row[:, column + 1] = second - third
        row[:, column + 2] = third
        weights[verts] = row
    neighbours = hand["neighbours"]
    inside = hand["mask"]
    for _ in range(opt["smooth"]):
        fresh = weights.copy()
        for v in region:
            ring = [u for u in neighbours[v] if inside[u]]
            if ring:
                fresh[v] = 0.5 * weights[v] + 0.5 * weights[ring].mean(0)
        weights = fresh
    weights[region] /= np.maximum(weights[region].sum(1, keepdims=True), 1e-12)
    return names, weights


def segment_turn(hand, axes, pose, name, k):
    """Rotation of one finger bone in rest space for a pose = (angles, spread, oppose)."""
    angles, spread, oppose = pose
    turn = rotation(axes[name][k], angles[name][k])
    if k == 0 and spread and spread.get(name):
        turn = rotation(hand["spread_axis"], spread[name]) @ turn
    if k == 0 and name == "Thumb" and oppose:
        turn = rotation(hand["oppose_axis"], oppose) @ turn
    return turn


def chain_matrices(hand, hand_joints, axes, pose):
    """4x4 rest-to-pose transforms per bone (bone_list order); the hand bone stays still."""
    names = bone_list()
    matrices = {"Hand": np.eye(4)}
    for name in FINGERS:
        parent = np.eye(4)
        for k, segment in enumerate(SEGMENTS[name]):
            joint = hand_joints[name][k]
            turn = segment_turn(hand, axes, pose, name, k)
            local = np.eye(4)
            local[:3, :3] = turn
            local[:3, 3] = joint - turn @ joint
            parent = parent @ local
            matrices[name + segment] = parent
    return np.array([matrices[n] for n in names])


def skin(points, weights, matrices):
    """Linear blend skinning; weight left over (other bones) keeps the rest position."""
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    moved = np.einsum("bij,nj->bni", matrices[:, :3, :], homogeneous)
    rest_share = 1.0 - weights.sum(1)
    return np.einsum("nb,bni->ni", weights, moved) + rest_share[:, None] * points


def pose_angles(pose, scale=1.0, thumb=None):
    """thumb = (metacarpal, proximal, distal, oppose) replaces the pose's own thumb values (see fit_thumb)."""
    spec = POSES[pose]
    angles = {}
    for name in FINGERS:
        base = spec.get(name, spec["thumb"] if name == "Thumb" else spec["fingers"])
        angles[name] = [scale * a for a in base]
    if thumb is not None:
        angles["Thumb"] = [scale * a for a in thumb[:3]]
    spread = None
    if spec.get("spread"):
        amount = scale * spec["spread"]
        spread = {"Thumb": amount * 1.5, "Index": amount, "Middle": 0.0, "Ring": -amount, "Little": -amount * 1.6}
    return angles, spread, scale * (spec.get("oppose", 0.0) if thumb is None else thumb[3])


def pieces(count, triangles):
    """Connected pieces of a mesh: a label per vertex (vertices in no triangle get their own label)."""
    parent = np.arange(count)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, c in np.asarray(triangles, np.int64).reshape(-1, 3):
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[rc] = ra
    roots = np.array([find(v) for v in range(count)])
    return np.unique(roots, return_inverse=True)[1]


def nearest_index(points, targets, chunk=2000):
    """For every point, the index of the nearest target and the distance to it."""
    points = np.asarray(points, float)
    index = np.zeros(len(points), np.int64)
    distance = np.zeros(len(points))
    for start in range(0, len(points), chunk):
        block = points[start:start + chunk]
        d = np.linalg.norm(block[:, None, :] - targets[None, :, :], axis=2)
        index[start:start + chunk] = d.argmin(1)
        distance[start:start + chunk] = d.min(1)
    return index, distance


def nearest_k(points, targets, k=4, chunk=2000):
    """For every point, the indices of its k nearest targets and the distances to them."""
    points = np.asarray(points, float)
    k = min(k, len(targets))
    index = np.zeros((len(points), k), np.int64)
    distance = np.zeros((len(points), k))
    for start in range(0, len(points), chunk):
        d = np.linalg.norm(points[start:start + chunk][:, None, :] - targets[None, :, :], axis=2)
        ties = np.argpartition(d, k - 1, axis=1)[:, :k]
        index[start:start + chunk] = ties
        distance[start:start + chunk] = np.take_along_axis(d, ties, axis=1)
    return index, distance


def rigid_follower_bones(points, triangles, hand, weights, reach=3.0):
    """Nails and the like: every connected piece near this hand follows one bone, the one the skin under it follows most.

    Returns (piece label per vertex, {piece: column in bone_list()}, nearest hand vertex per vertex). Pieces
    farther from the hand skin than reach times the thickest finger radius are left out (the other hand, toes).
    """
    region = np.nonzero(hand["mask"])[0]
    label = pieces(len(points), triangles)
    near, distance = nearest_index(points, hand["points"][region])
    near = region[near]
    limit = reach * max(hand["fingers"][n]["radius"] for n in FINGERS)
    chosen = {}
    for piece in np.unique(label):
        members = np.nonzero(label == piece)[0]
        if float(np.median(distance[members])) > limit:
            continue
        chosen[int(piece)] = int(weights[near[members]].sum(0).argmax())
    return label, chosen, near


def follower_drift(model, name, points, weights, near=None, k=4):
    """How far follower vertices slide or lift against the skin under them in a pose (rest units).

    Each vertex is tied to its k nearest skin vertices at rest; the drift is the largest change of those
    distances, so a piece that turns with the skin under it reads 0.
    """
    del near
    region = np.nonzero(model.hand["mask"])[0]
    rest_skin = model.points[region]
    matrices = model.matrices(name, 1.0)
    moved = skin(points, weights, matrices)
    skin_moved = skin(rest_skin, model.weights[region], matrices)
    ties, before = nearest_k(points, rest_skin, k)
    after = np.linalg.norm(moved[:, None, :] - skin_moved[ties], axis=2)
    return np.abs(after - before).max(1)


def _penetration():
    path = Path(__file__).resolve().with_name("lida_penetration_check.py")
    spec = importlib.util.spec_from_file_location("lida_penetration_check_for_hand", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _region_name(label):
    return FINGERS[label - 1] if label > 0 else "Palm"


def box_pairs(corners):
    """Triangle pairs (i < j) whose bounding boxes overlap, found through a grid of cells."""
    low, high = corners.min(1), corners.max(1)
    if not len(corners):
        return np.zeros((0, 2), np.int64)
    size = float(np.max(high - low)) + 1e-12                 # a cell holds the largest triangle
    first = np.floor(low / size).astype(np.int64)
    cells = {}
    for index, key in enumerate(map(tuple, first)):
        cells.setdefault(key, []).append(index)
    found = []
    offsets = [(i, j, k) for i in (0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) > (0, 0, 0) or (i, j, k) == (0, 0, 0)]
    for key, members in cells.items():
        members = np.array(members)
        for offset in offsets:
            other = cells.get((key[0] + offset[0], key[1] + offset[1], key[2] + offset[2]))
            if other is None:
                continue
            other = np.array(other)
            hit = (low[members][:, None] <= high[other][None]).all(2) & (low[other][None] <= high[members][:, None]).all(2)
            a, b = np.nonzero(hit)
            a, b = members[a], other[b]
            keep = a < b if offset == (0, 0, 0) else np.ones(len(a), bool)
            found.append(np.stack([np.minimum(a, b)[keep], np.maximum(a, b)[keep]], 1))
    if not found:
        return np.zeros((0, 2), np.int64)
    return np.unique(np.concatenate(found), axis=0)


def crossings(points, triangles, triangle_labels):
    """Crossing curves between hand triangles that share no vertex: {pair name: segments}.

    A pair inside one region is a fold ("fold:Index"); across regions it is "Index-Middle" and so on.
    """
    pen = _penetration()
    tri = np.asarray(triangles)
    pairs = box_pairs(points[tri])
    if len(pairs):
        share = (tri[pairs[:, 0]][:, :, None] == tri[pairs[:, 1]][:, None, :]).any((1, 2))
        pairs = pairs[~share]
    if not len(pairs):
        return {}
    segments, crossed = pen.tri_tri_segments(points, tri, points, tri, pairs, return_mask=True)
    found = {}
    for (a, b), segment in zip(pairs[crossed], segments):
        la, lb = int(triangle_labels[a]), int(triangle_labels[b])
        if la == lb:
            key = "fold:" + _region_name(la)
        else:
            names = sorted([_region_name(la), _region_name(lb)], key=lambda n: (["Palm"] + list(FINGERS)).index(n))
            key = names[0] + "-" + names[1]
        found.setdefault(key, []).append(segment)
    return {key: np.array(value) for key, value in found.items()}


def classify(key):
    """warn: fingers crossing each other or a finger folding into itself; info: a fingertip entering the palm."""
    if key.startswith("fold:"):
        return "fold" if key != "fold:Palm" else "palm"
    if key.startswith("Palm-"):
        return "palm"
    return "fingers"


class HandModel:
    """Rest points, triangles, labels, joints, axes and weights of one hand, ready to pose with numpy."""

    def __init__(self, hand, joints, axes, weights):
        self.hand = hand
        self.points = hand["points"]
        mask = hand["mask"]
        tri = hand["triangles"]
        keep = mask[tri].all(1)
        self.triangles = tri[keep]
        labels = hand["labels"]
        self.triangle_labels = np.array([np.bincount(labels[t] + 1, minlength=7).argmax() - 1 for t in self.triangles]) if len(self.triangles) else np.zeros(0, np.int64)
        self.joints = joints
        self.axes = axes
        self.weights = weights
        edges = hand["edges"]
        self.edges = edges[mask[edges].all(1)]
        self.rest_length = np.linalg.norm(self.points[self.edges[:, 0]] - self.points[self.edges[:, 1]], axis=1)
        self.thumb_pose = {}                       # pose name -> (metacarpal, proximal, distal, oppose) from fit_thumb
        thumb_or_palm = (self.triangle_labels == 1)
        self.thumb_triangles = self.triangles[thumb_or_palm]
        self.finger_triangles = self.triangles[self.triangle_labels != 1]      # the other fingers and the palm

    def pose(self, name, scale=1.0, thumb_axes=None, thumb=None):
        axes = dict(self.axes)
        if thumb_axes is not None:
            axes["Thumb"] = thumb_axes
        if thumb is None:
            thumb = self.thumb_pose.get(name)
        matrices = chain_matrices(self.hand, self.joints, axes, pose_angles(name, scale, thumb))
        return skin(self.points, self.weights, matrices)

    def matrices(self, name, scale=1.0):
        return chain_matrices(self.hand, self.joints, self.axes, pose_angles(name, scale, self.thumb_pose.get(name)))

    def spec(self, name, scale=1.0):
        return pose_angles(name, scale, self.thumb_pose.get(name))

    def thumb_crossing(self, moved):
        """Length of the curves where the thumb passes through the other fingers or the palm (rest-space units)."""
        if not len(self.thumb_triangles) or not len(self.finger_triangles):
            return 0.0
        pen = _penetration()
        boxes_a = moved[self.thumb_triangles]
        boxes_b = moved[self.finger_triangles]
        low_a, high_a = boxes_a.min(1), boxes_a.max(1)
        low_b, high_b = boxes_b.min(1), boxes_b.max(1)
        near = np.nonzero(((high_b >= low_a.min(0)) & (low_b <= high_a.max(0))).all(1))[0]
        if not len(near):
            return 0.0
        overlap = ((low_a[:, None, :] <= high_b[None, near, :]) & (high_a[:, None, :] >= low_b[None, near, :])).all(2)
        ia, ib = np.nonzero(overlap)
        if not len(ia):
            return 0.0
        pairs = np.stack([ia, near[ib]], 1)
        shared = (self.thumb_triangles[pairs[:, 0]][:, :, None] == self.finger_triangles[pairs[:, 1]][:, None, :]).any((1, 2))
        pairs = pairs[~shared]
        if not len(pairs):
            return 0.0
        segments = pen.tri_tri_segments(moved, self.thumb_triangles, moved, self.finger_triangles, pairs)
        if not len(segments):
            return 0.0
        return float(np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1).sum())

    def segment_vertices(self, name, k):
        """Vertices of one finger that mostly follow its k-th bone."""
        column = 1 + 3 * FINGERS.index(name) + k
        label = self.hand["labels"] == FINGERS.index(name) + 1
        return np.nonzero(label & (self.weights[:, column] > 0.5))[0]

    def metrics(self, moved, options):
        unit = self.hand["unit_mm"]
        found = crossings(moved, self.triangles, self.triangle_labels)
        pen = _penetration()
        groups = {}
        for key, segments in found.items():
            length = float(np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1).sum()) * unit
            spots = len(np.unique(pen.cluster_segments(segments, options["spot_mm"] / unit))) if len(segments) else 0
            groups[key] = {"curve_mm": round(length, 2), "spots": int(spots), "kind": classify(key)}
        new_length = np.linalg.norm(moved[self.edges[:, 0]] - moved[self.edges[:, 1]], axis=1)
        stretched = (new_length > options["stretch"] * self.rest_length) & ((new_length - self.rest_length) * unit > options["stretch_mm"])
        return groups, int(stretched.sum()), found


THUMB_GOALS = {"grip": ("wrap", "Index"), "fist": ("wrap", "Index"), "point": ("wrap", "Middle"),
               "pinch": ("tip", "Index"), "opposition": ("tip", "Little")}
THUMB_CURL = (15.0, 55.0, 65.0)      # metacarpal, proximal, distal at full curl: the thumb folds as one natural arc
THUMB_OPPOSE = 70.0                  # most the metacarpal turns toward the palm


def thumb_from(curl, oppose):
    return (THUMB_CURL[0] * curl, THUMB_CURL[1] * curl, THUMB_CURL[2] * curl, oppose)


def thumb_cost(model, name, thumb, thumb_axes=None):
    """How far the thumb tip is from where the pose wants it (mm), plus a heavy charge for passing through
    the fingers or the palm.

    wrap: the tip rests on the outside of the curled finger's middle part. tip: the tip meets that fingertip.
    """
    hand = model.hand
    unit = hand["unit_mm"]
    kind, finger = THUMB_GOALS[name]
    moved = model.pose(name, 1.0, thumb_axes=thumb_axes, thumb=thumb)
    tip = _thumb_tip(model, moved)
    if kind == "tip":
        target = _finger_tip(model, moved, finger)
        reach = hand["fingers"]["Thumb"]["radius"] + hand["fingers"][finger]["radius"]
    else:
        middle = model.segment_vertices(finger, 1)
        if not len(middle):
            middle = np.nonzero(hand["labels"] == FINGERS.index(finger) + 1)[0]
        centre = moved[middle].mean(0)
        palm_centre = model.points[hand["labels"] == 0].mean(0)
        outward = _unit(centre - palm_centre)
        reach = 0.0
        target = centre + outward * (hand["fingers"][finger]["radius"] + hand["fingers"]["Thumb"]["radius"])
    gap = max(0.0, float(np.linalg.norm(tip - target)) - reach) * unit
    crossing = model.thumb_crossing(moved) * unit
    return gap + 20.0 * crossing, gap, crossing


def fit_thumb(model, name, thumb_axes=None):
    """Thumb angles for one pose: (metacarpal, proximal, distal, oppose), gap mm, crossing mm.

    Two numbers are searched, how far the thumb curls (all three joints together, in fixed shares) and how
    far its base turns toward the palm, so the result always folds like a thumb.
    """
    best = None
    for curl in np.linspace(0.0, 1.0, 9):
        for oppose in np.linspace(0.0, THUMB_OPPOSE, 8):
            cost, gap, cross = thumb_cost(model, name, thumb_from(curl, oppose), thumb_axes)
            if best is None or cost < best[0] - 1e-9:
                best = (cost, gap, cross, float(curl), float(oppose))
    for step_curl, step_oppose in ((0.0625, 5.0), (0.03125, 2.5)):
        _cost, _gap, _cross, curl0, oppose0 = best
        for curl in (curl0 - step_curl, curl0, curl0 + step_curl):
            for oppose in (oppose0 - step_oppose, oppose0, oppose0 + step_oppose):
                if not (0.0 <= curl <= 1.0 and 0.0 <= oppose <= THUMB_OPPOSE):
                    continue
                cost, gap, cross = thumb_cost(model, name, thumb_from(curl, oppose), thumb_axes)
                if cost < best[0] - 1e-9:
                    best = (cost, gap, cross, float(curl), float(oppose))
    _cost, gap, cross, curl, oppose = best
    return tuple(round(a, 2) for a in thumb_from(curl, oppose)), round(gap, 2), round(cross, 2)


def fit_thumb_poses(model, poses):
    """Solve the thumb for every pose that has a goal; store it on the model and return a JSON-ready table."""
    table = {}
    for name in poses:
        if name not in THUMB_GOALS:
            continue
        thumb, gap, cross = fit_thumb(model, name)
        model.thumb_pose[name] = thumb
        table[name] = {"metacarpal": thumb[0], "proximal": thumb[1], "distal": thumb[2], "oppose": thumb[3],
                       "goal": "%s %s" % THUMB_GOALS[name], "gap_mm": gap, "crossing_mm": cross}
    return table


def thumb_search(model, options, angles=(-20.0, -10.0, 0.0, 10.0, 20.0)):
    """Try thumb rolls; for each, solve the fist and the pinch, and keep the roll whose thumb reaches both best."""
    del options
    rows = []
    for roll in angles:
        axes = hinge_axes(model.hand, thumb_roll=float(roll))["Thumb"]
        _fist, fist_gap, fist_cross = fit_thumb(model, "fist", thumb_axes=axes)
        _pinch, pinch_gap, pinch_cross = fit_thumb(model, "pinch", thumb_axes=axes)
        rows.append({"roll_deg": float(roll), "fist_gap_mm": fist_gap, "fist_thumb_crossing_mm": fist_cross,
                     "pinch_gap_mm": pinch_gap, "pinch_thumb_crossing_mm": pinch_cross})
    best = min(rows, key=lambda r: r["fist_gap_mm"] + r["pinch_gap_mm"] + 20.0 * (r["fist_thumb_crossing_mm"] + r["pinch_thumb_crossing_mm"]))
    return best["roll_deg"], rows


def _tip_vertices(model, name):
    labels = model.hand["labels"]
    slot = FINGERS.index(name) + 1
    verts = np.nonzero(labels == slot)[0]
    distance = model.hand["distance"][verts]
    return verts[distance >= np.quantile(distance, 0.9)]


def _finger_tip(model, moved, name):
    return moved[_tip_vertices(model, name)].mean(0)


def _thumb_tip(model, moved):
    return _finger_tip(model, moved, "Thumb")


def check_poses(model, poses, options):
    """Every pose in steps: crossing curves by pair, folds, palm entries, stretched edges, thumb reach."""
    unit = model.hand["unit_mm"]
    rest_groups, _rest_stretch, _ = model.metrics(model.points, options)
    results, warnings, marks = [], [], {}
    thumb_table = fit_thumb_poses(model, poses)
    for name in poses:
        worst = {}
        stretched_max = 0
        for step in range(1, options["steps"] + 1):
            scale = step / options["steps"]
            moved = model.pose(name, scale)
            groups, stretched, found = model.metrics(moved, options)
            stretched_max = max(stretched_max, stretched)
            for key, value in groups.items():
                base = rest_groups.get(key, {"curve_mm": 0.0, "spots": 0})
                new_curve = max(0.0, value["curve_mm"] - base["curve_mm"])
                if new_curve > worst.get(key, {"curve_mm": -1})["curve_mm"]:
                    worst[key] = {"curve_mm": round(new_curve, 2), "spots": value["spots"], "at": round(scale, 2), "kind": value["kind"]}
            if step == options["steps"]:
                marks[name] = (moved, found)
        final = model.pose(name, 1.0)
        reach = {}
        if name in ("pinch", "opposition"):
            reach["thumb_to_index_tip_mm"] = round(float(np.linalg.norm(_thumb_tip(model, final) - _finger_tip(model, final, "Index"))) * unit, 2)
        if name in ("fist", "grip"):
            index_mid = final[np.nonzero(model.hand["labels"] == 2)[0]].mean(0)
            reach["thumb_to_index_mm"] = round(float(np.linalg.norm(_thumb_tip(model, final) - index_mid)) * unit, 2)
        entry = {"pose": name, "angles": POSES[name], "crossings": worst, "stretched_edges_max": stretched_max, **reach}
        if name in thumb_table:
            entry["thumb"] = thumb_table[name]
            if thumb_table[name]["gap_mm"] > 2.0 * model.hand["fingers"]["Thumb"]["radius"] * unit:
                warnings.append("%s: the thumb stays %.0f mm short of its goal (%s); look at the thumb length and its base"
                                % (name, thumb_table[name]["gap_mm"], thumb_table[name]["goal"]))
        results.append(entry)
        for key, value in worst.items():
            if value["kind"] in ("fingers", "fold") and value["curve_mm"] > options["cross_tolerance_mm"]:
                warnings.append("%s: %s crosses %.1f mm (%d spots) at %d%%" % (name, key, value["curve_mm"], value["spots"], round(value["at"] * 100)))
        if stretched_max:
            warnings.append("%s: %d edges stretch past %.1fx and %.0f mm" % (name, stretched_max, options["stretch"], options["stretch_mm"]))
    return {"rest_crossings": rest_groups, "poses": results}, warnings, marks


def joint_report(hand, current=None):
    """JSON-ready joints per finger, with the distance to the current bone heads when given."""
    unit = hand["unit_mm"]
    rows = {}
    for name in FINGERS:
        data = hand["fingers"][name]
        items = []
        for k, joint_name in enumerate(JOINT_NAMES[name]):
            method, score, parts = data["methods"][k]
            item = {"joint": joint_name, "position": [round(float(x), 6) for x in data["joints"][k]], "method": method}
            if score is not None:
                item["score"] = score
            if parts:
                item["features"] = parts
            if data["positions"][k] is not None:
                item["from_web_mm"] = round(data["positions"][k] * unit, 2)
            if current is not None and name in current and k < len(current[name]) and current[name][k] is not None:
                item["current_bone_offset_mm"] = round(float(np.linalg.norm(data["joints"][k] - current[name][k])) * unit, 2)
            items.append(item)
        rows[name] = {"visible_length_mm": round(data["visible"] * unit, 2), "radius_mm": round(data["radius"] * unit, 2),
                      "vertices": int((hand["labels"] == FINGERS.index(name) + 1).sum()), "joints": items}
    return rows


# ---------------------------------------------------------------- Blender

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("measure, place and check need Blender Python; the numeric core works in ordinary Python") from error
    return bpy


def _unit_mm(rig=None):
    bpy = _bpy()
    scale = float(bpy.context.scene.unit_settings.scale_length) or 1.0
    factor = scale * 1000.0
    if rig is not None:
        factor *= float(np.mean(np.linalg.norm(np.array(rig.matrix_world)[:3, :3], axis=0)))
    return factor


def _mesh_data(obj, space):
    """Rest points (Basis, no modifiers) in the given 4x4 space and triangles of the mesh."""
    if obj is None or obj.type != "MESH":
        raise ValueError("--mesh must be a mesh object")
    mesh = obj.data
    mesh.calc_loop_triangles()
    flat = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", flat)
    matrix = space @ np.array(obj.matrix_world)
    points = flat.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
    corners = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", corners)
    return points, corners.reshape(-1, 3).astype(np.int64)


def read_bone_map(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    bones = data.get("human_bones") if isinstance(data, dict) else None
    if not isinstance(bones, dict):
        raise ValueError("The bone map needs a 'human_bones' object (role -> bone name), as for rig-audit")
    return bones


def side_roles(side):
    """VRM 1.0 role names for one side, in bone_list() order."""
    prefix = side
    return [prefix + "Hand"] + [prefix + name + segment for name in FINGERS for segment in SEGMENTS[name]]


def rig_bones(rig, mapping, side):
    roles = side_roles(side)
    missing = [role for role in roles if role not in mapping]
    if missing:
        raise ValueError("The bone map lacks: " + ", ".join(missing))
    names = [mapping[role] for role in roles]
    absent = [name for name in names if name not in rig.data.bones]
    if absent:
        raise ValueError("Bones not in the rig: " + ", ".join(absent))
    return names


def current_joints(rig, names):
    bones = rig.data.bones
    current = {}
    for slot, name in enumerate(FINGERS):
        chain = names[1 + 3 * slot: 4 + 3 * slot]
        heads = [np.array(bones[n].head_local) for n in chain]
        current[name] = heads + [np.array(bones[chain[2]].tail_local)]
    return current


def wrist_from_rig(rig, names):
    bones = rig.data.bones
    wrist = np.array(bones[names[0]].head_local)
    middle = np.array(bones[names[1 + 3 * 2]].head_local)
    return wrist, _unit(middle - wrist)


def bone_weights(obj, names, count):
    table = np.zeros((count, len(names)))
    slot = {group.index: names.index(group.name) for group in obj.vertex_groups if group.name in names}
    for vertex in obj.data.vertices:
        for element in vertex.groups:
            if element.group in slot:
                table[vertex.index, slot[element.group]] = element.weight
    return table


def rig_axes(rig, names, hand):
    """Bend axes of the existing bones: local X, signed so that a positive angle curls toward the palm."""
    bones = rig.data.bones
    palm = -hand["back"]
    axes = {}
    for slot, name in enumerate(FINGERS):
        rows = []
        for k in range(3):
            bone = bones[names[1 + 3 * slot + k]]
            frame = np.array(bone.matrix_local)[:3, :3]
            x_axis, y_axis = frame[:, 0], frame[:, 1]
            moved = rotation(x_axis, 10.0) @ y_axis
            rows.append(x_axis if float((moved - y_axis) @ palm) >= 0 else -x_axis)
        axes[name] = np.array(rows)
    return axes


def write_bones(rig, names, joints, axes, z_toward):
    """Edit the finger bones of the open file (in memory): heads, tails and rolls."""
    bpy = _bpy()
    from mathutils import Vector
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    try:
        for slot, name in enumerate(FINGERS):
            for k in range(3):
                bone = edit[names[1 + 3 * slot + k]]
                bone.use_connect = False
            for k in range(3):
                bone = edit[names[1 + 3 * slot + k]]
                bone.head = Vector(joints[name][k])
                bone.tail = Vector(joints[name][k + 1])
                d = _unit(joints[name][k + 1] - joints[name][k])
                hinge = axes[name][k]
                palm_side = np.cross(hinge, d)                    # local Z when local X = hinge
                bone.align_roll(Vector(palm_side if z_toward == "palm" else -palm_side))
            for k in (1, 2):
                edit[names[1 + 3 * slot + k]].use_connect = True
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")


def write_weights(obj, names, weights, region, along, fade):
    """Blend new hand weights into the vertex groups over the region; other groups fade out past the wrist."""
    count = len(obj.data.vertices)
    groups = {group.name: group for group in obj.vertex_groups}
    for name in names:
        if name not in groups:
            groups[name] = obj.vertex_groups.new(name=name)
    factor = _smoothstep(along, 0.0, fade)
    index_of = {group.index: group for group in obj.vertex_groups}
    changed = 0
    for v in np.nonzero(region)[0]:
        f = float(factor[v])
        if f <= 0:
            continue
        vertex = obj.data.vertices[int(v)]
        old = {index_of[e.group].name: e.weight for e in vertex.groups}
        new = dict.fromkeys(set(old) | set(names), 0.0)
        for name, w in old.items():
            new[name] += (1 - f) * w
        for column, name in enumerate(names):
            new[name] += f * float(weights[v, column])
        for name, w in new.items():
            if w > 1e-5:
                groups[name].add([int(v)], float(w), "REPLACE")
            elif name in old:
                groups[name].remove([int(v)])
        changed += 1
    return changed


def write_rigid_followers(followers, rig, hand, names, weights):
    """Give every piece of the follower meshes near this hand one bone at weight 1 (other bone groups are cleared there)."""
    space = np.linalg.inv(np.array(rig.matrix_world))
    bone_names = {bone.name for bone in rig.data.bones}
    report = {}
    for obj in followers:
        points, triangles = _mesh_data(obj, space)
        label, chosen, _near = rigid_follower_bones(points, triangles, hand, weights)
        groups = {group.name: group for group in obj.vertex_groups}
        deform = [group for group in obj.vertex_groups if group.name in bone_names]
        counts = {}
        for piece, column in chosen.items():
            bone = names[column]
            members = [int(v) for v in np.nonzero(label == piece)[0]]
            for group in deform:
                group.remove(members)
            if bone not in groups:
                groups[bone] = obj.vertex_groups.new(name=bone)
            groups[bone].add(members, 1.0, "REPLACE")
            counts[bone] = counts.get(bone, 0) + 1
        report[obj.name] = {"pieces_on_this_hand": len(chosen), "pieces_total": int(label.max()) + 1 if len(label) else 0,
                            "pieces_per_bone": counts}
    return report


def render_views(rig, mesh, hand, names, folder, poses=None, marks=None, size=640, keep=()):
    """Close views of the hand: rest with joint markers, and every pose (posed in memory, never saved)."""
    import bmesh
    from mathutils import Matrix, Quaternion, Vector
    bpy = _bpy()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light, shading.color_type, shading.show_cavity = "STUDIO", "SINGLE", True
    shading.single_color = (0.85, 0.78, 0.74)
    scene.world = bpy.data.worlds.new("lida_hand_world")
    scene.world.color = (0.22, 0.22, 0.24)
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.view_settings.view_transform = "Standard"
    camera = bpy.data.objects.new("lida_hand_camera", bpy.data.cameras.new("lida_hand_camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type, camera.data.clip_start, camera.data.clip_end = "ORTHO", 0.001, 100.0
    for obj in scene.objects:                         # only the hand mesh (and the markers added below) is drawn
        if obj.type in ("MESH", "CURVE", "SURFACE", "META", "FONT", "GPENCIL", "GREASEPENCIL", "VOLUME", "POINTCLOUD", "CURVES") and obj != mesh and obj not in keep:
            obj.hide_render = True
    for modifier in mesh.modifiers:                   # outline shells and the like hide the skin
        if modifier.type == "SOLIDIFY":
            modifier.show_render = False
    to_world = np.array(rig.matrix_world) if rig is not None else np.eye(4)
    region = hand["points"][hand["mask"]]
    centre = (region.max(0) + region.min(0)) / 2
    span = float((region.max(0) - region.min(0)).max()) * 1.35
    centre_w = to_world[:3, :3] @ centre + to_world[:3, 3]
    back_w = to_world[:3, :3] @ hand["back"]
    side_w = to_world[:3, :3] @ hand["lateral"]
    toward_w = to_world[:3, :3] @ hand["toward"]
    views = {"back": back_w, "palm": -back_w, "thumb": _unit(side_w + 0.35 * back_w), "tip": _unit(toward_w + 0.5 * back_w),
             "front": _unit(0.8 * side_w - 0.6 * back_w + 0.3 * toward_w)}     # from the thumb and palm side: the thumb in a fist
    images = {}

    def shot(name, direction):
        direction = Vector(_unit(direction))
        camera.location = Vector(centre_w) + direction * 3.0
        camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = span
        scene.render.filepath = str(folder / name)
        bpy.ops.render.render(write_still=True)
        return name

    if marks is not None:
        colors = [(0.95, 0.35, 0.3, 1), (0.95, 0.75, 0.2, 1), (0.35, 0.8, 0.35, 1), (0.3, 0.6, 0.95, 1), (0.75, 0.4, 0.95, 1)]
        radius = span / 120.0
        sets = [("measured", radius, colors)]
        if marks.get("current"):
            sets.append(("current", radius * 0.6, [(0.08, 0.08, 0.08, 1)] * 5))
        for key, size_, palette in sets:
            for slot, name in enumerate(FINGERS):
                builder = bmesh.new()
                for point in marks[key][name]:
                    bmesh.ops.create_uvsphere(builder, u_segments=10, v_segments=6, radius=size_,
                                              matrix=Matrix.Translation(Vector(to_world[:3, :3] @ point + to_world[:3, 3])))
                data = bpy.data.meshes.new("lida_hand_marks_%s_%s" % (key, name))
                builder.to_mesh(data)
                builder.free()
                obj = bpy.data.objects.new("lida_hand_marks_%s_%s" % (key, name), data)
                obj.show_in_front = True
                material = bpy.data.materials.new("lida_hand_marks_%s_%s" % (key, name))
                material.diffuse_color = palette[slot]
                data.materials.append(material)
                scene.collection.objects.link(obj)
        shading.color_type = "MATERIAL"
        for view, direction in views.items():
            images["rest_" + view] = shot("rest_%s.jpg" % view, direction)
    if poses:
        bones = rig.pose.bones
        rest = rig.data.bones
        for pose_name, (axes, pose) in poses.items():
            for slot, name in enumerate(FINGERS):
                for k in range(3):
                    bone = bones[names[1 + 3 * slot + k]]
                    frame = np.array(rest[names[1 + 3 * slot + k]].matrix_local)[:3, :3]
                    turn = segment_turn(hand, axes, pose, name, k)
                    local = frame.T @ turn @ frame
                    bone.rotation_mode = "QUATERNION"
                    bone.rotation_quaternion = Matrix(local.tolist()).to_quaternion()
            bpy.context.view_layer.update()
            for view in ("back", "palm", "thumb", "front"):
                images["%s_%s" % (pose_name, view)] = shot("%s_%s.jpg" % (pose_name, view), views[view])
        for bone in bones:
            bone.rotation_quaternion = Quaternion()
        bpy.context.view_layer.update()
    return images


def blender_skin_difference(rig, mesh, names, hand, axes, spec):
    """Pose the armature in memory, evaluate the mesh in Blender and compare with the numpy skinning (mm)."""
    from mathutils import Matrix, Quaternion
    bpy = _bpy()
    bones = rig.pose.bones
    rest = rig.data.bones
    for slot, name in enumerate(FINGERS):
        for k in range(3):
            frame = np.array(rest[names[1 + 3 * slot + k]].matrix_local)[:3, :3]
            turn = segment_turn(hand, axes, spec, name, k)
            bone = bones[names[1 + 3 * slot + k]]
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = Matrix((frame.T @ turn @ frame).tolist()).to_quaternion()
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = mesh.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    try:
        if len(data.vertices) != len(hand["points"]):
            return None
        flat = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", flat)
        space = np.linalg.inv(np.array(rig.matrix_world)) @ np.array(evaluated.matrix_world)
        points = flat.reshape(-1, 3) @ space[:3, :3].T + space[:3, 3]
    finally:
        evaluated.to_mesh_clear()
        for bone in bones:
            bone.rotation_quaternion = Quaternion()
        bpy.context.view_layer.update()
    return points


# ---------------------------------------------------------------- commands

def _hand_inputs(mesh, rig, mapping, side, wrist=None, toward=None, back=None, options=None):
    if rig is not None:
        if rig.type != "ARMATURE":
            raise ValueError("--rig must be an armature object")
        space = np.linalg.inv(np.array(rig.matrix_world))
        names = rig_bones(rig, mapping, side)
        if wrist is None:
            wrist, toward = wrist_from_rig(rig, names)
        else:
            wrist = space[:3, :3] @ np.asarray(wrist, float) + space[:3, 3]
            toward = space[:3, :3] @ np.asarray(toward, float)
    else:
        space, names = np.eye(4), None
        if wrist is None or toward is None:
            raise ValueError("Without --rig, give --wrist and --toward")
    points, triangles = _mesh_data(mesh, space)
    hand = measure_hand(points, triangles, wrist, toward, side, back=back, options=options, unit_mm=_unit_mm(rig))
    return hand, names


def command_measure(mesh, rig, mapping, sides, wrist, toward, back, options, render_dir):
    report = {"schema": REPORT_SCHEMA, "command": "measure", "mesh": mesh.name, "rig": rig.name if rig else None,
              "unit": "mm", "space": "armature" if rig else "world", "options": resolve_options(options), "hands": {}}
    warnings = []
    for side in sides:
        hand, names = _hand_inputs(mesh, rig, mapping, side, wrist, toward, back, options)
        current = current_joints(rig, names) if rig is not None else None
        entry = {"back_of_hand": [round(float(x), 4) for x in hand["back"]], "back_method": hand["back_method"],
                 "region_vertices": int(hand["mask"].sum()), "palm_vertices": int((hand["labels"] == 0).sum()),
                 "fingers": joint_report(hand, current)}
        if render_dir is not None:
            measured = {n: hand["fingers"][n]["joints"] for n in FINGERS}
            entry["images"] = render_views(rig, mesh, hand, names, render_dir / side, marks={"measured": measured, "current": current})
        report["hands"][side] = entry
        warnings += ["%s: %s" % (side, w) for w in hand["warnings"]]
    return report, warnings


def command_place(mesh, rig, mapping, sides, options, keep_weights, thumb_roll, z_toward, rigid_followers=()):
    if rig is None:
        raise ValueError("place needs --rig and --bones")
    report = {"schema": REPORT_SCHEMA, "command": "place", "mesh": mesh.name, "rig": rig.name, "unit": "mm",
              "options": resolve_options(options), "hands": {}}
    warnings = []
    for side in sides:
        hand, names = _hand_inputs(mesh, rig, mapping, side, options=options)
        opt = hand["options"]
        joints = {n: hand["fingers"][n]["joints"] for n in FINGERS}
        roll_rows = None
        weights_names, weights = hand_weights(hand)
        if thumb_roll == "auto":
            model = HandModel(hand, joints, hinge_axes(hand), weights)
            roll, roll_rows = thumb_search(model, opt)
        else:
            roll = float(thumb_roll)
        axes = hinge_axes(hand, thumb_roll=roll)
        before = current_joints(rig, names)
        write_bones(rig, names, joints, axes, z_toward)
        entry = {"fingers": joint_report(hand, before), "thumb_roll_deg": roll, "z_toward": z_toward,
                 "flex_sign": "positive local X curls the finger" if z_toward == "palm" else "negative local X curls the finger"}
        if roll_rows is not None:
            entry["thumb_roll_search"] = roll_rows
        if not keep_weights:
            mapped = [names[weights_names.index(n)] for n in weights_names]
            if rigid_followers:                      # the skin a hard piece sits on follows the same bone, so the piece stays seated
                space = np.linalg.inv(np.array(rig.matrix_world))
                for follower in rigid_followers:
                    f_points, f_triangles = _mesh_data(follower, space)
                    label, chosen, _near = rigid_follower_bones(f_points, f_triangles, hand, weights)
                    region = np.nonzero(hand["mask"])[0]
                    ties = region[nearest_k(f_points, hand["points"][region])[0]]
                    for piece, column in chosen.items():
                        bed = np.unique(ties[label == piece])
                        weights[bed] = 0.0
                        weights[bed, column] = 1.0
            entry["weighted_vertices"] = write_weights(mesh, mapped, weights, hand["mask"], hand["along"],
                                                       opt["fade_mm"] / hand["unit_mm"])
            if rigid_followers:
                entry["rigid_followers"] = write_rigid_followers(rigid_followers, rig, hand, mapped, weights)
                for follower_name, row in entry["rigid_followers"].items():
                    if not row["pieces_on_this_hand"]:
                        warnings.append("%s: no piece of %s lies on this hand" % (side, follower_name))
            done = {obj.name for obj in rigid_followers}
            followers = sorted({obj.name for obj in _bpy().context.scene.objects if obj.type == "MESH" and obj != mesh
                                and obj.name not in done and any(group.name in names[1:] for group in obj.vertex_groups)})
            if followers:
                warnings.append(side + ": other meshes weighted to these finger bones were not recomputed: " + ", ".join(followers)
                                + " (nails and other hard pieces: --rigid-followers)")
            entry["other_meshes_on_finger_bones"] = followers
        report["hands"][side] = entry
        warnings += ["%s: %s" % (side, w) for w in hand["warnings"]]
    return report, warnings


def command_check(mesh, rig, mapping, sides, options, poses, render_dir, followers=()):
    if rig is None:
        raise ValueError("check needs --rig and --bones")
    report = {"schema": REPORT_SCHEMA, "command": "check", "mesh": mesh.name, "rig": rig.name, "unit": "mm",
              "options": resolve_options(options), "poses": list(poses), "hands": {}}
    warnings = []
    for side in sides:
        hand, names = _hand_inputs(mesh, rig, mapping, side, options=options)
        opt = hand["options"]
        joints = current_joints(rig, names)
        axes = rig_axes(rig, names, hand)
        weights = bone_weights(mesh, names, len(hand["points"]))
        weights[~hand["mask"]] = 0.0
        model = HandModel(hand, joints, axes, weights)
        result, found_warnings = check_poses(model, poses, opt)[:2]
        moved_blender = blender_skin_difference(rig, mesh, names, hand, axes, model.spec("fist"))
        if moved_blender is not None:
            numpy_fist = model.pose("fist", 1.0)
            difference = float(np.abs(moved_blender[hand["mask"]] - numpy_fist[hand["mask"]]).max()) * hand["unit_mm"]
            result["blender_vs_numpy_fist_mm"] = round(difference, 3)
            if difference > 0.5:
                found_warnings.append("Blender's own deformation differs from this check by %.2f mm (other modifiers, shape keys or volume preservation); read the counts with care" % difference)
        else:
            result["blender_vs_numpy_fist_mm"] = None
        result["weights_in_hand"] = {"vertices_without_hand_weights": int((weights[hand["mask"]].sum(1) < 1e-6).sum())}
        if followers:
            space = np.linalg.inv(np.array(rig.matrix_world))
            unit = hand["unit_mm"]
            result["followers"] = {}
            for obj in followers:
                f_points, f_triangles = _mesh_data(obj, space)
                label, chosen, near = rigid_follower_bones(f_points, f_triangles, hand, weights)
                members = np.nonzero(np.isin(label, list(chosen)))[0]
                row = {"pieces_on_this_hand": len(chosen), "drift_mm": {}}
                if len(members):
                    f_weights = bone_weights(obj, names, len(f_points))
                    bones_per_piece = [int((f_weights[label == piece] > 1e-4).any(0).sum()) for piece in chosen]
                    row["pieces_on_more_than_one_bone"] = int(sum(1 for n in bones_per_piece if n > 1))
                    row["vertices_without_hand_weights"] = int((f_weights[members].sum(1) < 1e-6).sum())
                    for pose in poses:
                        drift = follower_drift(model, pose, f_points[members], f_weights[members], near[members])
                        row["drift_mm"][pose] = round(float(drift.max()) * unit, 2)
                    worst = max(row["drift_mm"].values()) if row["drift_mm"] else 0.0
                    if worst > opt["follower_drift_mm"]:
                        found_warnings.append("%s moves up to %.1f mm against the skin under it (rigid pieces: place --rigid-followers)" % (obj.name, worst))
                else:
                    found_warnings.append("no piece of %s lies on this hand" % obj.name)
                result["followers"][obj.name] = row
        if render_dir is not None:
            spec = {p: (axes, model.spec(p)) for p in poses}
            result["images"] = render_views(rig, mesh, hand, names, render_dir / side, poses=spec, keep=tuple(followers))
        report["hands"][side] = result
        warnings += ["%s: %s" % (side, w) for w in found_warnings + hand["warnings"]]
    return report, warnings


# ---------------------------------------------------------------- CLI

def _new_output(path, folder=False):
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
    descriptor, temporary = tempfile.mkstemp(prefix=".lida-hand-rig-", suffix=".blend", dir=path.parent)
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
    parser = argparse.ArgumentParser(prog="lida_hand_rig.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("measure", "place", "check"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
        sub.add_argument("--mesh", required=True, help="the mesh that holds the hand skin (often the body)")
        sub.add_argument("--rig", required=command != "measure")
        sub.add_argument("--bones", type=Path, required=command != "measure",
                         help="role -> bone name map (VRM 1.0 roles, the rig-audit format)")
        sub.add_argument("--side", required=True, choices=("left", "right", "both"))
        sub.add_argument("--report", required=True, type=Path)
        for key in DEFAULTS:
            sub.add_argument("--" + key.replace("_", "-"), type=int if key in ("steps", "smooth") else float)
        if command == "measure":
            sub.add_argument("--wrist", nargs=3, type=float, metavar=("X", "Y", "Z"), help="wrist point when there is no rig")
            sub.add_argument("--toward", nargs=3, type=float, metavar=("X", "Y", "Z"), help="direction from the wrist to the fingers")
            sub.add_argument("--back", nargs=3, type=float, metavar=("X", "Y", "Z"), help="back-of-hand direction, to override")
        if command in ("measure", "check"):
            sub.add_argument("--render-dir", type=Path, help="new folder for close views")
        if command == "place":
            sub.add_argument("--output-blend", required=True, type=Path)
            sub.add_argument("--keep-weights", action="store_true")
            sub.add_argument("--thumb-roll", default="auto", help="auto, or degrees")
            sub.add_argument("--z-toward", choices=("palm", "back"), default="palm")
            sub.add_argument("--rigid-followers", nargs="+", default=[], metavar="MESH",
                             help="nails and other hard pieces: every connected piece follows the one bone under it")
        if command == "check":
            sub.add_argument("--poses", nargs="+", choices=tuple(POSES), default=list(POSES))
            sub.add_argument("--followers", nargs="+", default=[], metavar="MESH",
                             help="nails and other meshes on the finger bones: drawn, and their movement against the skin is measured")
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
        if "--" not in sys.argv and any(Path(a).name.lower().startswith("blender") for a in sys.argv[:1]):
            print("Write the tool's arguments after '--', for example: blender -b --python lida_hand_rig.py -- measure ...", file=sys.stderr)
            return 2
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parser().parse_args(argv)
    report_path = None
    try:
        report_path = _new_output(args.report)
        source = args.input.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".blend":
            raise ValueError("Input must be an existing .blend file")
        if source == report_path:
            raise ValueError("Report must differ from input")
        output = render_dir = None
        if args.command == "place":
            output = _new_output(args.output_blend)
            if output in (source, report_path) or output.suffix.lower() != ".blend":
                raise ValueError("Candidate must be a distinct new .blend path")
            if args.thumb_roll != "auto":
                float(args.thumb_roll)
        if getattr(args, "render_dir", None) is not None:
            render_dir = _new_output(args.render_dir)
        options = {key: getattr(args, key) for key in DEFAULTS if getattr(args, key, None) is not None}
        resolve_options(options)
        mapping = read_bone_map(args.bones) if args.bones is not None else None
        before_sha = _file_hash(source)
        bpy = _bpy()
        if not bpy.app.background:
            raise ValueError("Run the CLI in a separate Blender background process")
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
        scene_objects = bpy.context.scene.objects
        mesh = scene_objects.get(args.mesh)
        if mesh is None:
            raise ValueError("Mesh not found: " + args.mesh)
        rig = None
        if args.rig:
            rig = scene_objects.get(args.rig)
            if rig is None:
                raise ValueError("Rig not found: " + args.rig)
            if mapping is None:
                raise ValueError("--rig needs --bones")
        sides = ("left", "right") if args.side == "both" else (args.side,)
        follower_objects = []
        for follower_name in getattr(args, "rigid_followers", None) or getattr(args, "followers", None) or []:
            follower = scene_objects.get(follower_name)
            if follower is None or follower.type != "MESH" or follower == mesh:
                raise ValueError("Follower must be another mesh in the scene: " + follower_name)
            follower_objects.append(follower)
        if args.command == "measure" and args.wrist is not None and len(sides) > 1:
            raise ValueError("--wrist describes one hand; measure one --side at a time")
        if args.command == "measure" and rig is None and args.wrist is None:
            raise ValueError("Give --rig and --bones, or --wrist and --toward")
        if render_dir is not None:
            render_dir.mkdir()
            for side in sides:
                (render_dir / side).mkdir()
        if args.command == "measure":
            report, warnings = command_measure(mesh, rig, mapping, sides, args.wrist, args.toward, args.back, options, render_dir)
        elif args.command == "place":
            report, warnings = command_place(mesh, rig, mapping, sides, options, args.keep_weights, args.thumb_roll, args.z_toward,
                                             follower_objects)
            _save_candidate(output)
            report["output"] = {"name": output.name, "sha256": _file_hash(output)}
        else:
            report, warnings = command_check(mesh, rig, mapping, sides, options, args.poses, render_dir, follower_objects)
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        report["warnings"] = warnings
        report["unverified"] = list(UNVERIFIED)
        report["status"] = "completed_with_findings" if warnings else "completed"
        code = 2 if warnings else 0
        _write_report(report_path, report)
        print(json.dumps({"command": args.command, "status": report["status"], "warnings": len(warnings),
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
