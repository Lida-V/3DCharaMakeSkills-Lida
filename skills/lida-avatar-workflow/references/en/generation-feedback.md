# Practical feedback from a separate new character production

[Japanese original](../generation-feedback.md)

This supplement draws on corrections to generated meshes, automatic rigs, mouth expressions, materials, and long-sleeve motion in **a separate new character production, distinct from Lida's avatar**. It collects specific failures and diagnostic methods found after applying the existing basic workflow. These are not results or adoption decisions from Lida's own model production.

The source records contain saving, read-back, images, and specified-clip tests. However, “zero across all keys” and “30-second review” describe finite tests of the recorded keys, directions, poses, and intervals. They do not guarantee arbitrary combinations, all-time safety, final user adoption, or success in untested destinations. The adjustments below are options. Decide from artwork, use, required movements, units, and actual scale. Do not turn source percentages, angles, millimeters, skin colors, or simulation frequencies into shared defaults.

## Where to use this chapter

| Symptom or stage | Relevant topic here | Basic workflow and existing diagrams |
| --- | --- | --- |
| Dented finger sides or an overly thick little finger | Cross-sections, smoothing, finger classification | [Hands](hand-shape.md), [mesh and weights](mesh-weight.md) |
| A thumb drops downward or the palm folds into an L | Actual joint locations and roll | [Hands](hand-shape.md), [Tripo initial rig](tripo-autorig.md) |
| Mouth corrections damage the original face or other expressions | Basis and all dependencies | [Mouth shapes](mouth-shapes.md), [expressions](expression-adjustment.md) |
| A straight-looking tongue or lower teeth emerging through the chin | Oral volume and depth | [Mouth shapes](mouth-shapes.md), [repair and completion](mesh-repair-completion.md) |
| One mouth corner looks split or the chin looks short | Separating shape, UVs, images, normals, and materials | [Adjustment methods](adjustment-methods.md), [destination appearance](cross-engine-look.md) |
| Hair disappears in FBX or old images appear | Actual draw ranges and embedded images | [Integration and handoff](visual-handoff.md) |
| A long sleeve folds vertically or flips when the arm moves | Parent pivots and current frames | [Secondary motion](secondary-motion.md), [mesh and weights](mesh-weight.md) |

No new figures are added. Use existing hand, local-correction, mesh-repair, and integration diagrams from the [diagram index](diagram-index.md), explicitly mapping them to the actual model.

## 1. For dented finger sides, separate smoothing from cross-section measurement

**Symptom:** Smoothing leaves depressions around particular points. An oblique little finger becomes too thick, or adjusting finger spread collapses width.

**Possible causes:**

- Averaging neighbors without regard to direction at a pole, where five or six edges meet, can pull a rounded cross-section inward.
- Taking raw-coordinate minima and maxima within a thick slice aligned to a fixed world axis mixes finger tilt and web-root bulges into the measured thickness.
- Evaluating splay or transverse-arch displacement from each vertex's sideways position moves opposite sides of a section by different amounts and narrows it.
- Overlapping thumb/index classifications, or required points omitted from both, can introduce another finger's displacement or weights. A proximity-based search can also cross a finger web into a neighbor.

**Practical adjustment:** First color-code problem points and finger ownership in plain shading and wireframe. Establish the lengthwise centerline and local sections. Measure width and thickness in coordinates relative to the centerline at each point's axial position. Preserve the wrist-side boundary and required web shape, and design taper for the target.

Where isotropic averaging collapses a section, compare **axial fairing using lengthwise neighbors within the same circumferential sector**. Fairing smooths irregularities along selected directions. Choose sector width and iterations by comparing original and resulting sections. Do not extend a method suitable for the palm unchanged into thin fingers.

For splay and transverse arches, evaluating one offset at the section centerline and applying it to the entire section can change position without changing width. Check classifications for both overlap and omissions, then blend smoothly between thumb, palm, and index regions. Web positions differ among fingers; do not remove all limits beyond one common threshold.

**Review:** Compare front, back, side, and oblique sections and outlines, width toward the tip, open hand, individual-finger bends, fist, pinch, and intermediate values. Check UVs, unaffected arm regions, nails, and erroneous weights from neighboring fingers too. Mirror symmetry is appropriate only when the artwork and specification are symmetric.

## 2. For the thumb, inspect real joints and bend axes before bone names

**Symptom:** The thumb drops downward instead of moving across the palm, or bending produces an L-shaped fold in the thenar region or palm edge.

**Possible causes:** Automatically placed joints miss the actual thumb shape and create a sharp kink near the base. Thumb roll matches the other four fingers even though its intended flexion axis differs relative to nail and palm.

**Practical adjustment:** Map CMC, the wrist-side base joint; MCP, the base of the free thumb; and IP, the joint within the thumb, to the real mesh and reference. Display bones and use small rotations to determine flexion, spreading, and opposition relative to the base, pad, and nail. Opposition turns the thumb toward the other fingers.

Choose joint locations from the bends required for a fist or pinch rather than copying fixed percentages of thumb length to another hand. Use nail-side orientation or similar landmarks to adjust roll, checking rotation-axis signs on both hands. Compare rotation-center correction separately from weight correction.

Internal bone names belong to that production. Do not infer CMC/MCP/IP or VRM 1.0 humanoid assignments merely from words such as `proximal`; create an explicit map to the output specification. Renaming bones alone does not establish conformance.

**Review:** Check thumb-only motion, fist, pinch, intermediate values, and return for palm folds, nail orientation, pad contact, and effects on other fingers. Read back reference pose, roll, weights, and humanoid assignments after saving, then verify required movement in the destination.

## 3. Rebuilding the mouth Basis must not roll back the whole face

**Symptom:** Repeated local welds and cuts split the mouth or damage normals, or restoring it also loses previously good eyes and expressions.

**Practical adjustment:** Preserve the current version. If referencing a healthy earlier version, recover **only the target mouth structure**. Separate visible lip rims, inward returns, adjacent skin, and mouth bag by connections and surface orientation. Equal-height points do not determine upper/lower ownership. Distinguish the intended mouth opening from wrong pinches, wire edges, and missing surfaces before repairing.

Define which keys will be rebuilt from Basis while preserving jaw bones, jaw outline, and the adopted face outside the mouth. Do not restore an entire old version over healthy eyelids, brows, other expressions, materials, or UVs. When adding or splitting vertices, remap all dependent keys, normals, weights, drivers, and expression bindings instead of reusing old vertex indices. A small difference in neutral appearance alone does not prove preservation.

**Review:** Inspect neutral shape, every dependent key, intermediate values, and required blends in the same saved version. Separately compare displacement outside the mouth, eye/brow movement, oral layer order, materials and images, saving, and actual export. If another request changes the jaw outline, record that scope and its preservation conditions separately.

## 4. A straight-looking tongue needs more than a front-view height change

**Possible causes:** Vertical compression made the tongue a plate, or a wedge rising toward the back remains. From an oblique view, the high back surface can still look like a straight board despite a rounded front outline.

**Practical adjustment:** Establish the tongue's visible position and area from the expression reference. Build a volume with tip, sides, back, and underside. The example used **an elliptical dome-like surface**, with a visible central high point descending smoothly both sideways and front-to-back. This is an option, not a requirement to give every character the same tongue. Match the peak and front/back curvature to the reference and available oral space.

**Review:** Alongside the front, inspect both oblique sides and profiles, narrow and wide openings, and intermediate values for board-like lines, a rising back, and intersections with oral walls. A specification without tongue animation still needs review of its visible 3D form.

## 5. Diagnose lower-tooth penetration and a white shelf below the tongue together

**Possible causes:** If chin skin recedes backward below the lower lip, moving a vertically tall lower-tooth mesh straight down can expose its bottom through the chin. Holding its height fixed can instead leave a white shelf floating in the open mouth.

**Practical adjustment:** In Basis, check tooth height, front-edge depth, and the dental arch. If needed, shorten the vertical extent to fit inside the mouth, then compare **combined downward and backward movement** when opening. Determine amounts from chin-skin slope and actual clearance, not lip displacement alone. Record which axes mean front, back, and down, plus units and scale.

Show upper teeth, lower teeth, tongue, mouth bag, and lip returns together to inspect front-to-back order. For rays against outer skin, record target faces, origins, direction, distance, tolerance, and clearance in actual units. **Zero in one-direction BVH ray tests does not establish safety at sides, edges, face intersections, or complete enclosure.** Combine them with real images of closed mouth, every dependent key, intermediate values, required blends, and oblique/profile views.

## 6. An uneven mouth corner needs separate shape, lipstick, normal, and light checks

**Possible causes:** A dark line baked beyond the real 3D corner, asymmetric UVs, incorrect lipstick fading, custom normals, and oblique light can combine to make one side look more deeply cut.

**Practical adjustment:** Inspect 3D shape in plain shading, then compare base color, lipstick, baked lines, normals, and light one at a time. Blend only unwanted duplicate lines into the surrounding skin gradient. Do not use color to hide holes or folds. For symmetric artwork, compare corresponding 3D points and UV triangles; preserve intentional asymmetry.

Check interpolation endpoint order too. For example, when using `smoothstep`, check the lower/upper edge order required by that implementation, using an explicit inverse mask if inversion is intended. Restrict normal corrections to the target before considering a whole-head recalculation.

**Review:** Compare both oblique sides, corner close-ups, closed mouth, smile, opening, and intermediate values under the same light and with changed light direction to separate shape from shading. Check actual destination double-sided rendering and exported images too.

## 7. Separate chin shape from where the skin color ends

**Symptom:** Facial skin color ends immediately below the mouth, making the remaining chin look long. Rounding then produces an overly broad bowl shape.

**Possible causes:** A dark neck/behind-ear material on the lower jaw makes the apparent face length differ from the real silhouette. Alternatively, the real chin may be too long or its sides lifted too strongly. Uniform rounding can erase a chin tip that should remain distinctive.

**Practical adjustment:** First compare mouth-to-chin and chin-to-neck outlines with the artwork in plain front, oblique, and side views. Use material colors and base-color-only display to inspect skin/shadow boundaries separately. If shape needs correction, protect mouth and neck boundaries and round side/oblique angularities locally while retaining the tip. Projected-outline curvature can be measured, but rounding iterations or angle thresholds are not appearance approval.

Check left/right signs on synthetic points before running a script on the real model. For example, `copysign(magnitude, x)` takes the absolute value of its first argument and gives it the sign of `x`. For inward movement, verify that the resulting point on each side is closer to the center. Passing an intended negative magnitude must not accidentally expand the jaw outward.

Even when applying one identical local displacement to Basis and dependent keys to preserve their relative differences, review every resulting key again. In images, create the required gradient from front chin to cheeks and underside while preserving healthy skin, lips, and neck continuity. Pale-skin colors and V-shaped/rounded preferences belong to the particular artwork, not a universal quality standard.

**Review:** Compare both oblique sides and profiles as well as the front, open mouth and intermediate expressions, underside, and neck boundary under matching conditions. Record shape, materials, normals, oral clearance, and preservation outside the target separately.

## 8. Face/body skin differences can come from both shader and image

**Possible causes:** Shadow boundaries, AO darkness, or shadow colors differ between face and body. Repair images may already contain darker paint. Shared correction may also affect ornaments in the same image.

**Practical adjustment:** Compare base color alone under matching light and exposure before restoring shadow, AO, and highlights. Match the adopted skin reference, separating changed values from edited image regions. Protect cloth, fittings, stockings, and other areas with skin masks rather than replacing a shared material wholesale with a skin shader. Save editing materials and output-compatible materials in their respective roles.

**Review:** Compare face, neck, shoulders, arms, hands, and legs in full-body and close-up views, then compare native materials and compatible exports after saving. Brightness follows artwork and user requirements; another production's RGB values and coefficients are not the correct answer by default.

## 9. Do not miss disappearing geometry, stale images, or lining intersections after export

| Symptom | Cause to investigate | Adjustment and review |
| --- | --- | --- |
| Hair shows in Blender but disappears in an FBX destination | Unused material slots or inconsistency between material arrays and loader draw ranges such as `geometry.groups` | Review whether unused slots are needed, then check the actual export with the real loader. Inspect valid draw ranges for all target faces and the actual display, not only visibility and opacity. |
| The export shows an old image after editing | The in-memory image differs from stale packed image data | Load the new image data and update references and embedding. Compare screen appearance, saved file, and real images inside FBX/VRM separately. |
| Added back cloth intersects the front | Reversing a nonplanar quad changes its triangulation diagonal between sides | Preserve correspondence to original triangulation and set required thickness, winding, and UVs. Inspect actual triangles on both sides and in motion. |
| Gold-material correction spills onto skin or hair | Uniform mask dilation in a shared UV image reaches other islands | Restrict edits to actual faces, UV regions, and required pixels. Preserve skin, hair, gem reflections, existing patterns, and unrelated pixels, checking all shared users. |

Identify visible faces with rays, face IDs, and real UVs where needed. White pixels or boundary-edge counts alone do not justify deleting faces or closing holes. Preserve source images, shape, UVs, and shared users while editing only the responsible layer. Record real-loader structure checks separately from actual application display review.

## 10. Bring an automatic-rig return back to a good source mesh

**Practical adjustment:** Compare the submitted copy and the Tripo or similar return for axes, rotation, scale, reference pose, and actual mesh correspondence. To preserve a good original mesh, UVs, normals, images, and materials, transfer verified donor bones and weights to corresponding surfaces rather than replacing everything with the returned mesh. Measure orientation and scale for each return; do not reuse another model's correction values.

Adding only a rig may omit colliders stored as child objects. Explicitly include required hierarchy, collider shapes and coordinate spaces, chains, endpoints, expressions, and humanoid assignments. Exporters may omit non-deforming terminal bones too: inspect the actual file rather than a configuration plan and choose the smallest suitable remedy.

Preserve native editing materials separately from compatible materials for FBX/VRM or other outputs. Do not rerun an old whole-scene material conversion to update bones. Check real connections, values, images, and saved rendering, not only node names or active flags.

**Review:** Compare preserved shape, UVs, images, normals, and materials, target weights, hierarchy, bone assignments, collider positions, and endpoints after save/reopen and in actual export. Record input version and before/after state to prevent a rebuild script from applying a correction twice to an already corrected input.

## 11. Separate sleeve weights from the rotation reference

**Symptom:** Elbow bending produces a vertical sleeve fold. Moving the arm forward flips the sleeve relative to its cuff. The sleeve develops an abrupt S-shaped bend.

**Possible causes:** A simple half-and-half LBS blend between chains with different pivots, such as upper arm and forearm, can fold the intervening region. Reconstructing bone rotation from particles using rest-pose world axes can leave the width axis inconsistent with the current arm and cause large twist. Independent targets for every segment can make angle limits and collision pushback conflict.

**Practical adjustment:** Separate cuff pins, upper-arm ornaments, and the main hanging cloth, checking unwanted hand/finger weights. Compare options such as placing the main hanging region on one chain. If different-pivot chains must be blended, evaluate the real elbow bend. One chain is not mandatory for every costume.

When reconstructing pose from cloth particles or a proxy surface, use **the current parent frame together with the parent/child relative rest orientation**. Separate following of arm direction from inheritance of forearm axial twist and compare any needed attenuation. Establish the main hanging direction first, then distribute finer motion into relative curvature farther down, adjusting for continuous bending including collisions.

The source production reconstructed main droop and relative flex from a small 2D cloth simulation. Its grid size, frequency, angle limits, gravity, and damping are not requirements. Saved cloth settings, scripted simulation, baked video, and real-time destination physics are separate states.

**Review:** Check arms down, forward, and raised, elbow bends and twist, intermediate/return movement, and after stopping. Inspect width alignment with the cuff, vertical folds, flipping, body/leg/ornament contact, and cloth stretching. Measure load under the same runtime conditions and choose a method that preserves the adopted shape.

## A short AI request

> Preserve [current saved version] and review [symptom] against the artwork and real images under matching conditions. First isolate shape, connections, joints/weights, controls, UVs/images, normals, and destination display. State [editable regions], [fixed regions], comparison conditions, and exit criteria.
>
> For fingers, check sections relative to local centerlines, shared offsets for splay, finger classification, and bend axes. For the mouth, preserve outer face, jaw outline, and other dependent keys, reviewing tongue, upper/lower teeth, bag, and lip returns in oblique/profile views and intermediate values. Separate chin/skin shape from material boundaries. For long sleeves, check pivots and current parent frames. Mark irrelevant items outside scope with reasons.
>
> After saving, read back the output through the real loader and check real images, bones/endpoints/colliders, and native/compatible materials. Report before/after results, preservation outside the target, tested objects, units, times, tolerances, user adoption, and unverified destination checks separately. Local zeros and specified-video results do not guarantee all movements or environments.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
