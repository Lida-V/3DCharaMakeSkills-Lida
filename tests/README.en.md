# Verification of the checks

[Japanese source](README.md)

The tests check rejection of broken links, local paths, excluded materials, credentials, replaced images, missing or inconsistent licenses and notices, inconsistent versions, disguised reference FBX files, and incomplete or altered ZIP contents. They also check reproducible ZIP creation and preservation of terms, notices, and helpers when the skill folder is copied on its own.

The attribution helper is checked for read-only and model-output behavior, check mode, English notices, and preservation of existing text. Translation checks cover missing or empty English files, unregistered chapters, and changes to the reviewed Japanese source. These are structural checks, not proof of translation meaning.

```sh
python -m unittest discover -s tests
```

`test_model_tools.py` runs with ordinary Python. It checks import and help without Blender, snapshot schema and comparison, unverified fields, and refusal to overwrite existing JSON. It does not exercise Blender model processing.

`test_accessory_fit.py` covers the numeric core of accessory fitting. Against an analytic elliptic cylinder it checks that the outline encloses the real surface, that axial position and azimuth do not change, open-arc detection, push-only, rigid pieces, warnings and refusal, and protection of existing outputs. It needs numpy and skips those tests where numpy is absent. Blender runs and render checks are recorded in [fitting accessories](../skills/lida-avatar-workflow/references/en/accessory-fit.md#verified-scope).

`test_penetration_check.py` covers the numeric core of the penetration check. With a strip passing through a cube it checks crossing length, spot grouping, hidden and allowed crossings, the conditions and thresholds of repair suggestions, before/after comparison, and protection of existing outputs. It needs numpy and skips those tests where numpy is absent. Blender runs and image checks are recorded in [find penetration by numbers and decide the repair](../skills/lida-avatar-workflow/references/en/penetration-check.md#verified-scope).

Separate synthetic-fixture checks used Blender 5.2.1 LTS: the earlier helper API covered 14 cases and its CLI 19; the later rig-audit addition covered 15 API and 9 CLI cases, plus one synthetic FBX case. See [tool scope and limitations](../skills/lida-avatar-workflow/references/en/model-tools.md). Fixtures and production models are not distributed.

To select a writable test location, set `LIDA_DISTRIBUTION_TEST_TEMP` to a dedicated directory. Otherwise the normal temporary directory is used. Each test cleans up only its own temporary folder. License text in test fixtures is not the pack's formal license.
