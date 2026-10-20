# Make the production plan first and include necessary corrections

[Japanese source](../production-plan.md) · Source baseline: 2026-10-20.

When production is requested, first combine **completion conditions, necessary diagnosis and corrections, execution order, and permitted changes** into one plan. Inspect any existing model and add needed stages proactively. Do not wait for a separate instruction such as “fix the hands next” for every part of the same commission.

Reading the skill alone does not begin environment changes or model processing. Apply it to the objects and scope authorized by an actual production request. A one-part correction needs a plan for that part and necessary dependencies, not a full-body rebuild.

[Quality proposal and stage goals](quality-goals.md) · [Process index](process-index.md) · [Concrete AI requests](ai-instructions.md)

## 1. Align completion conditions and permitted changes

| Plan item | Record briefly |
| --- | --- |
| Purpose and quality | Use, viewing distance, and what must be shown. Use [quality goals](quality-goals.md) for the proposal and reasons. |
| Reference materials and input version | Accepted art, multiple views, model, bones, keys, materials, and image versions. For a new head, plan [with-hair/without-hair three-view sheets and composition after generation](multiangle-threeview.md). Identify protected sources and work copies. |
| Required motions and expressions | Actual motions, left/right gaze, blinks, winks, and other expressions. Plan missing-material assessment, generation, and comparison of [expression sheets and individual images](expression-sheets.md), and needed individual 3D references. For still use, specify the camera angle. |
| Destination and deliverables | Authoring software, format, destination app, and required scope of models, comparison images, video, and change records. |
| Changing and fixed areas | Allowed parts, faces, shapes, bones, weights, keys, materials, and images; preserved design and areas outside scope. |
| Order and dependencies | Base shape/joint topology → [FBX/Tripo auto-rigging](tripo-autorig.md) for a new humanoid → bones, topology, and basic deformation → required expressions/motions → UVs/materials for stable parts → integration/export. Independent work may run in parallel. |
| Initial rig | For a new moving humanoid, introduce a VRM 1.0 skeleton with an upload FBX no larger than 150 MB. Plan input/received versions, size reduction, preservation comparison, and later rig/weight adjustment. Reuse a serviceable existing rig. |
| Exit conditions | Separate scope and results for [mechanical checks, images, motion, and save/destination checks](mechanical-visual-review.md). Include matching views/motions, checks after saving, the boundary being closed, and remaining work. CLI success alone is not completion. |

Carry forward established purpose, quality, art, and preservation conditions. For minor gaps, state assumptions and advance what is understood. If missing information affects an accepted design or permitted changes, present a concrete proposal for that area and seek confirmation.

Do not merely list expression sheets as materials the user must supply. The initial plan includes: establish accepted neutral-face version → list required patterns → generate/compare missing sheets or individual images → necessary individual 3D references → local keys. Use good existing material/keys and record why regeneration is unnecessary. Keep the five-item table below for structural and corrective diagnosis; record expression-reference readiness separately in this plan.

## 2. Include all five areas in the diagnostic plan

Record each as **unchecked / needed / unnecessary (reason) / deferred (reason) / done**. “Unchecked” means not yet investigated; “deferred” has a reason work cannot proceed and a resumption condition. Missing references or absent testing do not mean “unnecessary” or “done.”

For overall production, diagnose all five against the actual model and intended use. For a local request, retain the table and mark unrelated items “unnecessary (outside this request).” That does not claim the whole model was checked.

| Required diagnostic area | Inspect first | Corrections and exit conditions to plan when needed | Details |
| --- | --- | --- | --- |
| Mesh correction/completion | Neutral silhouette, volume, steps, gaps, incorrect connections, intentional openings, bending bands, and face flow | Choose local correction, filling, boundary connection, or reconstruction for the cause. Restore necessary attribute correspondence; check fixed regions, neutral shape, required motion, and reopening. | [Repair/completion](mesh-repair-completion.md), [topology/weights](mesh-weight.md) |
| Penetration correction | Offending part and counterpart, pose/time, neutral or moving, visible protrusion versus intended overlap | Separate shape, basic deformation, keys, and secondary-motion causes. Compare intermediate/return phases and related part pairs so a correction does not transfer a new penetration elsewhere. | [Cause isolation](adjustment-methods.md), [clothing/completion](skirt-hidden-modeling.md), [secondary motion](secondary-motion.md) |
| Material correction | Part → faces → actual material data → images/UVs → nodes/values → other users of shared data. Separate import/light/exposure from material causes. | Define scope with the table below. Correct only authorized layers; check preservation of shared users, original images and shapes, reopening, and the specified destination. | [Accessory materials](accessory-materials.md), [destination appearance](cross-engine-look.md) |
| Hand/finger motion correction | Both hands' fingers, thumbs, webs, bone centers/axes, weights, nails/sleeves; required grip/input motions as well as an open hand | Correct shape, topology, bones, weights, or pose according to the cause. In the same version, inspect required individual-finger motions, gripping, thumb opposition, intermediate/return phases, and dependent parts. | [Hand workflow](hand-shape.md) |
| Eye modeling/adjustment | Existing openings, spheres, images, rotation centers, fixed lines; required gaze, surprise, blinks, and left/right winks | Preserve or locally adjust adequate existing structure; add only missing surfaces/images. Check closed and intermediate states, gaze combinations, and export. | [Eye workflow](eye-modeling.md), [eyelids/expressions](expression-adjustment.md) |

This does not require changing all five. The table identifies necessity and prevents omitted requests. A still image with no finger motion may not need finger-motion tests; eyes already meeting the use do not need rebuilding. Do not reduce a required movement range to mark an item unnecessary.

## 3. Specify what material changes are allowed

“Material correction is OK” does not authorize unlimited changes to the art's palette, patterns, images, or all shared materials. Add a row for each target in the initial plan.

| Target part/faces | Actual material and shared users | Allowed layer/settings | Fixed items | Concrete proposal needing confirmation |
| --- | --- | --- | --- | --- |
| Specified crown faces (example) | Actual silver material, also used by waist ornaments | Assign a crown-only duplicate and adjust gloss strength, if already authorized | Palette, original image, UVs, shape, waist-ornament material | Only if repainting the pattern image proves necessary: scope and comparison proposal for that change |

This example's material separation and permission do not apply automatically to every request. Record the actual part/face range, image references/UV layer, node connections and values, and affected shared users. Identical names do not establish shared material data.

- **Scope is established:** Follow existing instructions through diagnosis, authorized correction, comparison, and saved-result checks. If “fix crown overexposure while preserving color and pattern” can be met by crown-only gloss adjustment, proceed within that request. Do not repeatedly seek approval for routine work.
- **Scope is unresolved:** Explain the cause and which colors, design, images, or shared users would change, using proposals under matching conditions. Confirm only that change and preserve the source until then.
- **Other work can advance:** Continue checks of shape or fingers that do not depend on the unresolved material change. Do not put all production on hold.

The actual adjustment procedure and preservation tests are in [accessory material correction](accessory-materials.md).

## 4. Execute the plan through verification

1. Align the input version and reference images; diagnose the five areas. Add needed corrections with target, cause, change scope, and dependencies.
2. Briefly present a [goal card](quality-goals.md) before each stage. Do not start final UV/material finishing for a part whose base or basic deformation is unresolved. Also make small early tests of features export may lose.
3. Within the production request, carry needed diagnosis, authorized corrections, and result verification through to completion. Merely reporting “correction needed” must not return the same authorized work to a wait for separate instructions.
4. Record CLI results separately from [image and motion assessment](mechanical-visual-review.md). Better numbers with unnatural appearance are still unmet. Under matching conditions, check neutral → intermediate → required maximum → return, and preservation outside scope. Save under a new name and reopen. Check the destination separately within the specified scope.
5. If the next stage's entry conditions are met and overall production includes it, record the next input version and goal and continue. For a local request, hand off the local results and remaining work and close that scope.

If sources/fixed parts change, a new failure appears, or two consecutive candidates for the same cause do not improve actual-use appearance, return to [re-diagnosis and records](trial-and-error.md) instead of accumulating patches. Separate local improvement, user selection, full-body integration, saving, and destination acceptance.

## Record template

```text
Purpose; normal viewing distance/framing:
Quality proposal, reason, priority parts:
Required motions/expressions; destination/format:
Reference/input version; protected source/work copy:
Expression references: neutral-face version; patterns; missing sheets/images and generation plan; required 3D references:
Initial rig: existing rig; upload FBX/measured size (within 150 MB); Tripo VRM 1.0 setting; received version/preservation; adjustments/remaining work:
Allowed changes; fixed scope:
Deliverables and completion boundary for this request:

Area                         Status       Evidence/target; next action
Mesh correction/completion   unchecked
Penetration correction       unchecked
Material correction          unchecked
Hand/finger motion           unchecked
Eye modeling/adjustment      unchecked
Status: unchecked / needed / unnecessary (reason) / deferred (reason) / done

Execution order and part dependencies:
Each stage: target state, changing/fixed scope, comparison, exit conditions:
Separate results/unverified items: mechanical / images / motion / save and destination:
Material targets: parts/faces, actual data/shared users, images/UVs, nodes/values:
Deferred items/reasons; missing information or confirmation; resumption conditions:
Next input version, entry conditions, work to continue within this request:
At completion: verified scope, unmet items, untested destinations, remaining work:
```

## Example initial AI instruction

> Use this Skills package and the attached art/model to produce 【specified quality】 for 【purpose】. First align purpose, viewing distance, required motions/expressions, destination, references/input versions, and allowed/fixed scope. Make a short production plan with a quality proposal and reason, stage order/dependencies, exit conditions, and deliverables.
>
> If expressions are needed, establish the neutral-face reference version and pattern list; plan missing-material assessment, generation, and comparison of expression sheets and individual images. Do not wait for separate instructions just because references are missing. Send only the needed individual images into 3D reference generation and use them for local keys on one face. Do not regenerate serviceable existing references or keys.
>
> Include mesh correction, penetration correction, material correction, hand/finger motion correction, and eye modeling/adjustment in the diagnostic plan. Track unchecked / needed / unnecessary (reason) / deferred (reason) / done. For necessary corrections, continue through diagnosis, authorized correction, and result checks within this production scope without waiting for me to request each separately. Do not uniformly rebuild everything or recreate eyes.
>
> For a new moving humanoid, check the neutral shape and joint topology, then send an FBX no larger than 150 MB to Tripo for a VRM 1.0 skeleton auto-rig. Compare preservation between the source and received result, then adjust bones, weights, and dependent parts. Do not regenerate a usable existing rig.
>
> Specify material scope down to parts, faces, actual material data, shared users, image/UV references, node connections, and values. Already authorized changes need no repeated approval. If unresolved color, design, image, or all-shared-material changes are necessary, show a concrete proposal and impact, and confirm only that change. Continue independent work meanwhile.
>
> Record target state, fixed areas, comparison conditions, and exit conditions for each stage. Check neutral, intermediate, required maximum, return, reopening, and the specified destination. Once the next stage's conditions are met, continue within the request; retain deferral reasons, resumption conditions, and unverified scope.

For a part-only request, replace the opening with “Correct only 【part】 to 【target state】” and mark unrelated diagnostic areas outside scope. The example itself grants no additional permission for environment changes or external publication.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
