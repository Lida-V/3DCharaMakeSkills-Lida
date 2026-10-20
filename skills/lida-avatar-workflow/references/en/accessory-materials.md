# Fixing materials on accessories and decorations

[日本語 / Japanese](../accessory-materials.md)

[Process index](process-index.md) · [Appearance differences between destinations](cross-engine-look.md) · [UV, image, and material correspondence](adjustment-methods.md)

Repainting an image first to fix silver ornaments, crowns, gems, or fittings that look too shiny, white, or crushed to black can create problems from another angle or in another application. **Check import settings and assignments, then distinguish material, image, geometry, and normal causes.** Images also feed materials, so these are not completely separate alternatives.

## Starting goal and inputs

| Item | Decide and provide |
| --- | --- |
| Goal | The decoration's color, shape, and detail remain readable at the specified distance. State whether the priority is the reference color, moving highlights, or both |
| Inputs | Baseline model, material and image versions, enlarged artwork, an angle showing the problem, destination and shader versions |
| Change and preserve | Target parts and materials; whether to preserve source pixels, UVs, shape, keys, bones, weights, and everything outside the target |
| Comparison | Identical camera, pose, resolution, lighting, and fixed exposure; both normal full-body distance and detail close-ups |
| Finish | Explain the cause and verify the intended appearance after saving and in the destination. Keep unsupported features as open items |
| Deliverables | Before/after images, part/material mapping, changed values, connections and assignments, preservation results, and unverified scope |

Include one angle where the symptom does not occur. Preserve the original and disconnect or replace inputs only in a diagnostic copy.

### Establish what may change

Record the target parts/faces, actual material data, images and UVs, node connections, values, and other users of that material in the [production plan's material change table](production-plan.md). Changing image pixels, the original palette or pattern, material gloss, and face assignments are different changes.

- If instructions or an existing agreement define the scope, proceed with diagnosis, correction, comparison, and saved-file checks within it without repeatedly requesting approval. For example, a request to fix a crown's blown highlights authorizes adjusting only its gloss while preserving the specified palette, source image, and other parts.
- If scope is unresolved, use a diagnostic copy to present the cause and a concrete proposal, establish what will change, then apply that change. “Fix the material” does not authorize changing the artwork's palette, images, and every shared user.
- Continue independent checks and corrections while a material decision is pending. An unresolved material change need not stop the whole production.

## Choose the repair layer with the diagram

![Original schematic dividing decoration repairs into M1 assignments, image settings and UVs; M2 material values and shared users; and M3 geometry and normals](../../assets/material-repair-selection.png)

[Enlarge the SVG](../../assets/material-repair-selection.svg). The shared diagram has Japanese labels: **M1** means assignments/image settings/UVs, **M2** material parameters/shared users, and **M3** geometry/normals. These numbers identify repair layers, not a mandatory repair order. First establish common input and display conditions. Diagram colors and values are neither measurements of the production model nor settings for every decoration.

| Symptom or finding | First repair layer to investigate | Avoid at this point |
| --- | --- | --- |
| Only some faces have the wrong color, or only another engine looks white | **M1:** face assignments, referenced images, color space, compression. Move to **M2** for color multiplication or presets | Do not repaint the source to compensate for a bad import |
| Blown highlights or gloss vary with light/view | **M2:** reflections, specular, MatCap, highlight compression; also check common exposure | Do not apply one base-color or metallic change to every metal |
| Gems look frosted, overly transparent, or disappear in overlaps | **M2:** supported transmission, coat, roughness, rendering mode and order | Do not assume every shader supports transmission/refraction |
| Thin chains or silver lines become dark blobs | **M2:** outline width, color, and target scope; compare with outlines temporarily disabled | Establish whether outlines are the cause before painting bright lines into an image |
| A pattern or dark patch stays fixed on the surface | **M1:** examine base color, AO, shadow color, and masks separately | Do not brighten painted shadows, AO, and material shading together |
| Silhouette, thickness, face direction, or joins look wrong | **M3:** actual geometry, face orientation, smoothing, custom normals | Do not hide holes, collapse, or bad joins with gloss/patterns |

If the whole model brightens or darkens together, return to [lighting, color management, and exposure](cross-engine-look.md). For missing faces, wrong connections, or missing volume, use [mesh repair and completion](mesh-repair-completion.md).

## First identify which faces use what

1. **Identify the target.** Isolate the part and use material-slot colors or another clear display to inspect assignments on visible faces. A name such as “silver material” is insufficient.
2. **Build a mapping.** Connect part/face range → material → images/masks and UV layer → destination material in one row. List parts that actually reference the same material data; matching names do not establish sharing.
3. **Check image roles.** Distinguish ordinary sRGB base-color images from numerical masks read as linear data. Match the actual role and source color space; inspect incorrect normal-map classification and compression.
4. **Read values back.** Save changed settings and inspect the resulting imported values. If reimporting or generating a preset resets them, include that source configuration in the repair.

In Lida's gems, a color image was automatically classified as a normal map and sRGB was disabled. Compression was corrected first, sRGB was then set, and readback confirmed the color returned. **This was not a pixel edit.**

## M2: adjust materials while preserving images

### Disable one suspected cause at a time

1. Capture a baseline and record base-color, AO, shadow, normal, specular, MatCap, and outline connections/values.
2. In a diagnostic copy, disable one suspected element and capture identical conditions. Try outlines first for chains, or specular/additive MatCap for silver highlight clipping.
3. Restore it before testing the next element. Disabling several together does not isolate a cause. Check transparent gems against the background and overlapping faces too.
4. Make a few alternatives for the causal parameter, such as original, moderate, and stronger correction. Reject an improvement in front view that loses detail in oblique or full-body views.

### Use features the shader implements

| Implementation | Parameters and interpretation |
| --- | --- |
| PBR | Reflection strength, roughness, metallic, and supported transmission/coat. Roughness changes reflection spread and metallic changes surface behavior; do not assign a universal value merely to match brightness |
| AngelToon | Compare highlight strength with `Spec Strength`, area with `Spec Size`, and edge softness with `Spec Soft`. In the current implementation, Size closer to 1 makes a narrower highlight. Treat additive/multiplicative MatCap and strength, `Highlight Knee` compression, and outline width/color separately |
| Unsupported feature | If transmission, coat, or refraction inputs do not exist, do not imitate them by looking for similarly named values. Choose a supported appearance and, if necessary, make baking to output images a separate step |

AngelToon specular and MatCap values are not replacements for PBR metallic/roughness. MatCap depends on view, so inspect several angles. **Rebuilding the MatCap image itself is an image change** and must be recorded as such. Check inputs and behavior in the [AngelToon specification](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/SPEC.ja.md).

### Control effects on shared materials

- Before changing a material, display all its users, such as crown, chains, and waist ornaments. A common adjustment is appropriate if those users are in scope and need the same correction. Do not change excluded parts according to the AI's preference.
- If only the target needs a different adjustment, choose a material copy or supported local mask. Copying alone does not change assignments: assign the target faces to the new material and recheck the original faces.
- Include a newly created mask image among the changed assets. When splitting materials, also check destination limits on material count and rendering cost.

### Leave a useful comparison record

| Record | Example wording |
| --- | --- |
| Baseline | Crown and waist ornaments share the same silver material; angled light washes out only the crown's detail |
| Isolation | Disabling specular restores the detail; disabling outlines does not change the whiteness |
| Candidate | Preserve images and reduce only specular strength. Record actual parameter names and before/after values |
| Shared users | Common adjustment darkens waist ornaments, so reject it and assign only crown target faces to a copied material |
| Decision | Compare full-body, oblique close-ups, and another light direction; record saved-file and destination results separately |

This is a recording template. Do not turn unperformed tests or example decisions into production achievements.

## M1 and M3: separate image, geometry, and normal causes

Temporarily replace base color with a flat color in a diagnostic copy. Preserve original alpha if transparency is needed, and toggle AO, shadow color, and specular independently. Darkness remaining after removing base color is not automatically a geometry defect.

| Finding | Next action |
| --- | --- |
| The symptom disappears only when a particular image is removed | Inspect its pattern, painted shadows, and UV correspondence. Locally correct only the needed image/mask in a separate output, preserving the original and pixels outside the allowed range |
| The same fold or dent remains with flat color | Inspect normal display, face orientation, and smoothing; if needed disable normal inputs/custom normals and compare actual geometry |
| Silhouette or section remains wrong without normal settings | Repair connection and volume. Report a geometry repair and recheck UVs, weights, keys, and dependencies |
| The symptom occurs only in the destination | Compare imported normals, materials, images, supported features, and draw order with the baseline environment |

Restore temporary colors and disabled inputs after diagnosis. If images need correction, distinguish adapting to destination limits from changing the artwork's pattern itself.

## Production examples and their limits

| Example | What was done | Verified scope and limit |
| --- | --- | --- |
| Silver ornaments were too reflective | Copied the material, weakened reflection, increased roughness, and compared identical conditions while preserving images, UVs, geometry, etc. | Through save/reload of a Blender EEVEE candidate; this did not establish reproduction elsewhere |
| Thin chains/silver lines looked like dark masses | Adjusted outline color/width and excluded some small decorations from outlines | With world-space width, apparent screen thickness changes with distance |
| Gems looked like frosted glass | An additional material correction reduced transmission and adjusted coat tint and related settings | Separate from earlier image edits adding facets/white lines; coat tint does not transfer directly to glTF/MToon |

These are examples from this production, not default reflection, roughness, or outline values, a universal treatment, or a promise of identical results in every engine.

## Saving, destination checks, and completion

1. **Check preservation.** For material-only corrections, compare source-image content hashes, UVs, geometry, keys, bones, weights, and excluded materials. Record intentional material copies and face reassignment separately.
2. **Record reproducible changes.** Save values, image references, node connections, shared users, and face assignments, not only material names. The [helper snapshot](model-tools.md) does not compare material-node internals or external-image contents; record those separately.
3. **Inspect at the intended viewing conditions.** Add required light directions, front/oblique/side views, full-body/detail views, and motions to the fixed baseline. Ensure crowns/chains remain readable and gems do not disappear with view.
4. **Check after saving and in the destination.** Load afresh and inspect missing images, resets to old presets, outlines, and transparent overlaps. For unsupported output features, record whether another material or baking is needed and what remains unverified.

Report cause / repaired layer / preservation / saved-file result / destination result / open items together. Local visual improvement does not establish whole-body or all-destination acceptance.

## Example first requests to the AI

Silver ornaments and chains:

> Make the attached ornaments' silver shape and details readable at the specified full-body distance. Start by stating the input version, comparison conditions, and completion criteria, and map parts → face materials → images/masks → shared users. Check import and color management, then isolate outlines, specular, and MatCap one at a time. Compare a few alternatives using only features in the actual shader. Preserve source images, UVs, geometry, keys, weights, and excluded parts. If local material separation is needed, verify face reassignment and effects on other users. Deliver before/after full-body and detail views at several angles, values and connections, save/reload and destination results, and remaining issues.

Cloudy gems or color mismatch:

> Preserve the attached reference color and separate the causes of cloudy and whitish gems. First check incorrect normal-map classification of base color, color space, compression, and material assignment. Then compare transmission, coat, specular, and rendering mode separately; use a temporary flat color to distinguish image from geometry/normal causes. Preserve the original, and do not repaint an image if a material correction is sufficient. Do not claim unsupported inputs reproduce correctly; define any necessary image edits in separate outputs. Report identical-light/exposure comparisons, several angles/backgrounds, saved-file and destination results, preserved items, and open issues.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
