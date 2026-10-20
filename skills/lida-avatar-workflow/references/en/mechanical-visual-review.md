# Combine mechanical checks with appearance and motion review

[Japanese source](../mechanical-visual-review.md) · Source baseline: 2026-10-20.

**The CLI helps prevent missed checks. Mechanical success alone does not make modeling or motion complete.** Inspect agreement with the art, natural deformation, and reproduction after saving/in the destination separately.

## Define review scope first

In the [production plan](production-plan.md) and [stage goals](quality-goals.md), record input version, changing parts, preserved features, normal viewing distance, required views/motions, destination, review material, and remaining work outside this stage. Carry forward established conditions without repeated approval for routine checks.

For still use, focus on specified camera/lighting and saved-result reproduction, without unnecessary full-body movement tests. For local corrections, limit scope to the target and dependencies. This does not permit shrinking required motions to exclude a defect.

## Separate four kinds of review

| Review | Investigate | Exit condition and limit |
| --- | --- | --- |
| Mechanical | File size, required bones/hierarchy/mapping, target-mesh assignments, before/after preservation, and each CLI's implemented items | Relevant conditions pass and warnings/untested items are read. Bone placement aesthetics and natural deformation need separate review. |
| Image comparison | Art features, proportions, silhouettes, thickness, joint positions, materials/shading | Reference/candidate meet the target at specified views/distances under matching conditions. Close-ups alone do not establish overall balance. |
| Motion | Collapse, stretch, creases, penetration during bending, dependent following, return | Required individual/combined movements have no conspicuous failures and return to reference. A few sampled images do not establish safety at all times. |
| Save/destination | Save/reopen, export/re-import, display/controls in the required runtime | The result reproduces. Separate authoring-software acceptance from destination acceptance; retain untested items as remaining work. |

Exit code `0` covers only the command's defined processing/check scope. Completion of `audit` is not aesthetic acceptance. See [model tools](model-tools.md) for `rig-audit`, upload size checks, and reading reports.

Correct bone names/counts do not resolve a bulging shoulder during arm raise, lost hand thickness when gripping, or a folded knee silhouette at intermediate angles. Diagnose bone location, face flow, weights, and controls; do not alter approved art or a good shape merely to fit numbers.

## Review actual images and movement in this order

1. **Align reference and candidate versions.** Use saved models and associate input hash/target names with mechanical reports, images, and video. After correction/re-saving, update affected checks and evidence. Label old images as older versions.
2. **Match conditions.** Align camera, pose, lighting, and materials; compare necessary front/side/oblique views. Assess overall balance at normal distance, enlarging only problem areas. Plain materials/wireframes help diagnose causes; also check actual materials.
3. **For moving use, inspect individual neutral → intermediate → required maximum → return.** Check abrupt deformation/switches between endpoints. Add required combinations: arm plus torso for shoulders, gripping including thumb plus wrist for hands, knee bending plus leg direction for knees, for example. Choose actual-use combinations.
4. **Inspect dependencies and reopening.** Display corresponding clothes, nails, ornaments, shadow layers, and similar parts. Restore parts hidden for diagnosis. Inspect after reopening and in required destinations. Record issue time/view/part.

Verification images come from the actual saved model. Generated images and schematics are targets/explanations, not replacement evidence for corrections. Use [visual handoff](visual-handoff.md) for image/version correspondence and [trial and error](trial-and-error.md) for cause isolation/re-diagnosis.

## Record selection and remaining work

Do not convert decreasing mechanical counts, bone counts, or general ratios into automatic aesthetic acceptance. Reject worse-looking candidates despite better numbers and retain the supporting comparison. Instead of one completion flag, record “pass / unmet / unchecked / outside scope (reason)” for each review.

```text
Input version/hash: [reference] → [candidate]. Changing region: [ ]. Fixed region: [ ].
Mechanical: [result/items/report]. Untested: [ ].
Images: [result/matching views and distances/images].
Motion: [result/individual, intermediate, maximum, return/required combinations/video times].
Save/destination: [result/environment/evidence].
Selection: [candidate, local selection, full-body integration, or other scope]. Remaining work/next input: [ ].
```

## Short AI request

> Adjust [target] in [input version] for [purpose/goal]. First plan the scope of mechanical checks, matching-condition images, required motion, and save/destination review. Preserve [conditions]. Include dependent parts when checking normal distance and necessary close-ups, neutral → intermediate → maximum → return, and [combined motions]. If appearance is unnatural despite mechanical success, mark the goal unmet. Report actual images/video tied to the saved version, verified scope, and remaining work separately.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
