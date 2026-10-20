# Generate expression sheets and individual references first

[日本語 / Japanese](../expression-sheets.md)

**If the avatar will use expressions, include expression-sheet generation in the initial material preparation and production plan.** Prepare the required mouth shapes, eye states, and emotions from one neutral face, compare them in a sheet, then proceed to 3D references and shape keys. When references are missing, return to material preparation within the authorized scope without waiting for separate instructions for each image.

[Production plan](production-plan.md) · [Input materials](input-materials.md) · [Expression meshes](expression-adjustment.md) · [Mouth shapes](mouth-shapes.md) · [Winks](wink-closure.md)

## Decide at the start

- **Baseline:** accepted neutral face, three-view sheet, face close-up, and required oblique/side views. Do not turn each expression into a different person.
- **Required patterns:** list them from the use case, inputs, and destination. Mark already generated, to generate, or unnecessary, with reasons.
- **Change and preserve:** specify the eyes/brows/mouth that move in each pattern and the facial features, head width, jaw, ears, neck, etc. that stay fixed.
- **Deliverables and finish:** a comparison sheet including neutral, individual images, and a name/ID, angle, and baseline-version mapping. Hair and labels must not hide the target areas; all faces must be comparable as the same person.

Plan generation initially, then create images from the accepted neutral version once it is established. If the baseline face is rebuilt, recheck existing sheets for agreement. Reuse adequate existing references or keys.

## Select patterns for the use case

| Group | Candidates for the list | Check separately |
| --- | --- | --- |
| Baseline | Ordinary open eyes, closed mouth | Features, silhouette, and eye/nose/mouth positions; comparison source for all keys at 0 |
| Mouth shapes | あ・い・う・え・お (a, i, u, e, o) | Width, opening, projection; preserve jaw outline and everything outside the mouth for a fixed-jaw method |
| Eyes | Ordinary closed eyes, required half-open states | Normal blink closure line and intermediate motion; exclude unwanted mouth/brow changes |
| Winks | Model-left/model-right; smiling closed-eye reference | Distinguish smiling closure from ordinary blink; keep opposite eye, mouth, and brows fixed |
| Emotions | Smile, anger, sadness, surprise, gentle expressions, and others needed | Identify which eyes/brows/mouth change. The target full emotion and the scope of an individual key are different |

Do not require every candidate. An open-mouth smile may need no additional 3D reference if existing smiling-eye, mouth-corner, and vowel keys combine adequately. A one-eye closure may use the [existing-delta method](wink-closure.md) when an accepted smiling-eye key can be split.

## From generated images to 3D production

1. **Make the list.** Map logical ID, expression name, model-side, angle, moving/fixed regions, and baseline version. A logical ID does not automatically become the destination key name; verify actual input assignments separately.
2. **Generate from the same face.** Reference the accepted neutral face and change only expression. Match framing, direction, scale, background, and light; do not redraw head width, nose, jaw, ears, neck, hairstyle, or clothes for each expression. Compare matched front views first, then add matched oblique/side views where depth or closure lines remain unclear.
3. **Save both sheet and individual images.** Put sheet names/IDs outside faces so lids, brows, and lips remain visible. Crop individual images from the same expression or verify correspondence in separate outputs. Mouth-only crops serve close-up comparison; distinguish them from whole-head reference-generation inputs.
4. **Generate 3D references only where needed.** For Tripo or similar services, use individual face images or several angles of the same expression appropriate to the input mode. Do not submit a complete sheet of multiple faces and expression labels as one model input. Reuse good reference models and keys.
5. **Create local keys on one baseline face.** Treat reference 3D as shape guidance and reflect only the specified mouth/lid/brow region. Do not transfer independently generated head width, under-jaw shapes, or unrelated vertex indices as a whole-face delta. Follow [expression inspection](expression-adjustment.md#inspection-order): neutral → intermediate → maximum → return, both sides, actual combinations, saving, and destination.

If using heads with and without hair, choose one face as the expression-sheet baseline. Add matching hairless helper images when hair hides brows/lids. Do not mix hairstyles or baseline heads between expressions.

## First image-generation request

```text
Using the attached accepted neutral face, create an expression sheet for [required expression list].
Include neutral as the comparison baseline. Preserve identity, facial features, head width, nose, jaw, ears, and neck.
Use the same front view, scale, lighting, and background. Change only the eyes/brows/mouth specified for each expression.
Distinguish ordinary blink, smiling closed eyes, and model-left/model-right winks.
Place names and IDs outside faces. Save matching individual images separately as well.
For [expressions requiring depth], also add oblique/side views of that same expression.
Provide a mapping of baseline version, ID, angle, changed regions, and fixed regions for every image.
```

For fixed-jaw mouth shapes, add “Change only the mouth region; preserve the jaw bone, jaw outline, and everything outside the mouth.” If a full-emotion target moves mouth/brows, do not mix those changes into the fixed-region conditions of a wink-only key.

## Request for full production

> Include baseline neutral-face selection, a required-expression list, and expression-sheet/individual-image generation and review in the initial production plan. Select mouth shapes, ordinary blink, left/right winks, and required emotions from the use case, and map baseline version, ID, angle, moving regions, and fixed regions. Once images are ready, make 3D references only for needed patterns and local keys on one baseline face. Reuse adequate references/keys. Report approval of the image sheet separately from acceptance of 3D, intermediate motion, saved files, and the destination.

## Verified scope and production lessons

The production used mouth, eye, and emotion images from the same face, then Tripo reference models to make local shape keys. This chapter makes that image preparation explicit in the initial plan as a comparison sheet plus individual inputs. It does not claim that every candidate expression was newly generated or that one sheet completed the 3D model.

Generated images are shape references. Agreement of a three-view sheet or approval of an expression sheet does not validate actual eye closure, contact, or intermediate motion.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
