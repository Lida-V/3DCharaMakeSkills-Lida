# Updating an installation and maintaining the distribution

[Japanese / 日本語](UPDATING.md) · Source baseline: 2026-10-20.

## Updating as a user

1. Check the source VERSION and changelog; note your installed version.
2. Back up any instructions, images, or settings you added.
3. Extract the new ZIP and replace the entire contents of `skills/lida-avatar-workflow`, retaining reference documents, images, LICENSE, NOTICE, and scripts.
4. Load the skill and confirm that the process index leads to needed chapters/images. Restore only needed custom changes from the old version.

Python, Git, and the shader are not required merely to read the procedures and make a model. For initial setup, use the installation check in [README](README.en.md).

## Updating as an author or contributor

1. In the production project, record reference versions, actual requests, causes, changing/fixed areas, comparisons, selection, and remaining work.
2. Put reusable methods in existing dedicated chapters and link from the process index. Do not copy private logs/models wholesale. Maintain corresponding Japanese/English chapters together. Before updating manifest `source_sha256`, compare meaning and conditions with the changed source. A hash update alone must not hide a missing translation or an unreviewed older version.
3. Add only original diagrams. Visually inspect source, lettering, comparison conditions, and selection status. Exclude reference dance FBX and renamed/converted reference motion.
4. Align VERSION, CHANGELOG, and `manifest.version`; explicitly list new files/image hashes in the manifest. Keep root and portable-skill LICENSE/NOTICE copies identical.
5. Run the README's validation, unit tests, and ZIP build. Also inspect the output ZIP's inventory for duplicates, missing/extra files, and content equality against source files.
6. Using your own permissions, update a work branch, review PR changes/CI, and merge into main. Do not put credentials in documents or command text.

This does not require another person to sign into the author's account. With Git, use your own clone/fork. In GitHub's UI, use Upload files for the target folder; do not select the whole production folder.

## Before publishing an app or derived Skills package

Following [attribution retention](skills/lida-avatar-workflow/references/en/usage-and-attribution.md), write source name, Lida, original URL, and used/modified portions into README, About, NOTICE, or similar files. Keep applicable LICENSE with reproduced/incorporated material. Confirm the conditions remain reachable from a standalone skill copy.

Check [LidaAngelToon](https://github.com/Lida-V/LidaAngelToon) version, supported environments, and licenses separately. This is not a requirement to credit outputs made only by following model-production procedures. The Blender model helper's separate GPL-3.0-or-later terms remain applicable to its code; do not impose the documentation's custom terms on it.

The administrator separately decides repository visibility changes and public releases. Packaging/building a ZIP alone does not authorize publication operations.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
