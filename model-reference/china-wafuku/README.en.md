# China Wafuku — Production reference model r35

[日本語](README.md) · English

© 2026 Lida · [Official source](https://github.com/Lida-V/3DCharaMakeSkills-Lida)

This is a separate production example from the Lida avatar, selected by the user as a completed reference. **[Download the reference-only ZIP](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/model-reference-r35/ChinaWafuku-Reference-r35.zip)** and open the model in a VRM 1.0 compatible tool. The regular Skills ZIP does not contain the model.

**Redistribution of the model and sale of modified versions are prohibited.** Read the [model-specific terms](MODEL-TERMS.en.md) first. Commercial use and redistribution terms for the Skills pack itself are unchanged.

## Use

1. Compare the downloaded files against `SHA256SUMS.txt` and the Release `.zip.sha256` file.
2. Open `ChinaWafuku-Reference-r35.vrm` as a reference, keeping it separate from the model you are producing. A suitable VRM environment is required separately.
3. Inspect only the relevant parts: shape, surface lines, bones and weights, expressions, and materials under matched conditions. Tell the AI which part and features to study. Follow the [observation guide](https://github.com/Lida-V/3DCharaMakeSkills-Lida/blob/main/skills/lida-avatar-workflow/references/en/model-reference.md).
4. Apply the observed principles to your own reference art and model structure. Do not copy the example's measurements, topology, or character design wholesale. Save adjustments to a new candidate and check appearance and motion.

## Contents and verification

| Item | Scope |
| --- | --- |
| Source version | r35 / internal revision37 |
| Format | VRM 1.0; 28 meshes, 125 nodes, 38 embedded images, 18 spring chains, 13 colliders |
| Included | One model, Japanese/English guides and terms, structure/hash JSON, checksums |
| Excluded | Edit-source Blend, FBX, reference dance or motion, API logs, production environment |
| Preservation check | Distribution and source VRM BIN bytes match exactly; JSON matches outside the public metadata |
| Appearance | VRM uses MToon-style materials, without the native LidaAngelToon editing node graph |
| Limits | Exported triangle topology is not the original edit topology; no Unity/UE appearance or motion acceptance is guaranteed |

Only public metadata has been aligned, so source and distribution VRM file hashes differ. `reference-manifest.json` records both hashes and the changed metadata fields. Public authorship is shown as Lida. The original production model remains unchanged.
