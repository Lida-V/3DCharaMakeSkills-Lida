# Auto-rig an FBX with Tripo, then adjust it

[Japanese source](../tripo-autorig.md) · Source baseline: 2026-10-20.

For a new moving humanoid, include **neutral shape and bending-region topology → FBX upload → Tripo auto-rig using the VRM 1.0 skeleton → bone/weight adjustment**. Do not jump straight to building every body bone manually. A repair with a usable existing rig, or a nonmoving use, does not require re-auto-rigging.

[Production plan](production-plan.md) · [Process index](process-index.md) · [Bone/topology/weight adjustment](mesh-weight.md)

## Starting goal and inputs

The goal is to preserve the accepted shape, receive a humanoid skeleton and initial weights for VRM 1.0, and prepare for rig adjustment. This is distinct from delivering a finished VRM.

- Accepted neutral shape, front/side reference images, units, character left/right and front/back, reference pose.
- Upload FBX separate from protected source; record target meshes, included/excluded parts, and restoration destination.
- Actual file size; existing UVs, material images, expression keys, and bones; explicitly required round-trip preservation.
- Required motion/destination, received skeleton/weight checks, and later-stage work.

Use a pose in which shoulders, crotch, and fingers are distinguishable. Repair major overlap, fusion, and missing regions first. Prepare finger/joint topology using [deformation-aware structure](mesh-weight.md), then reassess actual bending after auto-rigging.

## Upload FBX; maximum 150 MB

**The actual FBX being sent must be no larger than 150 MB.** Neither ZIP-compressed size nor authoring-file size establishes compliance. The [FBX conditions CLI](model-tools.md) reports actual size and identification format; a matching header does not guarantee complete syntax or Tripo acceptance. Record actual bytes and the limit shown by the service, leaving headroom. The user's 150M requirement also matched “≤150MB” on the [Tripo upload screen](https://studio.tripo3d.ai/ja/workspace/rigging?open=login), checked in the source on 2026-10-19. If the display changes when used, check the current condition.

If too large, investigate in this order, **on a copy only**:

1. Exclude filming backgrounds/props, duplicates, and unnecessary animation data. Do not exclude needed body/joints or protected parts with them.
2. If embedded images dominate, reduce/omit them only in the rigging input. Preserve original UVs/images/materials, restore after import, and compare.
3. If still needed, consider separated parts or a light proxy. Plan bone/weight correspondence back to the original and motion validation; never replace the finished source with the proxy.

Do not uniformly coarsen face/fingers/joints merely for size. Record upload FBX name/version/actual size and all omissions or reductions.

## From auto-rigging to adjustment

1. **Inspect the FBX.** Re-import it and compare scale, orientation, neutral shape, and included parts. Remove old rigs/animation only on the upload copy when necessary, recording removals.
2. **Upload to Tripo.** Explicitly select the humanoid **VRM 1.0** skeleton preset; do not proceed with a different default skeleton. If a pre-execution compatibility check exists, inspect its result.
3. **Receive under a new name.** Associate settings and input FBX with the received file and save an available output format. Record the FBX upload format separately from the received format.
4. **Compare with the source.** Check neutral shape under matching conditions, vertex/face correspondence, UVs, materials/images, and existing keys. If correspondence changed, do not transfer keys/weights using old vertex indices. Choose a preservation route such as fitting the new skeleton/weights to the good original mesh, and check conversion differences before continuing.
5. **Adjust bones before topology and weights.** Inspect the explicit rig/mapping using the [skeleton CLI](model-tools.md), recording [image/motion assessment](mechanical-visual-review.md) separately. Check character left/right, hierarchy, humanoid assignments, joint centers, local axes, and reference pose. Correct misplaced bending centers before aligning face flow and weight transitions. Use [bone/reference-pose checks](mesh-weight.md) and [hand bones/weights](hand-shape.md). Matching names alone does not prove correct mapping.
6. **Check motion and saving.** For shoulders, elbows, hips, knees, ankles, and fingers, inspect intermediate, maximum, and return phases of required individual, left/right, and combined motions. Check clothing/hair/accessory following and penetration; save under another name and reopen. Handoff changing/preserved regions and outstanding expression, secondary-motion, and destination checks.

Auto-rigging is a starting point. A winged humanoid still needs separate designs for the body humanoid skeleton and auxiliary wing bones. Hair/wing/clothing support, eye gaze, expressions, and secondary motion are not automatically finished. After major topology reconstruction, restore weight/dependency correspondence and diagnose the cause rather than repeatedly auto-rigging without a reason.

## Decisions when something goes wrong

| Symptom | Inspect first | Direction |
| --- | --- | --- |
| Too large | Actual upload FBX, embedded images, export selection | Remove unnecessary copy-only data while retaining required shape |
| Wrong bones or unclear humanoid mapping | Selected preset, actual bones/hierarchy/sides | Verify VRM 1.0 correspondence; renaming alone is insufficient |
| Wrong bending location | Joint center, axis, reference pose | Correct bones before topology/weights |
| Shape/expression changes or disappears | Received/source mesh correspondence, existing keys | Do not overwrite the source; return to a preservation-capable route |
| Body moves but clothes/ornaments detach | Same-bone correspondence, weights, parenting, double deformation | Align dependent parts to the same version, then retest movement/penetration |

## Short AI instruction

> Include one Tripo auto-rig stage in the moving-humanoid plan after neutral-shape and joint-topology checks. Keep the source, prepare an upload FBX within 150 MB, and choose the VRM 1.0 skeleton. Compare preservation of shape, UVs, materials, and existing keys in the received skeleton/initial weights before adjusting joint centers, axes, reference pose, humanoid mapping, topology/weights, and clothing/accessory following. Make size reductions on copies. Record neutral/intermediate/maximum/return checks, save/destination verification scope, and remaining work. Do not regenerate usable existing rigs.

## Specifications and verification limits

[Tripo's official Auto Rig documentation](https://developers.tripo3d.ai/en/docs/animations-rig) describes FBX input, a 150 MB limit, and humanoid VRM 1.0 bone naming. This is a **skeleton convention**, not a guarantee of a finished VRM containing expressions, materials, gaze, secondary motion, and metadata. Check correspondence with the [VRM 1.0 humanoid specification](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md) and [actual-output re-import](visual-handoff.md) separately.

This chapter incorporates a user-confirmed production route into future procedures. It does not claim all earlier models used this method, or that an FBX upload/auto-rig was executed while updating these documents.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
