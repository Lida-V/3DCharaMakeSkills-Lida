# Repair broken meshes and complete missing faces or volume

[日本語 / Japanese](../mesh-repair-completion.md)

**Identify the cause and openings to retain, then repair only the necessary region from a healthy boundary.** Closing every hole, welding everything, or subdividing cannot distinguish missing faces, wrong connections, and motion-induced collapse.

[Process index](process-index.md) · [Displacement and fixed regions](adjustment-methods.md) · [Skirts and hidden body](skirt-hidden-modeling.md) · [Deforming topology and weights](mesh-weight.md)

## Define goals and inputs first

Carry over intended use, viewing distance, required motions, and destination from [quality goals](quality-goals.md). Routine work does not need repeated approval.

> Starting example: repair [region] of the input while preserving accepted contours and required openings. Fix [connection loops, excluded shape, materials] and show the changed region and fade width. Compare matched front/side/rear/section views through neutral → intermediate → required maximum → return for steps, inversion, splits, and visible penetration. Finish this stage with attribute remapping and save/reload; record destination verification separately.

- **Original and working copy:** record input version, units, left/right/front/back, reference pose, and dependencies such as bones, keys, and modifiers. Do not fill holes directly in the protected original.
- **Shape references:** accepted front/side/rear and connection close-ups; same pose with clothing visible and hidden.
- **Problem scope:** parts, faces, times, visible directions, fixed boundary, edit range, and smooth return band.
- **Motion/output conditions:** required bends, twists, expressions, onset/return, destination, and export format.

Label undocumented areas as estimates. Deliver repaired model, change-region diagram, matched comparisons, attribute mapping, saved-file/export results, and open items.

## 1. Classify what looks like a hole

![Original repair selection schematic: K1 orientation/display; K2 local missing faces; K3 two-boundary connection; K4 local rebuilding/missing volume; retain intentional openings](../../assets/mesh-repair-selection.png)

The shared Japanese diagram explains repair choice. It is not a successful actual-model repair, recommended counts/layout, or an automatic repair feature. **K1** checks orientation/display, **K2** fills a local gap, **K3** connects matching boundaries, and **K4** rebuilds local topology/volume.

| Observation | First check and repair choice |
| --- | --- |
| Invisible only from behind, or only a dark line (K1) | Inspect plain/wireframe/front-back face displays. If geometry exists and is healthy, fix normals, one-sided display, outline, or image; do not overlay new faces |
| Connected faces have a neutral-shape step/dent | Locally correct coordinates/section and fade displacement toward the fixed boundary. Do not rebuild if existing topology suffices |
| Small missing area enclosed by healthy faces (K2/P1) | Check boundary and surrounding curvature; add a local patch |
| Two boundaries intended to connect are separated (K3/P2) | Establish partners, point correspondence, and loop order; bridge with a face band. For a coincident seam, also compare merging corresponding points |
| Widespread wrong connections, collapse, or slender faces (K4/P3) | Keep a healthy outer boundary and locally rebuild face flow |
| Missing volume such as torso, arm, or scalp base (K4/P3) | Design volume from connection sections and multiple angles. A planar small-hole cap is insufficient |
| Neutral is good but motion tears/collapses | Diagnose bones, weights, face flow, keys, and controls. Do not patch the deformed pose; repair baseline and deformation together if needed |

Waist openings, hems, cuffs, slits, designed mouth/eye openings, thin-cloth edges, and hair-card edges are not defects merely because they are boundaries. Do not weld intentional overlaps between separate parts or locks of hair.

UV seams, material boundaries, and hard-normal boundaries differ from geometric holes. Export may split vertices: if positions/deformation agree and the seam stays shut, point count alone does not establish a hole.

## 2. Establish a healthy boundary in neutral

1. On a duplicate, match reference pose/all-key state and switch plain, wireframe, and face-side displays. If only shading is faulty, use [material diagnosis](accessory-materials.md).
2. Identify backfaces, duplicates, unnecessary internal faces, and connections to wrong layers separately. Do not patch over retained overlapping faces.
3. Select a healthy surrounding boundary with sound position/flow. Preserve its vertices and neighboring faces; mark the rebuild extent with numbers/colors.
4. Inspect front, side, rear, and sections together to decide thickness, curvature, orientation, and layer order. Looking closed in one view is insufficient.
5. Separate coordinate correction on existing topology from adding/removing vertices/faces. The latter includes remapping UVs, weights, keys, etc.

Repair does not require preserving total vertex count. Separate excluded regions to retain from regions to change/remap. If destination or existing-key constraints make rebuilding difficult, explain why and show alternatives first.

## 3. Construct faces from the boundary

![Original boundary-repair schematic: P1 local small-hole patch; P2 connecting matching boundaries; P3 rebuilding inside a healthy perimeter](../../assets/mesh-boundary-repair.png)

In the shared Japanese diagram, **P1** patches a small gap, **P2** bridges matched boundaries, and **P3** locally reconstructs inside preserved healthy edges. Numbers are example corresponding points. Choose actual vertex/loop counts from spacing needed for curvature and deformation.

### Repair without rebuilding faces

- For reversed orientation as in K1, orient toward the intended front side. Do not uniformly make every object outward-facing without understanding inner surfaces or single-sided cloth.
- For coordinate corrections, move the symptom center and smoothly return displacement to 0 at the fixed boundary. A front-view push must not destroy side thickness.
- Even with unchanged topology, identify where to preserve baseline/key-relative deltas and which corrections to rebuild. Smoothing must not conceal wrong connections or missing geometry.

### K2/P1: patch a small hole

1. Trace the surrounding edges: confirm one full boundary with no edges from another layer. Exclude openings that must remain.
2. From boundary relief and neighboring tangents, define the patch bulge in section. Do not cut round body volume off with a flat cap.
3. A small nearly planar gap may permit simple filling. On curved/deforming regions, divide faces and join neighboring flow; do not settle for one large polygon.
4. With grid filling, inspect vertex order/start position and repair diagonal twisting or slender faces converging at the center.
5. Check orientation, tiny-area faces, duplicates, and triangulation diagonals; compare for boundary steps/sharp shadows.

Blender example: on a scoped copy, select only the hole boundary and try **Grid Fill**.

- Use it for roughly quadrilateral enclosures or matching opposite sides that can become a face grid; do not directly apply it to arbitrary large holes or missing volume.
- Adjust `Span` for grid arrangement and `Offset` for the starting correspondence; inspect flow into surrounding P1 rows.
- Set curvature/density separately. An automatically produced grid is not automatically completed joint topology.

See [Blender: Grid Fill](https://docs.blender.org/manual/en/latest/modeling/meshes/editing/face/grid_fill.html) for selection/operation details.

### K3/P2: bridge two boundaries

1. Name the loops A/B and corresponding landmarks such as front A0/B0. Match points on the same side, layer, and front/back position.
2. Align traversal order; check that A0→B0, A1→B1, etc. do not cross. Correct twisting caused by an offset start.
3. If counts differ, locally subdivide/clean the needed side or design a gradual density transition. Do not force correspondence by bulk nearest-point merging.
4. For separated loops, build a band with enough rows for curvature/thickness. For a coincident continuous seam, merge only corresponding points while preserving UVs/hard edges.
5. Inspect orientation, section steps, winding, slender faces, and duplicates. Retain intended separation such as seams, separate parts, or overlapping hair locks.

Inspect face-flow direction and inward folding as well as point distance. If loops only visually overlap, verify they do not separate during motion.

Blender example: remove unnecessary faces, select only the two intended edge rows, and use **Bridge Edge Loops**.

- It can connect edge chains as well as closed loops. Do not include another layer or openings to retain.
- Use `Twist` to adjust starting correspondence. Equal counts still twist if A0/B0 landmarks are misaligned.
- `Merge` combines corresponding rows rather than adding a band. Select it according to whether that is the intended construction.

Forcing equal counts is not a prerequisite. See [Blender: Bridge Edge Loops](https://docs.blender.org/manual/ja/5.2/modeling/meshes/editing/edge/bridge_edge_loops.html) for connectivity/operations.

### K4/P3: rebuild locally or complete volume

1. Remove the faulty area back to a healthy perimeter and preserve excluded regions. Global remeshing is not the default.
2. Block out missing body/base volume from connection sections, artwork, the other side, and other references. Do not blindly mirror asymmetric design.
3. Match front/side/rear contours and sections. Diagram verified shape separately from hidden estimated shape.
4. On bending regions, align rows with [deformation-band face flow](mesh-weight.md), blending density/curvature gradually into the healthy perimeter.
5. When fitting body under clothing, retain joint volume and removal/replacement requirements. A scalp base must avoid visible skin/moving eyelids and fill only missing regions.

Uniform cylinders for hidden body or skin-colored paint for missing hair volume leave problems in motion/other views. Check geometric continuity with neck/head/torso and required thickness.

## 4. Remap new faces to deformation and images

After adding/removing vertices/faces, do not copy keys/weights using old indices. Align source/target reference pose and coordinates; identify unchanged points versus points needing correspondence. Choose transfer based on same-side corresponding faces, surface positions, or another explicit mapping.

| Item | Concrete action |
| --- | --- |
| Connectivity/normals | Inspect duplicates, wrong joins, inverted faces, custom normals, and sharp edges. Rebuild needed smoothing/normals and inspect triangulated results |
| UVs/materials | Assign new-face UVs and per-face materials. Inspect checker stretch, inversion, seams, and actual pattern direction; preserve intentional overlap |
| Weights | Interpolate from same-side/same-region/same-layer faces and blend into existing connection-loop proportions. Do not pick the opposite side or a nearby different layer; normalize deform bones only |
| Expression/corrective keys | Check each key's influence scope and give new vertices required displacement. Verify 0 delta for excluded keys. Neither leave all new points at baseline nor force motion into every key. Record transferred, rebuilt, retired, and tested keys |
| Other attributes | Set vertex colors, AO, masks, normal groups, and other shader/control attributes on new points/faces |
| Support/constraints | Update hidden support surfaces and Surface/Mesh Deform correspondence; rebind in the reference state if needed. Check double transforms |
| Baking/export | Rebuild shape-dependent AO etc. where needed. Preserve source images and verify new parts are included in export selection, material assignment, bones, and keys |

When body completion uses clothing weights as a guide, do not transfer clothing secondary-motion bones directly into the body. Likewise, scalp base and neck skin need not follow identically merely because they are close: establish head/neck roles.

Even coordinate-only changes do not automatically preserve correct relative keys, dependent parts, or old AO. Use [UV/image correspondence](adjustment-methods.md) and [saved-version matching](visual-handoff.md).

A whole-mesh snapshot hash normally changes when vertices/faces change. Keep correspondence from original healthy points/faces to repaired geometry and compare allowed-change and preserved regions separately. Equal old indices do not prove correspondence. Report evidence for excluded-region preservation and validation of new faces.

## 5. Acceptance, stopping a method, and open items

- **Shape/preservation:** retain required openings and accepted silhouette, thickness, and joining curvature. Compare excluded geometry/UVs/weights/keys with tolerances established beforehand.
- **Neutral/motion:** use matched plain, wireframe, and actual-material views through neutral → onset → intermediate → required maximum → return. Inspect unclothed interiors and ordinary clothed distance.
- **Contact/stretch:** inspect new penetrations by counterpart, self-intersections, excessive stretch, and local inversion/tearing/collapse. Reduced total intersections may transfer the issue to another layer.
- **Saving:** save separately/reopen and reproduce geometry, keys, weights, images, and dependencies. Distinguish this from in-memory success.
- **Export/destination:** reimport exports to compare connections, bones, keys, materials. Separately inspect destination triangulation, deformation, and rendering; list unverified work.

If references are inadequate, correspondence crosses layers, or dependencies/keys cannot be remapped, record the impact, stop that construction, and return to a healthy copy. If two consecutive same-cause candidates fail to improve practical appearance, re-diagnose boundaries, sections, and deformation structure rather than repeating parameter tweaks.

The [bundled helper](model-tools.md) audits structure/values, snapshots/compares, and performs scoped weight normalization. It does not fill holes, regenerate shape, or test surface self-intersection/collision over all motion. Audit success is not visual/motion completion.

## Turn production failures into the next first request

| What happened | Decision to include next time |
| --- | --- |
| Body fitted inside clothes in neutral but emerged in motion | Fix connection ends, interpolate from same-side corresponding faces, and inspect intermediate neck/arm motion |
| Inflation/weight edits did not repair crotch fold-in | Rebuild lower topology against actual body faces; do not reuse old corrective keys without validation |
| Rounding hem tips left fold-in immediately above | Extend the transition through the cloth surface and update hidden support/binding |
| Hair dent remained without normals | Repair flat/valley sections geometrically, add only necessary inner base, and align new-face UVs/weights/AO |

These are local production improvements. Do not extend their checks to whole-body, every time, or destination acceptance. Record remaining issues and adoption separately.

## Short AI requests

**Diagnosis and local repair:**

> Inspect [input version, region, symptom, required motion]. Start with the goal and fixed/changed ranges. Distinguish intentional openings, display/normals, coordinate steps, small holes, separated boundaries, wrong connections, missing volume, and motion-only failure. Use plain/wireframe/face-side displays and front/rear/side sections; explain the chosen construction and reason. Retain healthy boundaries and repair only the necessary region without bulk welding, closing every opening, or global remeshing. Compare matched neutral/intermediate/maximum/return states for deterioration in excluded regions and other parts too.

**Rebuilding/completion and handoff:**

> Complete [missing region, references, destination], diagramming verified versus estimated shape and matching connection sections, curvature, thickness, and face flow. Do not reuse old indices for new-point keys/weights. Remap UVs, materials, normals, weights, every key, AO/other attributes, and support dependencies through same-side correspondence. Do not leave new-point key deltas unresolved; record rebuild/retirement decisions for nontransferable keys/controls. Deliver a change-region diagram, mappings, matched shape/motion comparisons, saved-file/destination results, and open issues. Distinguish local improvement from final adoption.

© 2026 Lida · [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
