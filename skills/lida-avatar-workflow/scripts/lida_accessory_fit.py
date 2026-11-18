# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Fit a ring-like accessory to a body part by radial moves only; no registration or import side effects.

Run in Blender with ``--background --factory-startup --python THIS.py -- COMMAND``.
measure: --input MODEL.blend --accessory Acc --partners Head Hair (--axis X Y Z | --axis-from partner|accessory)
         --report NEW.json
fit:     same, with --output-blend NEW.blend (the source object stays; a fitted copy is added).

Method. Distances are taken against a smooth enclosing outline R(azimuth, height) of the partner
meshes in ring coordinates, not against raw faces. The placement (position, direction, size) decided
by a person is kept. Only the distance from the ring axis changes, as a smooth function of azimuth;
the height along the axis never changes, so arches keep their shape. The band (inner contact line)
is brought to the target gap; everything else is only pushed out where it enters the outline.

The numeric core needs numpy only and runs in ordinary Python. Python API functions return reports
without writing files; only fit_copy() adds an in-memory copy. main() alone opens an explicitly
named blend and writes a new report/candidate. It never saves the input or user preferences.
Exit codes: 0 completed; 2 completed with warnings (remaining penetration, large stretch, doubtful
outline) or refused (the move would exceed the stretch limit; no candidate is written); 1 invalid input, I/O or execution error. A report is a measurement, not an appearance grade.
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


REPORT_SCHEMA = "lida.accessory-fit.report.v1"
DEFAULTS = {
    "gap_mm": 1.2,              # target gap of the band's inner contact line
    "floor_mm": 0.4,            # points outside the band are pushed out until at least this far
    "band_axial": 1.0,          # share of each azimuth's axial extent that counts as band (1 = all)
    "band_side": "low",         # which axial end the band sits at when band_axial < 1
    "band_depth_mm": None,      # radial thickness of the contact line; None = 3 % of the band radius
    "push_only": False,         # never pull the band inward
    "rigid_islands_mm": 0.0,    # connected pieces smaller than this move as one piece (0 = off)
    "reach_mm": 40.0,           # rays start this far outside the band
    "backfaces": "keep",        # keep: first hit of any face; skip: walk through faces seen from behind
    "grid_theta": 180,
    "grid_height": 64,
    "sectors": 72,
    "height_bins": 10,
    "iterations": 10,
    "closed_gap_deg": 30.0,     # an empty azimuth range wider than this makes the accessory an open arc
    "inside_tolerance_mm": 0.5,
    "stretch_warning": 0.15,    # warn when the largest move exceeds this share of the band radius
    "stretch_limit": 0.5,       # beyond this share no candidate is produced: the placement does not match
}
UNVERIFIED = [
    "appearance in renders from several directions (shape of pearls, spikes and arches after the move)",
    "evaluated geometry: modifiers, armature pose and shape keys (base mesh data in world space is used)",
    "custom normals, UV texel stretch and texture look after the radial move",
    "contact with other accessories and with partner parts outside the outline grid",
    "other poses, animation, secondary motion and skin weights of the fitted copy",
    "exported files and behavior in the target application",
]


# ---------------------------------------------------------------- numeric core (numpy only)

def _unit(vector, name):
    vector = np.asarray(vector, dtype=float).reshape(-1)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError(name + " must be three finite numbers")
    length = float(np.linalg.norm(vector))
    if length < 1e-12:
        raise ValueError(name + " must not be zero")
    return vector / length


def ring_frame(axis, front=(0.0, -1.0, 0.0)):
    """Return (e0, e1, a): azimuth 0 points to ``front`` projected off the axis, +90 deg is a x e0."""
    a = _unit(axis, "axis")
    f = _unit(front, "front")
    e0 = f - a * float(f @ a)
    if np.linalg.norm(e0) < 1e-6:
        for candidate in ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)):
            e0 = np.array(candidate) - a * float(np.array(candidate) @ a)
            if np.linalg.norm(e0) > 1e-6:
                break
    e0 = e0 / np.linalg.norm(e0)
    return e0, np.cross(a, e0), a


def to_ring(points, center, frame):
    e0, e1, a = frame
    d = np.asarray(points, dtype=float) - np.asarray(center, dtype=float)
    x, y = d @ e0, d @ e1
    return np.arctan2(y, x), d @ a, np.hypot(x, y)


def from_ring(theta, height, radius, center, frame):
    e0, e1, a = frame
    return (np.asarray(center, dtype=float) + np.outer(height, a)
            + np.outer(radius * np.cos(theta), e0) + np.outer(radius * np.sin(theta), e1))


def _wrap(angle):
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def gauss_smooth(values, sigma, periodic):
    values = np.asarray(values, dtype=float)
    if sigma <= 0 or len(values) < 2:
        return values.copy()
    reach = int(3 * sigma) + 1
    kernel = np.exp(-0.5 * (np.arange(-reach, reach + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    index = np.arange(-reach, len(values) + reach)
    index = index % len(values) if periodic else np.clip(index, 0, len(values) - 1)
    return np.convolve(values[index], kernel, mode="valid")


class Outline:
    """Smooth enclosing radius R(theta, height) of the partner around the ring axis."""

    def __init__(self, radius, raw, h0, h1, r_start, misses, backfaces):
        self.radius, self.raw = radius, raw
        self.h0, self.h1, self.r_start = float(h0), float(h1), float(r_start)
        self.miss_ratio, self.backface_ratio = float(misses), float(backfaces)
        nt, nh = radius.shape
        d_theta = (np.roll(radius, -1, axis=0) - np.roll(radius, 1, axis=0)) / (4.0 * np.pi / nt)
        d_height = np.gradient(radius, (self.h1 - self.h0) / max(nh - 1, 1), axis=1) if nh > 1 else np.zeros_like(radius)
        tangent = d_theta / np.maximum(radius, 1e-9)
        # radial gap / slope = first-order distance along the outline normal; capped where the surface ends
        self.slope = np.minimum(np.sqrt(1.0 + d_height ** 2 + np.where(radius > 1e-9, tangent, 0.0) ** 2), 4.0)

    def _bilinear(self, grid, theta, height):
        nt, nh = grid.shape
        f = (np.asarray(theta) + np.pi) / (2.0 * np.pi) * nt
        i0 = np.floor(f).astype(int)
        ft = f - i0
        i0, i1 = i0 % nt, (i0 + 1) % nt
        g = np.clip((np.asarray(height) - self.h0) / max(self.h1 - self.h0, 1e-12) * (nh - 1), 0, nh - 1)
        j0 = np.minimum(np.floor(g).astype(int), max(nh - 2, 0))
        gt = g - j0
        j1 = np.minimum(j0 + 1, nh - 1)
        return (grid[i0, j0] * (1 - ft) * (1 - gt) + grid[i1, j0] * ft * (1 - gt)
                + grid[i0, j1] * (1 - ft) * gt + grid[i1, j1] * ft * gt)

    def sample(self, theta, height):
        return self._bilinear(self.radius, theta, height)

    def distance(self, theta, height, radius):
        """Signed distance estimate to the outline (outside positive) and the slope factor used."""
        slope = self._bilinear(self.slope, theta, height)
        return (radius - self.sample(theta, height)) / slope, slope


def _neighbor_stack(grid):
    up = np.concatenate([grid[:, :1], grid[:, :-1]], axis=1)
    down = np.concatenate([grid[:, 1:], grid[:, -1:]], axis=1)
    return np.stack([np.roll(grid, 1, axis=0), np.roll(grid, -1, axis=0), up, down])


def build_outline(cast, center, frame, h0, h1, r_start, grid_theta=180, grid_height=64, dilate=1, smooth=8):
    """Cast rays from outside toward the axis; the first hit is the outermost surface.

    ``cast(origins, directions, max_distance)`` returns (distances, backface_flags); a miss is NaN.
    Cells are widened to the largest neighbour (features between rays are not lost) and then
    smoothed without ever going below that widened value, so the outline encloses the real surface.
    """
    if h1 <= h0 or r_start <= 0:
        raise ValueError("Outline needs a positive height range and start radius")
    theta = -np.pi + 2.0 * np.pi * np.arange(grid_theta) / grid_theta
    height = np.linspace(h0, h1, grid_height)
    tt, hh = np.meshgrid(theta, height, indexing="ij")
    origins = from_ring(tt.ravel(), hh.ravel(), np.full(tt.size, r_start), center, frame)
    e0, e1, _ = frame
    directions = -(np.outer(np.cos(tt.ravel()), e0) + np.outer(np.sin(tt.ravel()), e1))
    distance, backface = cast(origins, directions, float(r_start))
    distance = np.asarray(distance, dtype=float)
    miss = ~np.isfinite(distance)
    raw = np.where(miss, 0.0, r_start - np.where(miss, 0.0, distance)).reshape(tt.shape)
    raw = np.clip(raw, 0.0, r_start)
    base = raw.copy()
    for _ in range(dilate):
        base = np.maximum(base, _neighbor_stack(base).max(axis=0))
    radius = base.copy()
    for _ in range(smooth):
        radius = np.maximum(0.5 * radius + 0.5 * _neighbor_stack(radius).mean(axis=0), base)
    backface = np.asarray(backface, dtype=bool)
    return Outline(radius, raw, h0, h1, r_start, miss.mean(), backface[~miss].mean() if (~miss).any() else 0.0)


def fit_circle_center(x, y):
    """Algebraic circle fit; works for arcs as well as full rings."""
    design = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    solution, *_ = np.linalg.lstsq(design, x * x + y * y, rcond=None)
    return float(solution[0]), float(solution[1])


def accessory_center(points, frame, rounds=4):
    """Centre of the inner contact line: repeated circle fits to the innermost points per azimuth."""
    e0, e1, a = frame
    center = np.median(points, axis=0)
    for _ in range(rounds):
        theta, _, radius = to_ring(points, center, frame)
        sector = np.clip(((theta + np.pi) / (2 * np.pi) * 24).astype(int), 0, 23)
        inner = np.zeros(len(points), bool)
        for k in range(24):
            index = np.where(sector == k)[0]
            if len(index) >= 4:
                inner[index[radius[index] <= np.quantile(radius[index], 0.2)]] = True
        if inner.sum() < 8:
            break
        d = points[inner] - center
        cx, cy = fit_circle_center(d @ e0, d @ e1)
        center = center + cx * e0 + cy * e1
    return center - a * float((center - np.median(points, axis=0)) @ a)


def principal_axes(points):
    centered = points - points.mean(axis=0)
    values, vectors = np.linalg.eigh(centered.T @ centered / max(len(points), 1))
    return values, vectors                      # ascending variance; columns are directions


class _Layout:
    """Azimuth sectors of the accessory. Open arcs are shifted so their empty range sits at the seam."""

    def __init__(self, theta, sectors, closed_gap_deg, min_points=3):
        width = 2.0 * np.pi / sectors
        occupied = np.bincount(np.clip(((theta + np.pi) / width).astype(int), 0, sectors - 1), minlength=sectors) >= min_points
        if not occupied.any():
            raise ValueError("The accessory has too few points to analyse")
        best_len, best_start = 0, 0
        if not occupied.all():
            doubled = np.concatenate([occupied, occupied])
            run = 0
            for i, flag in enumerate(doubled):
                run = 0 if flag else run + 1
                if run > best_len and run <= sectors:
                    best_len, best_start = run, i - run + 1
        self.gap_deg = best_len * 360.0 / sectors
        self.closed = self.gap_deg < closed_gap_deg
        self.shift = 0.0 if self.closed else _wrap(-np.pi + (best_start + best_len / 2.0) * width) - np.pi
        self.sectors, self.width = sectors, width
        shifted = _wrap(theta - self.shift)
        raw = np.clip(((shifted + np.pi) / width).astype(int), 0, sectors - 1)
        used = np.bincount(raw, minlength=sectors) >= min_points
        self.first = 0 if self.closed else int(np.argmax(used))
        last = sectors - 1 if self.closed else int(sectors - 1 - np.argmax(used[::-1]))
        self.count = last - self.first + 1
        self.sector = np.clip(raw - self.first, 0, self.count - 1)
        self.position = (shifted + np.pi) / width - 0.5 - self.first       # fractional sector coordinate
        self.span_deg = 360.0 if self.closed else self.count * 360.0 / sectors

    def along(self, values, position=None):
        """Linear interpolation of per-sector values at fractional sector positions."""
        position = self.position if position is None else position
        if self.count == 1:
            return np.full(len(position), values[0]) if values.ndim == 1 else np.repeat(values[:1], len(position), 0)
        if self.closed:
            i0 = np.floor(position).astype(int)
            t = position - i0
            i0, i1 = i0 % self.count, (i0 + 1) % self.count
        else:
            p = np.clip(position, 0, self.count - 1)
            i0 = np.minimum(np.floor(p).astype(int), self.count - 2)
            t, i1 = p - i0, i0 + 1
        if values.ndim == 1:
            return values[i0] * (1 - t) + values[i1] * t
        return values[i0] * (1 - t)[:, None] + values[i1] * t[:, None]

    def fill(self, values):
        ok = np.isfinite(values)
        if not ok.any():
            return np.zeros(len(values))
        index = np.arange(len(values))
        if self.closed:
            return np.interp(index, index[ok], values[ok], period=len(values))
        return np.interp(index, index[ok], values[ok])


def band_mask(layout, height, radius, band_axial, band_side, band_depth):
    band = np.zeros(len(height), bool)
    for k in range(layout.count):
        index = np.where(layout.sector == k)[0]
        if len(index) < 3:
            continue
        if band_axial < 1.0:
            if band_side == "high":
                index = index[height[index] >= np.quantile(height[index], 1.0 - band_axial)]
            else:
                index = index[height[index] <= np.quantile(height[index], band_axial)]
        inner = np.quantile(radius[index], 0.05)
        band[index[radius[index] <= inner + band_depth]] = True
    return band


def solve_radial(layout, height, gap, slope, band, margin, floor, push_only=False, height_bins=10, iterations=10,
                 sigma_band=1.2, sigma_up=(1.0, 0.8)):
    """Radial displacement per point: D(azimuth) for the band plus an outward-only E(azimuth, height).

    ``gap`` is radial (radius minus outline radius); ``gap / slope`` is the distance to the outline.
    Radial moves keep azimuth and height, so the outline radius and slope of each point stay fixed.
    """
    n = layout.count
    D = np.zeros(n)
    for _ in range(iterations):
        missing = margin * slope - (gap + layout.along(D))     # radial move each point still needs
        need = np.full(n, np.nan)
        for k in range(n):
            m = band & (layout.sector == k)
            if m.sum() >= 3:
                need[k] = np.quantile(missing[m], 0.95)       # the closest 5 % define the contact line
        D = D + gauss_smooth(layout.fill(need), sigma_band, layout.closed)
        if push_only:
            D = np.maximum(D, 0.0)
    z0, z1 = float(height.min()), float(height.max()) + 1e-9
    zbin = np.clip(((height - z0) / (z1 - z0) * height_bins).astype(int), 0, height_bins - 1)
    zpos = np.clip((height - z0) / (z1 - z0) * height_bins - 0.5, 0, height_bins - 1)
    j0 = np.minimum(np.floor(zpos).astype(int), max(height_bins - 2, 0))
    j1 = np.minimum(j0 + 1, height_bins - 1)
    zt = zpos - j0
    E = np.zeros((n, height_bins))
    cell = layout.sector * height_bins + zbin

    def upper():
        rows = layout.along(E)
        return rows[np.arange(len(height)), j0] * (1 - zt) + rows[np.arange(len(height)), j1] * zt

    base = gap + layout.along(D)
    for _ in range(iterations):
        worst = np.zeros(n * height_bins)
        np.maximum.at(worst, cell, floor * slope - (base + upper()))
        G = np.maximum(worst, 0.0).reshape(n, height_bins)
        if not G.any():
            break
        Gs = np.stack([gauss_smooth(G[:, j], sigma_up[0], layout.closed) for j in range(height_bins)], axis=1)
        Gs = np.stack([gauss_smooth(Gs[k], sigma_up[1], False) for k in range(n)], axis=0)
        E = E + np.maximum(0.6 * G, Gs)        # keep 60 % of the raw need so smoothing cannot starve a peak
    return layout.along(D) + upper(), D, E


def connected_islands(vertex_count, edges):
    parent = np.arange(vertex_count)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in np.asarray(edges, dtype=int).reshape(-1, 2):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(i) for i in range(vertex_count)])
    _, labels = np.unique(roots, return_inverse=True)
    return labels


def gap_table(theta, gap, mask, unit_mm, step=30):
    rows = []
    degrees = np.degrees(theta)
    for start in range(-180, 180, step):
        m = mask & (degrees >= start) & (degrees < start + step)
        if m.any():
            rows.append({"azimuth_deg": start, "points": int(m.sum()),
                         "min_mm": round(float(gap[m].min() * unit_mm), 2),
                         "median_mm": round(float(np.median(gap[m]) * unit_mm), 2),
                         "max_mm": round(float(gap[m].max() * unit_mm), 2)})
    return rows


def gap_summary(gap, band, tolerance, unit_mm):
    b = gap[band] if band.any() else gap
    return {"band_gap_mm": {"min": float(b.min() * unit_mm), "median": float(np.median(b) * unit_mm),
                            "p95": float(np.quantile(b, 0.95) * unit_mm), "max": float(b.max() * unit_mm)},
            "all_points_inside_ratio": float((gap < -tolerance).mean()),
            "deepest_mm": float(gap.min() * unit_mm), "points": int(len(gap)), "band_points": int(band.sum())}


def resolve_options(options=None):
    resolved = dict(DEFAULTS)
    for key, value in (options or {}).items():
        if key not in DEFAULTS:
            raise ValueError("Unknown option: " + str(key))
        if value is not None:
            resolved[key] = value
    for key in ("gap_mm", "floor_mm", "rigid_islands_mm", "inside_tolerance_mm", "reach_mm", "stretch_warning", "stretch_limit"):
        if not isinstance(resolved[key], (int, float)) or not math.isfinite(resolved[key]) or resolved[key] < 0:
            raise ValueError(key + " must be finite and nonnegative")
    if resolved["reach_mm"] <= 0:
        raise ValueError("reach_mm must be positive")
    if not 0.0 < resolved["band_axial"] <= 1.0:
        raise ValueError("band_axial must be in (0, 1]")
    if resolved["band_side"] not in ("low", "high") or resolved["backfaces"] not in ("keep", "skip"):
        raise ValueError("band_side is low|high and backfaces is keep|skip")
    for key, low in (("grid_theta", 24), ("grid_height", 4), ("sectors", 12), ("height_bins", 1), ("iterations", 1)):
        if not isinstance(resolved[key], int) or resolved[key] < low:
            raise ValueError(key + " must be an integer of at least " + str(low))
    return resolved


def analyse(points, cast, frame, center, options=None, unit_mm=1000.0, edges=None, fit=False, partner_points=None):
    """Measure (and optionally fit) accessory points against the partner outline. Lengths are scene units."""
    opt = resolve_options(options)
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 12 or not np.isfinite(points).all():
        raise ValueError("The accessory needs at least 12 finite points")
    to_units = 1.0 / unit_mm
    center = np.asarray(center, dtype=float)
    theta, height, radius = to_ring(points, center, frame)
    layout = _Layout(theta, opt["sectors"], opt["closed_gap_deg"])
    probe = band_mask(layout, height, radius, opt["band_axial"], opt["band_side"], 0.0)
    band_radius = float(np.median(radius[probe])) if probe.any() else float(np.median(radius))
    depth = opt["band_depth_mm"] * to_units if opt["band_depth_mm"] is not None else 0.03 * band_radius
    band = band_mask(layout, height, radius, opt["band_axial"], opt["band_side"], depth)
    r_start = float(radius[band].max()) + opt["reach_mm"] * to_units
    pad = (float(height.max()) - float(height.min())) * 0.05 + 2.0 * to_units
    outline = build_outline(cast, center, frame, float(height.min()) - pad, float(height.max()) + pad, r_start,
                            opt["grid_theta"], opt["grid_height"])
    tolerance = opt["inside_tolerance_mm"] * to_units
    gap, slope = outline.distance(theta, height, radius)
    report = {
        "options": opt,
        "frame": {"axis": [float(v) for v in frame[2]], "azimuth_zero": [float(v) for v in frame[0]],
                  "center": [float(v) for v in center], "closed_ring": bool(layout.closed),
                  "arc_span_deg": float(layout.span_deg), "largest_empty_azimuth_deg": float(layout.gap_deg),
                  "band_radius_mm": band_radius * unit_mm, "band_depth_mm": depth * unit_mm},
        "outline": {"grid": [opt["grid_theta"], opt["grid_height"]], "ray_start_radius_mm": r_start * unit_mm,
                    "height_range_mm": [outline.h0 * unit_mm, outline.h1 * unit_mm],
                    "miss_ratio": outline.miss_ratio, "first_hit_backface_ratio": outline.backface_ratio,
                    "radius_range_mm": [float(outline.radius.min() * unit_mm), float(outline.radius.max() * unit_mm)]},
        "before": dict(gap_summary(gap, band, tolerance, unit_mm), per_azimuth_band=gap_table(theta, gap, band, unit_mm)),
        "warnings": [],
    }
    warnings = report["warnings"]
    if outline.backface_ratio > 0.05 and opt["backfaces"] == "keep":
        warnings.append("More than 5% of the outline rays first hit a face from behind: a ray may have started inside "
                        "a partner (reduce reach_mm) or partner normals are mixed; inspect before trusting the outline")
    if outline.miss_ratio > 0.5:
        warnings.append("More than half of the outline rays hit nothing: check axis, center and partner names")
    if partner_points is not None and len(partner_points):
        pt, ph, pr = to_ring(np.asarray(partner_points, dtype=float), center, frame)
        near = (ph >= outline.h0) & (ph <= outline.h1) & (pr <= r_start)
        if near.any():
            over = outline.distance(pt[near], ph[near], pr[near])[0]
            report["outline"]["real_points_outside_outline_mm"] = {
                "points": int(near.sum()), "p95": float(max(np.quantile(over, 0.95), 0) * unit_mm),
                "p99": float(max(np.quantile(over, 0.99), 0) * unit_mm), "max": float(max(over.max(), 0) * unit_mm)}
    if not fit:
        if report["before"]["all_points_inside_ratio"] > 0:
            warnings.append("Some accessory points are inside the outline beyond the tolerance")
        return None, report
    move, D, E = solve_radial(layout, height, gap * slope, slope, band, opt["gap_mm"] * to_units, opt["floor_mm"] * to_units,
                              opt["push_only"], opt["height_bins"], opt["iterations"])
    fitted = from_ring(theta, height, radius + move, center, frame)
    islands = {"enabled": False}
    if opt["rigid_islands_mm"] > 0:
        if edges is None:
            raise ValueError("rigid_islands_mm needs mesh edges")
        labels = connected_islands(len(points), edges)
        limit = opt["rigid_islands_mm"] * to_units
        moved = 0
        for label in range(int(labels.max()) + 1):
            index = np.where(labels == label)[0]
            piece = points[index]
            if np.linalg.norm(piece.max(axis=0) - piece.min(axis=0)) > limit:
                continue
            ct, ch, _ = to_ring(piece.mean(axis=0, keepdims=True), center, frame)
            direction = (np.cos(ct[0]) * frame[0] + np.sin(ct[0]) * frame[1])
            amount = float(np.median(move[index]))
            for _ in range(3):                  # rigid shift, then top up if a point still sits below the floor
                candidate = piece + direction * amount
                t2, h2, r2 = to_ring(candidate, center, frame)
                d2, s2 = outline.distance(t2, h2, r2)
                worst = int(np.argmin(d2))
                if d2[worst] >= opt["floor_mm"] * to_units - 1e-9:
                    break
                amount += (opt["floor_mm"] * to_units - d2[worst]) * s2[worst]
            fitted[index] = piece + direction * amount
            moved += 1
        islands = {"enabled": True, "pieces": int(labels.max()) + 1, "moved_rigidly": moved}
    theta2, height2, radius2 = to_ring(fitted, center, frame)
    gap2 = outline.distance(theta2, height2, radius2)[0]
    shift = np.linalg.norm(fitted - points, axis=1)
    ratio = float(shift.max() / max(band_radius, 1e-12))
    scale = (radius + move)[band] / np.maximum(radius[band], 1e-12)
    report["after"] = dict(gap_summary(gap2, band, tolerance, unit_mm), per_azimuth_band=gap_table(theta2, gap2, band, unit_mm))
    report["move"] = {"max_mm": float(shift.max() * unit_mm), "median_mm": float(np.median(shift) * unit_mm),
                      "band_azimuth_shift_mm": [float(D.min() * unit_mm), float(D.max() * unit_mm)],
                      "outward_push_max_mm": float(E.max() * unit_mm),
                      "axial_change_max_mm": float(np.abs(height2 - height).max() * unit_mm),
                      "max_move_over_band_radius": ratio,
                      "band_radius_scale_range": [float(scale.min()), float(scale.max())],
                      "rigid_islands": islands}
    report["refused"] = bool(ratio > opt["stretch_limit"])
    if report["refused"]:
        warnings.append("Refused: the largest move would be %.0f%% of the band radius. The placement, axis or center does "
                        "not match the partner; this tool does not re-place. Place the accessory by hand (or model a "
                        "matching piece) and measure again" % (ratio * 100))
    elif ratio > opt["stretch_warning"]:
        warnings.append("The largest move is %.0f%% of the band radius: the accessory is stretched; check the render and "
                        "consider re-placing it or modelling a piece that follows the partner" % (ratio * 100))
    if report["after"]["all_points_inside_ratio"] > 0.01:
        warnings.append("More than 1% of the points remain inside the outline beyond the tolerance")
    return fitted, report


# ---------------------------------------------------------------- Blender side

def _bpy():
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("This command needs Blender Python; the numeric core also works in ordinary Python") from error
    return bpy


def _mesh(obj, role):
    if obj is None or obj.type != "MESH":
        raise ValueError(role + " must be a mesh object")
    if obj.mode != "OBJECT":
        raise ValueError(role + " must be in Object Mode")
    return obj


def _world_points(obj):
    count = len(obj.data.vertices)
    flat = np.empty(count * 3)
    obj.data.vertices.foreach_get("co", flat)
    matrix = np.array(obj.matrix_world)
    return flat.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]


def _caster(partners, skip_backfaces):
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    trees = []
    for obj in partners:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        bm.normal_update()
        trees.append(BVHTree.FromBMesh(bm))
        bm.free()

    def cast(origins, directions, limit):
        distance = np.full(len(origins), np.nan)
        backface = np.zeros(len(origins), bool)
        for i in range(len(origins)):
            direction = Vector(directions[i])
            best, behind = None, False
            for tree in trees:
                origin, travelled = Vector(origins[i]), 0.0
                for _ in range(16):
                    location, normal, _, dist = tree.ray_cast(origin, direction, limit - travelled)
                    if location is None:
                        break
                    seen_from_behind = normal.dot(direction) > 0
                    if seen_from_behind and skip_backfaces:
                        travelled += dist + 1e-6
                        origin = location + direction * 1e-6
                        continue
                    if best is None or travelled + dist < best:
                        best, behind = travelled + dist, seen_from_behind
                    break
            if best is not None:
                distance[i], backface[i] = best, behind
        return distance, backface

    return cast


def _setup(accessory, partners, axis, axis_from, center, center_from, front, options):
    accessory = _mesh(accessory, "Accessory")
    partners = [_mesh(obj, "Partner") for obj in partners]
    if not partners:
        raise ValueError("Choose at least one explicit partner mesh")
    if accessory.name in {obj.name for obj in partners}:
        raise ValueError("The accessory cannot be its own partner")
    if accessory.data.shape_keys is not None:
        raise ValueError("The accessory has shape keys; fit a copy without keys or handle each key deliberately")
    opt = resolve_options(options)
    points = _world_points(accessory)
    partner_points = np.concatenate([_world_points(obj) for obj in partners])
    middle = np.median(points, axis=0)
    spread = float(np.median(np.linalg.norm(points - middle, axis=1)))
    if axis is not None:
        axis_vector, source = _unit(axis, "axis"), "explicit"
    elif axis_from == "partner":
        near = partner_points[np.linalg.norm(partner_points - middle, axis=1) <= 2.5 * spread]
        if len(near) < 12:
            raise ValueError("Too few partner points near the accessory to estimate an axis; pass --axis")
        axis_vector, source = principal_axes(near)[1][:, 2], "partner principal direction (largest spread near the accessory)"
    elif axis_from == "accessory":
        axis_vector, source = principal_axes(points)[1][:, 0], "accessory principal direction (smallest spread)"
    else:
        raise ValueError("Give an explicit axis or axis_from partner|accessory")
    frame = ring_frame(axis_vector, front)
    cast = _caster(partners, opt["backfaces"] == "skip")
    if center is not None:
        center_point, center_source = np.asarray(center, dtype=float), "explicit"
        if center_point.shape != (3,) or not np.isfinite(center_point).all():
            raise ValueError("center must be three finite numbers")
    else:
        center_point, center_source = accessory_center(points, frame), "circle fit to the accessory's inner points"
        if center_from == "partner":
            theta, height, radius = to_ring(points, center_point, frame)
            start = float(np.quantile(radius, 0.5)) + opt["reach_mm"] / _unit_mm()
            angles = -np.pi + 2 * np.pi * np.arange(180) / 180
            directions = -(np.outer(np.cos(angles), frame[0]) + np.outer(np.sin(angles), frame[1]))
            ring = np.zeros(180)
            for h in np.quantile(height, [0.25, 0.5, 0.75]):
                origins = from_ring(angles, np.full(180, h), np.full(180, start), center_point, frame)
                distance, _ = cast(origins, directions, start)
                ring += np.where(np.isfinite(distance), start - distance, 0.0) / 3.0
            x, y = ring * np.cos(angles), ring * np.sin(angles)
            cross = x * np.roll(y, -1) - np.roll(x, -1) * y
            area = 0.5 * cross.sum()
            if abs(area) > 1e-12:
                cx = ((x + np.roll(x, -1)) * cross).sum() / (6 * area)
                cy = ((y + np.roll(y, -1)) * cross).sum() / (6 * area)
                center_point = center_point + cx * frame[0] + cy * frame[1]
                center_source = "centroid of the partner outline around the accessory"
    edges = None
    if opt["rigid_islands_mm"] > 0:
        flat = np.empty(len(accessory.data.edges) * 2, dtype=np.int32)
        accessory.data.edges.foreach_get("vertices", flat)
        edges = flat.reshape(-1, 2)
    context = {"accessory": accessory.name, "partners": [obj.name for obj in partners],
               "axis_source": source, "center_source": center_source}
    return points, partner_points, cast, frame, center_point, opt, edges, context


def _unit_mm():
    scale = float(_bpy().context.scene.unit_settings.scale_length)
    return (scale if scale > 0 else 1.0) * 1000.0


def _finish(report, command, context):
    report.update({"schema": REPORT_SCHEMA, "command": command, "accessory": context["accessory"],
                   "partners": context["partners"], "unverified": list(UNVERIFIED)})
    report["frame"]["axis_source"] = context["axis_source"]
    report["frame"]["center_source"] = context["center_source"]
    report["status"] = "completed_with_warnings" if report["warnings"] else "completed"
    return report


def measure(accessory, partners, axis=None, axis_from=None, center=None, center_from="accessory",
            front=(0.0, -1.0, 0.0), options=None):
    """Return a gap report. Nothing in the scene changes."""
    points, partner_points, cast, frame, center_point, opt, edges, context = _setup(
        accessory, partners, axis, axis_from, center, center_from, front, options)
    _, report = analyse(points, cast, frame, center_point, opt, _unit_mm(), edges, False, partner_points)
    return _finish(report, "measure", context)


def fit_copy(accessory, partners, axis=None, axis_from=None, center=None, center_from="accessory",
             front=(0.0, -1.0, 0.0), options=None, copy_name=None):
    """Add a fitted copy next to the untouched source object and return (copy, report)."""
    bpy = _bpy()
    points, partner_points, cast, frame, center_point, opt, edges, context = _setup(
        accessory, partners, axis, axis_from, center, center_from, front, options)
    fitted, report = analyse(points, cast, frame, center_point, opt, _unit_mm(), edges, True, partner_points)
    if report["refused"]:
        report = _finish(report, "fit", context)
        report["status"] = "refused"
        return None, report
    name = copy_name or accessory.name + "_fit"
    if name in bpy.data.objects:
        raise ValueError("An object named " + name + " already exists")
    copy = accessory.copy()
    copy.data = accessory.data.copy()
    copy.name = name
    copy.data.name = name
    for collection in accessory.users_collection or [bpy.context.scene.collection]:
        collection.objects.link(copy)
    matrix = np.array(accessory.matrix_world)
    local = (fitted - matrix[:3, 3]) @ np.linalg.inv(matrix[:3, :3]).T
    copy.data.vertices.foreach_set("co", local.ravel())
    copy.data.update()
    copy["lida_accessory_fit_source"] = accessory.name
    report["copy"] = {"source": accessory.name, "candidate": copy.name,
                      "note": "Both objects remain; show one at a time when comparing"}
    return copy, _finish(report, "fit", context)


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


def _save_candidate(path):
    """Blender writes an owned temporary copy; final publication is exclusive."""
    bpy = _bpy()
    descriptor, temporary = tempfile.mkstemp(prefix=".lida-accessory-fit-", suffix=".blend", dir=path.parent)
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
    for command in ("measure", "fit"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
        sub.add_argument("--accessory", required=True)
        sub.add_argument("--partners", nargs="+", required=True)
        sub.add_argument("--report", required=True, type=Path)
        axis = sub.add_mutually_exclusive_group(required=True)
        axis.add_argument("--axis", nargs=3, type=float, metavar=("X", "Y", "Z"))
        axis.add_argument("--axis-from", choices=("partner", "accessory"))
        center = sub.add_mutually_exclusive_group()
        center.add_argument("--center", nargs=3, type=float, metavar=("X", "Y", "Z"))
        center.add_argument("--center-from", choices=("accessory", "partner"), default="accessory")
        sub.add_argument("--front", nargs=3, type=float, default=[0.0, -1.0, 0.0], metavar=("X", "Y", "Z"))
        sub.add_argument("--gap-mm", type=float)
        sub.add_argument("--floor-mm", type=float)
        sub.add_argument("--band-axial", type=float)
        sub.add_argument("--band-side", choices=("low", "high"))
        sub.add_argument("--band-depth-mm", type=float)
        sub.add_argument("--push-only", action="store_true", default=None)
        sub.add_argument("--rigid-islands-mm", type=float)
        sub.add_argument("--reach-mm", type=float)
        sub.add_argument("--backfaces", choices=("keep", "skip"))
        sub.add_argument("--grid-theta", type=int)
        sub.add_argument("--grid-height", type=int)
        sub.add_argument("--sectors", type=int)
        sub.add_argument("--inside-tolerance-mm", type=float)
        sub.add_argument("--stretch-warning", type=float)
        sub.add_argument("--stretch-limit", type=float)
        if command == "fit":
            sub.add_argument("--output-blend", required=True, type=Path)
            sub.add_argument("--copy-name")
            sub.add_argument("--hide-source", action="store_true")
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
        source = args.input.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".blend":
            raise ValueError("Input must be an existing .blend file")
        if source == report_path:
            raise ValueError("Report must differ from input")
        output = None
        if args.command == "fit":
            output = _new_output(args.output_blend)
            if output in (source, report_path) or output.suffix.lower() != ".blend":
                raise ValueError("Candidate must be a distinct new .blend path")
        options = {key: getattr(args, key) for key in DEFAULTS if getattr(args, key, None) is not None}
        before_sha = _file_hash(source)
        bpy = _bpy()
        if not bpy.app.background:
            raise ValueError("Run the CLI in a separate Blender background process; use API functions in an interactive session")
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)

        def find(name, role):
            obj = bpy.context.scene.objects.get(name)
            if obj is None:
                raise ValueError(role + " not found: " + name)
            return obj

        accessory = find(args.accessory, "Accessory")
        partners = [find(name, "Partner") for name in args.partners]
        common = dict(axis=args.axis, axis_from=args.axis_from, center=args.center,
                      center_from=args.center_from, front=args.front, options=options)
        if args.command == "measure":
            report = measure(accessory, partners, **common)
        else:
            copy, report = fit_copy(accessory, partners, copy_name=args.copy_name, **common)
            if copy is not None:
                if args.hide_source:
                    accessory.hide_viewport = accessory.hide_render = True
                    report["copy"]["source_hidden_in_output"] = True
                _save_candidate(output)
                report["output"] = {"name": output.name, "sha256": _file_hash(output)}
        if _file_hash(source) != before_sha:
            raise RuntimeError("Input SHA changed during command")
        report["input"] = {"name": source.name, "sha256": before_sha, "unchanged_after_command": True}
        code = 2 if report["warnings"] else 0
        _write_report(report_path, report)
        print(json.dumps({"command": args.command, "status": report["status"], "report": report_path.name,
                          "exit_code": code}, ensure_ascii=False))
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
