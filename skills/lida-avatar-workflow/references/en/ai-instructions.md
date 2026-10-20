# Instructions to give the AI from the first request

[Japanese source](../ai-instructions.md) · Source baseline: 2026-10-20.

Beyond “natural” or “smooth,” provide each material's role, changing region, preserved features, adjustment values, comparison conditions, and exit conditions. Follow the user's assignment preferences. Record observations about detail recognition or correction quality for that stage, without turning them into universal model rankings.

## Assigning different work

These are the user's assessments during Lida production as of 2026-10-15, not a comparison with identical inputs, time, and tools.

- **Opus 5.5:** Often entrusted with final modeling corrections involving appearance and overall balance, and assessed as working well in this production. Also used for comparison proposals, direction, and stage boundaries. This updates the earlier, then-current preference for Astra in art matching. Because it takes time, focus its use.
- **GPT-6 Astra / GPT-6.1 Sol:** Candidates for references, textures, documents, props/ornaments, and clearly scoped adjustments/implementation. Check the overall silhouette and surrounding connections rather than selecting solely on local improvement. This does not mean they cannot adjust the whole model.
- **Gemini 4 Argon:** Hair secondary motion was observed to be completed quickly. A candidate to try next for moving parts, constraints, and mechanisms; general superiority in rigging or skin weights is unverified.

Do not make this a fixed role chart. With common references/goals, compare total time to selection, additional correction count, agreement with the art, regressions elsewhere, and reproduction after saving. Increasing reasoning settings does not necessarily shorten time to selection; do not equate an app's Ultra setting with each provider's API options. Assign only one writer to a target mesh/rig; other reviewers inspect the same saved version.

Add this even to local corrections:

> Preserve the accepted full-body silhouette, proportions, and surrounding connections. Compare a close-up of the changed area and full-body front/side/oblique views under matching conditions. Reject local improvements that worsen the whole; show the cause and alternatives.

## Prepare first

At production start, put the [quality proposal/reasons](quality-goals.md), stage order, five-area diagnosis and necessary corrections, permitted changes, exit conditions, and deliverables into the [production plan](production-plan.md). At each stage, briefly state the target, how to assess it, and conditions for proceeding, carrying forward existing direction.

- Accepted reference mesh and art. The newest candidate is not necessarily the reference.
- For a new moving humanoid, [FBX/Tripo auto-rigging](tripo-autorig.md): actual upload FBX within 150 MB, VRM 1.0 skeleton setting, input/received versions, preservation results, and subsequent rig adjustment.
- [Expression sheets and individual images](expression-sheets.md): match neutral-face version, required patterns, and character's left/right; generate/compare missing images within the initial plan.
- Front/side/oblique images under matching conditions, plus close-ups/wireframes of the issue.
- Image roles: accepted reference, failure example, placement landmarks, design proposal, unverified candidate.
- Target/fixed parts and dependent bones, keys, support surfaces, and materials.
- Units/axes, representative motions, intermediate values, and required output formats.
- See [visual handoff](visual-handoff.md) for detailed image delivery.

## Seven parts of a request

1. **Purpose and stage goal:** Triggering condition and required appearance improvement that closes this stage; relation to overall quality.
2. **Reference:** Versions of shape, art, and joint table.
3. **Change scope:** Faces, rows, parts, and preserved boundaries.
4. **Preservation:** Required silhouette, length, spacing, bones, unrelated keys, UVs, and other conditions.
5. **Adjustment method:** Displacement direction/amount, transition-back distance, surface flow, and propagation to dependencies.
6. **Comparison:** Same camera, pose, and materials; inspect still, intermediate, and return states.
7. **Deliverables and assessment:** Decide acceptance/exit, next-stage, and re-diagnosis conditions first. Separate candidates, observed improvements, remaining work, and checks after saving/export.

## Ready-to-use request

For overall production, use the [integrated request with a plan](production-plan.md). Include mesh, intersections, materials, hands/fingers, and eyes from necessity diagnosis onward. For ordinary blinks/winks, use [wink closure](wink-closure.md). The following is for local corrections.

> Using 【reference material/version】, correct 【specific problem】 occurring during 【motion/view】.
> Overall quality targets are 【purpose, distance, required motions, destination】. This stage aims for 【target state/exit conditions】; record 【later-stage work】 separately.
> Change 【part/face rows】. Preserve 【fixed parts/features/data outside scope】.
> In 【axes/units】, specify displacement, transition-back region, tangents, and surface flow.
> First inspect dependencies in 【bones, weights, normals, keys, support surfaces, materials, driver references】, and align necessary updates to the same version.
> Compare 【views/poses】 under matching conditions, including intermediate values, combinations, and return to key 0/reference pose.
> Assess CLI mechanical results, actual images under matching conditions, motion including intermediate states, and save/destination results separately. Do not select a candidate whose appearance worsens despite better numbers; do not pass untested items.
> Report reopening results separately from untested output-format/runtime behavior.
> For preservation, state 【comparison target, units, maximum difference, predeclared tolerance】 and distinguish exact equality from within tolerance.
> Record the hash of the saved model used for images/video. Label material not regenerated after correction as an older version.
> If conditions conflict with the reference, do not silently relax preservation requirements; show the difficult region and alternative comparisons.

## Specifications that reduce misunderstanding

- For “inward/back,” specify world, face-local, or eyeball-local coordinates.
- For “preserve weights,” distinguish preserving the rule from preserving per-vertex values.
- For “round,” specify silhouette, cross-section, tangent, or normal changes.
- For “fix penetration,” distinguish visible protrusion, hidden contact, and exiting a hem.
- For “follow this diagram,” identify finished shape versus placement guide. Do not infer meaning from line color alone.
- For “preserve everything else,” specify measurements outside scope. Do not demand zero whole-shape difference during an authorized local shape change.
- When transferring from another generated asset, use it as corresponding shape reference; do not reuse vertex indices or the whole-head delta.

## Records after correction

- Actual request, added conditions, confirmed assignee, and input versions.
- Initial quality/stage goals, achieved/unmet conditions, and evidence for proceeding. Record reasons and downstream effects for goals changed during work.
- Candidate changes, matching-condition comparisons, and preservation outside scope.
- Separate numerical checks, actual on-screen appearance, reproduction after saving, user selection, and runtime environment.
- For part integration, reference pose, and secondary motion, use [integration/saved-version verification](visual-handoff.md). Separate visible pose from saved reference state, and saved settings from real-time motion.
- If first-attempt selection is unconfirmed, limit the success claim and retain the text as a proposed first request for next time.
- Update the five plan areas with status/evidence/next work. Untested is not unnecessary/done; deferrals need a reason and restart condition. Needed authorized corrections must not revert to waiting for individual instructions after a report.
- If two candidates for the same cause do not improve appearance, prioritize structural diagnosis over repetition.

## Request using the bundled tools

> Use the [model tools](model-tools.md) to inspect 【input version, target meshes, corresponding rig】 into external JSON. Compare before/after snapshots and separately report 【items allowed to change】 and 【fixed items】. Only where necessary, normalize weight sums into a separate candidate file and preserve the source. Separate untested items, appearance judged through images/intermediate motion, and results after reopening.

## Part-specific additions

For expressions, specify [outline lines, adjacent rows, and intermediate motion](expression-adjustment.md); for mouths, [fixed jaw/local keys](mouth-shapes.md). For hands, specify [curvature and weight recalculation](hand-shape.md); for clothing, [support regions, free edges, and layer order](skirt-hidden-modeling.md).

For wings, use [stage-specific requests for support body, feather rows, roots, and motion](wing-workflow.md). From the first request, specify overall silhouette, feather types, attachment surfaces, common following, front/back faces, and intermediate motion. For hair/feather motion, use [secondary-motion requests](secondary-motion.md), specifying fixed regions, required motions, custom controls, export rig, and destination verification.

For mottled shading, specify [AO isolation/local correction](adjustment-methods.md); for added parts, specify UV and bake targets in that chapter. For final review, use [actual VRM/submission-motion requests](visual-handoff.md), supplying the specified interval, natural combinations, issue times, and untested scope.

See the [process index](process-index.md) for dependencies, [adjustment methods](adjustment-methods.md) for recording numbers, and [topology/weights](mesh-weight.md) for structural instructions. Put Lida-specific preferences in [design choices](lida-design.md), separate from general technical acceptance.

## Requests to publish an app or derived Skills package

Use [attribution conditions/examples](usage-and-attribution.md). Actually write the source name, Lida, URL, and used/modified parts into the published work's README, About, NOTICE, or similar file; report location. Reading the skill to make a model does not require credits on that output. Exclude reference dance FBX and converted reference motion from distributions. Retrieve the shader from its [separate repository](shader-setup.md) only when needed.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
