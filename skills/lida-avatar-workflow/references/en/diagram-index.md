# Diagram index

[Japanese original](../diagram-index.md) · [Process index](process-index.md)

Use diagrams to check editable and fixed regions, directions, and connections that are easy to confuse in prose. Follow each link to its explanatory chapter. PNGs are for viewing and attaching to an AI request; SVGs allow enlargement.

The shared original diagrams retain their Japanese labels. Use the English descriptions here and the numbered/panel/color keys in the linked English chapters to identify their parts. Keep the visible **© 2026 Lida** attribution and repository URL when reusing the diagrams; see [NOTICE](../../NOTICE.md).

| Stage or difficulty | What to check in the diagram | Explanation | Diagram |
| --- | --- | --- | --- |
| Input materials and three-view sheets | Separate materials from one common reference; supply both multiple angles and the original reference. | [Input materials](input-materials.md), [three-view sheets](multiangle-threeview.md) | [PNG](../../assets/input-alignment-flow.png) / [SVG](../../assets/input-alignment-flow.svg) |
| Boundary of a local correction | Set displacement and transition width separately. A correction mask is not a skin weight. | [Adjustment methods](adjustment-methods.md) | [PNG](../../assets/local-mask-transition.png) / [SVG](../../assets/local-mask-transition.svg) |
| Blown highlights, cloudiness, or lost detail on ornaments | Separate M1 assignment/image settings/UVs, M2 material values/shared users, and M3 shape/normals. Check propagation through shared materials and preservation. | [Ornament material correction](accessory-materials.md) | [PNG](../../assets/material-repair-selection.png) / [SVG](../../assets/material-repair-selection.svg) |
| Holes, wrong connections, or missing parts | Preserve intentional openings. Choose K1 orientation/display, K2 patch faces, K3 boundary connection, or K4 reconstruction. | [Repair and completion](mesh-repair-completion.md) | [PNG](../../assets/mesh-repair-selection.png) / [SVG](../../assets/mesh-repair-selection.svg) |
| Rebuilding surfaces from boundaries | P1 local patch, P2 corresponding-point connection, P3 local reconstruction. Distinguish fixed boundaries, new faces, and inferred shape. | [Repair procedures](mesh-repair-completion.md) | [PNG](../../assets/mesh-boundary-repair.png) / [SVG](../../assets/mesh-boundary-repair.svg) |
| Eyeball structure and gaze | Separate sphere, iris/pupil, sclera, optional reflective surface, and head-fixed lines. | [Eyeball modeling](eye-modeling.md) | [PNG](../../assets/eye-structure-flow.png) / [SVG](../../assets/eye-structure-flow.svg) |
| Mouth and expression keys | Move only the target region on one shared face. Fix jaw, outline, and unrelated regions. | [Mouth shapes](mouth-shapes.md) | [PNG](../../assets/face-key-locality.png) / [SVG](../../assets/face-key-locality.svg) |
| Ordinary blink versus wink closure | W1 eye-only differences, W2 separation by the character's own left/right, W3 intermediate values/neighboring rows/separate layers. Preserve ordinary blink, mouth, brows, and opposite eye. | [Wink closure](wink-closure.md) | [PNG](../../assets/wink-eye-isolation.png) / [SVG](../../assets/wink-eye-isolation.svg) |
| White bands or folds at eyelids | Share one local transform between rim and adjacent rows, fading toward the outside. | [Expression adjustment](expression-adjustment.md) | [PNG](../../assets/eyelid-band-follow.png) / [SVG](../../assets/eyelid-band-follow.svg) |
| Hand shape, joints, and topology | Match back/palm orientation, landmarks, finger loops, thenar region, and finger-web connections. | [Hands](hand-shape.md) | [PNG](../../assets/hand-structure-map.png) / [SVG](../../assets/hand-structure-map.svg) |
| Diagnosing and reviewing hand deformation | Separate spatial distance from surface paths; check shape, bones, weights, and nails for individual fingers, a fist, and intermediate motion. | [Hands](hand-shape.md) | [PNG](../../assets/hand-deformation-check.png) / [SVG](../../assets/hand-deformation-check.svg) |
| A step after shortening the hand | Separate palm height from the outline around the U-shaped region, blending smoothly into preserved ends. | [Hands](hand-shape.md) | [PNG](../../assets/hand-shortening-flow.png) / [SVG](../../assets/hand-shortening-flow.svg) |
| Skirt interference and hidden surfaces | Preserve layer order and free hems; diagnose where a leg crosses a cloth surface. | [Skirts and hidden areas](skirt-hidden-modeling.md) | [PNG](../../assets/skirt-layer-route.png) / [SVG](../../assets/skirt-layer-route.svg) |
| Hair-strand shape, roots, and tips | Relate placement, centerline, cross-sections, width/thickness, overlap, scalp underlayer, and fixed/free ends. | [Hair workflow](hair-workflow.md) | [PNG](../../assets/hair-strand-structure.png) / [SVG](../../assets/hair-strand-structure.svg) |
| Hair patterns, holes, and protrusions | Isolate base color, connectivity, and surface order one at a time. | [Hair workflow](hair-workflow.md), [adjustment methods](adjustment-methods.md) | [PNG](../../assets/hair-cause-isolation.png) / [SVG](../../assets/hair-cause-isolation.svg) |
| Building wings from scratch | Review outline → support volume → a few feathers → all rows → intermediate motion. | [Wing workflow](wing-workflow.md) | [PNG](../../assets/wing-build-sequence.png) / [SVG](../../assets/wing-build-sequence.svg) |
| Feather layout and names across a wing | Relate primaries/secondaries/tertials, coverts, alula, and scapulars to upper and lower surfaces. | [Wing layout and terms](wing-feather-terms.md) | [PNG](../../assets/wing-feather-terms.png) / [SVG](../../assets/wing-feather-terms.svg) |
| Feather placement and orientation | Check feather types, shafts, covering order, and what surface attachment at the root means. | [Wing workflow](wing-workflow.md) | [PNG](../../assets/wing-feather-layout.png) / [SVG](../../assets/wing-feather-layout.svg) |
| Floating feather roots | Match support cross-section, attachment width, orientation, and weights together. | [Wing workflow](wing-workflow.md), [trial and error](trial-and-error.md) | [PNG](../../assets/wing-root-fit.png) / [SVG](../../assets/wing-root-fit.svg) |
| Integrating parts | Match adopted versions and dependencies; check saving, whole-body integration, and destination separately. | [Visual handoff and integration](visual-handoff.md) | [PNG](../../assets/integration-dependencies.png) / [SVG](../../assets/integration-dependencies.svg) |
| Edges around bending regions | Form continuous support bands before and after a joint. | [Mesh and weights](mesh-weight.md) | [PNG](../../assets/bend-support.png) / [SVG](../../assets/bend-support.svg) |
| Connections in strongly deforming bands | Inspect face/edge flow, abrupt density changes, and concentrated connections. | [Mesh and weights](mesh-weight.md) | [PNG](../../assets/flow-continuity.png) / [SVG](../../assets/flow-continuity.svg) |
| Edges on an actual knee mesh | Distinguish actual edges at the time from a proposed layout that was not implemented. | [Reading the knee diagrams](knee-edge-placement.md) | [PNG](../../assets/actual-knee-layout.png) / [SVG](../../assets/actual-knee-layout.svg) |
| Diagnosing a bent knee | Check stretching and collapse in neutral, intermediate, and bent shapes. | [Reading the knee diagrams](knee-edge-placement.md) | [PNG](../../assets/actual-knee-bend.png) / [SVG](../../assets/actual-knee-bend.svg) |

## Giving a diagram to an AI

1. Select one relevant diagram and provide it with real images of the target and its reference materials.
2. Identify which number or line corresponds to which area of the actual model. Align screen left/right with model left/right, and specify movement axes and units.
3. Add editable and fixed regions, intermediate poses, and exit criteria. Use the [request structure](ai-instructions.md).

Of all 24 diagram pairs, the two knee diagrams diagnose an earlier real mesh; they do not show current completion or approval. The other 22 are original explanatory schematics. Do not copy their shapes, row counts, or dimensions directly into the real model. Decide these from the actual shape and required movements.

Generating body and clothes in stages is a prevention proposal for future work. The facial improvement after preparing multiple angles is an observation from this production. Sources and verification scope are also documented in [included diagrams](../../assets/README.md).
