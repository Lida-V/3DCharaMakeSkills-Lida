# Validation and distribution ZIP

[Japanese source](README.md)

`validate.py` checks the allowlisted contents, relative links, skill format, image hashes, translation coverage, and recorded source versions. It does not prove translation accuracy or visual acceptance. `build_package.py` validates the source, builds a reproducible ZIP and SHA256, and audits the completed archive. Neither command changes a model or an external service.

See [updating](../UPDATING.en.md) for commands and the maintenance workflow.

The completed ZIP must include the reference VRM as a Skills component. If a source checkout lacks it, explicitly run `python scripts/build_package.py --fetch-reference-model` to retrieve the pinned official archive and verify size, SHA, and exact member. The default build does not access the network. Reading the skill does not download or execute the model.
