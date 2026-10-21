# Included figures and reference model

[Japanese source](README.md)

The [English diagram index](../references/en/diagram-index.md) links all 24 PNG/SVG pairs to their chapters. PNG is for display; SVG is for enlargement. Shared figures retain Japanese labels; English chapter captions and legends explain their numbers, colors, directions, fixed areas, and line meanings.

## Production reference model

The official finished Skills ZIP includes `model-reference/china-wafuku/ChinaWafuku-Reference-r35.vrm` as a Skills component. Copy it with the skill folder, then follow the [observation guide](../references/en/model-reference.md) to inspect structure at relevant stages. Normal installation does not require a separate model download.

Redistribution of the model and sale of modified versions are prohibited. Its [model-specific terms](model-reference/china-wafuku/MODEL-TERMS.en.md) are separate from the terms for the original figures below and GPL code. Users must not redistribute the complete ZIP containing the model.

GitHub Code / Source code ZIP contains maintenance source. Use the [official finished distribution ZIP](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.8.1/3DCharaMakeSkills-Lida-1.8.1.zip) to install the model together with the skill.

## Origin and role

All figures are original instructional schematics except the two historical knee diagnostics explicitly identified below.

| File stem | What it explains |
| --- | --- |
| `material-repair-selection` | Separate assignment, image/UV settings, material values and sharing, shape and normals; preserve source images |
| `mesh-repair-selection` | Preserve intended openings; choose orientation repair, patching, boundary joining, or local reconstruction |
| `mesh-boundary-repair` | Fixed boundary, new faces, corresponding points, observed versus inferred surfaces; not a successful-repair result |
| `wink-eye-isolation` | Ordinary blink versus smiling closure, eye-only deltas, character-left/right masks, intermediate values, adjacent rows and separate layers |
| `input-alignment-flow` | Stage-specific references and three-view sheets from one baseline; staged generation is a next-time preventive proposal |
| `local-mask-transition` | Displacement versus return width; an edit mask is separate from skin weights |
| `eye-structure-flow` | Eye surface, iris/pupil, sclera, optional reflection layer, and lines that must not rotate with the eyeball |
| `face-key-locality` | Local expression keys with jaw, outline, and unrelated regions fixed |
| `eyelid-band-follow` | Local eyelid-edge and adjacent-row transforms, with an outward fade |
| `hand-shortening-flow` | Adjust palm height separately from the U-shaped thumb/index outline |
| `hand-structure-map` | Hand orientation, landmarks, joint loops, bones, thumb mound, and web-to-palm continuity; no universal topology or proportions |
| `hand-deformation-check` | Spatial distance versus surface paths; shape, bone and weight diagnosis; intermediate finger/thumb/grip poses and nail following |
| `skirt-layer-route` | Layer order, support regions, free hems, and leg routes |
| `hair-strand-structure` | Hair-only layout, centerline, width/thickness/section, roots/tips, scalp foundation, fixed/free ends; guides are distinct from mesh and bones |
| `hair-cause-isolation` | Isolate hair base color, connections, and surface order |
| `wing-build-sequence` | Check outline, support body, a few feathers, complete rows, and intermediate motion in order |
| `wing-feather-terms` | General bird feather groups, upper/lower surfaces, and root covering; not a fixed fantasy-wing specification |
| `wing-feather-layout` | Fantasy-wing feather types, shafts, overlap order, and attachment surfaces |
| `wing-root-fit` | Fantasy-wing sections, attachment width, direction, and weights |
| `integration-dependencies` | Integrate the chosen part versions with their dependencies; version letters are illustrative |
| `bend-support` | Continuous support bands around a joint |
| `flow-continuity` | Face and edge flow across the maximum-deformation band |
| `actual-knee-layout` | Historical actual-mesh diagnosis; distinguish the observed mesh from an unimplemented layout proposal |
| `actual-knee-bend` | Historical bending diagnosis of an actual mesh; not a finished successful example |

Schematics organize production methods. They are not new before/after evidence or proof of adoption. Distinguish real edges, dashed proposals, and schematic geometry. See [reading the knee diagrams](../references/en/knee-edge-placement.md).

Shapes, dimensions, row counts, and version symbols are not common settings. Match the figure's colors, numbers, solid/dashed lines, and directions to images of the actual target model. Visually inspect the PNG before updating it.

## Attribution visible on standalone figures

All 24 SVG/PNG pairs have a margin below the explanation displaying “© 2026 Lida · 3DCharaMakeSkills-Lida” and `github.com/Lida-V/3DCharaMakeSkills-Lida`. This identifies the origin when an image is shared alone without covering text, lines, or arrows.

The original SVG shapes and text are preserved; PNG is rendered from SVG. Check that the attribution band is readable in both. Adding the band did not change the usage terms.
