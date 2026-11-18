# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Measure a hand mesh, place the finger joints, rolls and weights from it, and check the grips.

Run in Blender with ``--background --factory-startup --python THIS.py -- COMMAND``.

measure: --input MODEL.blend --mesh Body --side left (--rig Armature --bones MAP.json | --wrist X Y Z --toward X Y Z)
         --report NEW.json [--render-dir NEW_FOLDER] [--head-meshes Head ...] [--body-meshes Body ...]
         [--head-height-mm N] [--height-mm N] [--heads N] [--proportion-table TABLE.json]
place:   --input MODEL.blend --mesh Body --rig Armature --bones MAP.json --side left|right|both
         --report NEW.json --output-blend NEW.blend [--keep-weights] [--thumb-roll auto|DEGREES] [--z-toward palm|back]
         [--rigid-followers Nails ...]
check:   --input MODEL.blend --mesh Body --rig Armature --bones MAP.json --side left|right|both
         --report NEW.json [--render-dir NEW_FOLDER] [--poses relax grip fist point pinch spread opposition]
         [--followers Nails ...] [--accept APPROVED_CHECK.json]
compare: --before OLD.json --after NEW.json --report NEW.json      (two measure or two check reports; no Blender)
bones:   --input MODEL.blend --rig Armature --report NEW.json --output-map NEW_MAP.json
run:     --input MODEL.blend --mesh Body --rig Armature --side left|right|both --out-dir NEW_FOLDER
         [--bones MAP.json] [--rigid-followers Nails ...] [--accept APPROVED_CHECK.json] [--views none|findings|all]

measure splits the hand into five fingers by surface connectivity (a merge tree of the distance
along the surface from the wrist), so a ray or a nearest point never picks up a neighbouring finger.
Each finger's joints are read from the mesh where it shows them (a palmar crease, a dorsal knuckle,
a gathering of edge loops) inside a window around an anatomical prior; where the mesh is silent the
prior is used and the report says so. The back of the hand follows from the side, the finger
direction and the thumb, so no axis is guessed from names. measure also reports the proportions: inside
the hand (palm against hand length, palm length against width, thumb reach) and against the body (hand
against forearm, head height and height, and the height in heads), next to rounded human values. A
stylised design differs on purpose, so the warning bands are options. The hand size against the head is
judged by a table of hand length / head height by head count; the table is a starting guide whose rows
state their basis, and it can be replaced (--proportion-table), shifted (--heads, --proportion-tolerance)
or bypassed (--hand-head-min/--hand-head-max).

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

compare reads two reports and lists what got worse, better or changed, from the numbers alone. check
--accept reads a check against the report of an approved model, so that only values worse than the
approved ones (and new kinds of warning) are reported. bones writes the role -> bone name map from what
the rig carries: roles stored by a VRM add-on first, then bone names and the hierarchy. run does bones
(when no map is given), measure, check, place, check again and compare in one process and one new
folder. Nothing is rendered unless asked: --views findings draws only the poses that still have a
warning, before and after side by side; --views all draws every pose.

The numeric core needs numpy only. The input blend is never saved; place and run write a new blend.
Exit codes: 0 nothing to report; 2 findings, warnings or a usage error; 1 invalid input or execution error.
"""

import argparse
import hashlib
import heapq
import importlib.util
import json
import math
import os
from pathlib import Path
import re
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
    # proportion bands (measure): outside them a warning is given. Set them from the design when it is stylised.
    "palm_share_min": 0.48,     # palm length / hand length (wrist to the middle-finger web / wrist to the middle fingertip)
    "palm_share_max": 0.62,
    "palm_aspect_max": 1.45,    # palm length / palm width
    "thumb_reach_min": 1.0,     # thumb tip / palm length along the hand: under 1 the thumb ends before the finger webs
    "hand_head_min": 0.5,       # hand length / head height (crown to chin)
    "hand_head_max": 0.95,
    "hand_forearm_min": 0.5,    # hand length / forearm length (elbow to wrist)
    "hand_forearm_max": 0.9,
    "proportion_tolerance": 0.15,   # the table's hand size is accepted within +/- this share
}
# Hand length / head height by head count: a starting guide, not a rule. "basis" says where a row comes from;
# only the human rows and the measured rows rest on measurements. Replace it with --proportion-table, or
# override single values with --heads, --hand-head-min and --hand-head-max.
PROPORTION_TABLE = (
    {"heads": 3.0, "hand_per_head": 0.30, "basis": "rule of thumb (not measured)"},
    {"heads": 4.0, "hand_per_head": 0.36, "basis": "rule of thumb (not measured)"},
    {"heads": 5.0, "hand_per_head": 0.42, "basis": "rule of thumb (not measured)"},
    {"heads": 6.0, "hand_per_head": 0.46, "basis": "measured: one stylised design sheet and its model"},
    {"heads": 7.0, "hand_per_head": 0.64, "basis": "measured hand / height on anime-style examples; head count assumed"},
    {"heads": 7.5, "hand_per_head": 0.81, "basis": "adult human"},
    {"heads": 8.0, "hand_per_head": 0.86, "basis": "adult human"},
)
HUMAN_REFERENCE = {   # an adult human hand and body, rounded; a stylised design may differ on purpose
    "palm_share": 0.57, "palm_length_per_width": 1.25, "palm_per_middle_finger": 1.3, "thumb_per_index": 0.67,
    "thumb_reach": 1.15, "hand_per_head": 0.78, "hand_per_forearm": 0.73, "hand_per_height": 0.108, "heads": 7.5,
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
COMPARE_SCHEMA = "lida.hand-rig.compare.v1"
COMPARE_TOLERANCE = {"mm": 0.5, "count": 0.0, "ratio": 0.01}   # a value must move more than this to count
BONE_MAP_SCHEMA = "lida.model-tools.humanoid-map.v1"            # the map format rig-audit reads
BONE_FINGER_WORDS = {"thumb": "Thumb", "index": "Index", "middle": "Middle", "ring": "Ring", "little": "Little",
                     "pinky": "Little", "pinkie": "Little"}
BONE_SKIP_WORDS = ("tip", "end", "nub", "leaf", "ik", "pole", "target", "ctrl", "control", "helper", "org", "mch")
LABEL_GLYPHS = {   # 5 x 7 capitals, enough for BEFORE / AFTER
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
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


def hand_proportions(hand):
    """Lengths (mm) and ratios inside one hand, measured along the hand from the wrist point that was given."""
    unit = hand["unit_mm"]
    wrist, toward, lateral = hand["wrist"], hand["toward"], hand["lateral"]
    fingers = hand["fingers"]

    def along(point):
        return float((np.asarray(point) - wrist) @ toward) * unit

    palm_length = along(fingers["Middle"]["base"])
    hand_length = along(fingers["Middle"]["joints"][3])
    palm_points = hand["points"][hand["labels"] == 0]
    s = (palm_points - wrist) @ toward * unit
    across = (palm_points - wrist) @ lateral * unit
    band = (s > 0.5 * palm_length) & (s < 0.9 * palm_length)
    palm_width = float(across[band].max() - across[band].min()) if band.sum() > 2 else float("nan")
    points = hand["points"]
    s_all = (points - wrist) @ toward
    off = points - wrist - np.outer(s_all, toward)
    near = np.linalg.norm(off, axis=1) < 0.6 * hand["reach"]
    side = (points - wrist) @ lateral
    narrow_at, narrow_width = None, None
    step = hand["reach"] / 24.0
    for start in np.arange(-0.5 * hand["reach"], 0.3 * hand["reach"], step):
        inside = near & (s_all >= start) & (s_all < start + step)
        if inside.sum() < 6:
            continue
        width = float(side[inside].max() - side[inside].min())
        if narrow_width is None or width < narrow_width:
            narrow_at, narrow_width = float(start + step / 2), width
    middle = fingers["Middle"]["visible"] * unit
    result = {
        "hand_length_mm": round(hand_length, 1), "palm_length_mm": round(palm_length, 1), "palm_width_mm": round(palm_width, 1),
        "finger_visible_mm": {name: round(fingers[name]["visible"] * unit, 1) for name in FINGERS},
        "palm_share": round(palm_length / hand_length, 3),
        "palm_length_per_width": round(palm_length / palm_width, 3) if palm_width == palm_width else None,
        "palm_per_middle_finger": round(palm_length / middle, 3),
        "thumb_per_index": round(fingers["Thumb"]["visible"] / max(fingers["Index"]["visible"], 1e-12), 3),
        "thumb_reach": round(along(fingers["Thumb"]["joints"][3]) / palm_length, 3),
        "narrowest_wrist_section_mm": None if narrow_at is None else round(narrow_at * unit, 1),
    }
    return result


def body_ratios(hand_length_mm, forearm_mm=None, upper_arm_mm=None, head_mm=None, height_mm=None):
    """Hand length against the arm, the head and the height; None where a length was not given."""
    def ratio(a, b):
        return None if a is None or b is None or b <= 0 else round(a / b, 3)

    return {"forearm_mm": forearm_mm, "upper_arm_mm": upper_arm_mm, "head_height_mm": head_mm, "height_mm": height_mm,
            "hand_per_forearm": ratio(hand_length_mm, forearm_mm), "hand_per_upper_arm": ratio(hand_length_mm, upper_arm_mm),
            "hand_per_head": ratio(hand_length_mm, head_mm), "hand_per_height": ratio(hand_length_mm, height_mm),
            "heads": ratio(height_mm, head_mm)}


def read_proportion_table(rows):
    """Validate a table: a list of {"heads", "hand_per_head", optional "basis"}; returns it sorted by heads."""
    if isinstance(rows, dict):
        rows = rows.get("rows")
    if not isinstance(rows, (list, tuple)) or len(rows) < 1:
        raise ValueError("The proportion table needs a list of rows (or an object with 'rows')")
    table = []
    for row in rows:
        try:
            heads, value = float(row["heads"]), float(row["hand_per_head"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Each proportion table row needs numeric 'heads' and 'hand_per_head'")
        if not (math.isfinite(heads) and math.isfinite(value) and heads > 0 and value > 0):
            raise ValueError("Proportion table values must be positive")
        table.append({"heads": heads, "hand_per_head": value, "basis": str(row.get("basis", "not stated"))})
    table.sort(key=lambda r: r["heads"])
    if len({r["heads"] for r in table}) != len(table):
        raise ValueError("The proportion table repeats a head count")
    return table


def table_expectation(table, heads, tolerance, head_mm=None):
    """Hand length / head height the table gives for a head count (straight lines between rows, flat past the ends)."""
    table = read_proportion_table(list(table))
    at = [r["heads"] for r in table]
    values = [r["hand_per_head"] for r in table]
    expected = float(np.interp(heads, at, values))
    below = max([r for r in table if r["heads"] <= heads], key=lambda r: r["heads"], default=table[0])
    above = min([r for r in table if r["heads"] >= heads], key=lambda r: r["heads"], default=table[-1])
    result = {"heads_used": round(float(heads), 2), "expected_hand_per_head": round(expected, 3),
              "band": [round(expected * (1 - tolerance), 3), round(expected * (1 + tolerance), 3)],
              "basis": sorted({below["basis"], above["basis"]}),
              "outside_table": bool(heads < at[0] or heads > at[-1])}
    if head_mm:
        result["expected_hand_mm"] = round(expected * head_mm, 1)
        result["band_mm"] = [round(result["band"][0] * head_mm, 1), round(result["band"][1] * head_mm, 1)]
    return result


def proportion_warnings(inside, body, options, expectation=None):
    """Warnings where a ratio leaves its band. The bands are options: set them from the design for a stylised character."""
    found = []
    share = inside["palm_share"]
    if share > options["palm_share_max"]:
        found.append("the palm is %d%% of the hand length (human about 57%%, band up to %d%%): a long palm or short fingers; "
                     "the thumb then ends short of the fingers" % (round(share * 100), round(options["palm_share_max"] * 100)))
    elif share < options["palm_share_min"]:
        found.append("the palm is %d%% of the hand length (human about 57%%, band from %d%%): a short palm or long fingers"
                     % (round(share * 100), round(options["palm_share_min"] * 100)))
    aspect = inside["palm_length_per_width"]
    if aspect is not None and aspect > options["palm_aspect_max"]:
        found.append("the palm is %.2f times as long as it is wide (human about 1.25): a long, narrow palm" % aspect)
    if inside["thumb_reach"] < options["thumb_reach_min"]:
        found.append("the thumb tip ends at %d%% of the palm length, before the finger webs (human about 115%%)" % round(inside["thumb_reach"] * 100))
    measured = body.get("hand_per_head") if body else None
    if expectation is not None and measured is not None:
        low, high = expectation["band"]
        if not low <= measured <= high:
            text = "the hand is %.2f times the head height; for %.1f heads the table gives about %.2f (%.2f to %.2f)" % (
                measured, expectation["heads_used"], expectation["expected_hand_per_head"], low, high)
            if "expected_hand_mm" in expectation:
                text += ", a hand of about %.0f mm instead of %.0f mm" % (expectation["expected_hand_mm"], inside["hand_length_mm"])
            found.append(text + " [" + "; ".join(expectation["basis"]) + "]")
    for key, low, high, label in (("hand_per_head", "hand_head_min", "hand_head_max", "the head height"),
                                  ("hand_per_forearm", "hand_forearm_min", "hand_forearm_max", "the forearm")):
        value = body.get(key) if body else None
        if value is None or (key == "hand_per_head" and expectation is not None):
            continue
        if value < options[low]:
            found.append("the hand is %.2f times %s (band from %.2f): a small hand for this body" % (value, label, options[low]))
        elif value > options[high]:
            found.append("the hand is %.2f times %s (band up to %.2f): a large hand for this body" % (value, label, options[high]))
    return found


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


# ---------------------------------------------------------------- comparing reports (plain Python)

def _loose(text):
    """A warning with its numbers blanked, so the same kind of finding matches across two runs."""
    return re.sub(r"[-+]?\d+(?:\.\d+)?", "#", str(text))


def _raw_warnings(report):
    """The warnings of a report as they were before --accept filtered them."""
    block = report.get("accept")
    if isinstance(block, dict) and isinstance(block.get("warnings_without_accept"), list):
        return list(block["warnings_without_accept"])
    return list(report.get("warnings") or [])


def check_metrics(report):
    """{(side, pose, metric): (value, unit)} of a check report. Every value is 'lower is better'."""
    rows = {}
    for side, hand in (report.get("hands") or {}).items():
        for entry in hand.get("poses") or []:
            pose = entry.get("pose")
            for key, value in (entry.get("crossings") or {}).items():
                rows[(side, pose, "crossing " + key)] = (float(value.get("curve_mm", 0.0)), "mm")
            rows[(side, pose, "stretched edges")] = (float(entry.get("stretched_edges_max", 0)), "count")
            thumb = entry.get("thumb") or {}
            if "gap_mm" in thumb:
                rows[(side, pose, "thumb gap")] = (float(thumb["gap_mm"]), "mm")
            if "crossing_mm" in thumb:
                rows[(side, pose, "thumb crossing")] = (float(thumb["crossing_mm"]), "mm")
        for name, row in (hand.get("followers") or {}).items():
            for pose, value in (row.get("drift_mm") or {}).items():
                rows[(side, pose, "drift of " + name)] = (float(value), "mm")
            for field in ("pieces_on_more_than_one_bone", "vertices_without_hand_weights"):
                if field in row:
                    rows[(side, "-", "%s: %s" % (name, field.replace("_", " ")))] = (float(row[field]), "count")
        count = (hand.get("weights_in_hand") or {}).get("vertices_without_hand_weights")
        if count is not None:
            rows[(side, "-", "vertices without hand weights")] = (float(count), "count")
    return rows


def measure_values(report):
    """{(side, group, name): value} of a measure report: lengths and ratios, with no better or worse."""
    rows = {}

    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    for side, hand in (report.get("hands") or {}).items():
        proportions = hand.get("proportions") or {}
        for group in ("hand", "body"):
            for key, value in (proportions.get(group) or {}).items():
                if number(value):
                    rows[(side, group, key)] = float(value)
                elif isinstance(value, dict):
                    for inner, inner_value in value.items():
                        if number(inner_value):
                            rows[(side, group, "%s %s" % (key, inner))] = float(inner_value)
        for finger, data in (hand.get("fingers") or {}).items():
            for key in ("visible_length_mm", "radius_mm"):
                if number(data.get(key)):
                    rows[(side, finger, key)] = float(data[key])
            for joint in data.get("joints") or []:
                for key in ("from_web_mm", "current_bone_offset_mm"):
                    if number(joint.get(key)):
                        rows[(side, finger, "%s %s" % (joint.get("joint"), key))] = float(joint[key])
    return rows


def compare_reports(before, after, tolerance=None):
    """Two measure reports or two check reports, value by value. No rendering and no Blender.

    check: every metric is 'lower is better'; a value that rose by more than the tolerance is 'worse'.
    measure: lengths and ratios are listed as 'changed'; a warning that is new in `after` is the finding.
    """
    tol = dict(COMPARE_TOLERANCE)
    for key, value in (tolerance or {}).items():
        if key not in tol:
            raise ValueError("Unknown tolerance: " + str(key))
        if value is not None:
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("tolerance %s must be a finite non-negative number" % key)
            tol[key] = float(value)
    command = after.get("command") if isinstance(after, dict) else None
    if (not isinstance(before, dict) or before.get("schema") != REPORT_SCHEMA or after.get("schema") != REPORT_SCHEMA
            or before.get("command") != command or command not in ("measure", "check")):
        raise ValueError("compare needs two measure reports or two check reports of this tool")
    worse, better, changed, skipped = [], [], [], []
    if command == "check":
        old, new = check_metrics(before), check_metrics(after)
        old_poses, new_poses = {key[:2] for key in old}, {key[:2] for key in new}
        for key in sorted(set(old) | set(new)):
            side, pose, name = key
            if key[:2] not in old_poses or key[:2] not in new_poses:
                skipped.append({"side": side, "pose": pose, "metric": name,
                                "reason": "only in the %s report" % ("after" if key[:2] in new_poses else "before")})
                continue
            unit = (new.get(key) or old.get(key))[1]
            a, b = old.get(key, (0.0, unit))[0], new.get(key, (0.0, unit))[0]
            row = {"side": side, "pose": pose, "metric": name, "before": a, "after": b, "delta": round(b - a, 3), "unit": unit}
            if b - a > tol[unit] + 1e-9:
                worse.append(row)
            elif a - b > tol[unit] + 1e-9:
                better.append(row)
    else:
        old, new = measure_values(before), measure_values(after)
        for key in sorted(set(old) | set(new)):
            side, group, name = key
            if key not in old or key not in new:
                skipped.append({"side": side, "group": group, "value": name,
                                "reason": "only in the %s report" % ("after" if key in new else "before")})
                continue
            a, b = old[key], new[key]
            limit = tol["mm"] if name.endswith("_mm") else tol["ratio"]
            if abs(b - a) > limit + 1e-9:
                changed.append({"side": side, "group": group, "value": name, "before": a, "after": b, "delta": round(b - a, 4)})
    old_warnings, new_warnings = _raw_warnings(before), _raw_warnings(after)
    old_kinds, new_kinds = {_loose(w) for w in old_warnings}, {_loose(w) for w in new_warnings}
    added = [w for w in new_warnings if _loose(w) not in old_kinds]
    resolved = [w for w in old_warnings if _loose(w) not in new_kinds]
    findings = len(worse) if command == "check" else len(added)
    return {"schema": COMPARE_SCHEMA, "command": "compare", "compared": command, "tolerance": tol,
            "before": {"input": before.get("input"), "mesh": before.get("mesh")},
            "after": {"input": after.get("input"), "mesh": after.get("mesh")},
            "worse": worse, "better": better, "changed": changed, "not_compared": skipped,
            "new_warnings": added, "resolved_warnings": resolved,
            "summary": {"worse": len(worse), "better": len(better), "changed": len(changed), "not_compared": len(skipped),
                        "new_warnings": len(added), "resolved_warnings": len(resolved), "findings": findings}}


def apply_accepted(report, warnings, accepted, tolerance=None):
    """Read a check against an approved check report: only what is worse, or a new kind of warning, stays.

    Returns (warnings to report, block for report["accept"]). The unfiltered warnings are kept in the block.
    """
    if not isinstance(accepted, dict) or accepted.get("command") != "check" or accepted.get("mesh") != report.get("mesh"):
        raise ValueError("--accept must be a check report of the same mesh")
    difference = compare_reports(accepted, dict(report, warnings=list(warnings)), tolerance)
    kept = ["%s: %s: %s rose from %g to %g %s against the accepted report"
            % (row["side"], row["pose"], row["metric"], row["before"], row["after"], row["unit"]) for row in difference["worse"]]
    uncovered = {(row["side"], row["pose"]) for row in difference["not_compared"]}
    for warning in difference["new_warnings"]:
        parts = warning.split(": ")
        kept.append(warning + ((" (not in the accepted report)") if tuple(parts[:2]) in uncovered else " (new against the accepted report)"))
    block = {"accepted_input": accepted.get("input"), "tolerance": difference["tolerance"], "worse": difference["worse"],
             "better": difference["better"], "not_compared": difference["not_compared"],
             "warnings_without_accept": list(warnings), "accepted_warnings": len(warnings) - len(difference["new_warnings"])}
    return kept, block


# ---------------------------------------------------------------- bone map from the rig (plain Python)

def bone_words(name):
    """Lower-case words and numbers of a bone name: 'J_Bip_L_Index1' -> ['j', 'bip', 'l', 'index', '1']."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(name))
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
    return [word for word in re.split(r"[^A-Za-z0-9]+", text.lower()) if word]


def _bone_side(words):
    left = "left" in words or "l" in words
    right = "right" in words or "r" in words
    return "left" if left and not right else "right" if right and not left else None


def guess_bone_map(bones, declared=None, sides=("left", "right")):
    """Role -> bone name for the hands, arms and head, from data the rig already carries.

    bones: [{"name", "parent", "head": (x, y, z)}] in rest pose. declared: roles stored by a VRM add-on, used first.
    Fingers are found by name (thumb / index / middle / ring / little or pinky, with a left / right mark) and
    ordered by depth in the hierarchy, so numbered and worded names both work. The hand is the bone the finger
    chains meet in. Where finger names say nothing, five chains under a named hand are ordered by position.
    Returns {"human_bones", "methods", "missing", "notes"}; `missing` lists the hand roles that were not found.
    """
    index = {bone["name"]: bone for bone in bones}
    children = {}
    for bone in bones:
        children.setdefault(bone.get("parent"), []).append(bone["name"])

    def ancestors(name):
        chain = []
        parent = index[name].get("parent")
        while parent in index:
            chain.append(parent)
            parent = index[parent].get("parent")
        return chain

    depth = {name: len(ancestors(name)) for name in index}
    words = {name: bone_words(name) for name in index}
    found, methods, notes = {}, {}, []
    for role, name in (declared or {}).items():
        if isinstance(name, str) and name in index:
            found[role], methods[role] = name, "declared"
    helper = set(BONE_SKIP_WORDS)
    for side in sides:
        chains = {}
        for finger in FINGERS:
            roles = [side + finger + segment for segment in SEGMENTS[finger]]
            if all(role in found for role in roles):
                chains[finger] = [found[role] for role in roles]
                continue
            group = [name for name in index if _bone_side(words[name]) == side and not helper & set(words[name])
                     and BONE_FINGER_WORDS.get(next((w for w in words[name] if w in BONE_FINGER_WORDS), None)) == finger]
            if finger != "Thumb":
                group = [name for name in group if "metacarpal" not in words[name]]
            if any("def" in words[name] for name in group):         # a control rig: keep the deforming copies
                group = [name for name in group if "def" in words[name]]
            group.sort(key=lambda name: (depth[name], name))
            for root in group:                                      # the shallowest bone with two more of the group below it
                below = [name for name in group if root in ancestors(name)]
                if len(below) >= 2:
                    group = [root] + below
                    break
            group = group[:3]
            if len(group) == 3 and all(group[k] in ancestors(group[k + 1]) for k in range(2)):
                chains[finger] = group
                for role, name in zip(roles, group):
                    found.setdefault(role, name)
                    methods.setdefault(role, "name")
        hand_role = side + "Hand"
        if hand_role not in found:
            parents = [index[chain[0]].get("parent") for chain in chains.values() if index[chain[0]].get("parent") in index]
            named = [name for name in index if _bone_side(words[name]) == side and not helper & set(words[name])
                     and ("hand" in words[name] or "wrist" in words[name]) and not set(words[name]) & set(BONE_FINGER_WORDS)]
            named.sort(key=lambda name: (depth[name], name))
            if len(parents) >= 2:
                lines = [[parent] + ancestors(parent) for parent in parents]
                shared = [name for name in lines[0] if all(name in line for line in lines[1:])]
                if shared:
                    found[hand_role], methods[hand_role] = shared[0], "where the finger chains meet"
            if hand_role not in found and named:
                found[hand_role], methods[hand_role] = named[0], "name"
        if hand_role in found and len(chains) < 5:                # no usable finger names: order the chains by position
            hand_name = found[hand_role]
            loose = []
            for child in children.get(hand_name, []):
                chain = [child]
                while len(children.get(chain[-1], [])) == 1:
                    chain.append(children[chain[-1]][0])
                if len(chain) >= 3 and not helper & set(words[child]):
                    loose.append(chain)
            if len(loose) == 5:
                points = lambda chain: (np.array(index[chain[0]]["head"], float), np.array(index[chain[2]]["head"], float))
                directions = [_unit(points(chain)[1] - points(chain)[0]) for chain in loose]
                mean = _unit(np.sum(directions, axis=0))
                thumb = int(np.argmin([float(d @ mean) for d in directions]))
                origin = points(loose[thumb])[0]
                rest = sorted((k for k in range(5) if k != thumb),
                              key=lambda k: float(np.linalg.norm(_perp(points(loose[k])[0] - origin, mean))))
                for finger, k in zip(FINGERS, [thumb] + rest):
                    if finger in chains:
                        continue
                    chains[finger] = loose[k][:3]
                    for role, name in zip([side + finger + segment for segment in SEGMENTS[finger]], loose[k][:3]):
                        found[role], methods[role] = name, "position under the hand"
                notes.append("%s: finger names were not recognised; five chains under %s were ordered from the thumb by position. "
                             "Check the map before using it." % (side, hand_name))
        if hand_role in found:
            line = [name for name in ancestors(found[hand_role]) if not {"twist", "roll"} & set(words[name])]

            def arm(test):
                return next((name for name in line if test(set(words[name]))), None)

            lower = arm(lambda w: "lowerarm" in w or "forearm" in w or "elbow" in w or ({"lower", "fore"} & w and "arm" in w))
            upper = arm(lambda w: "upperarm" in w or ("upper" in w and "arm" in w)
                        or ("arm" in w and not {"lower", "fore", "forearm", "lowerarm"} & w))
            how = "name"
            if lower is None or upper is None or lower == upper:
                lower, upper, how = (line + [None, None])[0], (line + [None, None])[1], "hierarchy above the hand"
            for role, name in ((side + "LowerArm", lower), (side + "UpperArm", upper)):
                if name is not None and role not in found:
                    found[role], methods[role] = name, how
    if "head" not in found:
        heads = [name for name in index if "head" in words[name] and not helper & set(words[name]) and _bone_side(words[name]) is None]
        heads.sort(key=lambda name: (len(words[name]), depth[name], name))
        if heads:
            found["head"], methods["head"] = heads[0], "name"
    used = {}
    for role, name in found.items():
        used.setdefault(name, []).append(role)
    for name, roles in sorted(used.items()):
        if len(roles) > 1:
            notes.append("one bone is used for several roles: %s <- %s" % (name, ", ".join(sorted(roles))))
    missing = [role for side in sides for role in side_roles(side) if role not in found]
    return {"human_bones": dict(sorted(found.items())), "methods": dict(sorted(methods.items())), "missing": missing, "notes": notes}


# ---------------------------------------------------------------- before / after picture (numpy only)

def stamp_label(pixels, text, left=8, top=8, scale=4):
    """Write BEFORE / AFTER style capitals into an image array (rows from the top, RGBA 0..1) on a dark tab."""
    text = "".join(ch for ch in str(text).upper() if ch in LABEL_GLYPHS)
    width = len(text) * 6 * scale + scale
    height = 9 * scale
    pixels[top:top + height, left:left + width, :3] = 0.08
    for slot, ch in enumerate(text):
        for row, line in enumerate(LABEL_GLYPHS[ch]):
            for column, mark in enumerate(line):
                if mark == "#":
                    y, x = top + (row + 1) * scale, left + (slot * 6 + column + 1) * scale
                    pixels[y:y + scale, x:x + scale, :3] = 1.0
    return pixels


def pair_image(before, after, labels=("BEFORE", "AFTER"), gap=8):
    """Two images of the same height side by side (before on the left), each with its label inside the picture."""
    before, after = np.array(before, dtype=np.float32), np.array(after, dtype=np.float32)
    if before.ndim != 3 or after.ndim != 3 or before.shape[0] != after.shape[0] or before.shape[2] != 4 or after.shape[2] != 4:
        raise ValueError("pair_image needs two RGBA images of the same height")
    spacer = np.ones((before.shape[0], gap, 4), np.float32)
    stamp_label(before, labels[0])
    stamp_label(after, labels[1])
    return np.concatenate([before, spacer, after], axis=1)


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


def rig_bone_rows(rig):
    return [{"name": bone.name, "parent": bone.parent.name if bone.parent else None,
             "head": [float(x) for x in bone.head_local], "tail": [float(x) for x in bone.tail_local]} for bone in rig.data.bones]


def declared_human_bones(rig):
    """Roles a VRM add-on stored on the armature (VRM 1.0 humanoid), read as plain data; {} when there are none."""
    def child(node, key):
        if node is None:
            return None
        value = getattr(node, key, None)
        if value is None:
            try:
                value = node[key]
            except (KeyError, TypeError, IndexError, AttributeError):
                value = None
        return value

    def stored(owner):                                     # with the add-on not loaded, its data is still in the file
        node = child(owner, "vrm_addon_extension")
        if node is None and hasattr(owner, "bl_system_properties_get"):
            try:
                node = child(owner.bl_system_properties_get(), "vrm_addon_extension")
            except (TypeError, RuntimeError):
                node = None
        return node

    node = stored(rig.data)
    for key in ("vrm1", "humanoid", "human_bones"):
        node = child(node, key)
    found = {}
    if node is None:
        return found
    by_uuid = {}
    for bone in rig.data.bones:                            # newer add-on versions point at a bone by its stored id
        uuid = child(stored(bone), "uuid")
        if isinstance(uuid, str) and uuid:
            by_uuid[uuid] = bone.name
    roles = ["head"] + [role for side in ("left", "right") for role in side_roles(side) + [side + "LowerArm", side + "UpperArm"]]
    for role in roles:
        snake = re.sub(r"([A-Z])", lambda m: "_" + m.group(1).lower(), role)
        entry = child(child(node, snake), "node")
        name = child(entry, "bone_name")
        if not (isinstance(name, str) and name):
            name = by_uuid.get(child(entry, "bone_uuid"))
        if isinstance(name, str) and name in rig.data.bones:
            found[role] = name
    return found


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


def body_lengths(rig, mapping, side, head_meshes=(), body_meshes=()):
    """Forearm and upper arm from the bones; head height and height from the named meshes (rest shape, world up = Z)."""
    unit = _unit_mm(rig)
    bones = rig.data.bones
    notes = []

    def head_of(role):
        name = mapping.get(role) if mapping else None
        return np.array(bones[name].head_local) if isinstance(name, str) and name in bones else None

    hand, lower, upper = head_of(side + "Hand"), head_of(side + "LowerArm"), head_of(side + "UpperArm")
    forearm = None if hand is None or lower is None else round(float(np.linalg.norm(hand - lower)) * unit, 1)
    upper_arm = None if lower is None or upper is None else round(float(np.linalg.norm(lower - upper)) * unit, 1)
    if forearm is None:
        notes.append("forearm not measured: the bone map has no %sLowerArm" % side)

    def heights(objects, bone_name=None):
        low, high = None, None
        for obj in objects:
            mesh = obj.data
            flat = np.empty(len(mesh.vertices) * 3)
            mesh.vertices.foreach_get("co", flat)
            world = np.array(obj.matrix_world)
            z = flat.reshape(-1, 3) @ world[2, :3] + world[2, 3]
            group = obj.vertex_groups.get(bone_name) if bone_name else None
            if group is not None:
                keep = np.zeros(len(z), bool)
                for vertex in mesh.vertices:
                    for element in vertex.groups:
                        if element.group == group.index and element.weight >= 0.5:
                            keep[vertex.index] = True
                if keep.any():
                    z = z[keep]
            if len(z):
                low = float(z.min()) if low is None else min(low, float(z.min()))
                high = float(z.max()) if high is None else max(high, float(z.max()))
        return None if low is None else round((high - low) * unit, 1)

    head = heights(head_meshes, mapping.get("head") if mapping else None) if head_meshes else None
    height = heights(body_meshes) if body_meshes else None
    if head is None:
        notes.append("head height not measured: name the bare head (no hair, no crown) with --head-meshes")
    if height is None:
        notes.append("height not measured: name the body meshes with --body-meshes (rest pose, standing along Z)")
    return forearm, upper_arm, head, height, notes


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


def _pose_model(mesh, rig, mapping, side, options):
    """The hand as it is rigged now: measured hand, bone names, bend axes, weights and the posing model."""
    hand, names = _hand_inputs(mesh, rig, mapping, side, options=options)
    joints = current_joints(rig, names)
    axes = rig_axes(rig, names, hand)
    weights = bone_weights(mesh, names, len(hand["points"]))
    weights[~hand["mask"]] = 0.0
    return hand, names, axes, weights, HandModel(hand, joints, axes, weights)


def _pair_sheet(before_path, after_path, out_path):
    """BEFORE | AFTER in one JPEG, composed from two rendered files with Blender's image API."""
    bpy = _bpy()
    arrays = []
    for path in (before_path, after_path):
        image = bpy.data.images.load(str(path))
        width, height = image.size
        flat = np.empty(width * height * 4, dtype=np.float32)
        image.pixels.foreach_get(flat)
        arrays.append(flat.reshape(height, width, 4)[::-1])
        bpy.data.images.remove(image)
    sheet = np.ascontiguousarray(pair_image(arrays[0], arrays[1])[::-1], dtype=np.float32)
    height, width = sheet.shape[:2]
    image = bpy.data.images.new("lida_hand_pair", width, height, alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(out_path)
    image.file_format = "JPEG"
    image.save()
    bpy.data.images.remove(image)


def command_measure(mesh, rig, mapping, sides, wrist, toward, back, options, render_dir, head_meshes=(), body_meshes=(),
                    head_height_mm=None, height_mm=None, heads=None, table=None, table_source="built-in"):
    report = {"schema": REPORT_SCHEMA, "command": "measure", "mesh": mesh.name, "rig": rig.name if rig else None,
              "unit": "mm", "space": "armature" if rig else "world", "options": resolve_options(options), "hands": {}}
    warnings = []
    for side in sides:
        hand, names = _hand_inputs(mesh, rig, mapping, side, wrist, toward, back, options)
        current = current_joints(rig, names) if rig is not None else None
        entry = {"back_of_hand": [round(float(x), 4) for x in hand["back"]], "back_method": hand["back_method"],
                 "region_vertices": int(hand["mask"].sum()), "palm_vertices": int((hand["labels"] == 0).sum()),
                 "fingers": joint_report(hand, current)}
        inside = hand_proportions(hand)
        forearm = upper_arm = head = height = None
        notes = []
        if rig is not None:
            forearm, upper_arm, head, height, notes = body_lengths(rig, mapping, side, head_meshes, body_meshes)
        head = head_height_mm if head_height_mm is not None else head
        height = height_mm if height_mm is not None else height
        body = body_ratios(inside["hand_length_mm"], forearm, upper_arm, head, height)
        entry["proportions"] = {"hand": inside, "body": body, "human_reference": dict(HUMAN_REFERENCE), "notes": notes}
        expectation = None
        explicit_band = any(key in (options or {}) for key in ("hand_head_min", "hand_head_max"))
        heads_used = heads if heads is not None else body["heads"]
        if heads_used is not None and not explicit_band:
            expectation = table_expectation(table or PROPORTION_TABLE, heads_used, hand["options"]["proportion_tolerance"], head)
            expectation["source"] = table_source
            expectation["heads_from"] = "--heads" if heads is not None else "measured height / head height"
            if expectation["outside_table"]:
                notes.append("the head count lies outside the table; its nearest row was used")
            entry["proportions"]["table"] = expectation
        elif explicit_band:
            notes.append("--hand-head-min/--hand-head-max were given, so the table was not used")
        else:
            notes.append("the table was not used: no head count (give --heads, or name --head-meshes and --body-meshes)")
        warnings += ["%s: %s" % (side, w) for w in proportion_warnings(inside, body, hand["options"], expectation)]
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
        hand, names, axes, weights, model = _pose_model(mesh, rig, mapping, side, options)
        opt = hand["options"]
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
    for command in ("measure", "place", "check", "run"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
        sub.add_argument("--mesh", required=True, help="the mesh that holds the hand skin (often the body)")
        sub.add_argument("--rig", required=command != "measure")
        sub.add_argument("--bones", type=Path, required=command in ("place", "check"),
                         help="role -> bone name map (VRM 1.0 roles, the rig-audit format); run reads the rig when it is omitted")
        sub.add_argument("--side", required=True, choices=("left", "right", "both"))
        if command == "run":
            sub.add_argument("--out-dir", required=True, type=Path, help="new folder for every report, the candidate and any views")
        else:
            sub.add_argument("--report", required=True, type=Path)
        for key in DEFAULTS:
            sub.add_argument("--" + key.replace("_", "-"), type=int if key in ("steps", "smooth") else float)
        if command == "measure":
            sub.add_argument("--wrist", nargs=3, type=float, metavar=("X", "Y", "Z"), help="wrist point when there is no rig")
            sub.add_argument("--toward", nargs=3, type=float, metavar=("X", "Y", "Z"), help="direction from the wrist to the fingers")
            sub.add_argument("--back", nargs=3, type=float, metavar=("X", "Y", "Z"), help="back-of-hand direction, to override")
        if command in ("measure", "run"):
            sub.add_argument("--head-meshes", nargs="+", default=[], metavar="MESH", help="the bare head (no hair), for the head height")
            sub.add_argument("--body-meshes", nargs="+", default=[], metavar="MESH", help="the meshes that span the full height")
            sub.add_argument("--head-height-mm", type=float, help="head height (crown to chin), to override")
            sub.add_argument("--height-mm", type=float, help="height, to override")
            sub.add_argument("--heads", type=float, help="the design's head count, to use instead of the measured one")
            sub.add_argument("--proportion-table", type=Path,
                             help="JSON rows of heads / hand_per_head (/ basis) to use instead of the built-in table")
        if command in ("measure", "check"):
            sub.add_argument("--render-dir", type=Path, help="new folder for close views")
        if command == "place":
            sub.add_argument("--output-blend", required=True, type=Path)
        if command in ("place", "run"):
            sub.add_argument("--keep-weights", action="store_true")
            sub.add_argument("--thumb-roll", default="auto", help="auto, or degrees")
            sub.add_argument("--z-toward", choices=("palm", "back"), default="palm")
            sub.add_argument("--rigid-followers", nargs="+", default=[], metavar="MESH",
                             help="nails and other hard pieces: every connected piece follows the one bone under it")
        if command in ("check", "run"):
            sub.add_argument("--poses", nargs="+", choices=tuple(POSES), default=list(POSES))
            sub.add_argument("--accept", type=Path,
                             help="a check report of an approved model: only values worse than it, and new kinds of warning, are reported")
            sub.add_argument("--accept-tolerance-mm", type=float, help="a length may rise this much against --accept (default 0.5)")
            sub.add_argument("--accept-tolerance-count", type=float, help="a count may rise this much against --accept (default 0)")
        if command == "check":
            sub.add_argument("--followers", nargs="+", default=[], metavar="MESH",
                             help="nails and other meshes on the finger bones: drawn, and their movement against the skin is measured")
        if command == "run":
            sub.add_argument("--views", choices=("none", "findings", "all"), default="none",
                             help="none: numbers only (default). findings: draw only the poses that still have a warning. all: every pose")
    sub = commands.add_parser("compare")
    sub.add_argument("--before", required=True, type=Path, help="a measure or check report")
    sub.add_argument("--after", required=True, type=Path, help="a report of the same command, made later")
    sub.add_argument("--report", required=True, type=Path)
    sub.add_argument("--tolerance-mm", type=float, help="a length must change more than this to count (default 0.5)")
    sub.add_argument("--tolerance-count", type=float, help="a count must change more than this to count (default 0)")
    sub.add_argument("--tolerance-ratio", type=float, help="a ratio must change more than this to be listed (default 0.01)")
    sub = commands.add_parser("bones")
    sub.add_argument("--input", required=True, type=Path)
    sub.add_argument("--rig", required=True)
    sub.add_argument("--side", choices=("left", "right", "both"), default="both")
    sub.add_argument("--report", required=True, type=Path)
    sub.add_argument("--output-map", required=True, type=Path, help="new JSON file for the role -> bone name map")
    return parser


def _safe_console():
    """Names the console cannot encode are escaped instead of failing after the report is written."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


def _read_report(path, what):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(what + " not found: " + path.name)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(what + " must be a JSON report of this tool")
    return data


def _source_blend(path):
    source = Path(path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".blend":
        raise ValueError("Input must be an existing .blend file")
    return source


def _open_blend(source):
    bpy = _bpy()
    if not bpy.app.background:
        raise ValueError("Run the CLI in a separate Blender background process")
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    return bpy.context.scene.objects


def _named_meshes(scene_objects, values, exclude=None, what="Mesh"):
    found = []
    for value in values or []:
        obj = scene_objects.get(value)
        if obj is None or obj.type != "MESH" or obj == exclude:
            raise ValueError("%s not found among the scene's meshes: %s" % (what, value))
        found.append(obj)
    return found


def _read_table(path, heads):
    table, table_source = None, "built-in"
    if path is not None:
        table_path = path.expanduser().resolve()
        if not table_path.is_file():
            raise ValueError("Proportion table not found: " + table_path.name)
        table = read_proportion_table(json.loads(table_path.read_text(encoding="utf-8-sig")))
        table_source = table_path.name
    if heads is not None and not (math.isfinite(heads) and heads > 0):
        raise ValueError("--heads must be a positive number")
    return table, table_source


def _close_report(report, warnings, source_info):
    report["input"] = source_info
    report["warnings"] = list(warnings)
    report["unverified"] = list(UNVERIFIED)
    report["status"] = "completed_with_findings" if warnings else "completed"
    return report


def _fail(command, report_path, error):
    report = {"schema": REPORT_SCHEMA, "command": command, "status": "error",
              "error_type": type(error).__name__, "message": str(error)}
    if report_path is not None and not report_path.exists():
        try:
            _write_report(report_path, report)
        except OSError:
            pass
    print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
    return 1


def _main_compare(args):
    report_path = None
    try:
        report_path = _new_output(args.report)
        tolerance = {"mm": args.tolerance_mm, "count": args.tolerance_count, "ratio": args.tolerance_ratio}
        report = compare_reports(_read_report(args.before, "--before"), _read_report(args.after, "--after"), tolerance)
        findings = report["summary"]["findings"]
        report["status"] = "completed_with_findings" if findings else "completed"
        code = 2 if findings else 0
        _write_report(report_path, report)
        print(json.dumps({"command": "compare", "status": report["status"], "summary": report["summary"],
                          "report": report_path.name, "exit_code": code}, ensure_ascii=False))
        return code
    except Exception as error:
        return _fail("compare", report_path, error)


def _main_bones(args):
    report_path = None
    try:
        report_path = _new_output(args.report)
        map_path = _new_output(args.output_map)
        source = _source_blend(args.input)
        if len({source, report_path, map_path}) != 3:
            raise ValueError("Input, report and map must be three different paths")
        before_sha = _file_hash(source)
        scene_objects = _open_blend(source)
        rig = scene_objects.get(args.rig)
        if rig is None or rig.type != "ARMATURE":
            raise ValueError("Rig not found: " + args.rig)
        sides = ("left", "right") if args.side == "both" else (args.side,)
        guess = guess_bone_map(rig_bone_rows(rig), declared_human_bones(rig), sides)
        _write_report(map_path, {"schema": BONE_MAP_SCHEMA, "spec_version": "1.0", "human_bones": guess["human_bones"]})
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        warnings = ["no bone found for " + role for role in guess["missing"]] + guess["notes"]
        report = {"schema": REPORT_SCHEMA, "command": "bones", "rig": rig.name, "bones_in_rig": len(rig.data.bones),
                  "human_bones": guess["human_bones"], "methods": guess["methods"], "missing": guess["missing"],
                  "output": {"name": map_path.name, "sha256": _file_hash(map_path)}}
        _close_report(report, warnings, {"name": source.name, "sha256": before_sha, "unchanged_after_command": True})
        report["unverified"] = ["whether each bone is the intended one: read `methods`, and look at any role found by position or hierarchy"]
        code = 2 if warnings else 0
        _write_report(report_path, report)
        print(json.dumps({"command": "bones", "status": report["status"], "roles": len(guess["human_bones"]),
                          "missing": len(guess["missing"]), "report": report_path.name, "exit_code": code}, ensure_ascii=False))
        return code
    except Exception as error:
        return _fail("bones", report_path, error)


def _flagged_poses(report, warnings, sides, poses):
    """{side: [pose, ...]} of the poses a warning names, for drawing only what still needs a look."""
    flagged = {side: [] for side in sides}
    for warning in warnings:
        parts = str(warning).split(": ")
        if len(parts) >= 2 and parts[0] in flagged and parts[1] in poses and parts[1] not in flagged[parts[0]]:
            flagged[parts[0]].append(parts[1])
    for side in sides:
        limit = report["options"]["follower_drift_mm"]
        for row in ((report["hands"].get(side) or {}).get("followers") or {}).values():
            for pose, value in (row.get("drift_mm") or {}).items():
                if value > limit and pose not in flagged[side]:
                    flagged[side].append(pose)
        if any(str(w).startswith(side + ": ") for w in warnings) and not flagged[side] and "fist" in poses:
            flagged[side].append("fist")
    return flagged


def _main_run(args):
    """bones (when no map is given) -> measure -> check -> place -> check again -> compare, in one process."""
    report_path = None
    try:
        out_dir = _new_output(args.out_dir)
        source = _source_blend(args.input)
        if args.thumb_roll != "auto":
            float(args.thumb_roll)
        options = {key: getattr(args, key) for key in DEFAULTS if getattr(args, key, None) is not None}
        resolve_options(options)
        accepted = _read_report(args.accept, "--accept") if args.accept is not None else None
        tolerance = {"mm": args.accept_tolerance_mm, "count": args.accept_tolerance_count}
        table, table_source = _read_table(args.proportion_table, args.heads)
        given_map = read_bone_map(args.bones) if args.bones is not None else None
        before_sha = _file_hash(source)
        sides = ("left", "right") if args.side == "both" else (args.side,)
        _bpy()
        out_dir.mkdir()
        report_path = out_dir / "run.json"
        source_info = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        files, steps = {}, {}

        def load():
            scene_objects = _open_blend(source)
            mesh = scene_objects.get(args.mesh)
            if mesh is None:
                raise ValueError("Mesh not found: " + args.mesh)
            rig = scene_objects.get(args.rig)
            if rig is None or rig.type != "ARMATURE":
                raise ValueError("Rig not found: " + args.rig)
            followers = _named_meshes(scene_objects, args.rigid_followers, mesh, "Follower")
            return scene_objects, mesh, rig, followers

        def emit(name, report):
            _write_report(out_dir / name, report)
            files[name] = _file_hash(out_dir / name)

        scene_objects, mesh, rig, followers = load()
        if given_map is not None:
            mapping = given_map
            steps["bones"] = {"source": args.bones.name}
        else:
            guess = guess_bone_map(rig_bone_rows(rig), declared_human_bones(rig), sides)
            emit("bones.json", {"schema": BONE_MAP_SCHEMA, "spec_version": "1.0", "human_bones": guess["human_bones"]})
            steps["bones"] = {"source": "read from the rig", "methods": guess["methods"], "notes": guess["notes"], "missing": guess["missing"]}
            if guess["missing"]:
                raise ValueError("The rig does not show these hand bones; write a map and pass --bones: " + ", ".join(guess["missing"]))
            mapping = guess["human_bones"]
        warnings = ["bones: " + note for note in steps["bones"].get("notes", [])]

        measure, found = command_measure(mesh, rig, mapping, sides, None, None, None, options, None,
                                         _named_meshes(scene_objects, args.head_meshes), _named_meshes(scene_objects, args.body_meshes),
                                         args.head_height_mm, args.height_mm, args.heads, table, table_source)
        emit("measure.json", _close_report(measure, found, source_info))
        steps["measure"] = {"report": "measure.json", "warnings": len(found)}
        warnings += ["measure: " + w for w in found]

        before = None
        try:
            before, found = command_check(mesh, rig, mapping, sides, options, args.poses, None, followers)
            emit("check_before.json", _close_report(before, found, source_info))
            steps["check_before"] = {"report": "check_before.json", "warnings": len(found)}
        except ValueError as error:
            steps["check_before"] = {"skipped": str(error)}

        output = out_dir / (source.stem + "_hands.blend")
        placed, found = command_place(mesh, rig, mapping, sides, options, args.keep_weights, args.thumb_roll, args.z_toward, followers)
        _save_candidate(output)
        placed["output"] = {"name": output.name, "sha256": _file_hash(output)}
        files[output.name] = placed["output"]["sha256"]
        emit("place.json", _close_report(placed, found, source_info))
        steps["place"] = {"report": "place.json", "output": output.name, "warnings": len(found)}
        warnings += ["place: " + w for w in found]

        after, found = command_check(mesh, rig, mapping, sides, options, args.poses, None, followers)
        after_info = {"name": output.name, "sha256": placed["output"]["sha256"], "state": "checked in memory right after place; saved as this file"}
        if accepted is not None:
            found, after["accept"] = apply_accepted(after, found, accepted, tolerance)
        emit("check_after.json", _close_report(after, found, after_info))
        steps["check_after"] = {"report": "check_after.json", "warnings": len(found), "read_against_accept": accepted is not None}
        warnings += ["check: " + w for w in found]
        if before is not None:
            difference = compare_reports(before, after)
            difference["status"] = "completed_with_findings" if difference["summary"]["findings"] else "completed"
            emit("compare.json", difference)
            steps["compare"] = dict(difference["summary"], report="compare.json")
            warnings += ["compare: %s: %s: %s rose from %g to %g %s" % (r["side"], r["pose"], r["metric"], r["before"], r["after"], r["unit"])
                         for r in difference["worse"]]

        views = {"mode": args.views, "images": 0}
        wanted = {side: list(args.poses) for side in sides} if args.views == "all" else \
            _flagged_poses(after, found, sides, args.poses) if args.views == "findings" else {}
        if any(wanted.values()):
            folder = out_dir / "views"
            folder.mkdir()
            names = {}
            for state in ("after", "before"):             # after is in memory; before opens the input again (nothing is saved)
                if state == "before":
                    scene_objects, mesh, rig, followers = load()
                (folder / state).mkdir()
                for side, poses in wanted.items():
                    if not poses:
                        continue
                    (folder / state / side).mkdir()
                    hand, bone_names, axes, _weights, model = _pose_model(mesh, rig, mapping, side, options)
                    fit_thumb_poses(model, poses)
                    spec = {pose: (axes, model.spec(pose)) for pose in poses}
                    names[(state, side)] = render_views(rig, mesh, hand, bone_names, folder / state / side, poses=spec, keep=tuple(followers))
            (folder / "pairs").mkdir()
            for side in wanted:
                shared = sorted(set(names.get(("before", side), {}).values()) & set(names.get(("after", side), {}).values()))
                if shared:
                    (folder / "pairs" / side).mkdir()
                for name in shared:
                    _pair_sheet(folder / "before" / side / name, folder / "after" / side / name, folder / "pairs" / side / name)
                    views["images"] += 1
            views.update({"folder": "views", "poses": wanted, "pairs": "views/pairs/<side>/<pose>_<view>.jpg, BEFORE on the left"})
        elif args.views == "findings":
            views["note"] = "no pose has a warning, so nothing was drawn"

        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        report = {"schema": REPORT_SCHEMA, "command": "run", "mesh": args.mesh, "rig": args.rig, "sides": list(sides),
                  "steps": steps, "files": files, "views": views}
        _close_report(report, warnings, source_info)
        code = 2 if warnings else 0
        _write_report(report_path, report)
        print(json.dumps({"command": "run", "status": report["status"], "warnings": len(warnings), "folder": out_dir.name,
                          "candidate": output.name, "views": views["images"], "exit_code": code}, ensure_ascii=False))
        return code
    except Exception as error:
        return _fail("run", report_path, error)


def main(argv=None):
    _safe_console()
    if argv is None:
        if "--" not in sys.argv and any(Path(a).name.lower().startswith("blender") for a in sys.argv[:1]):
            print("Write the tool's arguments after '--', for example: blender -b --python lida_hand_rig.py -- measure ...", file=sys.stderr)
            return 2
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parser().parse_args(argv)
    if args.command == "compare":
        return _main_compare(args)
    if args.command == "bones":
        return _main_bones(args)
    if args.command == "run":
        return _main_run(args)
    report_path = None
    try:
        report_path = _new_output(args.report)
        source = _source_blend(args.input)
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
        accepted = _read_report(args.accept, "--accept") if getattr(args, "accept", None) is not None else None
        before_sha = _file_hash(source)
        scene_objects = _open_blend(source)
        mesh = scene_objects.get(args.mesh)
        if mesh is None:
            raise ValueError("Mesh not found: " + args.mesh)
        rig = None
        if args.rig:
            rig = scene_objects.get(args.rig)
            if rig is None:
                raise ValueError("Rig not found: " + args.rig)
            if mapping is None:
                raise ValueError("--rig needs --bones (the bones command writes a map from the rig)")
        sides = ("left", "right") if args.side == "both" else (args.side,)
        follower_objects = _named_meshes(scene_objects, getattr(args, "rigid_followers", None) or getattr(args, "followers", None),
                                         mesh, "Follower")
        if args.command == "measure" and args.wrist is not None and len(sides) > 1:
            raise ValueError("--wrist describes one hand; measure one --side at a time")
        if args.command == "measure" and rig is None and args.wrist is None:
            raise ValueError("Give --rig and --bones, or --wrist and --toward")
        if render_dir is not None:
            render_dir.mkdir()
            for side in sides:
                (render_dir / side).mkdir()
        if args.command == "measure":
            table, table_source = _read_table(args.proportion_table, args.heads)
            report, warnings = command_measure(mesh, rig, mapping, sides, args.wrist, args.toward, args.back, options, render_dir,
                                               _named_meshes(scene_objects, args.head_meshes), _named_meshes(scene_objects, args.body_meshes),
                                               args.head_height_mm, args.height_mm, args.heads, table, table_source)
        elif args.command == "place":
            report, warnings = command_place(mesh, rig, mapping, sides, options, args.keep_weights, args.thumb_roll, args.z_toward,
                                             follower_objects)
            _save_candidate(output)
            report["output"] = {"name": output.name, "sha256": _file_hash(output)}
        else:
            report, warnings = command_check(mesh, rig, mapping, sides, options, args.poses, render_dir, follower_objects)
            if accepted is not None:
                warnings, report["accept"] = apply_accepted(report, warnings, accepted,
                                                            {"mm": args.accept_tolerance_mm, "count": args.accept_tolerance_count})
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        _close_report(report, warnings, {"name": source.name, "sha256": before_sha, "unchanged_after_command": True})
        code = 2 if warnings else 0
        _write_report(report_path, report)
        print(json.dumps({"command": args.command, "status": report["status"], "warnings": len(warnings),
                          "report": report_path.name, "exit_code": code}, ensure_ascii=False))
        return code
    except Exception as error:
        return _fail(args.command, report_path, error)


if __name__ == "__main__":
    raise SystemExit(main())
