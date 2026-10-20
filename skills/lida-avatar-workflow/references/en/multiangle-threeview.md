# Build three-view sheets from multiple face angles

[Japanese source](../multiangle-threeview.md) · Source baseline: 2026-10-20.

[Process index](process-index.md) · [Input materials](input-materials.md)

Inspect one face from multiple angles before generating three directions independently. Establish cheek, jaw, and skull volume, then organize a common-scale three-view sheet. **Prepare heads both with and without hair from the start, generate each in 3D, and combine the necessary meshes afterward.**

## Five steps

The bottom row of the [input relationship diagram](../../assets/input-alignment-flow.png) shows the common flow: reference art → multiple angles → three-view sheet → rough 3D. Green **2** identifies the facial-volume branch; the blue return arrow means the original art must accompany the angle references into three-view generation. The top green **1** is the separate body/clothing branch; its blue marks and gray dashed lines indicate common height/proportion alignment. The diagram is schematic, not evidence of a generated model's quality.

Split heads into the two branches below and supply both original art and angle references to three-view generation.

1. Choose one illustration as the reference facial character and outline.
2. Prepare front, oblique, exact-side, and low-angle views of the same face, both showing the hairstyle and exposing cheeks/jaw/skull without hair.
3. Refer to both the original and angle images to create **front/side/back head sheets with hair and without hair**, matching scale, expression, and skull. Removing hair must not redesign head size or facial features.
4. Generate rough 3D from each; compare the without-hair face/skull against the with-hair hairstyle, roots, and fit around the head.
5. Combine the accepted face/skull with necessary hair mesh. Inspect front, oblique, side, back, and low-angle views. Establish neutral face and hair placement before expressions.

Lida's example used a 45-degree oblique supplementary view. Choose angles according to the regions whose volume is unclear.

## Roles of the two heads

| Head | Main checks and parts used in 3D |
| --- | --- |
| With hair | Finished hairstyle outline, parting, hairline, crown/back volume, ear overlap; use hair and required root shapes |
| Without hair | Face, cheeks/jaw/skull, ear/short-neck connections; reference face/head for composition |

The with-hair version is **generation input for a head including the face**. It differs from [hair-only references](input-materials.md), which exclude faces/mannequins. The without-hair version must show the same skull volume, not a flattened head made by merely subtracting the hair outline.

## Composing meshes after 3D generation

1. Open work copies of both. Align scale, orientation, and position with common eyes, nose, ears, chin, and neck landmarks. Aligned images do not guarantee aligned generated shapes. Distinguish hairstyle top from skull top; do not distort a good face merely to match the hair-side head.
2. Use the good without-hair face/skull as reference and select only needed hair/roots from the with-hair version. If face and hair are fused, inspect the boundary and separate or reconstruct locally. Superimposing two entire heads is insufficient.
3. Remove unnecessary duplicate faces, scalps, and interior surfaces. Check hairline, behind-ear, and nape steps, gaps, exposed scalp, and penetration. Do not indiscriminately weld intentionally overlapping strands or separate parts.
4. Align UVs, materials, normals, head/neck weights, existing keys, and shadow layers. Check neutral face, expressions, neck motion, hair visible/hidden comparisons, and save/reopen. See [repair and attribute correspondence](mesh-repair-completion.md) and [integration/saved-version verification](visual-handoff.md).

“Composition” means selecting good regions and making them usable in the same model. Joining everything into one object or welding every boundary is not itself the goal. If good head/hair assets already exist, neither needs automatic regeneration.

> Generate with-hair and without-hair heads from three-view sheets sharing one reference. Preserve the accepted without-hair face/skull and combine selected hair and required roots from the with-hair version. Align scale and position with common landmarks, remove duplicate heads/interior surfaces, and check hairline, behind-ear, and nape connections. Report UV/material/normal/weight/expression correspondence and results for required motion and reopening.

## Landmarks to align

- Heights of skull top, chin, eyes, nose, mouth, ears, and neck base.
- Face width, skull front-to-back length, and eye/nose/mouth depth in profile.
- Cheek fullness, surfaces turning under the chin, and face-to-skull proportions.
- Expression, mouth opening, apparent age, colors, scale, and camera perspective.

“Round” does not mean turn the head into a sphere. Preserve the reference facial character and specify where thickness and surface turning are needed. When measuring head-to-body proportion, distinguish hair-inclusive height from skull size.

## Example request for angle references

```text
Draw the same character as the attached reference from the front, oblique angle, exact side, and below.
Keep expression, face width, eye/nose/mouth arrangement, apparent age, and colors consistent.
Show the accepted hairstyle and roots in the with-hair version; expose cheeks, under-chin surfaces, and skull in the supplementary without-hair version.
Both versions must retain the same skull, facial character, eyes/nose/mouth, ears, and neck positions.
Preserve the reference facial character; do not create a different face at each angle.
```

## Example request for three-view sheets

```text
Use both reference art and angle images to compose front, side, and back views of the same head.
Align height, scale, face/skull proportions, and eye/nose/mouth/ear/neck positions; minimize perspective differences.
Prepare two sets for head-only 3D input: A, the head with its accepted hairstyle; B, the same head without hair.
Exclude unnecessary ornaments in both; include only the necessary short neck, on a plain background.
Removing hair must not alter facial/skull size or shape. Distinguish the hair-inclusive outline from the skull outline.
Treat appearance references including clothes/shoulders as a separate use from head-only input.
```

These are reusable request examples. Generated art is not an exact 3D projection, so overlay and compare landmarks between directions afterward.

## Lessons from failure

In Lida's example, facial roundness was insufficient and repeated local corrections did not reach the target, so production restarted from input images. The user assessed improved roundness after creating multiple angles first and organizing them into three-view sheets.

Instructions explicitly describing roundness and jaw shape were also used. This was not a controlled test isolating the angle references' effect; the method alone does not guarantee the desired shape.

Save old inputs, new inputs, and rough 3D with their correspondence. Record input improvement separately from final model selection. Preserve a route back to good silhouettes; if improvement remains insufficient, return to structural diagnosis in [adjustment methods](adjustment-methods.md).

The added practice of generating a with-hair head early and later composing it with a without-hair head to reduce head/hair distortion is the user's production knowledge from this project. It does not establish a universal improvement rate or guarantee that the method eliminates all failures.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
