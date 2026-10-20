# Adjust expressions without breaking the facial mesh

[日本語 / Japanese](../expression-adjustment.md)

Adjust contour lines, neighboring faces, and the motion between expression values together. A natural endpoint is unfinished if intermediate values fold or open holes. See the [process index](process-index.md) for the full workflow and [adjustment methods](adjustment-methods.md) for displacement and fade instructions.

To build eyeball curvature, iris, sclera, line layers, or gaze, first read [eye modeling](eye-modeling.md). Use the [bundled tools](model-tools.md) to inspect key structure and values; judge eyelid appearance, contact, and intermediate motion here.

## Materials to prepare

If images are missing, start with [expression sheets and individual images](expression-sheets.md). Include generation and comparison in the initial plan instead of assuming references exist. Good existing references need not be regenerated.

- Accepted neutral-face mesh and eye, mouth, and expression images made from that same face.
- Matching-camera, matching-scale front, left/right oblique, side, and low-angle comparisons.
- Enlargements marking inner/outer eye corners, upper/lower lids, mouth corners, and lip rims.
- Baseline file, target range, fixed regions, and existing key list.
- Plain and actual-material displays. State each image's role in the [visual handoff](visual-handoff.md).

## Separate problems before editing

1. If the neutral face lacks the intended roundness, diagnose the baseline instead of hiding it with expressions. Fix it first when it falls within the full-production scope. For a local request such as a wink with a fixed baseline, preserve the neutral face and show local options and their limits.
2. Distinguish folded faces, painted lines, normal artifacts, and exposed cavity interiors using plain color, part colors, and backface views.
3. Build keys on one baseline mesh. Do not transfer vertex indices or whole-face deltas from independently generated faces.
4. Specify the changing region and the band where displacement fades to zero. Revalidate old keys transferred to a new baseline face.

## Eye closure

Ordinary blinking and a smiling one-eye closure serve different purposes. The [wink workflow](wink-closure.md) splits only the eye region of a smiling closure from the same baseline into left/right keys, preserving the mouth, brows, opposite eye, and ordinary blink. Repair the source smiling closure line and intermediate motion before splitting if needed.

1. Define the closed-lid line in front view, including heights at inner corner, center, and outer corner.
2. Show eye-local up, depth, and circumferential directions around the eyeball center. Do not confuse them with global facial up/down.
3. Treat eyelashes and painted lid creases as bands; move them while preserving their band shape.
4. Couple the rim with adjacent face rows, gradually returning to the baseline across unmarked skin. Fix the brows within the specified range.
5. Even with a common formula, inspect inner-corner face orientation and gaps on each side independently.

One production example used six upper rows and two lower rows as bands. Choose row counts for the actual mesh; these are not universal requirements. A smiling arc can be specified as a line between endpoints plus a central rise, for example `h(u)=H×(4u(1-u))^1.25`, where `u=0` is the inner corner, `u=1` the outer corner, and `H` the rise at center. Keep height and closure amount as independent parameters. Merely pushing the lower lid upward often creates a straight line crossing the iris midway. Map upper/lower lids and both corners to the same closure curve.

## White inner-corner lines, holes, and folds

![Original schematic: the eyelid rim and first neighboring row share a local transform, which fades across outer rows](../../assets/eyelid-band-follow.png)

The shared Japanese diagram illustrates a possible white-band cause: mismatched motion between the rim and adjacent faces. It is not a successful production mesh or a universal required row count. The rim and first row share local axis position, rotation angle, and radius change; this does not mean translating every vertex by the same vector. For fixed regions, fade bands, and intermediate checks also applicable to mouths, see the [local mouth-key diagram](mouth-shapes.md#procedure).

- If the rim moves while the next row moves in another direction, intervening faces twist and expose a white band.
- Give the first neighboring row the rim's local rotation, axis position, and radius change, then weaken the transform from subsequent rows outward.
- One production example gave the second row about 50% follow and returned to baseline over roughly 10–20% of eye width.
- Aligning the lower rim to the upper rim moves along eye-local up; do not confuse it with moving into depth.
- To repair a folded face, fix the rim, upper lid, inner wall, and brow while moving only the faulty lower faces in small increments.
- Applying one side's successful upper/lower limits directly to the other can create a different hole or line.
- A “no holes” finding depends on sampling detail. Reinspect suspicious intervals with close-ups and finer intermediate values.

## Sad and gentle eyes

- Specify inner corner, center, outer corner, and a smooth curve between them instead of deriving height only from a fixed fraction of available closure.
- Lowering only the outer corner often makes the contour unnatural. Preserve the original curvature and adjust its height relative to the inner region.
- If raising the inner corner reveals previously hidden eyeball, reconsider surrounding downward motion as well as the rise amount.
- A correction made with fixed brows is not completion of the entire brow-inclusive expression.

## Mouth profile and visible teeth

- A mouth can be round in front yet angular in profile if its corners pinch into depth. Preserve front-view width/height and adjust lip-rim depth separately.
- In one example, a particular vowel's rim depth changed by up to about 0.35 mm, with the same displacement applied to two adjacent lip rows.
- That amount is an example. Establish mouth size, units, and face spacing before choosing a value.
- Check painted mouth lines and inner-wall color too. Rolling the entire lip inward to hide a line easily creates new intersections.
- Inspect teeth at closed, intermediate, and open values. Hiding teeth for every vowel changes vowels that need them visible.
- See [mouth shapes](mouth-shapes.md) for mouth-only keys and a fixed jaw.

## Shadows, painted lines, and separate parts

- After changing skin, inspect overlying shadow and line parts. Measure sinking below skin separately from floating above it.
- Change only the required expression deltas; do not move the neutral face and other expressions together.
- Make separate eyelashes follow corresponding skin faces. Unconditionally rotating an open root can expose its interior.
- If painted lid lines move with gaze, separate lines fixed to the face from patterns belonging to the eyeball.

## Inspection order

1. Check each key alone at 0, 10, 25, 50, 75, and 100%; inspect left/right winks separately.
2. Check actual combinations such as vowels together or smile plus blink.
3. Explicitly state input rules, such as vowel sum ≤1 or same-eye blink plus wink ≤1.
4. For combinations that double-add closure, consider a transition such as smile `e` and blink `1-e`.
5. Sample faulty intervals more finely than the normal increment. Valid endpoints do not validate the interval.
6. Inspect left/right oblique, side, and low views as well as front; plain and actual materials; full view and detail.
7. Save/reopen and verify return to key 0, fixed-region displacement, and preservation of UVs, materials, and other keys.

## First request

> Use this neutral face as the baseline and modify only the specified eye/mouth region. Design its contour, neighboring face rows, and intermediate motion together. Use the diagram's local coordinates to specify displacement and the return-to-baseline band. Preserve fixed regions and excluded keys. Compare each side in close-up, intermediate values of individual keys and combinations, and return after saving. Report candidates, verified improvements, and remaining issues separately.

## Scope of the results

Production examples locally improved closure lines and mouth profiles, but fine inner-corner gaps, points at mouth corners, and intermediate tooth exposure required separate checks. A local face pass does not establish whole-body attachment, gaze, export-format, or in-game acceptance. Design preferences are collected in [Lida's design notes](lida-design.md).
