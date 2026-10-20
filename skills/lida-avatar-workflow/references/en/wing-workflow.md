# Designing wings, placing feathers, and making them move

[Japanese original](../wing-workflow.md)

[Process index](process-index.md) · [Quality and goals](quality-goals.md) · [Diagram index](diagram-index.md)

Work in this order: **overall outline and support volume → overlap tests with a few feathers → expand to the full wing → body following and movement → UVs, materials, and export**. Fixing roots and joints after placing many feathers can require rebuilding placement, weights, and motion together.

This chapter covers fictional wings growing from a character's back. Bird structure helps explain roles; it is not a unique anatomical solution or a guarantee of flight. The sequence below is **a workflow for future work**, consolidated from production trial and error. It is not a record of following that sequence once and succeeding on the first attempt.

Use the [included tools](model-tools.md) to check topology, UV, weight, and shape-key values, and the image/motion conditions here to review attachment and opening/closing appearance. The tools do not automatically generate wings.

## Materials and the initial target

- Front, back, side, and oblique views of the approved character, showing wing outline, back attachment, and feather tiers.
- References for neutral, opening, closing, and folded shapes. Prepare only needed states; mark unknown undersides or intermediate shapes as design proposals.
- Reference body, hair, and costume models, plus a wing base or reference model. Generated models from Tripo or similar services can guide shape, but may lack a skeleton, separated feathers, or deformable topology. Keep useful existing shapes without requiring regeneration.
- Viewing distance, required motion, software/output format, and performance constraints. Match body posture and the direction or phase of movement in motion references too.

Following [quality proposals](quality-goals.md), explain targets concretely to beginners: “For full-body use, roots stay attached and feather rows do not suddenly split during required movements”; or “For back close-ups too, refine attachment on both surfaces, feather edges, and shading.” For still images, appearance from the required camera is an exit criterion. For animated use, include movement and reproduction in the destination. Carry forward any already specified high quality or artwork fidelity.

## Starting goals for each stage

Before starting, record input version, editable/fixed regions, matched comparisons, exit criteria, deliverables, and remaining work in a [goal card](quality-goals.md). This does not mean requesting approval again at every routine stage.

| Stage | Target for this stage | What to inspect before proceeding |
| --- | --- | --- |
| 1. Rough design | Map outline, attachment, joints, and feather rows together. | A layout that reads as the same wing in neutral and required expanded shapes. |
| 2. Support volume | Continuous shape and thickness from back to tip even with feathers hidden. | Back and side views, feather-free close-ups in neutral, intermediate, and expanded states. |
| 3. Representative patch | Establish roots, orientation, and overlap of flight feathers and coverts. | Plain-colored views of both surfaces, root sections, and intermediate opening/closing. |
| 4. Root attachment | Match support cross-section, root surfaces, and weights to prevent conspicuous detachment. | Root centers and edges; both surfaces and side views of adjacent tiers during opening/closing. |
| 5. Mesh, full wings, body following | Refine deformable topology and weights; connect rows across both sides and to the body. | Whole-body/close-up views, each side alone, global movement, forward bends, twists, and raised arms. |
| 6. Opening, flapping, flex | Coordinate joints and rows through specified phases; preserve roots while bending tips. | Side-view frame stepping; neutral, intermediate, required maximum, return; flex off/on and combinations. |
| 7. Finishing and export | Refine UVs/materials and compare the saved version with destination reproduction. | Grid, actual materials, save/reopen, export read-back, and destination. |

![Original schematic showing wing construction from support volume and representative patches to the complete rows](../../assets/wing-build-sequence.png)

The Japanese-labeled diagram's steps are 1 overall shape, 2 feather-free support volume, 3 a few neighboring flight feathers and coverts, 4 all rows, and 5 closing/intermediate/opening checks. Orange lines and circles are provisional bones and joints. Shapes, feather counts, and bone counts are not fixed specifications or evidence of real-model completion or successful export.

### The route actually taken in production

Early work rebuilt support volume and feather rows, then tested opening/closing and flex with shape keys and Geometry Nodes. Later, the setup was **redesigned around bones and weights for easier export**, mapping usable feather shells and UVs to new centerlines. It was not simply a generated-service model with a rig added unchanged.

Next, the flight-feather fan and covert following were adjusted together; root cut faces, insertion angles, and local support thickness were corrected. Whole-body integration added secondary motion from the middle of flight feathers toward their tips, while roots, coverts, and support volume followed the posed structure without added secondary motion. Appearance of saved animation, saving/exporting standard spring settings, and reproduction of custom controls in the destination are separate checks. Do not present the old Geometry Nodes prototype as the final implementation or a recommended rig that transfers unchanged.

## 1. Map outline, joints, and feather rows first

On back and side references, draw the back attachment region, support centerline, bending positions, leading/trailing edges, and feather roots and tips. Mark the model's left/right, upper/lower surfaces, and root-to-wingtip direction. Screen “up/down” can reverse meaning when the body leans or the opposite surface is viewed.

If feather-group names or regions are unfamiliar, start with [wing layout and terms](wing-feather-terms.md). Number primaries, secondaries, tertials, coverts, alula, and scapulars against the artwork, distinguishing general bird structure from the adopted fictional design.

Use rough bones or guides and low-density shapes to test neutral, half-open, fully open, and required folded states. Do not trace the artwork's wingtip only with bone endpoints: **the outline also includes the length of feathers extending beyond the support volume**. Check space occupied around hair and costume from the side too.

> AI request: Using the approved artwork, show wing outline, back attachment, support axes, joints, flight feathers, and covering rows in one diagram. First build one low-density wing far enough to compare neutral, intermediate, and expanded shape. Generate large feather counts and final materials after that review.

## 2. Hide feathers and build the wing body's thickness

The support volume is the wing body's shape around the bones. Connect volume from the back attachment through the root and joints toward the end, creating surfaces for feather attachment. Bones alone, thin rods hidden with short feathers, or spheres covering joins may provide insufficient attachment width.

Choose cross-sections along the centerline and adjust **width, depth, and thickness on the feather-attachment side separately**. Expand only deficient sections and blend smoothly into those before and after them. Thickening everything to contain roots also expands the leading edge and wrist, changing the artwork's outline.

If opening a joint stretches it into a long thin shape, check centerline curvature, adjacent section orientation, bone rotation centers, and weight transitions before subdividing. Avoid abrupt section flips; keep surface and thickness continuous across joints. Do not uniformly thin root, elbow-like, and wrist-like regions together either.

**Exit check:** Hide hair and feathers to expose the back connection. Compare neutral, intermediate, and expanded states for conspicuous rods, bulges, sharp folds, or holes. Even if feathers cover the structure in the final design, inspect it internally.

## 3. Test feather types and rows with a few neighbors

See [the numbered terms diagram](wing-feather-terms.md#diagram-numbers-and-names) for overall regions and names. The following diagram supports adjustments to shafts, covering roles, and attachment surfaces; it does not show every bird feather group.

![Schematic of inner and outer flight feathers, coverts, shafts, and overlap on both wing surfaces](../../assets/wing-feather-layout.png)

Panel A separates flight-feather and covert roles; B shows a root attached as a surface, not just a point; C checks gaps during movement. Gray is the continuous support, light blue flight feathers, pale purple coverts, and green the root attachment region. Center lines are shafts; dotted root lines are hidden attachments. Inspect the two surfaces independently rather than copying the top underneath.

| Role | Placement and shape checks |
| --- | --- |
| Outer-wing flight feathers, corresponding to primaries | Fan from distal support; connect length, width, and taper to the outer outline. |
| Inner-wing flight feathers, corresponding to secondaries | Follow the inner support and form a continuous surface through neighboring overlap. |
| Shorter feathers covering roots, corresponding to coverts | Place them to cover flight-feather attachments, matching required tiers and lengths to the artwork. |

Names and tiers explain roles. Fictional wings need not share one row count or a bird's feather count. Number requirements such as “three tiers” on the image so they are not confused with two surfaces or simple thickness.

Select representative patches near the inner wing, across a joint, and at the tip. Make a few flight feathers and coverts on both surfaces. Do not rely on shortened copies of one flight feather for all coverts, uniform rounded capsules, or randomness alone to create naturalness. Compare individual shapes and their visible appearance within the wing.

**Shaft direction** differs from **the direction of an edge across the root**. Align shafts with their support region and the overall fan; align root width with the support surface. Using the support tangent as every shaft's direction can reverse feathers at a joint.

Vary neighboring lengths, angles, and root positions continuously, without an abrupt break at the inner/outer boundary. Determine overlap on each surface separately. After mirroring, check surface fronts, vanes, and shafts again.

Changing length alone may not change appearance when another feather hides it. Review angular differences, root spacing, actual exposed length, and tip steps in the same image. When changing flight-feather attachments or fan centers, reposition corresponding coverts too. Rotating coverts about their old center can leave small holes and dark rims.

## 4. Match root shape, placement, and weights together

![Schematic matching support cross-section, feather-root width and position, and shared following](../../assets/wing-root-fit.png)

Gray marks support volume, blue feathers, green attachment regions, and orange directional guides. Items 1–3 are support section/attachment position, root-width direction, and weights at corresponding positions. Dotted lines indicate hidden roots. The diagram explains fictional design, not a unique anatomical answer or successful whole-wing result.

When roots float, do more than move feathers farther inward. Adjust in this order:

1. **Support:** Check width and thickness on the attachment side.
2. **Root surface:** Match width, crosswise direction, and insertion angle so both ends fit the support surface, not only the center.
3. **Transition extent:** Fit the root locally, blending back to the original free vane and tip. Do not flatten roots into box-like steps.
4. **Row order:** Inspect paired tiers from both sides and obliquely for hidden roots piercing the covering tier.
5. **Following:** Match weights so support and feather roots at corresponding positions follow the same joint transition.

A root-center-inside-support test cannot detect floating width edges or exposed cut faces. Inspect actual root surfaces, side views, and intermediate poses. Also check roots that are embedded but reappear as small fragments along a ridge.

If hooks or humps appear beyond insertion points, inspect **cut-face width, rise from that cut, and clearance from the support** in section. Repeatedly adding lift whenever contact appears can grow a hump along existing overlaps. Derive required height once from the reference shape, cap height and slope relative to insertion, and blend smoothly outward. Choose limits from model thickness and required shape. If contact exceeds them, return to row layout and attachment diagnosis.

Separating feathers to reduce intersection counts can leave floating roots and a wing that looks like separate boards. Whether hidden overlap is acceptable depends on use and user requirements. Treat conspicuous penetration, holes, and detached connections separately.

> AI request: Work on the attached representative patch. Preserve support reference positions and free feather tips. Match the attachment-side cross-section, root-surface width, tilt and insertion position, and weights at corresponding support locations. Do not pass on root centers alone: compare both edges and upper/middle-tier relationships on both surfaces, from the side, and during opening/closing. Do not hide gaps through simple depth separation or global thickening.

## 5. Refine topology and weights, then connect the full body

Build support surfaces with cross-section rows along the centerline and connecting edges. Provide continuous deformation bands around joints instead of concentrating stretching into one long face. On feathers, connect rows along the long axis from root to tip and distribute faces where bending is needed. Uniformly increasing edges is different from designing a bending shape. See [mesh and weights](mesh-weight.md) for density, branching, and skinning decisions.

Share support/root weights at corresponding positions and transition toward the weights needed by free ends. If a narrow joint transition causes abrupt angles between neighboring feathers, inspect support and feathers together and widen or adjust that band. Do not give the same bend strength to everything, including coverts.

Matching following does not mean assigning identical bone names and percentages everywhere. If a feather root travels as a child of an arm-side bone, include parent transforms when comparing it with support movement. Avoid pulling roots toward two different rotation centers. Change flight-feather bend weights by position along the shaft, avoiding unwanted widthwise differences that cause twisting. Match normalization, influence counts, and deformation method to destination constraints.

For export, test representative feathers that reproduce needed bends with bones and weights early. Before adding faces or bones, compare root preservation, smooth bending, and reproduction after export. Even when reusing old feather shells or UVs, do not assume old vertex-index correspondence for bones, keys, and weights remains valid.

Validate representative patches on one wing before extending to the full wing. After applying changes to the opposite side, test each wing independently as well as both together. Verify that controlling one side does not move the other.

Check the following path from **body bones such as the chest → wing rig → support and feather meshes**. The rig may follow the chest while feather meshes miss global body motion. Also inspect duplicated movement from overlapping parenting, constraints, and armature deformation.

Test whole-body translation/rotation, forward bending, twisting, and raised arms alone and in combinations. Keep both hair-free connection views and normal-distance views with hair and costume restored.

## 6. Adjust opening, flapping, and flex separately

- **Opening and folding:** Coordinate root, elbow-like and wrist-like joints, and feather fans. Merely narrowing apparent feather width is not folding the wing.
- **Flapping:** Establish the primary movement direction and joint shapes for push and return phases first. Inspect front/back and up/down relative to a leaning body from the side.
- **Flex:** Preserve roots and increase the needed bend toward unsupported tips. Give flight feathers and coverts different extents and strengths.

After isolated tests, review opening + flapping + flex, left/right asymmetry, and combinations with body poses. Use video and frame stepping for intermediate, hold, and return phases, not only angle endpoints. Brief feather collisions or angle jumps may be invisible at a few sample poses; sample problem intervals more finely.

Define responsibility and evaluation/composition order so pose controls and secondary motion do not overwrite the same bone rotation. Whether using separate bones or additive differences on one chain, verify that disabling secondary motion restores the adopted pose, and returning all controls to baseline restores neutral shape. Assign roles from the real control and motion setup, not bone names alone.

If neighboring feathers split because they bend from different references, compare a small patch using shared support positions, bend references, and deformation order. A shared deformation alone does not eliminate discrete triangle intersections or shaft stretching. Check length, width, face inversions, and appearance before and after bending.

Production revised movement directions and verified independent left/right opening and body following. Flex made with keys or time offsets is controlled animation, not proof of aerodynamic response or live physics. See [secondary motion](secondary-motion.md) for motion bones, damping, fixed roots, and export limitations.

## 7. Check UVs, materials, saving, and export

After shape and basic following stabilize, organize UVs for both feather surfaces, required end faces, and support volume. Try more segmentation at strongly bending roots and use a grid to inspect stretching, reversal, collapse, and seams. Unwrapping every part separately into 0–1 is different from creating a non-overlapping atlas for one image.

Map shafts and feather-detail directions to UVs and check that patterns do not reverse from root to tip. For thin edges or transparency, compare close-up and normal distance, both sides, and destination rendering. Do not conceal shape or overlap problems with dark shading or fine patterns.

Before finishing, make a small export of support, flight feathers, and coverts, and read back bones, keys, UVs, materials, and deformation order. In production, a specified clip using bones and corrective keys was read back, while custom Geometry Nodes flex was not included unchanged. This describes that particular test, not compatibility of every wing or format.

That read-back concerned an older prototype. In the later bone-and-weight wing, body and wing rigs were merged on an export copy, and a test export with standard spring settings was also checked. This still does not prove that custom angle limits, whole-wing inertia, or the control panel were reproduced in the destination. Recheck the current input version.

Choose how required motion reaches the destination: bones and supported keys, recorded movement for a fixed video, or equivalent controls implemented in the destination, for example. Distinguish a recorded fixed clip from a rig following arbitrary inputs. Production-software control UIs and driver expressions do not transfer automatically.

Close and reopen the saved file and regenerate neutral/motion images from the same version. Finally [match saved version, export, and destination](visual-handoff.md), reporting verified scope and remaining work separately for appearance, finite motion tests, saving, and destination behavior.

## A feather that looks folded: separate bending from overlap

One feather appearing folded toward the viewer does not necessarily mean the feather itself is bent. In Lida's example, one feather's full width was exposed at the secondary/primary boundary, making depth and brightness steps conspicuous. It remained with secondary motion disabled, and the isolated feather's bend angle did not explain the appearance.

1. Identify the model, video, time, and camera in the reported image. Do not assume it is a crop of the video delivered immediately beforehand. Reproduce the same conditions.
2. Separate centerline bending, depth relative to neighbors, visible width, overlap order, and brightness. Compare neutral/opening/closing, motion off/on, and plain/actual materials as needed.
3. For proposals pushing one feather back or rotating a whole row, check new neighbor intersections, rear-view notches, and root gaps. Reject an option that worsens another area even if the measured step becomes smaller.
4. Decide whether to retain the step as part of the design or redesign row depth using artwork, overall appearance, and viewing distance. Do not automatically rebuild approved overlap for numeric reasons alone.

After comparison, the decision in this example was to retain the existing boundary overlap. Do not distribute rejected local patches as general improvements or adopted corrections. Keep the evidence in [mechanical, image, and motion review](mechanical-visual-review.md) and [trial-and-error records](trial-and-error.md).

## Put repeated failures into the next first instruction

| What happened in production | Specify from the start next time |
| --- | --- |
| Bones and feathers left the wing body and back connection too thin. | Build feather-free support first and inspect attachment region, thickness, and joints. |
| Rounding every feather still produced repeated boards or capsules. | Compare representative feather types and neighboring patches both individually and within the wing. |
| Local patches had inconsistent feather directions. | Show continuous shafts, lengths, and weights across inner/outer regions in one layout. |
| Repositioned flight feathers left holes beneath coverts. | Adjust fan-angle differences and attachment positions, and map coverts to the same rotation centers. |
| Separating feathers reduced intersections but left floating roots. | Match support sections, root width/orientation, insertion, and following together. |
| Root centers passed but root edges pierced the upper tier. | Inspect root edges and paired neighboring tiers from both sides, obliquely, and during movement. |
| Repeated contact push-ups created a hump beyond a root. | Derive height once from reference shape and limit height/slope from the insertion point. |
| One wing moved but failed to follow changed body poses. | Diagram the body-bone-to-mesh path and test global movement and combined poses. |
| Isolated flex worked, but folding or left/right combinations collided. | Combine neutral, opening/closing, folding, positive/negative flex, and left/right asymmetry. |
| Preview motion disappeared on export. | Read back representative patches early; distinguish bones, keys, custom controls, and deformation order. |

These are prevention instructions derived from real problems. They do not guarantee success in one attempt or safety at untested times or joints. If two consecutive candidates for the same cause fail to improve practical appearance, stop changing values and rediagnose support, attachment, feather rows, and deformation references.

### A consolidated request for next time

> The use and destination are [use/destination], and the target is [viewing distance, required appearance and motion]. Use [approved artwork/model version] and preserve [outline, tier count, regions].
> First briefly state each stage's target, fixed areas, comparison conditions, exit criteria, deliverables, and remaining work. Inspect support without feathers. Refine shafts, root surfaces, overlap, and shared following on representative feather-type patches before expanding to the full wings.
> Compare [required opening, folding, flapping] at neutral, intermediate, required maximum, and return states, from both surfaces and the side, independently by left/right and combined with the body. Do not pass on root centers alone; inspect edges and exposure between tiers. Separate fixed roots from free ends for flex and adjust neighboring feathers with the same reference.
> Test export dependencies on representative patches before final UV work and align saved-model, image, and video versions. Report changes, preservation outside the target, actually reviewed states, adoption and remaining work, and destination checks still unverified separately.

Keep preferences such as Lida's artwork-specific outline and feather overlap in [the design afterword](lida-design.md). Use [trial and error](trial-and-error.md) for records and [visual handoff](visual-handoff.md) for reference-image roles and diagram numbers.
