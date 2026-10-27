# Use a finished model as a production reference

[Japanese source](../model-reference.md) · Source baseline: 2026-10-21.

The finished **r35** example of the new China/Wafuku character is included as a production-reference component of the Skills pack for understanding the relationships among face shape, bones, weights, clothing, materials, and expressions. Adapt the reasons and checks you observe to your own art, proportions, and use. This guide does not recommend copying parts into another model or using the character design without authorization.

## Download and install together

1. Download and extract the [official finished Skills 1.9.0 ZIP](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.9.0/3DCharaMakeSkills-Lida-1.9.0.zip). It includes the reference VRM, approximately 41 MB.
2. Copy the entire `skills/lida-avatar-workflow` folder to your skill location, including `assets`, `references`, `scripts`, and terms. The reference model is at `assets/model-reference/china-wafuku/ChinaWafuku-Reference-r35.vrm`.
3. Read the [model-specific terms](../../assets/model-reference/china-wafuku/MODEL-TERMS.en.md), then inspect only the parts needed for production in a separate session of a VRM-compatible tool. Reading alone must not start model processing or environment changes.

GitHub **Code → Download ZIP / Source code ZIP** is the maintenance source and does not contain the model itself. Use the finished distribution ZIP above for normal installation. The [standalone official r35 download](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/tag/model-reference-r35) remains available if only the model needs to be retrieved again.

## Separate model terms from document/code terms

**Redistribution of the model and sale of modified versions are prohibited.** Therefore users must not redistribute the official complete ZIP containing the model. Documents, diagrams, and code separated from the model and its extracted assets retain their existing respective LICENSE and GPL conditions. These terms do not prohibit studying the model for commercial production or selling a different, independently created model.

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

> Use the r35 reference VRM included in the skill to inspect only hand/finger and sleeve structure. Compare the neutral shape with intermediate arm/finger bends. Briefly report the relationships among bones, weights, and adjacent parts, why they may be useful as a reference, and what the VRM alone cannot establish. The new model will be designed for my own art and use, so do not adopt the example's numbers as defaults or transfer its parts.

Record the input version, software, inspected views/motions, observed relationships, and unchecked items. Separate completion of the example from acceptance of the model currently being made or of another destination.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
