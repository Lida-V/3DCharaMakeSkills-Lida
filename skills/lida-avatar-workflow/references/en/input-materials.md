# Images and models to prepare first

[Japanese source](../input-materials.md) · Source baseline: 2026-10-20.

From the [process index](process-index.md), prepare only materials needed now. Consistency of character, proportions, scale, and pose matters more than image count.

New production from images assumes a 3D generation service such as Tripo creates base models or part-specific references, followed by correction in software such as Blender. Supply reference images, generation service, and modeling software separately. Inspect and finish the generated mesh, motion, and agreement with the art. Correcting an existing model does not require new generation.

## Materials to prepare

![Schematic of staged materials and three-view sheets from one reference](../../assets/input-alignment-flow.png)

**English legend:** Green section **1**, upper row: reference design → base-body references → clothed references → outerwear references. Blue dots/lines mark matching heights/proportions; gray dashed lines are alignment guides. Keep one pose, scale, and landmark definition. The red note identifies staged clothing generation as a prevention proposal for a future production, not a procedure for stacking three independently generated complete bodies. Green section **2**, lower row: reference art → multiple face angles → three-view sheet → rough 3D. The blue return arrow means supply both the original art and angle references when creating the three-view sheet. Align expression, scale, perspective, heights, and front/back depth. These are relationships between inputs, not generated-image or actual-model comparisons.

Align upper/lower landmarks and scale and derive the necessary materials from one reference. Staged body/clothing/outerwear generation is a future prevention proposal. See the [dedicated procedure](multiangle-threeview.md) for multiangle face references and three-view sheets.

| Material | Make clear |
| --- | --- |
| Finished design art | Front/side/back proportions, clothing boundaries, lengths/openings, hair and accessory positions |
| Base-body art | Shoulder, torso, arm, crotch, and leg shapes; simple close-fitting base clothing is acceptable |
| Clothed art | Clothing silhouette on the same body, with supplementary hidden sleeve/hem/back views |
| Art with outerwear | Opening, thickness, interior, and overlap with underlying clothing |
| Head with hair | Front/side/back from the beginning; hairstyle outline, hairline, crown/back-of-head volume, overlap with ears |
| Head without hair | Same face, skull, scale, expression as the with-hair version; cheeks, under-chin, ears, short neck; reference face/head after generation |
| Hair/part art | Strand silhouettes and depth order, roots, thickness, tips; purpose of each part |
| Expression sheet and individual images | Required mouth shapes, ordinary blink, left/right winks, and emotions from one neutral face; correspondence of neutral reference cell, character's left/right, fixed areas, image IDs |

Nude images are not required. Decide first whether the body under clothing becomes visible in motion or whether clothing will be removed/replaced.

## Beginner's order

1. Choose one finished design. Mark crown, chin, shoulders, crotch, knees, soles, and other landmarks.
2. Derive clothing and then outerwear images from the same base body without changing proportions.
3. Follow [multiple angles → three-view sheets](multiangle-threeview.md) to prepare both with-hair and without-hair versions of the same head.
4. For expressive uses, [generate and compare the expression sheet and individual patterns](expression-sheets.md) from the accepted neutral face. Do not regenerate adequate existing references.
5. Generate both heads in 3D and [compose the good face/head and hair regions](multiangle-threeview.md). Compare neutral form/connections in front, side, and back views. Create required expression 3D references from individual images and retain them as shape references at this stage.
6. For a new moving humanoid, establish neutral shape/joint topology and use [Tripo VRM 1.0 auto-rigging with an FBX within 150 MB](tripo-autorig.md). Compare source/received data, then adjust bones, weights, and clothing/dependent deformation. Keep usable existing rigs.
7. Make local expression keys on one reference face. Check connections through expressions and necessary neck motion. If keys already exist, retain them and compare preservation/movement through the auto-rig round trip.
8. Finish detailed UVs, color, and materials after shape and basic movement are established.

The base → clothes → outerwear split is a future prevention proposal, not a measured successful production sequence from Lida's example.

In 3D, use one common body and separately editable clothing/outerwear. When separating a clothed model, inspect body boundaries and missing hidden regions.

## Making hair-only references

These conditions apply to hair-only generation input. **Three-view head images with hair include the face and serve a different input purpose.**

- Match front, side, and back views of the same hairstyle so strand flow is clear.
- For hair-only input, exclude extra face, body, and background forms.
- A strand ending in one tip should taper width/thickness smoothly without branching.
- Distinguish silhouette references from color/gloss references.

Use the [hair workflow](hair-workflow.md) for structure, hairline, material, and movement order and concrete prompts. Record approval of a reference separately from inspection of 3D generated from it.

## Common difficulties

Finalizing only the front view leaves clothing backs/interiors and shoulder thickness to guesswork. Independently generated full-body views can also change head size or facial depth between directions.

Lida's example needed later reconstruction of torso/arms inside clothing. Fitting them inside clothes in neutral pose still left motion exposure, requiring matching connection ends and weights. See [hidden-body completion](skirt-hidden-modeling.md).

Label each image with purpose/version, distinguishing shape references, failure examples, and unimplemented proposals. Lida-specific appearance is in [design/preferences](lida-design.md).

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
