# China Wafuku — Production reference model r35

[日本語](README.md) · English

© 2026 Lida · [Official source](https://github.com/Lida-V/3DCharaMakeSkills-Lida)

This completed example, distinct from the Lida avatar, is a production-reference component of the Skills. **[Download the complete Skills ZIP with the model](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.8.1/3DCharaMakeSkills-Lida-1.8.1.zip)**, extract it, and install the entire skill folder. The VRM 1.0 and its terms are installed together; no separate download is needed.

**Redistribution of the model and sale of modified versions are prohibited. Users may not redistribute the complete ZIP containing it.** Read the [model-specific terms](MODEL-TERMS.en.md). Documentation, diagrams, and code can still be used and redistributed under their applicable licenses after excluding the model.

## Use

1. Check the complete Skills ZIP against the Release `.zip.sha256` file.
2. Open the skill's `assets/model-reference/china-wafuku/ChinaWafuku-Reference-r35.vrm` as a reference, keeping it separate from the model you are producing. A suitable VRM environment is required separately.
3. Inspect only the relevant parts: shape, surface lines, bones and weights, expressions, and materials under matched conditions. Tell the AI which part and features to study. Follow the [observation guide](https://github.com/Lida-V/3DCharaMakeSkills-Lida/blob/main/skills/lida-avatar-workflow/references/en/model-reference.md).
4. Apply the observed principles to your own reference art and model structure. Do not copy the example's measurements, topology, or character design wholesale. Save adjustments to a new candidate and check appearance and motion.

## Contents and verification

| Item | Scope |
| --- | --- |
| Source version | r35 / internal revision37 |
| Format | VRM 1.0; 28 meshes, 125 nodes, 38 embedded images, 18 spring chains, 13 colliders |
| Included | One reference model, Japanese/English model-specific terms, and structure/hash JSON in the complete Skills ZIP |
| Excluded | Edit-source Blend, FBX, reference dance or motion, API logs, production environment |
| Preservation check | Distribution and source VRM BIN bytes match exactly; JSON matches outside the public metadata |
| Appearance | VRM uses MToon-style materials, without the native LidaAngelToon editing node graph |
| Limits | Exported triangle topology is not the original edit topology; no Unity/UE appearance or motion acceptance is guaranteed |

Only public metadata has been aligned, so source and distribution VRM file hashes differ. `reference-manifest.json` records both hashes and the changed metadata fields. Public authorship is shown as Lida. The original production model remains unchanged.
