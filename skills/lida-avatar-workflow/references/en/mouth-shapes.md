# Mouth shape keys with a fixed jaw

[日本語 / Japanese](../mouth-shapes.md)

Use this procedure to preserve the face/jaw shape and create mouth shapes only around the mouth. If choosing jaw-driven motion, define its preservation conditions separately. See [expression meshes](expression-adjustment.md) for eyes/emotions and [adjustment methods](adjustment-methods.md) for displacement instructions.

When the Basis, tongue, or lower-teeth position needs diagnosis, read [mouth-interior and expression feedback](generation-feedback.md). Check the neutral form and key dependencies while preserving the agreed fixed-jaw conditions.

## Materials to prepare

If mouth images are missing, put [expression sheets and individual images](expression-sheets.md) into the initial plan and make required mouth shapes from the same closed-mouth neutral face. Reuse good existing images, reference models, and keys.

- Accepted closed-mouth neutral face and あ・い・う・え・お (a, i, u, e, o) images made from it.
- Front and oblique/side images that reveal lip projection.
- Tripo reference models for closed mouth and each vowel. These are shape references, not finished animation.
- Baseline mesh and a diagram marking jaw bone, jaw outline, and mouth edit region.
- Positions and visibility conditions for teeth, tongue, and mouth interior, if present.

## Procedure

![Original schematic: move only the mouth region on one baseline mesh while fixing the jaw and excluded areas](../../assets/face-key-locality.png)

Use each Tripo model as a shape reference; do not transfer its vertex indices or whole-face delta. In the shared Japanese diagram, **blue** is the moving mouth region, **orange** the band fading displacement to zero, and **gray** the fixed boundary/jaw. Row count and mouth shapes are illustrative, not a finished production mesh. Specify affected and fixed regions separately for [eye/emotion keys](expression-adjustment.md) too.

1. First check the neutral face's width, roundness, nose, and jaw.
2. Align reference models to the same orientation/scale and compare mouth width, opening, and projection.
3. Make mouth keys on one baseline face; do not replace the whole head with a reference.
4. Limit changes to lips, corners, opening, and necessary inner-mouth areas.
5. Smoothly weaken displacement outward, reaching zero at the boundary and beyond.
6. Verify zero jaw-bone rotation/translation and zero displacement of jaw-outline and outside-mouth vertices.
7. Compare individual keys, intermediate values, and combinations, then save/reopen.

## Concrete adjustments

- Parameterize width, vertical opening, and depth projection independently. A front view cannot establish depth.
- Move lip rims and neighboring faces continuously instead of pulling mouth corners as isolated points.
- For a different face size, compare proportions to mouth half-width rather than copying millimeter values.
- Add an outer fade band so displacement does not leak into cheeks, nose, eyes, jaw outline, or neck.
- Inspect inner lips and boundaries with teeth/tongue. A correct opening outline can still contain intersecting inner faces.
- If the target cannot be reached with a fixed jaw, show the difficult area in comparisons instead of silently loosening preservation conditions.

## Combinations and pitfalls

- Independently generated heads differ in vertex count/order, nose, jaw, etc.; do not transfer deltas by matching indices.
- Confirm key 0 returns to the neutral face. Do not mix different neutral faces among vowels.
- In addition to 25, 50, 75, and 100% opening, test vowel blends such as 50:50 and 70:30.
- This production limited total vowel input to 1. Sums above 1 folded corners, so output used the same rule.
- That rule is not universal; choose it for the actual keys and software's additive behavior.
- First test whether existing mouth/smile keys provide an open-mouth smile. Add references only where needed.

## First request

> Create mouth-only shape keys on the closed-mouth baseline from the vowel reference models. Do not rotate/translate the jaw bone. Preserve jaw outline, cheeks, nose, eyes, neck, and everything outside the mouth. Adjust lip rims, neighboring faces, and mouth interior continuously; state width, opening, depth, and fade range. Compare individual keys, intermediate values, vowel blends, and return after saving. State the input-sum rule.

## Verified scope

The production demonstrated local mouth-key creation with jaw/outside-mouth fixation and checked the specified deformation conditions. This alone did not approve tooth roots, tongue, every expression combination, whole-body attachment, VRM, or in-game appearance. Fix the baseline-face version before making expressions. See [process dependencies](process-index.md) and [Lida-specific design](lida-design.md).
