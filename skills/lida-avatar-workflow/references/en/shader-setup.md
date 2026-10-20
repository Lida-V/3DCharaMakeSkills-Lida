# Getting and choosing LidaAngelToon

[Japanese original](../shader-setup.md)

[LidaAngelToon](https://github.com/Lida-V/LidaAngelToon) is a separate shader repository. You do not need it to use this model-making workflow. Choose it for the appearance and software you need.

Choose the ZIP for your environment from the public [Release v0.2.1](https://github.com/Lida-V/LidaAngelToon/releases/tag/v0.2.1). The repository distribution version is 0.2.1; each implementation is version 0.1.0. The complete source ZIP is for developers, not for installing the Blender add-on.

| Destination | Distribution and verified scope |
| --- | --- |
| Blender | [Blender add-on ZIP](https://github.com/Lida-V/LidaAngelToon/releases/download/v0.2.1/LidaAngelToon-0.2.1-blender-addon.zip). Apply, restore, save, and reopen were verified on primitives in Blender 5.2.1 LTS / EEVEE. Cycles and other Blender versions are unsupported or unverified. |
| Unity | [Unity ZIP](https://github.com/Lida-V/LidaAngelToon/releases/download/v0.2.1/LidaAngelToon-0.2.1-unity.zip). Actual rendering was verified on Windows with Unity 6000.6.0f1 / URP 17.6 / Linear / Forward+ / D3D11. [Installation](https://github.com/Lida-V/LidaAngelToon/blob/main/unity/README.md). |
| Unreal Engine | [UE ZIP](https://github.com/Lida-V/LidaAngelToon/releases/download/v0.2.1/LidaAngelToon-0.2.1-unreal.zip). Actual rendering was verified on Windows / UE 5.8. Python builds materials and related assets; `.uasset` files are not included. The implementation is Unlit and does not receive cast shadows. [Installation](https://github.com/Lida-V/LidaAngelToon/blob/main/unreal/README.md). |
| VRM MToon | A separate material specification. Blender features do not all transfer unchanged. Read back and compare the actual export. |

The [Lida model images in the shader README](https://github.com/Lida-V/LidaAngelToon#リダのモデルで見る3つの表示例) compare Blender development-reference materials with the Unity and UE implementations. The Blender column does not show application of the distributed add-on, and each engine column uses specially configured materials and images. They do not demonstrate identical appearance from defaults alone. Numeric equivalence between the add-on and common HLSL, unlisted operating systems/APIs/versions, and automatic VRM conversion are unverified or not included.

## The shortest Blender setup

1. Download the Blender add-on ZIP above and read [support scope](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/SUPPORT.md) and [LICENSE](https://github.com/Lida-V/LidaAngelToon/blob/main/LICENSE).
2. In Blender, use Edit → Preferences → Add-ons → Install from Disk. Select the ZIP without extracting it, enable the add-on, and use EEVEE.
3. Add a sphere and open LidaAngelToon with `N` in the 3D View. Choose `Cloth` → `Apply to selected meshes`, then check color and shadow in rendered display before applying it to a model copy. Preserve original materials and images. Compare the whole body and required close-ups with the same light and camera.
4. If exporting, use [the read-back procedure](visual-handoff.md) to check how materials, AO, highlights, and outlines reproduce.

The target is the active material of selected meshes. Follow the shader repository's [installation and update instructions](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/INSTALL.md) for setup, main-light selection, and restoring original materials. Displaying correctly in Blender does not guarantee the same appearance elsewhere.

You do not need to install the Skills, Blender material generator, Unity/UE implementations, and extra VRM features all at once. Choose your supported environment and prepare only its required dependencies. Neither reference dance FBX files nor avatar models are included in the shader pack.

## Starting in Unity or UE

For Unity, place `unity/com.github.lida-v.lidaangeltoon` from the ZIP with its `.meta` files, create URP materials, and set base colors and images. For UE, place `unreal/LidaAngelToon` under Content, enable the Python Editor Script Plugin, and build materials and related assets with the included script. Follow each installation document above for exact placement and requirements.

Check the main light, outlines, and colors on primitives first. Then assign materials to a model copy and compare full-body and close-up views. Check translucent overlap, outline normals, exposure and tone curves, and UE's cast-shadow limitation too. Supply your own model, images, and material assignment table; Blender settings do not transfer automatically.

For differences, use [appearance adjustment by destination](cross-engine-look.md). Check image import and color management, base color and shadow, hair highlights, then outlines and transparency. Separate shared-source corrections from engine-specific behavior.

## Updates and attribution

Record the version, presets, and your material changes, and update a recoverable copy. Check primitives → model comparisons under matching conditions → save and reopen. Do not reuse an old-version video as verification of a new version.

Models and ordinary rendered outputs require no credit. When including the shader in a public app or new Skills, follow [attribution](usage-and-attribution.md) and the shader's file-specific licenses. The Blender add-on using `bpy` is GPL-3.0-or-later. In 0.2.1, Unity, UE, common HLSL, documentation, and original assets use Lida Attribution License 1.1. Preserve `LICENSE.md` in the Unity package and UE folder; the shader repository's LICENSE governs the file-by-file mapping. This does not change the Skills' own terms.
