# Verification of the checks

[Japanese source](README.md)

The tests check rejection of broken links, local paths, excluded materials, credentials, replaced images, missing or inconsistent licenses and notices, inconsistent versions, disguised reference FBX files, and incomplete or altered ZIP contents. They also check reproducible ZIP creation and preservation of terms, notices, and helpers when the skill folder is copied on its own.

The attribution helper is checked for read-only and model-output behavior, check mode, English notices, and preservation of existing text. Translation checks cover missing or empty English files, unregistered chapters, and changes to the reviewed Japanese source. These are structural checks, not proof of translation meaning.

```sh
python -m unittest discover -s tests
```

`test_model_tools.py` runs with ordinary Python. It checks import and help without Blender, snapshot schema and comparison, unverified fields, and refusal to overwrite existing JSON. It does not exercise Blender model processing.

Separate synthetic-fixture checks used Blender 5.2.1 LTS: the earlier helper API covered 14 cases and its CLI 19; the later rig-audit addition covered 15 API and 9 CLI cases, plus one synthetic FBX case. See [tool scope and limitations](../skills/lida-avatar-workflow/references/en/model-tools.md). Fixtures and production models are not distributed.

To select a writable test location, set `LIDA_DISTRIBUTION_TEST_TEMP` to a dedicated directory. Otherwise the normal temporary directory is used. Each test cleans up only its own temporary folder. License text in test fixtures is not the pack's formal license.
