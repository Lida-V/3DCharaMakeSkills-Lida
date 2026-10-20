# Communicate corrections to the AI with images and short text

[Japanese source](../visual-handoff.md) · Source baseline: 2026-10-20.

[Process index](process-index.md) · [AI instructions](ai-instructions.md)

Separate [mechanical checks from image/motion assessment](mechanical-visual-review.md). Even when a CLI passes, inspect appearance from the same saved version. Attach necessary comparison images rather than conveying position and selection in words alone. Briefly identify what to change where, and what to preserve.

If hair disappears or an old image reappears in FBX, use [material-slot, draw-range, and embedded-image diagnostics](generation-feedback.md). Check the exported content separately from the Blender viewport.

## Minimum image set

1. **Target/approved shape:** Reference version, angle, preserved features.
2. **Problem:** Reported view, normal viewing distance, necessary plain-material/wireframe close-ups.
3. **Candidate:** Corrected result with the same camera, pose, and lighting; include problematic intermediate motion.

If hair/clothing was hidden for diagnosis, state this and also inspect restored appearance. Select references needed for this part rather than handing over a large undifferentiated batch.

## Five notes for every image

| Item | Example |
| --- | --- |
| Number and role | Figure 02 is a failure example, not a finished target. |
| Panels, direction, pose | Reference on left, candidate on right; character's left profile during arm raise. |
| Location and symptom | Wide depression below the shoulder in the right middle panel makes the arm look inserted into the torso. |
| Target and fixed parts | Connect shoulder roundness; preserve accepted chest, clothing, skeleton structure. |
| Exit condition and remaining work | Compare neutral/intermediate states with plain/actual materials at normal distance; identify the remaining valley too. |

Distinguish screen left/right from character left/right. Match images to input models rather than inferring version solely from a filename.

## Distinguish actual results from diagrams

- [Bending support bands](../../assets/bend-support.svg) and [surface flow](../../assets/flow-continuity.svg) are design schematics, not completed real models. Read their English legends in the [topology/weight chapter](mesh-weight.md).
- In [knee layout](../../assets/actual-knee-layout.svg), gray lines are actual edges and colored dashed lines are unimplemented/unverified placement proposals.
- In [knee bending](../../assets/actual-knee-bend.svg), colored lines track the same actual edges. The earlier comparison did not resolve folding. The [knee chapter](knee-edge-placement.md) explains the English correspondence.
- Inspect placement, actual connections, and bone/weight correspondence rather than line counts. Do not describe temporary guides as implemented work.

Take verification images from the saved model; do not redraw the shape with image generation. A diagram omitting hidden lines cannot establish all internal contacts or volume as acceptable.

## Ready-to-use request

```text
Input: [confirmed version]. Figure 01: [target]; 02: [problem]; 03: [candidate under matching conditions].
First briefly explain each image's role and the visible issue.
Correct [tier/row/part] in Figure 02 toward [target appearance], preserving [fixed areas].
Separate shape, connection, bone, weight, normal, and image causes; adjust the appropriate scope.
Compare [neutral, problematic intermediate, required maximum, return] under matching conditions and present actual images.
If appearance is unnatural despite meeting numerical conditions, mark the goal unmet and record preservation and remaining work.
```

## Before integrating parts

![Schematic of merging accepted part deltas into a common base and checking dependencies, reopening, and destination](../../assets/integration-dependencies.png)

**English legend:** **1** lists selected versus unverified part versions: body A/B, hand C/D, face E/F. **2** merges only selected deltas into one base, aligning scale, coordinates, and rest pose while preserving unrelated shape/UV/material/key data. **3** uses blue boxes for changed sources and orange boxes for dependencies: hand shape → joints, bone directions, weights, nails, pose; body shape/topology → clothes, ornaments, support surfaces, connections; face shape/topology → expressions, eyelashes, lines/shadows; hair shape/placement → bones, following, painted shadows. Arrows show the direction of impact. Do not reuse old vertex indices or bone locations blindly. **4** saves/reopens and compares neutral/intermediate poses under matching camera/light. **5** makes a small destination export test for bones, keys, following, and display. Each is a separate check.

Versions A–F are explanatory symbols, not real selection status. A file with the newest number may still contain older parts; first list selected and unverified versions. Arrows lead from a changed part toward dependent data needing correspondence checks. Review [hand shape](hand-shape.md), [expressions](expression-adjustment.md), and [dependent-part adjustments](adjustment-methods.md) together. Record per-part correspondence, integrated appearance/movement, reopening, and destination tests separately; an untested candidate is not a proven success.

## Verify integration and the saved version

When combining heads with/without hair, use [head/hair composition](multiangle-threeview.md). Handoff the versions for face, skull, scalp, ears, neck, hair, expressions, and shadow layers as one set. Aligned images and aligned generated geometry are separate facts. Preserve the chosen face while checking hair attachment.

1. **Treat each part and its dependencies as a set.** List input version, joint locations/axes/reference pose, weight rules/values, and corresponding clothes/nails/ornaments. Identical bone names do not guarantee identical motion if locations/controls differ. Include normals, corrective keys, modifier order, and driver references. Compare integrated actual data and appearance in the same poses.
2. **Distinguish preservation outcomes.** Use exact equality, within a predeclared tolerance, and unchecked accurately. Give units, comparison target/pose, maximum difference, and tolerance. Passing with a small difference is not “zero difference.” Record input-file hash equality separately from numerical evaluated-shape comparisons.
3. **Verify reference pose.** A pose that looks like a T-pose does not establish that the saved source's reference pose is T. Reopen and inspect bone/mesh reference states; export to required destinations and verify pose/deformation reproduction. Unexported parts remain untested.
4. **Match submission material to the saved version.** Save and reopen the final model and record its hash (content identifier). Images/video retain the hash of their actual model input and comparison conditions. After correction/re-saving, regenerate affected material even if the filename stayed the same. Retain older material only with an explicit older-version label, never as current evidence.
5. **Inspect secondary motion over real time.** With [secondary motion/export](secondary-motion.md), separate fixed areas, settings, baking, custom controls, and actual destination behavior. Record actual video duration, motion range, tested objects/times, and inspected return/settling range.

These are integration/handoff methods. Choose destinations/motions relevant to the use; do not extend unchecked scope into overall acceptance.

## Re-import the VRM and inspect submission motion

Align the accepted display model, actual saved VRM, matching camera/light, user-specified submission interval, and natural control combinations. At the start, define which appearance/motion results close the review.

1. **Inspect actual-file structure.** From VRM JSON and embedded images, check material format, image dimensions, and expression/morph correspondence. Record whether measurements cover counts, maxima, or every element. Matching maximum displacement does not establish all-vertex equality. Standardizing image dimensions does not establish acceptable size, face count, or runtime cost.
2. **Re-import under matching conditions.** Compare the saved VRM with the authoring version under the same camera/light, covering full body/face and needed expressions, mouths, gaze, wings, and sitting. Record differences in color, shadow, gloss, outlines, and unsupported controls. Successful re-import display does not establish equivalent runtime motion.
3. **Inspect the specified interval.** With full-body and necessary face close-ups, review entry, intermediate, hold, and return across the whole submission interval; visible hair/arm/clothing/wing interference; exposed roots/cores; expression transitions. Link findings to a control timetable, recording time, part, operation, and representative image. Recheck corrected intervals and dependencies.

Separate a short diagnostic video from the final video. Carry forward user-specified final length/combinations; do not add a long compilation or all expressions for testing without request. Use [secondary motion/export](secondary-motion.md) to distinguish baked motion from real-time motion, and the previous section to match submission versions.

Example first request: “Create a video showing full body and face during 【specified interval】 with 【natural expression/mouth/wing combinations】. Separate actual-VRM structural checks, re-import under matching conditions, submission-interval visual review, and untested runtime behavior. Report issue times and remaining work.”

## Saving and publication checks

Save input version, panel descriptions, pose, role, and selection with images. Update descriptions with image changes; do not present old parts as images of a newer integrated version.

Examples in this package are restricted to Lida's own production images and original diagrams. Before publication, inspect image text, mixed comparison subjects, and link destinations; exclude personal information, local paths, and private material. Update public-image relative links and [trial-and-error records](trial-and-error.md) together.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
