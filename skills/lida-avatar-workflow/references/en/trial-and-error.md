# Turn trial and error into the next first instruction

[Japanese original](../trial-and-error.md)

Do not end a failure report with “adjusted.” Record the cause, changed conditions, comparison result, and what to include in the next first instruction.
Judge progress by demonstrated improvements and remaining work, not candidate counts or stage numbers.

## Records to keep

- Reference materials and versions, the actual request, and conditions added later.
- The assigned AI and the AI whose participation was actually confirmed. Do not attribute results to an unconfirmed contributor.
- Edited regions, values, coordinate axes, transition regions, and preserved areas.
- Comparisons under matching conditions; isolated, intermediate, and combined movements; and checks after saving.
- Distinctions between a candidate, local improvement, user adoption, and verification in the export or runtime environment.
- A consolidated request for next time. Record “succeeded on the first attempt” only if first-attempt adoption was actually confirmed.

## Instructions learned from repeated problems

| Problem | Cause or key correction | Include in the first instruction |
| --- | --- | --- |
| Fingers, eyeballs, or penetration were left until another instruction | The workflow described stages but did not put their necessity and next actions into the overall plan. | Diagnose the initial plan's five review items, recording required/unnecessary/deferred and the reasons. Carry necessary authorized corrections through result verification. |
| Material correction changed colors or other ornaments | Editable images, values, nodes, assignments, and actual shared users were not distinguished. | Record target faces and editable layers in the plan. Ask only about concrete unresolved design changes; continue independent work. |
| Using an ordinary blink on one eye did not produce the desired wink | Ordinary blinking and smiling closed-eye expression were treated as the same goal. | [Separate only the adopted eye differences by side](wink-closure.md), preserving ordinary blink, mouth, brows, and opposite eye. Inspect intermediate values, combinations, and remaining issues. |
| Hair-only references showed a face, or removing it left a cavity | Removing the face alone did not reconstruct hidden hair and roots. | Show no face, keep hidden hair continuous, connect roots, and prevent unwanted branching at tips. |
| A face made from three-view images was flat | Information about profile and oblique roundness was insufficient. | Prepare multiple angles of the same character first, then construct the three-view sheet from them. |
| Expression lines matched but white bands or folds appeared | Rim and adjacent surfaces moved separately. | Design the line, neighboring rows, and intermediate movement together; inspect left and right separately. |
| Shortening a hand created a sharp transition at its base | Height distribution and transition distance no longer matched the length. | Check length, thickness, and curvature together; distinguish the weight rule from recalculated values. |
| Reducing skirt intersections made another layer penetrate | Layers were corrected independently and judged only by total counts. | Preserve layer order with a common reference and check new interference by pose × part pair. |
| Cloth stretched excessively despite zero intersections | Contact pushback was tested without cloth-length checks. | Review contact, edge stretching, cloth length, inversion, and appearance separately. |
| Uniformly rounded feathers still looked mechanical | Mathematical outline checks did not address feather types or attachment. | Test a few neighboring feathers first for type-specific outlines, roots, axes, and overlap. |
| Avoiding feather intersections left floating roots | Depth separation broke attachment. | Match support cross-section, attachment width, orientation, and weights together. |
| Fitting neck clothing removed its spread in the artwork | Tight body fit took priority over design. | Fix the artwork's outline and spread first, then correct following within those constraints. |
| A UV image alone was insufficient to transfer patterns | The image contained no per-face UV coordinates. | Supply a UV-equipped mesh and matching image, with correspondence to the reference shape. |
| Images and videos of the same-named model differed | The video was not updated after resaving. | Match input hashes of the saved model and each review item; regenerate materials affected by the revision. |
| A summary claimed exact equality despite measured differences | Passing within tolerance was restated as zero difference. | Record units, scope, maximum difference, and tolerance; distinguish tolerance-based passing from exact equality. |
| A part matched alone but moved or shaded differently after integration | Versions of joints, weights, normals, or control dependencies were mixed. | Integrate each part and its related data together, then inspect the saved model in the same pose. |
| Secondary motion looked natural in preview but differed after export | Custom angle limits, inertia, or one-sided constraints were assumed to transfer. | Use [saving and exporting secondary motion](secondary-motion.md); distinguish settings, baking, custom controls, and actual destination behavior. |
| Higher resolution did not fix mottled hair | Vertex AO moved the shadow boundary unevenly. | Separate [base color, AO, shadow, normals, and highlights](adjustment-methods.md), comparing smoothing and darkness on target parts independently. |
| Baking added hair changed the original image | UV regions and bake targets were reused. | [Separate materials, UVs, and images on an export copy](adjustment-methods.md), preserving source images. |
| Successful export still gave different appearance or motion | Structural checks were confused with appearance and destination reproduction. | Separate [real-file read-back and required-motion review](visual-handoff.md); record measured scope and problem times. |
| Lighting changes did not fix a black mouth interior | In this production the mouth bag's base color itself was dark. | [Inspect visible faces and base color alone](cross-engine-look.md); separate shared-source correction from engine-specific differences. |
| Correcting feather base-color edges left a dark shadow-side line | The shadow-color image contained the same dark edge. | [Check base color, shadow color, and alpha together](cross-engine-look.md); establish the image's alpha convention before correcting a separate output. |
| Silver highlights or cloudy gems were repainted without resolving the issue | Reflection, transmission, outlines, or import settings can also be responsible. | First [choose between image, material, and shape corrections](accessory-materials.md); compare shared users and the saved result in its destination. |
| Closing all holes also blocked hems or leg passages | Required openings were not distinguished from missing faces. | Mark retained openings and healthy connection boundaries before [choosing a repair method](mesh-repair-completion.md). |
| New faces connected at rest but split during movement | New-vertex weights, shape keys, or support correspondence were unverified. | [Remap and verify new faces](mesh-repair-completion.md); do not finish after checking only neutral shape. |

## Use diagrams to locate causes and correction scope

![Schematic isolating hair patterns, connections, and surface order](../../assets/hair-cause-isolation.png)

Wavy patterns, breaks, and plate-like protrusions in hair have different causes. In panels 01, 02, and 03, respectively test uniform base color, trace mesh boundaries, and inspect side-section surface order. Blue is the narrow strand surface, orange the main surface; arrows indicate surface front direction. Change display conditions one at a time with the same camera and pose, and correct only what the diagnosis supports. This is not a real-model success image.

![Schematic matching a fictional wing's cross-section, attachment direction, and weights](../../assets/wing-root-fit.png)

Before separating feathers to avoid intersection, match support cross-section, the width direction of root surfaces, attachment positions, and weights at corresponding support locations. Gray is the support volume, blue the feather, green the attachment region to match, and orange the direction marker; dotted lines indicate hidden attachment. Items 1–3 mean cross-section/position, root-width direction, and weights at matching positions. Check both sides of adjacent feathers and intermediate motion, not only root-center points. This explains fictional-wing design; it is neither a unique anatomical solution nor a completed whole wing.

## Order for isolating the cause

1. Check the reference shape. Do not hide an incorrect shape with weights.
2. Show only the target and compare material-free, wireframe, and actual-material displays.
3. Separate rest, single movements, intermediate poses, and combinations.
4. Locate the cause in shape, connections, weights, controls, or materials.
5. Define one correction unit for one cause and compare it. Check unrelated regions for changes at the same time.
6. If two consecutive candidates for the same cause do not improve practical appearance, stop searching values and diagnose the structure again.

## Consolidate into the next request

> The reference is the attached approved material. Last time, [cause] produced [failure]. Include [conditions added later] from the start this time. Fix [preserved regions] and adjust [editable region, axis, amount, and transition]. Compare [matching views and intermediate poses]. Separate local improvement, confirmed adoption, remaining work, and unverified runtime behavior.

Improved three-view alignment and facial roundness after providing multiple angles were production observations, not a controlled experiment measuring that factor alone.
Keep AI evaluations specific to the observed stage and prioritize the user's choice. Do not attribute misunderstandings only to the user's wording.
Consolidating later conditions into the first request does not guarantee first-attempt success next time.

For techniques, see [expressions](expression-adjustment.md), [mouth shapes](mouth-shapes.md), [hands](hand-shape.md), [skirts and hidden areas](skirt-hidden-modeling.md), and [wing production and repeated corrections](wing-workflow.md).
Keep the common request structure in [AI instructions](ai-instructions.md) and visual preferences in [Lida's design](lida-design.md).
Check submitted image/video versions, reference poses, and the verified scope of secondary motion in [visual handoff and saved-version checks](visual-handoff.md).
