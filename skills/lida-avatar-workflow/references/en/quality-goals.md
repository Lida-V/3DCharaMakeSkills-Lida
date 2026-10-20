# Initial quality proposal and goals for each stage

[Japanese source](../quality-goals.md) · Source baseline: 2026-10-20.

At the start of production, propose what the model will be used for and how far it will be finished. At the start of each stage, decide and record what must work before that stage ends. “High quality” or “natural” does not identify whether the target concerns appearance, movement, or reproduction in the destination. Describe an observable state.

Put the initial quality proposal into the [production plan](production-plan.md), connecting it to necessary diagnosis and corrections, stage order and dependencies, permitted changes, and deliverables. Keep all five diagnostic areas—mesh, intersections, materials, hands/fingers, and eyes—in view. A quality proposal must not send already needed corrections back into a wait for separate instructions.

## Proposal when starting a model

Gather the purpose, usual viewing distance and framing, required motions and expressions, software and output format, and parts that matter most on screen. Carry forward existing instructions. State assumptions for unknown conditions and make the proposal concrete with the information available.

| Quality option | Observable result | Main work | Suitable purpose |
| --- | --- | --- | --- |
| 1. Shape study | Front, side, and oblique views allow comparison of body proportions, neutral face, hair, and clothing silhouettes. Motion in actual use is untested. | Rough 3D, shape corrections, minimum display setup | Checking design and volume first |
| 2. Quality for moving use | Character features read at the usual distance; required expressions and motions have no conspicuous tearing, collapse, or penetration; the result reproduces in its destination. | Joints, topology, weights, expressions, part integration, UVs/materials, export and destination checks | Streaming, games, moving avatars |
| 3. Finish suitable for close-ups | Lips, eyelids, hair tips, clothing edges, shading, and seams do not stand out unnaturally in the specified close-ups. Moving uses also meet option 2's motion and destination requirements. | Close inspection and adjustment of visible shapes, connections, and materials, with required motion/expression comparisons | Facial close-ups, showcases, films with close shots |

Preserve the specified character's features in every option. Option 1 is an unfinished study, not a finished model ready for actual use. Even when option 3 is the final goal, begin by checking rough forms. Making a prototype does not lower the final target.

Still images and display models can also target finished quality at normal distance or in close-up. Set the exit condition to reproducing the finished image at the specified camera angle and lighting from the saved source. Add rig, expression, and engine checks only where the use needs them.

Briefly state the **recommended option, reason, priority parts, and additional work**. Do not invent unverified differences in cost, time, counts, or resolution. Existing user requirements take priority; do not lower Lida's agreed target. Also carry forward the latest assignment preferences and production evaluation. In the user's 2026-10-15 assessment, Opus was often entrusted with shape corrections involving appearance and overall balance and worked well in this production. Earlier Astra preference describes the assessment at that time, not a general ranking of models. See the assignment discussion in [AI instructions](ai-instructions.md) for specific roles and unverified areas.

### Example initial proposal

> Assuming this is for streaming with a large face on screen and a full-body showcase, I recommend option 2 for overall motion and option 3 for the visible face, hair, and clothing.
> At the normal viewing distance, I will refine silhouettes and motion. In facial close-ups, I will inspect mouth/eyelid connections and hair tips. The additional work is close-up shape and material adjustment, plus tests of intermediate expression values and combinations.
> I will first check proportions and the neutral face with rough forms. Final acceptance will use the specified distance, motions, and destination.

This is a proposal based on assumed uses, not a new quality decision or completion report for Lida.

## Decide quality along several axes

| Axis | Decide initially |
| --- | --- |
| Appearance | What to preserve from the art, and which views/distances determine silhouette and volume matching |
| Movement | Motions, expressions, necessary ranges, and unacceptable visible failures |
| Destination | Format, supported bones/keys/physics mechanisms, and checks in the destination |
| Performance | Device runtime, loading, and display constraints, based on measurements or destination requirements |
| Detail | Close-up parts and the scope of patterns, edges, and connection finishing |

Adding detail alone does not establish higher overall quality. If appearance conflicts with movement, or reproduction with performance, show the proposed changes and appearance so priorities can be resolved. Do not ask for the same agreement each time; add only what new conditions change.

## Goal card to record at the start of each stage

For corrections, reference generation, rigging, finishing, integration, and export, briefly present these six items and save them in the production notes. Fill the card using established directions; it is not a recurring approval gate.

1. **Target state:** What will work, under which conditions, when this stage ends?
2. **Input and scope:** Reference/model versions, changing parts, fixed forms, and dependent parts.
3. **Comparison conditions:** Views, distances, motions/intermediate values, and close-ups using the same camera and materials.
4. **Acceptance and exit conditions:** Target appearance, preservation outside scope, needed measurements, and save checks. Decide exact equality versus a tolerance before measuring, with units and scope. Match submitted images/video to the final saved version. A reduction in counts alone is insufficient.
5. **Conditions for proceeding and remaining work:** Shapes and correspondence data the next stage needs, deferred finishing/destination checks, responsible work and handoff material.
6. **Conditions for re-diagnosis:** A fixed part changes, a new failure appears, or two consecutive candidates addressing the same cause fail to improve appearance in actual use, for example.

### Example start of a mouth-shape stage

> Target: Add the “a” mouth shape to the accepted neutral face, matching width, opening, and protrusion to the reference while keeping the jaw and face outline fixed.
> Inputs/scope: Closed-mouth reference face and front/oblique/side references. Change only the mouth region and necessary mouth interior. Fix the jaw bone, jaw outline, cheeks, nose, eyes, neck, and areas outside the mouth region.
> Comparison: Check key 0, intermediate values, 1, and return to 0 from the same angles. Enlarge mouth corners, lips, and adjacent surfaces. Test mixtures with existing keys in combinations that will actually be used.
> Acceptance/exit: Continuous lips and adjacent surfaces, with no conspicuous creases or mouth-interior breakthroughs. Confirm zero displacement in fixed areas and save/reopen persistence.
> Next/remaining: Record this key's local checks before the next vowel. Record separately if all vowels, full-body integration, or display in the destination remain untested.
> Re-diagnosis: If the target cannot be reached with the jaw fixed, boundaries fail, or two candidates addressing the same cause do not improve appearance, revisit the allowed region, connections, and reference-shape correspondence.

This illustrates a stage boundary. Dividing vowels or checks into small steps does not remove the eventual acceptance requirements for all required mouth shapes and the destination.

## Separate mechanical checks from visual acceptance

The CLI checks bones, hierarchy, assignments, values, and preservation; it does not replace [image and motion assessment](mechanical-visual-review.md). Record the required mechanical results, art/candidate comparisons under matching conditions, intermediate motion, and save/destination results separately. Matching bone counts or hashes does not resolve an unnatural shoulder, hand, knee, or mismatch with the art. Do not change a good shape or required motion merely to pass a number.

## Choose checks relevant to the stage

- **Neutral shape:** reference silhouettes and connections. **Intermediate:** abrupt creases or switches. **Required maximum:** limits of the intended range. **Return:** restoration of the reference state.
- **Save/reopen:** the work persists. **Destination:** exported appearance, movement, and controls reproduce. These checks have different meanings.
- For integration, reference pose, secondary motion, and submission version matching, use [saved-version verification](visual-handoff.md). Treat visible pose, saved settings, and motion over real time as separate exit conditions.
- Choose poses and dependent parts relevant to the stage. Zero intersections in unrelated extreme poses must not become a universal entry/exit gate.
- Final UVs/materials follow stable shape and basic deformation in the changed part. Make small export-dependency trials before final finishing. Do not pack every full-body test into one local correction.

If cloth physics will be handed off to the destination, the authoring stage can end after preparing shapes, connections, and corresponding assets, testing export/re-import and control-transfer conditions, and checking full-body integration. Inspect cloth tension, drape, and penetration separately in the destination; do not pass an untested appearance. If the authoring software must produce final images, include the necessary cloth appearance there in its exit conditions. Stage boundaries depend on use, and unfinished work must name its handoff destination.

At stage end, add achieved items, unmet items, remaining work, and the next input version to the card. If a goal changes, record why and what it affects; do not silently erase the original unmet condition.

## Define the scope of provisional completion

At the start of final review, align the deliverable being closed, specified views and motion interval, remaining major issues, and handoff version. A predicted finish is not completion: check treatment of visible remaining issues, reproduction after saving, and image/video correspondence to the input version.

Use the user's video length and expression combinations. Do not add an unnecessary full-length/all-expression compilation to a check of natural actual use. Recheck corrected intervals and related motion; separate numerical checks, visual inspection, and final selection. This does not authorize shrinking a required motion range to hide an unmet goal.

Handoff includes the selected version and recoverable source, reproduction procedure, checked scope, known limitations, and later stages. Completion in the authoring software, output-file verification, destination reproduction, and publication/distribution conditions are separate boundaries. Do not automatically restart deferred stages; record when re-diagnosis will be needed.

Use [output re-import and submission-motion review](visual-handoff.md). Continue to the [process index](process-index.md) for order, [AI instructions](ai-instructions.md) for prompts, and [trial and error](trial-and-error.md) for re-diagnosis and records.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
