# What to adjust, by how much, and over which region

[日本語 / Japanese](../adjustment-methods.md)

[Process index](process-index.md) · [AI instructions](ai-instructions.md)

Separate causes before choosing displacement, reference axes, and fixed regions. Work on a duplicate that can return to the good original, with comparisons using identical camera, pose, and lighting.

## First six steps

1. Fix the input version, affected region, view, and motion.
2. Separate shape, connections, bones, weights, normals, images, and display causes.
3. Record units, movement axes, scaling center, and shape landmarks.
4. Adjust amount/range locally, fading smoothly to 0 at fixed boundaries.
5. Update corresponding clothes, ornaments, support surfaces, and corrective keys.
6. Compare neutral, intermediate, required maximum, and return; record saved-file preservation and open issues.

## Choose adjustments for the symptom

| Symptom | What to edit | Check together |
| --- | --- | --- |
| Neutral-shape step/dent | Vertex positions, face flow, connectivity | Surrounding curvature, silhouette, fixed boundaries |
| Tears/collapse in motion | Bone centers/axes, weight transitions, topology | Intermediates, inner/outer thickness, clothes/ornaments |
| Forked hair tips | Root connectivity, one centerline, width/thickness taper | Root and flow; trimming branch tips alone is insufficient |
| Plate-like hair protrusion | Inner/outer face order, front/back positions of required points | Neighboring locks and silhouette; smoothing alone cannot fix ordering |
| Unnatural dark lines/patterns/shadows | Geometry, normals, base color, painted shadows, display edges | Isolate with flat color, disabled normal map, etc. |
| Only mouth interior is black, or feather edges are dark | [Base/shadow color, alpha, and destination rendering](cross-engine-look.md) | Isolate faces/material before changing global exposure/shadow |
| Floating decorations/collapsed tubes | Part-level translation/rotation, band-end curvature, tube section | Thickness/connection; do not just push every point to a nearest face |

For gaps/wrong connections, select patching, bridging, or local reconstruction in [mesh repair/completion](mesh-repair-completion.md). For clipped silver, cloudy gems, or unreadable decorative lines, see [material correction](accessory-materials.md). Separate image/material/shape causes and establish comparisons before editing.

## Diagnose mottled hair through AO

AO represents darkness in occluded areas. Prepare the accepted shape, enlarged symptom image, and a copy where base color, shadow, AO, normals, and gloss can be displayed separately.

1. Disable each component individually under identical camera/light. If the image alone is clean, investigate shading before increasing resolution.
2. If vertex AO baked to coarse geometry makes shadow boundaries mottled, smooth only the target part and adjust retained darkness separately. Compare weak/moderate/strong under matched conditions while retaining lock depth.
3. A shared-material coefficient affects other hair too. Restrict changes to target vertex attributes or a local mask. Apply the same correction once to display and export paths.
4. Recheck expressions and front/side/top lighting, including preservation of excluded shape, images, and shading.

Lida's bangs used eight smoothing passes and 35% retained darkness. These are example values, not defaults. Large patches remained with smoothing alone, so darkness was adjusted separately.

If AO means 0=dark and 1=unoccluded, use `newAO = 1 - (1 - smoothedAO) × retainedDarkness`. Retained darkness 0 removes AO darkness; 1 keeps the smoothed value. For a shader with different semantics, first verify range and dark/light direction.

Example first request: “Isolate base color, AO, shadow, normals, and gloss one at a time. Compare smoothing and darkness only on [part]. Preserve other shared-material users and provide expression/light-direction comparisons and output results.”

## Choose amount and boundaries

![Original schematic showing how different fade widths change a boundary despite equal displacement](../../assets/local-mask-transition.png)

In the shared Japanese diagram, **orange** is the correction mask, **blue** the corrected position, and **green** fixed points. This mask is not a skin weight. Test displacement and return width independently and measure actual evaluated displacement.

Local movement is `newPosition = originalPosition + maskValue × displacement`. Set center to 1, preserved areas to 0, and blend smoothly. If a boundary folds, examine amount, return width, and source face density separately.

Measure penetration/step width first, compare a weak candidate with the necessary amount, then reduce a candidate that clears the symptom to find its threshold. Check required motion clearance.

One hair example retained a plate at 0.7 mm, cleared it at 0.8 mm, and selected 1.0 mm. These values apply to that region, not other hair. Lock-joining lines and other issues remained; this was not completion of all hair.

Subdivision/interpolation can spread an effect beyond the mask. Measure both configured width and the region actually moved after evaluation.

Scaling is `newPosition = center + scale × (originalPosition − center)`. Specify center as well as scale and inspect jaw, neck, and ornaments. Measure head-to-body proportions with consistent landmarks such as crown and chin; do not mix hair-inclusive height with skull size.

## Update dependent parts

Use the [hair cause-isolation diagram](../../assets/hair-cause-isolation.png) for patterns, gaps, and plates. Inspect flat color, topology, and sections in turn; distinguish base color, connections, and face order.

- If changing a baseline with the same topology, carry needed displacement into keys while preserving intended relative deformation.
- If rebuilding topology, re-establish correspondence rather than reusing key/weight vertex indices.
- Match positions/displacements between visible cloth and hidden support surfaces; reset constraints when needed.
- Create painted shadows from the original image after final shape; do not darken repeatedly on every correction.

Reduced total cloth intersections may move new penetration into another layer. Check deterioration per part using [skirts and completion](skirt-hidden-modeling.md). For mouths/eyes, continue with [expression adjustment](expression-adjustment.md).

## Deliver UVs, images, and materials together

UVs map image positions to faces. **An image alone does not include how it is mapped to the model.** For regions with settled shape/basic following, align these items:

| Deliverable | Record in the mapping |
| --- | --- |
| Mesh with UVs | Input version, part, active UV layer, intended overlap/mirroring |
| Material/face assignments | Which faces use which material and which image/UV layer it references |
| Corresponding images | File, role such as base color/AO, dimensions, saved status, destination settings |

1. **Inspect mapping first.** Use a checker for stretch, inversion, and seams, then actual images for pattern direction/position and line width at normal distance and in required motion. Overlap count alone does not justify changing intentional overlap.
2. **Decide whether rearrangement is needed.** Preserve usable UVs. Moving UVs changes image correspondence, so transfer/rebake only necessary areas. Resolution changes alone do not fix mapping.
3. **Separate source and output images.** Recreate shape-dependent AO etc. only where needed; do not stack correction onto the original. Preserve originals in a copy and check excluded UVs/materials/images.
4. **Save and reload.** Save images and include external references in delivered files or use supported embedding. In a fresh model load, inspect missing images, wrong UV layers, and incorrect assignments. For exported destinations, compare color, transparency, and seams separately.

Example first request: “Map [part]'s UV mesh, images, and material assignments and inspect with a checker and actual materials. Do not globally rearrange usable UVs; transfer images only in changed areas and preserve sources. Check a fresh load and the destination, reporting unverified scope.”

## Added hair UVs and baking

Parts can reuse the same image/UV region for display, yet conflict if different part-specific AO is baked into that shared image. Use the [mapping and saved-file checks](#deliver-uvs-images-and-materials-together) to inspect shared bake destinations first.

Only if baking conflicts, separate added-part materials, UVs, and images in an export copy. Preserve originals/existing hair; inspect strand direction, seams, and exported shading. Do not reuse old-shape AO without validation after geometry/topology changes.

Example first request: “Inspect added-part UV overlap. If bakes conflict, separate materials/UVs/images in the export copy. Preserve existing images and compare reimported strand direction and seams.”

## For thin-collar penetration, compare motion relative to the skin

When clearance between neck skin and collar is small, compare corresponding skin/collar weights and deformation methods before widening clothing. In Lida's example, capped collar neck weights made it move less than the skin. The symptom also reproduced in Blender, so engine influence-count limits alone were not the cause.

1. Compare skin/collar from the same version in neutral, looking down/up, head tilt, turning sideways, and required combinations. Match bones and display/reference poses; distinguish visible protrusion from hidden overlap.
2. Interpolate weights from corresponding skin faces in the rest shape and smooth along collar connectivity. Ensure a nearby under-jaw surface with different motion is not selected. Choose influence count, rounding, and smoothing passes for the destination/shape.
3. Per-vertex transfer can distort rigid fittings. Let a fitting follow collectively using representative weights from its attachment, for example, then separately inspect ring shape, connection, and cloth contact. Identical weights alone do not guarantee perfect rigidity.
4. Preserve neutral shape, UVs, materials, face/expressions, and other excluded regions. Check combined neck/upper-body/shoulder motion, contact with hair/bodice/fittings, saved-file behavior, and required destinations.
5. Check whether bone/weight regeneration rules overwrite the fix. Update the builder or record a post-build delta application and verification procedure.

This diagnoses a collar lying close to skin. It does not prescribe copying skin weights uniformly into all clothes or freely moving cloth. Use [mesh/weights](mesh-weight.md) together with [mechanical, image, and motion review](mechanical-visual-review.md).

## Correct locally or rebuild?

For local position/shading, define preservation and correct locally. If skull/cheek volume, joint position/length, or hair connections differ from the baseline, stop repeating the same parameter change and re-diagnose structure.

Leave “symptom → cause → axes/units → amount/range → fixed regions → related parts → comparison/open issues” for next time. Consolidate later-added conditions in [trial-and-error records](trial-and-error.md); do not promise first-attempt acceptance.
