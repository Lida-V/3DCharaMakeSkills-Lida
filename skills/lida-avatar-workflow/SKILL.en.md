# Lida Avatar Workflow

[Japanese / 日本語](SKILL.md) · [English](SKILL.en.md)

Use the language requested by the user. For English, use this guide and only the needed [English references](references/en/README.md). For Japanese, use [SKILL.md](SKILL.md) and the relevant Japanese chapters. Do not load both language trees in full. Switching language does not change the production scope or permissions. English source baseline: 2026-10-21.

Select reusable decisions and concrete instructions from the lessons of Lida's production. For beginners, briefly explain materials, execution order, adjustment methods, and common difficulties. Separate Lida-specific appearance choices from technical problems.

This skill packages knowledge, request methods, production helper scripts, and a production reference model. New production from images assumes a service such as Tripo generates base models or part-specific references, followed by correction and finishing in software such as Blender. Existing-model corrections do not require regeneration. The official finished distribution ZIP includes reference model r35. Modeling software, 3D generation services, image-generation APIs, connectors, credentials, and the original editable Blend are not bundled. Before actual work, check available methods in the current environment and prioritize the user's instructions.

## Carry forward usage terms and attribution

Commercial and noncommercial use of this Skills material is permitted, including sales of models made using the methods, commissioned work, and incorporation into commercial apps or Skills. Check generation-service and third-party-material conditions separately. The included reference model has model-specific terms.

Creating models, images, or video alone does not require credits on those outputs. When creating an app or new Skills package for publication, actually record the source name, Lida, original URL, and used/modified portions in README, About, or NOTICE, and report the location. This does not claim ownership of general methods or require changing the entire destination project's license.

Use [usage categories, examples, and helper](references/en/usage-and-attribution.md), the bundled [LICENSE](LICENSE), and [NOTICE](NOTICE.md). [English license](LICENSE.en.md) and [English notice](NOTICE.en.md) are companion translations. Reading alone must not write automatically to another project; retain attribution within the request to create the published work. Do not distribute reference dance FBX or converted reference motion.

The Blender helper `lida_model_tools.py` separately uses **GPL-3.0-or-later**. Retain its notices and [GPL text](scripts/LICENSE-GPL-3.0-or-later.txt); do not apply this documentation's additional attribution conditions to GPL code. See [tool scope and terms](references/en/model-tools.md).

Only when a shader is needed, check the [separately distributed LidaAngelToon](references/en/shader-setup.md). It is optional for this Skills package. Do not promise unimplemented Unity/UE support.

Follow the [finished-model reference guide](references/en/model-reference.md) to use the included China/Wafuku character r35 as a component for studying shape, bones, weights, materials, expressions, and secondary motion. Its location is `assets/model-reference/china-wafuku/ChinaWafuku-Reference-r35.vrm`. Inspect the relevant structure within a production request; reading alone must not start model processing or environment changes. Redistribution of the model and sale of modified versions are prohibited, so do not redistribute the complete ZIP containing it. Documents and code separated from the model retain their existing respective terms. Read the [model-specific terms](assets/model-reference/china-wafuku/MODEL-TERMS.en.md).

## Read only what is needed

When production is requested, start with a [production plan](references/en/production-plan.md). Briefly align purpose, quality, input version, order/dependencies, changing/fixed regions, exit conditions, and deliverables. Always include **mesh correction, penetration correction, material correction, hand/finger motion correction, and eye modeling/adjustment** in the diagnostic plan. Track unchecked / needed / unnecessary (reason) / deferred (reason) / done. Needed corrections must not wait for separate instructions. Do not force every area to be rebuilt; keep part-only requests local.

For expressive work, include [expression-sheet and individual-image generation](references/en/expression-sheets.md) in initial reference preparation. From the accepted neutral face, list required mouth shapes, ordinary blink, left/right winks, and emotions; plan missing-image generation and comparison. Reuse good references/keys. Send only necessary individual images to 3D reference generation, not the entire sheet as input for one head.

For a new moving humanoid, after neutral-shape/joint-topology checks, include [Tripo auto-rigging](references/en/tripo-autorig.md). Introduce a VRM 1.0 skeleton with an upload FBX within 150 MB, compare preservation against the source, then adjust bones, weights, and dependencies. A usable existing rig needs no regeneration.

For materials, establish allowed changes to parts, faces, actual material data, shared users, images/UVs, nodes, and values. Existing instructions that settle the scope need no repeated approval. If unresolved design, palette, image, or shared-user changes are necessary, show a concrete proposal and impact; confirm only that change and continue independent work.

Read [quality targets and stage goals](references/en/quality-goals.md) at production start and before each stage. Initially propose concrete quality and reasons from purpose, viewing distance, required motions, and destination. For each stage, briefly present and record target state, comparison/exit conditions, changing/fixed regions, deliverables, and later-stage work.

Carry forward established quality, purpose, and art without approval at every routine start. Separate final quality from local handoff goals. Do not reduce quality or required movement to conceal an unmet goal.

For broad work, choose from the [process index](references/en/process-index.md). Do not load all references at once.

For directions, change regions, or connections, select only needed figures from the [diagram index](references/en/diagram-index.md). Map figure numbers to actual images; distinguish schematics from earlier actual-mesh diagnosis. PNGs serve display/attachment, SVGs enlargement. Shared diagrams retain Japanese labels; use their English captions and legends.

| Current work | Read |
| --- | --- |
| Initial plan, preventing omitted corrections, stage order | [Production plan/five-area diagnosis](references/en/production-plan.md), [quality proposals/goals](references/en/quality-goals.md) |
| Inspect a finished example's face, hands/fingers, joints, sleeves, materials, secondary motion, and expressions | [Included r35 model: reference procedure and terms](references/en/model-reference.md) |
| Finger, mouth-interior, FBX-round-trip, or sleeve issues in new production | [Feedback from another new production](references/en/generation-feedback.md) |
| Mouth corners, UV/material boundaries, rigging, secondary motion, or save/export issues in recent production | [Recent production lessons](references/en/recent-production-lessons.md) |
| Art, base body, clothing, part references | [Input materials](references/en/input-materials.md), [multiple angles to three-view sheets](references/en/multiangle-threeview.md) |
| Initial rig from FBX, 150 MB size preparation | [Tripo auto-rigging/VRM 1.0 skeleton](references/en/tripo-autorig.md) |
| Topology, joints, skin weights | [Topology/weights](references/en/mesh-weight.md), [knee edge placement](references/en/knee-edge-placement.md) |
| Diagnosing shape, shading, or following | [Adjustment methods](references/en/adjustment-methods.md) |
| Accessory reflections, gems, decorative lines; image versus material cause | [Accessory material correction](references/en/accessory-materials.md) |
| Missing/incorrect faces, filling, boundary connection, missing-part completion | [Mesh repair/completion](references/en/mesh-repair-completion.md) |
| Appearance between engines/shots, dark mouth interior, dark feather edges | [Destination appearance adjustment](references/en/cross-engine-look.md) |
| Unnatural appearance/movement despite mechanical success; scope and selection | [Mechanical/image/motion assessment](references/en/mechanical-visual-review.md) |
| Executable topology/UV/weight/key checks; saved-version comparison | [Model tools](references/en/model-tools.md) |
| Eyeballs, iris, sclera, gaze | [Eye modeling](references/en/eye-modeling.md) |
| Eyes, mouth, expressions | [Expression adjustment](references/en/expression-adjustment.md), [mouth shapes](references/en/mouth-shapes.md) |
| Missing expression references; required patterns from neutral face | [Expression sheets/individual images](references/en/expression-sheets.md) |
| Ordinary blink versus smiling closed eyes, left/right winks | [Wink closure](references/en/wink-closure.md) |
| Initial hands, finger topology/bones/weights, nails, steps after shortening | [Hand production/adjustment](references/en/hand-shape.md) |
| Hair references, strand structure, hairline, material, secondary motion | [Hair workflow](references/en/hair-workflow.md) |
| Layered clothing, hidden body, penetration | [Skirt/hidden-body completion](references/en/skirt-hidden-modeling.md) |
| Wing design, support body, feather rows/roots, weights, opening/closing | [Wing workflow](references/en/wing-workflow.md) |
| Whole-wing feather regions, terminology, upper/lower faces, overlap | [Feather layout/terms](references/en/wing-feather-terms.md) |
| Hair/feather secondary motion, export rig, destination checks | [Secondary motion/export](references/en/secondary-motion.md) |
| Image-based requests, selection, failure records | [Visual handoff](references/en/visual-handoff.md), [trial and error](references/en/trial-and-error.md), [AI instructions](references/en/ai-instructions.md) |

## Establish inputs and change scope

- Align accepted neutral shape, current candidate, art version, purpose, required motions, and reference pose. The newest number alone does not identify the accepted shape.
- Separate base body → clothing → outerwear stages while retaining one character's proportions, scale, and pose. Check facial volume across multiple angles before organizing three-view sheets.
- Prepare initial head three-view sheets both with/without hair, then generate with the same face/skull/scale. Compose the without-hair face/head with selected hair/roots from the with-hair version, removing duplicate heads and resolving fused regions. Use [reference/composition steps](references/en/multiangle-threeview.md). Distinguish this from the no-face requirement for hair-only inputs; do not regenerate an already good model.
- Label references by role: target/approved shape, problem, candidate, design explanation. A failure image is not a finished target.
- Supply matching front/side/oblique views and needed close-ups; inspect neutral form first. Do not try to fix neutral-form steps/indentations with bones/weights alone.
- Specify target, fixed areas, allowed changes, connection boundaries, and exit conditions. Keep recoverable deltas back to good approved shapes; do not overwrite protected sources.

## Use production tools at the relevant stages

Where Blender is available, inspect the [bundled tools](references/en/model-tools.md). Use `audit` after receiving rough 3D and around topology/UV/weight/key corrections; use `snapshot` and `compare` for fixed-item checks. Select bundled functions before generating the same inspection code again.

Specify meshes, rig, input version, and output paths. Start diagnosis in a separate session. Use `normalize-copy` only when weight sums need correction, preserving the source. After receiving/changing bones, use `rig-audit` on explicit rig, humanoid map, and meshes. Before FBX upload, inspect format/actual size with `lida_file_check.py`. Read untested scope in JSON, then [inspect images/movement from the same saved version](references/en/mechanical-visual-review.md). CLI 0 or better numbers alone do not pass modeling, deformation, or destination behavior. Re-diagnose unnatural appearance as unmet. Record unavailable execution as not performed. Reading the skill alone must not start model processing or environment changes.

## Align mesh and movement

- Verify units, character left/right and front/back, bone center/long axis/rotation axis, and destination reference pose. Do not specify directions solely by screen up/down.
- Identify actual bending bands in neutral/intermediate/maximum poses. Map compression, extension, face flow, and weight transitions on images.
- For knees, elbows, and fingers, design closed loops across the long axis with connecting longitudinal edges. Do not concentrate bending on one central line.
- Select/move existing loops to establish spacing; add only where needed. Counts, horizontal loops, and example millimeter values are not universal answers.
- For shoulders/hips, design multidirectional flow and branching. Do not directly apply a one-direction cylinder diagram. Judge poles, density changes, and long thin faces relative to strong deformation bands.
- Do not pass/fail solely by quads versus triangles. Inspect holes, duplicate/interior faces, disconnected boundaries, reversals, and steps while preserving good outlines/connections.
- For new humanoids, use [FBX → Tripo auto-rig → VRM 1.0 skeleton](references/en/tripo-autorig.md) as the initial setup, then move/adjust bones and weights early. Retain good existing rigs. Record row layout separately from weight transitions; check intermediate bending/twisting, left/right/combined motion, volume, and penetration.
- Make expression deltas for target regions on one reference face. For mouth-only changes, fix jaw, face outline, and outside-mouth regions; inspect individual keys, intermediate values, and combinations.

## Choose corrections for the cause

- Diagnose shape, topology, bone placement, weights, normals, and images/materials separately. Better numbers with unnatural matching-condition images remain unmet.
- Blend local changes gradually into surroundings without new steps at fixed boundaries. When shortening hands, also inspect thickness and thumb → web → finger continuity.
- Correct large visible penetrations, tears, and collapse first. Small outline improvements do not resolve major problems. Assess hidden overlap by actual appearance/use.
- If repeated coefficient changes for the same cause do not improve appearance, stop repeating the failing approach and re-diagnose connections, cloth allowance, support, and reference shape.
- Treat partial success, contact in finitely sampled poses, persistence, physics, and destination reproduction separately. Do not extend success beyond checked scope.

## Integrate parts and check again

- Verify input versions, joints/weights, normals, and control dependencies together. Use [integration/saved-version verification](references/en/visual-handoff.md).
- Treat accepted deltas, input version, joint table, weight rules, and nails/clothes/ornament versions as a set. Do not combine changed hands with old finger bones or nails.
- Determine shape delta → necessary bone generation/weight updates → dependency following → part cleanup/renaming order from actual dependencies. Avoid applying a delta twice.
- After topology changes, recheck vertex-index-dependent keys, UVs, support surfaces, ornaments, and inspection data. Do not reuse old correspondence on changed shape without verification.
- A full-body candidate image does not prove the latest versions of every part are present. Compare actual integrated meshes, bones, and parts with inputs.
- Final UVs/materials follow stable shape and basic deformation in changed parts. Test export dependencies before finishing; inspect lines/seams at final resolution and viewing distance.

## Handoff images and production notes

- Accompany images with figure numbers, panel meanings, character direction/pose, inspection region, fixed parts, and exit conditions. Numbers/schematics alone do not establish actual results.
- Distinguish actual edges, trial guides, schematics, and acceptance images rendered from saved models. Do not redraw verification images with generation.
- Separate states: proposal, implementation, local check, user selection, full-body integration, save/reopen, export/destination verification. Record unfinished work and selection.
- Distinguish exact equality from within tolerance; verify the saved model version used for images/video. An older video after a same-name resave is not current acceptance evidence.
- Merge later-added conditions into the next initial request. Record actual inputs, cause, changing region, preservation, comparison, and remaining work. Example numbers are not universal defaults.
- Prioritize user assignment instructions. Astra/Opus assessments are observations from individual production, not universal rankings or evidence of an unconfirmed assignee's work.
- A 54-bone humanoid, no auxiliary bones, maximum 2K, and similar conditions belong to Lida's production use. Do not apply them automatically elsewhere; check that destination's requirements.
- Distribution/article images are restricted to your own production models/original diagrams. Do not reproduce external-model images, names, or mixed comparisons. Separate appearance preferences into a short note.
- Record reusable improvements in the project's designated authoritative documents and knowledge log. Do not copy private absolute paths, credentials, or unorganized production logs into distributed material.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
