# Use a finished model as a production reference

[Japanese source](../model-reference.md) · Source baseline: 2026-10-21.

The finished **r35** example of the new China/Wafuku character is distributed separately as a reference for understanding the relationships among face shape, bones, weights, clothing, materials, and expressions. Adapt the reasons and checks you observe to your own art, proportions, and use. This guide does not recommend copying parts into another model or using the character design without authorization.

## Optional download and model terms

- [Download the reference ZIP from the official GitHub repository](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/model-reference-r35/ChinaWafuku-Reference-r35.zip): `ChinaWafuku-Reference-r35.zip`. The VRM inside is approximately 41 MB.
- Check the version and contents on the [release page](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/tag/model-reference-r35), then read the model terms, provenance, and file inventory inside the ZIP.
- **Redistribution of the model itself and sale of modified versions are prohibited.** These are separate conditions for this model. Keep them separate from the commercial-use terms for the Skills documents/diagrams and the terms for the GPL production helper code.

The model is not bundled in the main Skills ZIP; downloading it is optional. Reading the skill alone must not automatically download, extract, or load the model. Within a request to inspect the model, identify the downloaded file, its terms, and available VRM-compatible software, preserve the original, and inspect it in a separate session.

## Return from the observed part to its workflow

First view the neutral shape from the front, side, and an oblique angle, then isolate only the needed parts. Before copying bone names or numeric values, establish how the shape, moving regions, weights, and adjacent parts correspond.

| Part to inspect | What to observe | Workflow for your own production |
| --- | --- | --- |
| Face and eyeballs | Compare cheek/jaw volume, eye positions/rotation centers, and visible mouth-interior surfaces from matching angles | [Neutral-shape adjustment](adjustment-methods.md), [eyes](eye-modeling.md) |
| Hands and fingers | Inspect the thumb base/axes, web connections, and thickness changes during individual-finger motion and a partial fist | [Hand shape, bones, and weights](hand-shape.md) |
| Joints | Map shoulder/elbow/knee bone centers, bending bands, weight transitions, and silhouettes in neutral, intermediate, and maximum poses | [Topology and weights](mesh-weight.md) |
| Sleeves | Inspect cloth allowance around elbows/wrists, clearance from the body, and folds/penetration while bending the arm | [Practical sleeve feedback](generation-feedback.md), [repair and completion](mesh-repair-completion.md) |
| Materials | Read actual faces, UVs, images, material assignments/shared users, transparency, and outline settings together | [Material correction](accessory-materials.md), [destination appearance](cross-engine-look.md) |
| Secondary motion | Identify fixed roots, moving bone chains, collision settings, and affected parts; play required motions and their return | [Secondary motion and export](secondary-motion.md) |
| Expressions | Compare VRM expression names with their actual deformation/material bindings; inspect affected parts individually, at intermediate values, and in combinations | [Expressions](expression-adjustment.md), [mouth shapes](mouth-shapes.md), [winks](wink-closure.md) |

## What the VRM can reveal

The distributed VRM is an exported model. Its triangles do not reveal the original editing topology or quad layout, and its source modifiers, controls, and working history may not be retained. Distinguish bones, materials, expressions, and secondary-motion settings reconstructed by an importer from information stored in the VRM.

Obtaining this reference model does not guarantee LidaAngelToon compatibility, the same appearance, or display/motion in UE. For a required destination, separately perform [mechanical/image/motion assessment](mechanical-visual-review.md) and [save/re-import checks](visual-handoff.md).

For example, give the AI this request:

> Use the downloaded r35 reference VRM to inspect only hand/finger and sleeve structure. Compare the neutral shape with intermediate arm/finger bends. Briefly report the relationships among bones, weights, and adjacent parts, why they may be useful as a reference, and what the VRM alone cannot establish. The new model will be designed for my own art and use, so do not adopt the example's numbers as defaults or transfer its parts.

Record the input version, software, inspected views/motions, observed relationships, and unchecked items. Separate completion of the example from acceptance of the model currently being made or of another destination.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
