# Preserving the character's appearance across destinations

[Japanese original](../cross-engine-look.md)

[Process index](process-index.md) · [Materials and images](adjustment-methods.md) · [Shader downloads and support scope](shader-setup.md)

For choosing what to correct on silver, gems, crowns, and fittings, see [accessory material decisions and procedures](accessory-materials.md). If you find missing volume or wrong connections, check shape with [mesh repair](mesh-repair-completion.md) before matching appearance.

The same model and images can look different because of color interpretation, light, shadows, outlines, or transparency. **Separate global display settings, individual materials, and rendering differences before correcting them.** Use this procedure when moving to another engine or matching the character between film shots.

## Establish these points at the start

| Item | Brief record |
| --- | --- |
| Goal | Preserve face, hair, and eye colors, shading, and outlines appropriate to the use and distance. If pixel matching is required, define its scope and tolerance separately. |
| Inputs | Versions of reference model, images, material preset, destination, and shader. |
| Editable and fixed | Display settings or materials to correct this time; shape, UVs, bones, expressions, and other items to preserve. |
| Comparison | Same camera position, field of view, resolution, pose, main light, and fixed exposure. Front, oblique, and side face views plus the whole body. |
| Exit and delivery | The saved result retains the reference impression in the destination. Deliver before/after images, changed values, preservation results, specification differences, and remaining work. |

## Adjustment order

1. **Match comparison conditions.** Record the camera and light above and lock exposure. Temporarily remove bloom or shot-specific grading that obstructs comparison. This does not prohibit production effects.
2. **Check image import and color management.** Match each image's role and original color space: for example, read ordinary sRGB base-color images as sRGB and numeric masks as linear data. Check misidentified normal maps, compression, exposure, and tone mapping. Do not repaint images to compensate for incorrect settings.
3. **Separate base color from shadow.** For whole-model differences, inspect display settings. For one dark area, such as the mouth, isolate its material. On a diagnostic copy, disable base color, AO, shadow, normals, and highlights one at a time and identify the visible faces and images.
4. **Match shading and hair highlights.** Adjust shadow boundaries, darkness, cast shadows from hair, and MatCap strength and position separately. MatCap highlights vary with viewing direction, so one front view is insufficient. Matching coefficients cannot restore cast shadows absent from the destination.
5. **Check outlines and transparency.** Review line width in close-up and whole-body views. Inspect feathers and hair against bright and dark backgrounds, at overlapping angles and during motion. Cutout and translucent rendering differ in edge behavior and draw order; choose for the intended use.
6. **Save and read back.** Save corrected materials and images into real files and reload them in the destination. Compare several angles and required expressions and movements. Check that old presets or regeneration processes do not undo the correction.

After a successful change, inspect unrelated areas under the same conditions. For small differences, also investigate capture order and rendering stabilization. Do not stack material corrections without identifying the cause.

## When only the mouth interior looks black

The interior includes the mouth bag, tongue, teeth, and inner lips. First identify the dark faces, for example by color-coding materials. Before increasing light on the whole face, **inspect those faces with base color alone, independent of lighting, AO, and shadow**. If darkness occurs only in video, compare a saved image of the same frame, the video, and the finished output to distinguish crushed blacks from export/color conversion and a source-material issue.

- If import, exposure, and color management are correct and base-color-only rendering is still dark, inspect the source color. Compare a few brightness options, separation from teeth and tongue, open “ah” and “oh” shapes, closed mouth, and smile. Do not make one color a default for every character.
- If base color alone looks natural, return to AO, shadow, cast shadows, and overlapping surfaces. Do not remove all body shadows to fix one mouth.
- If a shared color is the cause, update the reference material and corresponding output presets. A material multiplying base color by a shadow tint requires different values from a material with independent shadow color.

In Lida's production, the mouth bag's base color was dark and lighting/shadow changes had little effect, so only base color was changed. Besides Blender and VRM, actual Unity and UE rendering showed improvement in the same direction. **This corrected shared source material; it did not resolve an engine-specific difference.**

Example AI request:

> Check the expression showing the black mouth and a neutral face under matching conditions. Identify the visible faces first, then isolate the mouth bag's base color from light, AO, and shadows to explain the cause. If needed, compare a few mouth-bag-only color options while preserving shape, expressions, and other materials. Review front and oblique open-mouth views, closed mouth, and smile after saving in the destination. Report changed values, preservation of unrelated areas, and remaining work.

## When head and body skin shade differently

When skin on a separate material—such as a rebuilt head—is exported, that skin alone may receive no shade, so the neck seam shows a color difference. MToon shade is “shade image × shade color factor”; if the shade image is the base color image itself and the factor is 1, the shade equals the base color and shading disappears. Move the production toon material's shade color into the factor, or bake a shade image, then compare the neck seam with the body skin under the same light. If the shade boundary (shift) values differ from the body, an oblique light shows a step at the seam, so compare those values as well.

## When feather edges have a dark line

For transparent-image edges, **inspect the shadow-color image and alpha together with base color**. Correcting only base color may leave a dark edge on the shadowed side.

1. Enlarge the same feather against both bright and dark backgrounds and display base color, shadow color, and alpha separately. Distinguish lines caused by transparency order, cutout threshold, or outlines.
2. Establish whether RGB is multiplied by alpha and match the shader's expected convention. Do not unpremultiply an image that is already correct.
3. Only if image correction is needed, create a separate output. If shadow color is RGB-only, reference the correct alpha from the matching base-color image or equivalent. Avoid naïve division near alpha zero; extending visible feather color into transparent pixels is another approach.
4. Preserve image dimensions, original alpha, opaque regions, and unrelated images. Deliver both base-color and shadow-color images to the destination. After saving, recheck bright/dark backgrounds, the whole feather, and overlapping motion.

In Lida's VRM, base-color correction alone was insufficient: shadow-color images also retained dark edges. Both were corrected using corresponding alpha while preserving alpha itself. Verification covered VRM read-back rendering, not transparency ordering in every application.

Example AI request:

> Diagnose dark feather edges by separating base color, shadow color, alpha, outlines, and transparency mode. If image correction is required, establish the RGB/alpha convention, correct both color images into separate outputs, and preserve original alpha and opaque regions. Compare close-ups on bright and dark backgrounds, whole feathers, and overlapping movement in the destination. Record saved-image versions and unverified scope.

## For gray stains on cloth, isolate the outline shell

Similar-looking stains in Unity and UE need not share a cause. First isolate cloth fronts/backs, individual layers, outline shells, and corrective displacement one at a time. Compare with the same camera and time.

- **If an inner shell extends through outer cloth:** preserve required edge lines and compare a mask that suppresses outlines only inside the back cloth. In Lida's Unity example, only B in the outline mask changed; other channels and the front side were preserved. Check what B means in the shader being used; other images do not necessarily use that convention.
- **If corrective displacement swaps front/back depth order:** test whether the issue remains at zero shell thickness and disappears with the corrective disabled. In Lida's UE example, moving a test material's shell deeper away from the camera improved it. Supplying the same mask as Unity alone did not.
- **If depth adjustment is available:** check support in the shader being used and compare from small values. Excessive depth can hide needed lines. Inspect edges, oblique views, undersides, and motion. Also test whether orthographic projection preserves screen position as expected, alongside perspective. Example values are not universal defaults.

Isolate the cause before removing every outline, changing cloth shape, or distributing the same fix to every environment. Improvement in a test material, inclusion in a distributed shader version, and application to the real model are separate states. Do not present an unpublished feature as publicly released.

## Keeping the same character across shots

The following is an operating proposal drawn from production comparisons, not a workflow demonstrated across a complete film.

- **Save a character reference.** Under fixed comparison lighting, capture front, oblique, and side face views plus the whole body. Save material presets, distinctive base color/shadow/highlight/outline features, and versions together.
- **Record shot treatment separately.** Keep production lighting, exposure, and grading with the shot. When colors change, inspect capture conditions first instead of repainting the character's source colors every time.
- **Compare after finishing too.** Compare the face and silhouette after production grading, resolution changes, and compression with the reference. Record intentional changes; do not accidentally carry compensations into the next shot.

Example first AI request:

> Use the attached reference model and material preset. Compare front, oblique, and side face views and the whole body with the recorded camera, light, and fixed exposure. Check image import and color management first, then adjust base color, shadow, hair highlights, outlines, and transparency separately. Preserve shape, UVs, bones, and expressions. Deliver matched before/after images, changed values, save/reload results in the destination, specification differences, and remaining work. Finally compare the production shot after grading with the reference, recording character-material changes separately from shot changes.

## What to verify with AngelToon

There is no ranking of adjustment effort or guarantee of matching all three environments from defaults. The Blender column in the public comparison uses production-reference materials; it is distinct from applying the distributed Blender add-on to the real model. Unity and UE also use model-specific images, masks, and presets.

The current UE implementation is Unlit and does not receive cast shadows, leaving differences such as the appearance of hair depth. VRM MToon is a separate material specification. See [shader setup](shader-setup.md) for installation, versions, and supported environments, and these references for comparison conditions:

- [AngelToon color management and tone mapping](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/COLOR-AND-TONEMAP.md)
- [Real-model comparison conditions and limitations](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/images/engine-models.md)
- [Material examples including MatCap](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/images/README.md)

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
