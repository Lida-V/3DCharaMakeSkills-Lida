# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Find where a part (hair, ribbon, cloth) passes through other meshes, and say how each place can be repaired.

Run in Blender with ``--background --factory-startup --python THIS.py -- COMMAND``.
check:   --input MODEL.blend --parts Hair --solid Body Tail [--thin Fin Chain] [--allow Head]
         --report NEW.json [--render-dir NEW_DIR]
advise:  --input MODEL.blend --parts Hair --solid Body Tail --report NEW.json [--render-dir NEW_DIR]
compare: --before OLD.json --after NEW.json --report NEW.json      (ordinary Python is enough)

Method. check computes the exact curves where the triangles of a part cross the triangles of each
partner, asks from many directions whether each piece of curve can be seen from outside, groups
nearby pieces into spots and lists them by visible length. For closed partners (--solid) it also
measures how deep sample points of the part lie inside. advise splits the part's faces for analysis
only, finds each stretch buried in a solid partner and measures its depth, buried extent, number and
width of entries and how much of the entry can be seen; from these it names one repair: delete,
delete_scrap, trim, pull_tip, push, reroute_or_cut or leave. compare matches the spots of two check
reports and lists new, gone and changed ones.

The numeric core needs numpy only and runs in ordinary Python. The input blend is opened read-only
and never saved; marks and cameras for --render-dir exist in memory only. Reports and image folders
must be new paths. Exit codes: 0 completed without findings; 2 completed with findings (visible
intersections, repairs to do, new or grown spots) or warnings; 1 invalid input, I/O or execution
error. A report is a measurement and a suggestion, not an appearance grade: thresholds are options.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


REPORT_SCHEMA = "lida.penetration.report.v1"
DEFAULTS = {
    "tolerance_mm": 0.5,        # a sample deeper than this inside a solid partner counts as inside
    "cluster_mm": 8.0,          # pieces of curve closer than this belong to one spot
    "view_directions": 48,      # directions used to ask whether a place can be seen from outside
    "vote_directions": 11,      # rays per sample for the inside vote against a solid partner
    "seen_directions": 2,       # a piece seen from at least this many directions counts as visible
    "visible_spot_mm": 1.0,     # a spot with more visible curve than this is reported as visible
    "levels": 2,                # advise: midpoint splits of every face (analysis only)
    "reach_mm": 80.0,           # advise: samples farther than this from a partner get a coarse vote
    "shallow_mm": 4.0,          # advise: buried no deeper than this -> push
    "tip_extent_mm": 35.0,      # advise: a single-entry stretch no longer than this -> pull_tip
    "push_ratio": 0.6,          # advise: push while depth <= ratio * entry width ...
    "push_max_mm": 15.0,        # ... and depth <= this
    "hidden_share": 0.05,       # advise: entry seen on less than this share -> leave
    "small_island_cm2": 40.0,   # advise: islands smaller than this that are mostly inside -> delete
    "island_inside_share": 0.6,
    "scrap_cm2": 1.5,           # advise: an outside patch smaller than this next to a buried stretch
    "match_mm": 20.0,           # compare: spots closer than this are the same spot
    "grow_mm": 5.0,             # compare: visible curve grown by more than this counts as worse
}
UNVERIFIED = [
    "appearance in renders: whether a crossing reads as a fault or as an intended overlap (roots, tucked ends)",
    "other poses, frames and shape-key states than the one evaluated (pass --frame, or pose a copy, and run again)",
    "views outside the sampled directions; a place seen only from below still counts as visible",
    "depth values against partners with open borders or inner shells (the inside vote can be doubtful)",
    "thin partners in advise (fins, chains): only check lists their crossings",
    "the repair itself: advice is a rule on measured sizes with adjustable thresholds, not a design decision",
]
ADVICE = ("delete", "delete_scrap", "trim", "pull_tip", "push", "reroute_or_cut", "leave")


# ---------------------------------------------------------------- numeric core (numpy only)

def sphere_dirs(count):
    """Evenly spread unit directions (Fibonacci sphere)."""
    index = np.arange(count) + 0.5
    polar = np.arccos(1 - 2 * index / count)
    turn = math.pi * (1 + 5 ** 0.5) * index
    return np.stack([np.cos(turn) * np.sin(polar), np.sin(turn) * np.sin(polar), np.cos(polar)], axis=1)


def clean_triangles(points, triangles):
    """Drop zero-area triangles; return (triangles, open_edge_count)."""
    points, triangles = np.asarray(points, float), np.asarray(triangles, np.int64).reshape(-1, 3)
    cross = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]], points[triangles[:, 2]] - points[triangles[:, 0]])
    triangles = triangles[np.linalg.norm(cross, axis=1) > 1e-14]
    edges = np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    _, count = np.unique(edges, axis=0, return_counts=True)
    return triangles, int((count == 1).sum())


def _plane_crossings(corners, signed):
    signed = np.where(signed == 0, 1e-12, signed)
    points = np.zeros((len(corners), 2, 3))
    found = np.zeros(len(corners), dtype=np.int64)
    with np.errstate(divide="ignore", invalid="ignore"):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            ok = (signed[:, i] * signed[:, j] < 0) & (found < 2)
            share = signed[:, i] / (signed[:, i] - signed[:, j])
            cut = corners[:, i] + share[:, None] * (corners[:, j] - corners[:, i])
            rows = np.nonzero(ok)[0]
            points[rows, found[rows]] = cut[rows]
            found[rows] += 1
    return points, found == 2


def tri_tri_segments(points_a, triangles_a, points_b, triangles_b, pairs, return_mask=False):
    """Segments (n, 2, 3) where triangle pairs (index in a, index in b) really cross.

    With return_mask, also return which of the given pairs crossed (the segments follow that order).
    """
    pairs = np.asarray(pairs, np.int64).reshape(-1, 2)
    if not len(pairs):
        return (np.zeros((0, 2, 3)), np.zeros(0, bool)) if return_mask else np.zeros((0, 2, 3))
    p = np.asarray(points_a, float)[np.asarray(triangles_a)[pairs[:, 0]]]
    q = np.asarray(points_b, float)[np.asarray(triangles_b)[pairs[:, 1]]]
    normal_p = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    normal_q = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    normal_p /= np.maximum(np.linalg.norm(normal_p, axis=1), 1e-300)[:, None]
    normal_q /= np.maximum(np.linalg.norm(normal_q, axis=1), 1e-300)[:, None]
    cut_p, ok_p = _plane_crossings(p, np.einsum("nij,nj->ni", p - q[:, :1], normal_q))
    cut_q, ok_q = _plane_crossings(q, np.einsum("nij,nj->ni", q - p[:, :1], normal_p))
    line = np.cross(normal_p, normal_q)
    length = np.linalg.norm(line, axis=1)
    ok = ok_p & ok_q & (length > 1e-9)
    line = line / np.maximum(length, 1e-12)[:, None]
    origin = cut_p[:, 0]
    along_p = np.einsum("nij,nj->ni", cut_p - origin[:, None], line)
    along_q = np.einsum("nij,nj->ni", cut_q - origin[:, None], line)
    low = np.maximum(along_p.min(1), along_q.min(1))
    high = np.minimum(along_p.max(1), along_q.max(1))
    ok &= high - low > 1e-10
    segments = np.stack([origin + low[:, None] * line, origin + high[:, None] * line], axis=1)[ok]
    return (segments, ok) if return_mask else segments


def brute_pairs(points_a, triangles_a, points_b, triangles_b):
    """All triangle pairs whose boxes overlap; for small meshes and tests (Blender uses BVH overlap)."""
    a, b = np.asarray(points_a)[np.asarray(triangles_a)], np.asarray(points_b)[np.asarray(triangles_b)]
    hit = (a.min(1)[:, None] <= b.max(1)[None]).all(2) & (b.min(1)[None] <= a.max(1)[:, None]).all(2)
    return np.argwhere(hit)


def weld(points, triangles, step):
    """Merge vertices at the same place (UV seams split them); return (points, triangles)."""
    key = np.round(np.asarray(points, float) / step).astype(np.int64)
    _, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return np.asarray(points, float)[first], inverse.ravel()[np.asarray(triangles)]


def subdivide(points, triangles):
    """Split every triangle into four at edge midpoints. Analysis only; the model is not changed."""
    triangles = np.asarray(triangles, np.int64)
    edges, inverse = np.unique(np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1),
                               axis=0, return_inverse=True)
    middle = len(points) + inverse.ravel().reshape(3, -1).T
    points = np.concatenate([points, (points[edges[:, 0]] + points[edges[:, 1]]) / 2])
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    ab, bc, ca = middle[:, 0], middle[:, 1], middle[:, 2]
    return points, np.concatenate([np.stack(x, 1) for x in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])


class _Sets:
    """Disjoint sets over 0..n-1."""

    def __init__(self, count):
        self.parent = list(range(count))

    def find(self, item):
        parent = self.parent
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            parent[item], item = root, parent[item]
        return root

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[a] = b

    def labels(self):
        return np.array([self.find(i) for i in range(len(self.parent))], dtype=np.int64)


def cluster_points(points, radius):
    """Label points so that points closer than radius (through chains) share a label."""
    points = np.asarray(points, float)
    sets = _Sets(len(points))
    cells = {}
    keys = np.floor(points / radius).astype(np.int64)
    for index, key in enumerate(map(tuple, keys)):
        cells.setdefault(key, []).append(index)
    offsets = [(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)]
    for key, members in cells.items():
        near = [m for o in offsets for m in cells.get((key[0] + o[0], key[1] + o[1], key[2] + o[2]), ())]
        block = points[near]
        for index in members:
            close = np.nonzero(((block - points[index]) ** 2).sum(1) <= radius * radius)[0]
            for other in close:
                sets.union(index, near[other])
    return sets.labels()


def cluster_segments(segments, radius):
    """Label segments: ends closer than radius join, and the two ends of a segment always belong together."""
    count = len(segments)
    ends = cluster_points(np.concatenate([segments[:, 0], segments[:, 1]]), radius)
    sets = _Sets(len(ends))
    for index in range(len(ends)):
        sets.union(index, int(ends[index]))
    for index in range(count):
        sets.union(index, index + count)
    return sets.labels()[:count]


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
    for key in ("view_directions", "vote_directions", "seen_directions", "levels"):
        resolved[key] = int(resolved[key])
    if resolved["view_directions"] < 6 or resolved["vote_directions"] < 3 or resolved["levels"] > 4:
        raise ValueError("view_directions >= 6, vote_directions >= 3 and levels <= 4 are required")
    return resolved


def _round(values, digits=4):
    return [round(float(v), digits) for v in values]


def _best_view(escape, weight, directions):
    seen = (escape * weight[:, None]).sum(0)
    if len(seen) == 0 or seen.max() <= 0:
        return np.array([0.0, -1.0, 0.0])
    return directions[int(np.argmax(seen))]


def analyse_contacts(parts, partners, overlap, inside, visible, options=None, unit_mm=1000.0):
    """Core of check.

    parts: {name: (points, triangles)}; partners: {name: (points, triangles, kind, allowed)} with kind
    "solid" or "thin". overlap(part, partner) -> candidate triangle pairs. inside(partner, points) ->
    (vote 0..1, distance to the surface). visible(points) -> bool (n, view_directions): True where a
    ray from the point leaves the model. Returns (report, marks) with marks = [(spot, segments)].
    """
    opt = resolve_options(options)
    directions = sphere_dirs(opt["view_directions"])
    pairs_out, spots, warnings = [], [], []
    for part, (points, triangles) in parts.items():
        samples = np.concatenate([points, points[triangles].mean(1)])
        for name, (partner_points, partner_triangles, kind, allowed) in partners.items():
            if name == part:
                continue
            segments = tri_tri_segments(points, triangles, partner_points, partner_triangles, overlap(part, name))
            length = np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1) * unit_mm
            entry = {"part": part, "partner": name, "kind": kind, "allowed": bool(allowed), "curve_mm": round(float(length.sum()), 1)}
            deep_points, deep = np.zeros((0, 3)), np.zeros(0)
            if kind == "solid":
                vote, near = inside(name, samples)
                depth = np.where(vote > 0.5, near, 0.0) * unit_mm
                bad = depth > opt["tolerance_mm"]
                unsure = float(((vote > 0.25) & (vote < 0.75)).mean()) if len(vote) else 0.0
                entry.update({"samples": int(len(samples)), "inside_percent": round(100 * float(bad.mean()), 2),
                              "deepest_mm": round(float(depth.max()) if len(depth) else 0.0, 2),
                              "unsure_percent": round(100 * unsure, 2)})
                if unsure > 0.05:
                    warnings.append("The inside vote against " + name + " is doubtful for %.0f %% of the samples of %s; "
                                    "check for open borders or inner shells" % (100 * unsure, part))
                deep_points, deep = samples[bad], depth[bad]
            pairs_out.append(entry)
            if not len(segments):
                continue
            middle = segments.mean(1)
            escape = np.asarray(visible(middle), bool)
            seen = escape.sum(1) >= opt["seen_directions"]
            label = cluster_segments(segments, opt["cluster_mm"] / unit_mm)
            spot_depth = {}
            for start in range(0, len(deep_points), 2000):
                block = deep_points[start:start + 2000]
                distance = np.linalg.norm(block[:, None] - middle[None], axis=2)
                nearest = distance.argmin(1)
                for row in np.nonzero(distance[np.arange(len(block)), nearest] * unit_mm < 60.0)[0]:
                    key = label[nearest[row]]
                    spot_depth[key] = max(spot_depth.get(key, 0.0), float(deep[start + row]))
            for key in np.unique(label):
                rows = label == key
                weight = length[rows]
                spot = {"part": part, "partner": name, "kind": kind, "allowed": bool(allowed),
                        "center": _round(middle[rows].mean(0)),
                        "size_mm": round(float(np.linalg.norm(middle[rows].max(0) - middle[rows].min(0)) * unit_mm), 1),
                        "curve_mm": round(float(weight.sum()), 1),
                        "visible_curve_mm": round(float(weight[seen[rows]].sum()), 1),
                        "openness": round(float((escape[rows].mean(1) * weight).sum() / max(weight.sum(), 1e-9)), 3),
                        "depth_mm": round(spot_depth.get(key, 0.0), 2) if kind == "solid" else None,
                        "view": _round(_best_view(escape[rows], weight, directions), 3)}
                spots.append((spot, segments[rows]))
    spots.sort(key=lambda item: (item[0]["allowed"], -item[0]["visible_curve_mm"], -item[0]["curve_mm"]))
    for index, (spot, _) in enumerate(spots):
        spot["id"] = index + 1
    counted = [s for s, _ in spots if not s["allowed"]]
    visible_spots = [s for s in counted if s["visible_curve_mm"] > opt["visible_spot_mm"]]
    by_partner = {}
    for spot in visible_spots:
        row = by_partner.setdefault(spot["partner"], {"visible_spots": 0, "visible_curve_mm": 0.0})
        row["visible_spots"] += 1
        row["visible_curve_mm"] = round(row["visible_curve_mm"] + spot["visible_curve_mm"], 1)
    summary = {"spots": len(counted), "visible_spots": len(visible_spots),
               "visible_curve_mm": round(sum(s["visible_curve_mm"] for s in counted), 1),
               "hidden_curve_mm": round(sum(s["curve_mm"] - s["visible_curve_mm"] for s in counted), 1),
               "allowed_spots": len(spots) - len(counted), "by_partner": by_partner}
    if visible_spots:
        warnings.append("%d visible intersection spots (%.0f mm of visible curve); see spots"
                        % (len(visible_spots), summary["visible_curve_mm"]))
    report = {"unit": "mm", "unit_mm": unit_mm, "options": opt, "summary": summary, "pairs": pairs_out,
              "spots": [s for s, _ in spots], "warnings": warnings}
    return report, spots


def advise_stretch(m, opt):
    """Name one repair for a buried stretch from its measured sizes; returns (advice, reason)."""
    if m["entry_points"] == 0:
        return "delete", "the whole island lies inside the partner and cannot be seen"
    if m["visible_share"] < opt["hidden_share"]:
        return "leave", "the entry cannot be seen from outside"
    if m["island_inside_share"] > opt["island_inside_share"] and m["island_area_cm2"] < opt["small_island_cm2"]:
        return "delete", "most of a small island lies inside"
    if m["depth_mm"] <= opt["shallow_mm"]:
        return "push", "shallow: moving it about %.0f mm outward clears it" % (m["depth_mm"] + 1)
    if m["entries"] == 1:
        if m["extent_mm"] <= opt["tip_extent_mm"]:
            return "pull_tip", "only the tip is buried: bend the last part about %.0f mm outward" % (m["depth_mm"] + 1)
        return "trim", "it goes in and does not come out: cut at the entry and close the end"
    if m["depth_mm"] <= opt["push_ratio"] * max(m["entry_width_mm"], 1.0) and m["depth_mm"] <= opt["push_max_mm"]:
        return "push", "depth %.0f mm against a lock width of %.0f mm: a smooth outward move is possible" % (m["depth_mm"], m["entry_width_mm"])
    return "reroute_or_cut", ("depth %.0f mm against a lock width of %.0f mm: pushing would change the shape; "
                              "reroute it outside or cut the buried stretch and close both ends") % (m["depth_mm"], m["entry_width_mm"])


def analyse_buried(part, points, triangles, solids, inside, visible, options=None, unit_mm=1000.0):
    """Core of advise for one part.

    solids: list of partner names. inside(partner, points) -> (vote, distance). visible(points) -> bool
    (n, view_directions). Returns (info, items, marks) with marks = [(item, segments)].
    """
    opt = resolve_options(options)
    directions = sphere_dirs(opt["view_directions"])
    points, triangles = weld(points, triangles, 0.01 / unit_mm)
    triangles, _ = clean_triangles(points, triangles)
    edge0 = float(np.median(np.linalg.norm(points[triangles[:, 0]] - points[triangles[:, 1]], axis=1)) * unit_mm) if len(triangles) else 0.0
    for _ in range(opt["levels"]):
        points, triangles = subdivide(points, triangles)
    count = len(points)
    depth, partner = np.zeros(count), np.full(count, -1)
    for index, name in enumerate(solids):
        vote, near = inside(name, points)
        own = np.where(vote > 0.5, near, 0.0) * unit_mm
        better = own > depth
        depth[better], partner[better] = own[better], index
    buried = depth > opt["tolerance_mm"]
    area = np.linalg.norm(np.cross(points[triangles[:, 1]] - points[triangles[:, 0]],
                                   points[triangles[:, 2]] - points[triangles[:, 0]]), axis=1) / 2 * unit_mm * unit_mm
    vertex_area = np.zeros(count)
    for corner in range(3):
        np.add.at(vertex_area, triangles[:, corner], area / 3)
    edges = np.unique(np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1), axis=0)
    islands, stretches = _Sets(count), _Sets(count)
    same = buried[edges[:, 0]] == buried[edges[:, 1]]
    for (a, b), keep in zip(edges.tolist(), same.tolist()):
        islands.union(a, b)
        if keep:
            stretches.union(a, b)
    island, stretch = islands.labels(), stretches.labels()
    island_area = np.bincount(island, weights=vertex_area, minlength=count)
    island_inside = np.bincount(island, weights=vertex_area * buried, minlength=count)
    stretch_area = np.bincount(stretch, weights=vertex_area, minlength=count)
    # entries: edges with one end inside; each mixed triangle joins its two crossing edges into a chain
    crossing = edges[~same]
    index_of = {tuple(e): i for i, e in enumerate(crossing.tolist())}
    chains = _Sets(len(crossing))
    marks_all = []
    mixed = triangles[(buried[triangles].sum(1) % 3) != 0]
    for tri in mixed.tolist():
        found = [index_of[e] for e in (tuple(sorted((tri[0], tri[1]))), tuple(sorted((tri[1], tri[2]))), tuple(sorted((tri[2], tri[0])))) if e in index_of]
        for other in found[1:]:
            chains.union(found[0], other)
        if len(found) == 2:
            marks_all.append(found)
    chain = chains.labels() if len(crossing) else np.zeros(0, np.int64)
    cut = (points[crossing[:, 0]] + points[crossing[:, 1]]) / 2 if len(crossing) else np.zeros((0, 3))
    a_inside = buried[crossing[:, 0]] if len(crossing) else np.zeros(0, bool)
    inner = np.where(a_inside, crossing[:, 0], crossing[:, 1]) if len(crossing) else np.zeros(0, np.int64)
    outer = np.where(a_inside, crossing[:, 1], crossing[:, 0]) if len(crossing) else np.zeros(0, np.int64)
    escape = np.asarray(visible(cut), bool) if len(cut) else np.zeros((0, len(directions)), bool)
    seen = escape.sum(1) >= opt["seen_directions"]
    marks_all = np.array(marks_all, np.int64).reshape(-1, 2)
    info = {"part": part, "islands": int(len(np.unique(island))), "median_edge_mm": round(edge0, 1), "check_points": int(count),
            "area_cm2": round(float(vertex_area.sum()) / 100, 1),
            "inside_area_percent": round(100 * float(vertex_area[buried].sum() / max(vertex_area.sum(), 1e-12)), 2)}
    items, marks = [], []

    def segments_of(rows):
        if not len(marks_all) or not len(rows):
            return np.zeros((0, 2, 3))
        chosen = np.zeros(len(crossing), bool)
        chosen[rows] = True
        use = marks_all[chosen[marks_all[:, 0]] & chosen[marks_all[:, 1]]]
        return np.stack([cut[use[:, 0]], cut[use[:, 1]]], axis=1)

    for key in np.unique(stretch[buried]):
        member = stretch == key
        rows = np.nonzero(stretch[inner] == key)[0]
        loops = np.unique(chain[rows])
        widths = [float(np.linalg.norm(cut[rows[chain[rows] == c]].max(0) - cut[rows[chain[rows] == c]].min(0)) * unit_mm) for c in loops]
        home = island[np.nonzero(member)[0][0]]
        body = points[member]
        measured = {"entry_points": int(len(rows)), "entries": int(len(loops)),
                    "visible_share": float(seen[rows].mean()) if len(rows) else 0.0,
                    "depth_mm": float(depth[member].max()),
                    "extent_mm": float(np.linalg.norm(body.max(0) - body.min(0)) * unit_mm),
                    "entry_width_mm": max(widths) if widths else 0.0,
                    "island_area_cm2": float(island_area[home]) / 100,
                    "island_inside_share": float(island_inside[home] / max(island_area[home], 1e-12))}
        advice, reason = advise_stretch(measured, opt)
        owners = partner[member]
        item = {"part": part, "partner": solids[int(np.bincount(owners[owners >= 0]).argmax())], "advice": advice, "reason": reason,
                "center": _round(body.mean(0)), "buried_area_cm2": round(float(stretch_area[key]) / 100, 2),
                "buried_extent_mm": round(measured["extent_mm"], 1), "depth_mm": round(measured["depth_mm"], 1),
                "entries": measured["entries"], "entry_width_mm": round(measured["entry_width_mm"], 1),
                "visible_entry_percent": round(100 * measured["visible_share"]),
                "island_area_cm2": round(measured["island_area_cm2"], 1),
                "island_inside_percent": round(100 * measured["island_inside_share"]),
                "view": _round(_best_view(escape[rows], np.ones(len(rows)), directions), 3),
                "_score": float(seen[rows].sum()) * float(stretch_area[key]) ** 0.5}
        if len(rows):
            item["entry_center"] = _round(cut[rows].mean(0))
            item["entry_size_mm"] = round(float(np.linalg.norm(cut[rows].max(0) - cut[rows].min(0)) * unit_mm), 1)
        items.append(item)
        marks.append((item, segments_of(rows)))
    # scraps: small outside patches whose surroundings are buried (they show as flakes on the skin)
    for key in np.unique(stretch[~buried]):
        if not 0 < stretch_area[key] < opt["scrap_cm2"] * 100:
            continue
        rows = np.nonzero(stretch[outer] == key)[0]
        if not len(rows):
            continue
        shown = float(seen[rows].mean())
        owners = partner[inner[rows]]
        item = {"part": part, "partner": solids[int(np.bincount(owners[owners >= 0]).argmax())],
                "advice": "delete_scrap" if shown >= opt["hidden_share"] else "leave",
                "reason": "an outside flake of %.1f cm2 whose surroundings are buried: remove it or push it in" % (stretch_area[key] / 100),
                "center": _round(points[stretch == key].mean(0)), "scrap_area_cm2": round(float(stretch_area[key]) / 100, 2),
                "depth_mm": round(float(depth[inner[rows]].max()), 1), "visible_entry_percent": round(100 * shown),
                "view": _round(_best_view(escape[rows], np.ones(len(rows)), directions), 3),
                "entry_center": _round(cut[rows].mean(0)),
                "entry_size_mm": round(float(np.linalg.norm(cut[rows].max(0) - cut[rows].min(0)) * unit_mm), 1),
                "_score": float(seen[rows].sum()) * 3.0}
        items.append(item)
        marks.append((item, segments_of(rows)))
    return info, items, marks


def finish_advice(infos, items, options, unit_mm):
    items.sort(key=lambda item: -item.pop("_score"))
    counts = {name: 0 for name in ADVICE}
    for index, item in enumerate(items):
        item["id"] = index + 1
        counts[item["advice"]] += 1
    todo = sum(v for k, v in counts.items() if k != "leave")
    warnings = ["%d buried stretches need a repair decision; see items" % todo] if todo else []
    coarse = [i["part"] for i in infos if i["median_edge_mm"] > 10.0]
    notes = ["The median edge of %s is coarse; subdivide locally before a push repair" % ", ".join(coarse)] if coarse else []
    return {"unit": "mm", "unit_mm": unit_mm, "options": resolve_options(options), "parts": infos,
            "summary": {k: v for k, v in counts.items() if v}, "items": items, "warnings": warnings, "notes": notes}


def compare_reports(before, after, options=None):
    """Match the spots of two check reports; list new, gone and changed ones."""
    opt = resolve_options(options)
    for name, report in (("before", before), ("after", after)):
        if report.get("schema") != REPORT_SCHEMA or report.get("command") != "check":
            raise ValueError(name + " is not a check report of this tool")
    unit = float(after.get("unit_mm", 1000.0))
    old = [s for s in before["spots"] if not s["allowed"]]
    new = [s for s in after["spots"] if not s["allowed"]]
    used, rows = set(), []
    for spot in new:
        best, best_distance = None, opt["match_mm"]
        for index, other in enumerate(old):
            if index in used or (other["part"], other["partner"]) != (spot["part"], spot["partner"]):
                continue
            distance = float(np.linalg.norm(np.array(other["center"]) - np.array(spot["center"])) * unit)
            if distance <= best_distance:
                best, best_distance = index, distance
        if best is None:
            rows.append({"change": "new", "after_id": spot["id"], "part": spot["part"], "partner": spot["partner"],
                         "center": spot["center"], "visible_curve_mm": spot["visible_curve_mm"]})
            continue
        used.add(best)
        delta = round(spot["visible_curve_mm"] - old[best]["visible_curve_mm"], 1)
        change = "worse" if delta > opt["grow_mm"] else "better" if delta < -opt["grow_mm"] else "same"
        rows.append({"change": change, "before_id": old[best]["id"], "after_id": spot["id"], "part": spot["part"],
                     "partner": spot["partner"], "center": spot["center"], "visible_curve_mm": spot["visible_curve_mm"],
                     "visible_curve_change_mm": delta})
    for index, other in enumerate(old):
        if index not in used:
            rows.append({"change": "gone", "before_id": other["id"], "part": other["part"], "partner": other["partner"],
                         "center": other["center"], "visible_curve_mm_before": other["visible_curve_mm"]})
    counts = {}
    for row in rows:
        counts[row["change"]] = counts.get(row["change"], 0) + 1
    visible_new = [r for r in rows if r["change"] == "new" and r["visible_curve_mm"] > opt["visible_spot_mm"]]
    warnings = []
    if visible_new or counts.get("worse"):
        warnings.append("%d new visible spots and %d grown spots after the change" % (len(visible_new), counts.get("worse", 0)))
    return {"unit": "mm", "summary": {"changes": counts,
                                      "visible_curve_mm_before": before["summary"]["visible_curve_mm"],
                                      "visible_curve_mm_after": after["summary"]["visible_curve_mm"],
                                      "visible_spots_before": before["summary"]["visible_spots"],
                                      "visible_spots_after": after["summary"]["visible_spots"]},
            "changes": sorted(rows, key=lambda r: ("new", "worse", "same", "better", "gone").index(r["change"])),
            "warnings": warnings}


# ---------------------------------------------------------------- Blender side

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("check and advise need Blender Python; compare and the numeric core work in ordinary Python") from error
    return bpy


def _unit_mm():
    scale = float(_bpy().context.scene.unit_settings.scale_length)
    return (scale if scale > 0 else 1.0) * 1000.0


def _evaluated(obj, depsgraph):
    """World-space points and triangles of the evaluated mesh (modifiers and pose included)."""
    if obj is None or obj.type != "MESH":
        raise ValueError("Not a mesh object: " + (obj.name if obj else "None"))
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        flat = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", flat)
        matrix = np.array(evaluated.matrix_world)
        points = flat.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
        corners = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("vertices", corners)
    finally:
        evaluated.to_mesh_clear()
    triangles, open_edges = clean_triangles(points, corners.reshape(-1, 3))
    return points, triangles, open_edges


class _Scene:
    """Evaluated meshes, BVH trees and the ray callbacks the core needs."""

    def __init__(self, names, options):
        from mathutils.bvhtree import BVHTree
        bpy = _bpy()
        self.options = options
        self.unit = _unit_mm()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        self.meshes, self.open_edges, self.trees = {}, {}, {}
        for name in names:
            obj = bpy.context.scene.objects.get(name)
            if obj is None:
                raise ValueError("Object not found: " + name)
            points, triangles, open_edges = _evaluated(obj, depsgraph)
            if not len(triangles):
                raise ValueError("Object has no faces: " + name)
            self.meshes[name], self.open_edges[name] = (points, triangles), open_edges
            self.trees[name] = BVHTree.FromPolygons(points.tolist(), triangles.tolist())
        all_points, all_triangles, offset = [], [], 0
        for obj in bpy.context.scene.objects:
            if obj.type != "MESH" or obj.hide_render:
                continue
            points, triangles = self.meshes[obj.name] if obj.name in self.meshes else _evaluated(obj, depsgraph)[:2]
            if len(triangles):
                all_points.append(points)
                all_triangles.append(triangles + offset)
                offset += len(points)
        self.everything = BVHTree.FromPolygons(np.concatenate(all_points).tolist(), np.concatenate(all_triangles).tolist())
        self.view = sphere_dirs(options["view_directions"])
        self.vote = sphere_dirs(options["vote_directions"])

    def overlap(self, part, partner):
        return self.trees[part].overlap(self.trees[partner])

    def _vote(self, tree, points, directions):
        from mathutils import Vector
        result = np.zeros(len(points))
        for row, point in enumerate(points):
            odd = 0
            for direction in directions:
                origin, ray, hits = Vector(point), Vector(direction), 0
                while hits < 40:
                    location = tree.ray_cast(origin, ray)[0]
                    if location is None:
                        break
                    hits += 1
                    origin = location + ray * 1e-5
                odd += hits & 1
            result[row] = odd / len(directions)
        return result

    def inside(self, partner, points):
        from mathutils import Vector
        tree = self.trees[partner]
        near = np.array([tree.find_nearest(Vector(p))[3] for p in points])
        close = near * self.unit < self.options["reach_mm"]
        vote = np.zeros(len(points))
        vote[close] = self._vote(tree, points[close], self.vote)
        if (~close).any():
            vote[~close] = self._vote(tree, points[~close], self.vote[:3])
        return vote, near

    def visible(self, points):
        from mathutils import Vector
        start = 0.6 / self.unit
        result = np.zeros((len(points), len(self.view)), bool)
        for row, point in enumerate(points):
            for column, direction in enumerate(self.view):
                ray = Vector(direction)
                result[row, column] = self.everything.ray_cast(Vector(point) + ray * start, ray)[0] is None
        return result


def _names(objects):
    return [obj if isinstance(obj, str) else obj.name for obj in objects]


def check(parts, solid=(), thin=(), allow=(), options=None):
    """Return (report, marks) for the current scene state. Nothing in the scene changes."""
    opt = resolve_options(options)
    parts, solid, thin, allow = _names(parts), _names(solid), _names(thin), set(_names(allow))
    if not parts or not (solid or thin):
        raise ValueError("Give at least one part and one partner")
    if set(solid) & set(thin):
        raise ValueError("A partner is either solid or thin, not both")
    scene = _Scene(parts + [n for n in solid + thin if n not in parts], opt)
    partners = {name: scene.meshes[name] + ("solid" if name in solid else "thin", name in allow) for name in solid + thin}
    report, marks = analyse_contacts({name: scene.meshes[name] for name in parts}, partners, scene.overlap,
                                     scene.inside, scene.visible, opt, scene.unit)
    report["open_edges"] = {name: scene.open_edges[name] for name in solid}
    return _finish(report, "check", parts, solid + thin), marks


def advise(parts, solid, options=None):
    """Return (report, marks): one repair suggestion per buried stretch. Nothing in the scene changes."""
    opt = resolve_options(options)
    parts, solid = _names(parts), _names(solid)
    if not parts or not solid:
        raise ValueError("Give at least one part and one solid partner")
    scene = _Scene(parts + [n for n in solid if n not in parts], opt)
    infos, items, marks = [], [], []
    for name in parts:
        info, found, found_marks = analyse_buried(name, *scene.meshes[name], [s for s in solid if s != name],
                                                  scene.inside, scene.visible, opt, scene.unit)
        infos.append(info)
        items.extend(found)
        marks.extend(found_marks)
    report = finish_advice(infos, items, opt, scene.unit)
    report["open_edges"] = {name: scene.open_edges[name] for name in solid}
    return _finish(report, "advise", parts, solid), marks


def _finish(report, command, parts, partners):
    report.update({"schema": REPORT_SCHEMA, "command": command, "parts": report.get("parts", parts) if command == "advise" else parts,
                   "partners": partners, "unverified": list(UNVERIFIED)})
    report["status"] = "completed_with_findings" if report["warnings"] else "completed"
    return report


MARK_COLORS = {"spot": (1.0, 0.0, 0.05, 1.0), "delete": (1.0, 0.0, 0.0, 1.0), "delete_scrap": (1.0, 0.0, 0.0, 1.0),
               "trim": (1.0, 0.45, 0.0, 1.0), "pull_tip": (1.0, 0.9, 0.0, 1.0), "push": (0.0, 0.8, 0.2, 1.0),
               "reroute_or_cut": (0.8, 0.0, 1.0, 1.0)}


def render_marks(marks, folder, top=24, size=700):
    """Draw the marks as coloured tubes and render one close view per entry plus four overviews.

    Adds a camera, a world and curve objects to the open scene in memory. Call it only in a process
    that will not save the file. Returns {id: image name}.
    """
    import bmesh
    from mathutils import Vector
    bpy = _bpy()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light, shading.color_type, shading.show_cavity = "STUDIO", "TEXTURE", True
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("lida_penetration_world")
    scene.world.color = (0.2, 0.2, 0.2)
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.view_settings.view_transform = "Standard"
    camera = bpy.data.objects.new("lida_penetration_camera", bpy.data.cameras.new("lida_penetration_camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type, camera.data.clip_start, camera.data.clip_end = "ORTHO", 0.001, 100.0
    groups = {}
    for entry, segments in marks:
        if len(segments) and entry.get("advice") != "leave":
            groups.setdefault(entry.get("advice", "spot"), []).append(segments)
    tubes = []
    for kind, pieces in groups.items():
        builder = bmesh.new()
        for a, b in np.concatenate(pieces):
            builder.edges.new((builder.verts.new(a), builder.verts.new(b)))
        mesh = bpy.data.meshes.new("lida_penetration_" + kind)
        builder.to_mesh(mesh)
        builder.free()
        obj = bpy.data.objects.new("lida_penetration_" + kind, mesh)
        scene.collection.objects.link(obj)
        for other in bpy.context.selected_objects:
            other.select_set(False)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.convert(target="CURVE")
        obj = bpy.context.view_layer.objects.active
        material = bpy.data.materials.new("lida_penetration_" + kind)
        material.diffuse_color = MARK_COLORS[kind]
        obj.data.materials.append(material)
        tubes.append(obj)

    def shot(name, center, direction, scale):
        direction = Vector(direction).normalized()
        camera.location = Vector(center) + direction * 5.0
        camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = scale
        for tube in tubes:                              # keep the marks readable at every zoom
            tube.data.bevel_depth = scale / 260.0
        scene.render.filepath = str(folder / name)
        bpy.ops.render.render(write_still=True)

    images = {}
    shown = [(entry, segments) for entry, segments in marks if len(segments) and entry.get("advice") != "leave"]
    for entry, segments in sorted(shown, key=lambda item: item[0]["id"])[:top]:
        ends = segments.reshape(-1, 3)
        extent = float(np.linalg.norm(ends.max(0) - ends.min(0)))
        name = "%s_%03d.jpg" % ("item" if "advice" in entry else "spot", entry["id"])
        shot(name, (ends.max(0) + ends.min(0)) / 2, entry["view"], min(max(0.09, extent * 1.7), 0.45))
        images[entry["id"]] = name
    corners = []
    for obj in scene.objects:
        if obj.type == "MESH" and not obj.hide_render:
            matrix = np.array(obj.matrix_world)
            corners.append(np.array(obj.bound_box) @ matrix[:3, :3].T + matrix[:3, 3])
    corners = np.concatenate(corners)
    center, span = (corners.max(0) + corners.min(0)) / 2, float((corners.max(0) - corners.min(0)).max()) * 1.05
    for name, direction in (("front", (0, -1, 0)), ("back", (0, 1, 0)), ("left", (1, 0, 0)), ("right", (-1, 0, 0))):
        shot("overview_%s.jpg" % name, center, direction, span)
    return images


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


def _read_report(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError("Report not found: " + path.name)
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "advise"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
        sub.add_argument("--parts", nargs="+", required=True, help="meshes to examine (hair, ribbons, cloth)")
        sub.add_argument("--solid", nargs="+", default=[] if command == "check" else None, required=command == "advise",
                         help="closed partners (body, head, tail): depth is measured")
        sub.add_argument("--report", required=True, type=Path)
        sub.add_argument("--render-dir", type=Path, help="new folder for close views of the findings")
        sub.add_argument("--top", type=int, default=24, help="number of close views")
        sub.add_argument("--frame", type=int, help="evaluate this frame instead of the saved one")
        sub.add_argument("--tolerance-mm", type=float)
        sub.add_argument("--view-directions", type=int)
        sub.add_argument("--vote-directions", type=int)
        sub.add_argument("--seen-directions", type=int)
        if command == "check":
            sub.add_argument("--thin", nargs="+", default=[], help="open or thin partners (fins, chains): curves only")
            sub.add_argument("--allow", nargs="+", default=[], help="partners whose crossings are intended; listed apart")
            sub.add_argument("--cluster-mm", type=float)
            sub.add_argument("--visible-spot-mm", type=float)
        else:
            for key in ("levels", "reach_mm", "shallow_mm", "tip_extent_mm", "push_ratio", "push_max_mm", "hidden_share",
                        "small_island_cm2", "island_inside_share", "scrap_cm2"):
                sub.add_argument("--" + key.replace("_", "-"), type=int if key == "levels" else float)
    sub = commands.add_parser("compare")
    sub.add_argument("--before", required=True, type=Path)
    sub.add_argument("--after", required=True, type=Path)
    sub.add_argument("--report", required=True, type=Path)
    sub.add_argument("--match-mm", type=float)
    sub.add_argument("--grow-mm", type=float)
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
        options = {key: getattr(args, key) for key in DEFAULTS if getattr(args, key, None) is not None}
        if args.command == "compare":
            report = compare_reports(_read_report(args.before), _read_report(args.after), options)
            report.update({"schema": REPORT_SCHEMA, "command": "compare", "before": args.before.name, "after": args.after.name,
                           "status": "completed_with_findings" if report["warnings"] else "completed"})
        else:
            source = args.input.expanduser().resolve()
            if not source.is_file() or source.suffix.lower() != ".blend":
                raise ValueError("Input must be an existing .blend file")
            if source == report_path:
                raise ValueError("Report must differ from input")
            folder = _new_output(args.render_dir) if args.render_dir else None
            before_sha = _file_hash(source)
            bpy = _bpy()
            if not bpy.app.background:
                raise ValueError("Run the CLI in a separate Blender background process; use API functions in an interactive session")
            bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
            if args.frame is not None:
                bpy.context.scene.frame_set(args.frame)
            if args.command == "check":
                report, marks = check(args.parts, args.solid, args.thin, args.allow, options)
            else:
                report, marks = advise(args.parts, args.solid, options)
            report["frame"] = int(bpy.context.scene.frame_current)
            if folder is not None:
                folder.mkdir()
                images = render_marks(marks, folder, args.top)
                for entry in report["spots" if args.command == "check" else "items"]:
                    if entry["id"] in images:
                        entry["image"] = images[entry["id"]]
                report["images"] = {"folder": folder.name, "overviews": ["overview_front.jpg", "overview_back.jpg",
                                                                          "overview_left.jpg", "overview_right.jpg"]}
            if _file_hash(source) != before_sha:
                raise RuntimeError("Input SHA changed during command")
            report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
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
