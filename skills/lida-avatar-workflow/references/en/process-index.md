# Process index for an avatar made from images

[Japanese source](../process-index.md) · Source baseline: 2026-10-21.

Start with required materials, execution order, common difficulties, and adjustment methods, then open the chapter for the part you are working on. The official finished distribution ZIP includes the methods and reference model r35, but not the original editable Blend or production environment.

[Use the included finished r35 model as a reference](model-reference.md): observe the VRM inside the skill to study face, hands/fingers, joints, sleeves, materials, secondary motion, and expressions, informing decisions in stages 3–7. Read the model-specific terms and distinguish VRM triangles from original editing topology. Load the relevant parts within the production request.

[Practical feedback from another new character](generation-feedback.md): diagnose hands, the mouth interior, FBX display, donor rigs, and long sleeves. Include these lessons in the initial plan when relevant.

[Recent production lessons](recent-production-lessons.md): diagnose mouth-corner opening, UV/material boundaries, bones and weights, secondary motion, and saved/exported results at the relevant stage.

## Shortest path through the workflow

Begin with a [production plan](production-plan.md), aligning [target quality](quality-goals.md), input version, order/dependencies, change scope, and exit conditions. Diagnose mesh, intersections, materials, hand/finger motion, and eyes. Necessary corrections must not wait for another individual instruction. If a material change's scope is unresolved, show a concrete proposal and confirm only that change.

Before each stage, use the quality chapter's goal record to state and save what will be enough to close that stage. Separate overall completion from a local handoff, carrying forward established directions.

For regions difficult to describe in words, use the [diagram index](diagram-index.md). Map changing areas, directions, and fixed parts to images of the actual model.

Choose stages needed for the use. For still/display work, do not mandate unnecessary rig, expression, or engine tests; require reproduction of the finished specified view from the saved source. This does not waive essential stages or motions for moving use.

| Order | Work | Ready to proceed when… (adapt to the use at stage start) | References |
| --- | --- | --- | --- |
| 1 | Propose finished quality and make the plan | A short plan covers purpose/distance/motion/destination, five-area diagnosis/corrections, scope, dependencies, exit conditions, and deliverables. | [Plan](production-plan.md), [quality/goals](quality-goals.md), [inputs](input-materials.md) |
| 2 | Prepare body, clothing, outerwear, heads with/without hair, hands, and required expression sheets | Face/proportions/scale match; head/hair composition regions are chosen. The neutral expression, required pattern list, generated/compared sheets and individual images can lead to needed individual 3D references. | [Inputs](input-materials.md), [three-view/head-hair composition](multiangle-threeview.md), [expression sheets](expression-sheets.md), [hand references/landmarks](hand-shape.md) |
| 3 | Inspect rough 3D neutral shape and eye construction | Front/side/oblique views match proportions, facial volume, silhouette, and connections. Eye openings, spheres, images, and rotation centers are checked; only necessary additions are selected. | [Repair/completion](mesh-repair-completion.md), [eyes](eye-modeling.md), [adjustment methods](adjustment-methods.md), [AI instructions](ai-instructions.md) |
| 4 | For a new humanoid, auto-rig an FBX with Tripo's VRM 1.0 skeleton, then adjust bones/topology/weights | Upload FBX is within 150 MB; received version and preservation against the source are checked. Bone reference pose, centers/axes, bending bands, faces, and weights correspond; required intermediate motion has no major collapse/stretch. | [Initial Tripo rig](tripo-autorig.md), [topology/weights](mesh-weight.md), [knees](knee-edge-placement.md), [hand topology/joints](hand-shape.md) |
| 5 | Adjust mouth, eyes, hands, clothes, wings, and penetration | Specified-scene issues are corrected, with fixed parts, boundaries, and dependencies checked. Test individual/combined/intermediate/return motion and new penetrations for each relevant part pair. | [Expressions](expression-adjustment.md), [winks](wink-closure.md), [mouths](mouth-shapes.md), [hands](hand-shape.md), [clothes](skirt-hidden-modeling.md), [wings](wing-workflow.md) |
| 6 | Finish UVs, color, and materials on stable parts | Mesh/UV/image/material correspondence is aligned; colors, lines, seams, and movement-related stretching at the intended distance remain checkable after reopening. | [Accessory materials](accessory-materials.md), [UV/image/material handoff and adjustment](adjustment-methods.md) |
| 7 | Integrate and check saving/destination | Dependency versions and bone reference states agree; full body and reopened reproduction are checked. Submission images/video match the version. If the destination is untested, label it a handoff candidate only. | [Integration/saved versions/images](visual-handoff.md), [trial and error](trial-and-error.md) |

In stages 3–7, separate [mechanical checks, image comparison, motion review, and save/destination checks](mechanical-visual-review.md). Alongside relevant CLI results, assess front/side/oblique views from the same saved model, normal viewing distance, close-ups of the issue, and required intermediate/return motion. Reject candidates whose appearance worsens even if numbers improve.

Make small early export trials for mechanisms that may be lost. Blender appearance and reproduction in the destination need separate checks. For missing surfaces, incorrect connections, or insufficient parts in stages 3–5, use [repair-method selection and construction](mesh-repair-completion.md). After changing faces, restore UV, material, normal, weight, expression, and dependent support-surface correspondence. For silver, gems, and fittings in stage 6, use [material diagnosis before repainting](accessory-materials.md).

In stage 4, after neutral shape and joint topology, follow [upload FBX → Tripo VRM 1.0 skeleton → preservation comparison → rig adjustment](tripo-autorig.md). Do not unconditionally regenerate a good rig. Receiving an initial skeleton differs from finishing a VRM.

Connect stage 2's [expression sheets/individual images](expression-sheets.md) to stage 5's local mouth, eyelid, and emotion keys. The sheet serves comparison; individual images and 3D models serve shape reference; one saved face mesh is the deformation target. For hair/feather motion, establish shape and basic deformation before [secondary motion and export](secondary-motion.md).

Use the [wing workflow from references through support body, feather rows, and movement](wing-workflow.md). Before placing many feathers, inspect support-body thickness/joints with feathers hidden, and the attachment surfaces and intermediate motion of a few feathers.

Use the [hand workflow from references through nails and motion](hand-shape.md). Inspect open-hand proportions/thickness, knuckle arrangement, and thumb/web connections from stage 3; do not postpone them until after shape is supposedly fixed.

Use the [hair workflow for references, strands, roots, materials, and secondary motion](hair-workflow.md). First test total length, width/thickness, roots/tips, and face/arm passages with a few strands, then expand. Do not hide structural deficits with color/gloss; add secondary motion after basic deformation is stable.

If feather names and regions are unclear, map numbers from the [primary/secondary/tertiary and covert layout](wing-feather-terms.md) onto the art. General bird structure does not prescribe mandatory counts or row numbers for a fantasy wing.

For mottled stage-6 shading, use [AO diagnosis and UV separation for added hair](adjustment-methods.md). In stage 7, check [actual VRM re-import and specified motion](visual-handoff.md), then hand off the [provisional completion boundary](quality-goals.md) and remaining work.

If color, shading, gloss, outline, or transparency changes between destinations in stages 6–7, use [destination appearance adjustment](cross-engine-look.md). Separate common-source problems from rendering differences for dark mouth interiors or feather edges; manage cross-shot reference images and material presets there too.

Final cloth finishing branches by destination. For final Blender images, finish its physical appearance there. For an engine handoff, the local goal is shape assets, corresponding controls, and integration conditions; inspect completed tension, motion, and contact in the destination.

## Where to use the bundled tools

Use [model tools](model-tools.md) for upload-FBX format/size, stage-4 skeleton/humanoid mapping and named meshes, and topology/UV/weight/key checks in stages 3–5. Compare before/after changes or the stage-7 saved version item by item. Judge shapes, roots, and joints through images and motion. If only weight sums are wrong, use normalization limited to a copy. For eyes, follow the [sphere/iris/line-layer/gaze workflow](eye-modeling.md).

## What to give the AI at each stage

- Confirmed input version, target art, and neutral shape.
- Views, poses, and close-ups that expose the issue.
- Changing parts, fixed forms, connection boundaries, related clothes/ornaments.
- Motions under matching conditions and exit conditions.

Beyond “natural” or “round,” show which silhouette, thickness, or motion is required on the image. [Visual handoff](visual-handoff.md) and [AI instructions](ai-instructions.md) provide requests.

## Checks that reduce rework

1. Do not try to fix steps/indentations already present in neutral shape through weights alone.
2. Align bending regions and weight transitions rather than merely adding points/faces.
3. After topology changes, check keys, UVs, clothing, and ornament correspondence.
4. Integrate accepted deltas with dependencies; do not mix in old bones or nails.
5. Record local improvement, visual selection, full-body integration, and destination checks separately.

Identify diagrams as targets, problems, design proposals, or actual comparisons. Dashed placement proposals and unmet examples must not become supposedly finished structures.

## About Lida's examples

Dimensions, angles, and point counts were tried for this body and use. Re-establish them from landmarks and movement for another character rather than copying them as defaults.

Appearance choices for face, hair, and clothing are in [Lida's design/preferences](lida-design.md). Use the stage chapters for technical verification.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
