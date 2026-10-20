# Usage categories and attribution in published work

[Japanese source](../usage-and-attribution.md) · Source baseline: 2026-10-20.

## Commercial use

This package permits commercial and noncommercial use, including model sales, commissioned production, commercial images/video, and incorporation into commercial apps or new Skills. The attribution-retention conditions below apply to both. Check generation-service, input-material, third-party-model, and other applicable conditions separately.

## Creating a model

If you only read this skill to create a 3D model, image, or video, that output does not need credits to Lida or these documents. Check any separate conditions for materials, services, and models you use.

## Publishing an app or new Skills package

When publishing an app/new Skills package that refers to these documents or incorporates text, diagrams, AI instructions, or helper code, put the following source information where recipients can read it. Use README, About, or Third-party notices for apps; README or NOTICE for skills, for example.

> Production procedures and AI instructions refer to “3DCharaMakeSkills-Lida” by Lida.
> https://github.com/Lida-V/3DCharaMakeSkills-Lida
> Used/modified portions: identify the chapters actually used and the changes made.

If also using the shader, retain LidaAngelToon / Lida / https://github.com/Lida-V/LidaAngelToon and actual use/modification details. Carry forward its applicable licenses separately.

Within the request to create the published work, the AI writes attribution into actual files and reports locations/content. Adding attribution only to a prompt is insufficient; do not remove existing author notices. Reading the skill alone does not authorize changes to another project.

The bundled Blender `lida_model_tools.py` separately uses GPL-3.0-or-later. Retain the [tool's applicable terms](model-tools.md) and GPL text; do not add this documentation's custom conditions to GPL code. The helper below does not create the GPL text or a complete code-distribution package.

## Helper script for attribution files

With Python available, run from the skill folder. It is unnecessary for model creation alone.

```sh
python scripts/ensure_attribution.py --target app --component skills --project-dir <published-project-folder> --language en --changes "Referred to the material-planning and deformation-review procedures"
python scripts/ensure_attribution.py --target app --component skills --project-dir <published-project-folder> --language en --check
```

Use `--target skill` for a derived skill, or `--component both` if including the shader too. The helper appends to `THIRD_PARTY_NOTICES.md` in the specified destination, preserving existing text/change notes without duplicate sources. `--check` only inspects. If reproducing or bundling the documents, retain [LICENSE](../../LICENSE) as well as attribution.

`--language en` selects new English attribution. Existing Japanese/English entries are not rewritten; changing language does not add duplicates. Supply change notes in that language describing the actual use.

## Distinguish license terms from AI publication practice

The formal permission is in the [bundled LICENSE](../../LICENSE), and original source notices in [NOTICE](../../NOTICE.md). [English license assistance](../../LICENSE.en.md) and [English notice assistance](../../NOTICE.en.md) are companion translations, not changes to permission. Attribution-retention conditions apply to reproduction, modification, and redistribution of the material. AI publication procedures also record the reference when only general methods are consulted without copying text; this does not claim exclusive rights over ideas/facts outside copyright. The destination project as a whole need not adopt this license.

These documents do not grant rights to the character, model, received materials, or reference dance FBX. Keep self-created and third-party materials separate. Exclude reference FBX, renamed copies, and converted reference motion from distribution packages.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
