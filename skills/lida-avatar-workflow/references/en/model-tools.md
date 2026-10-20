# Use the bundled model-production tools

[Japanese source](../model-tools.md) · Source baseline: 2026-10-20.

**The Skills package guides decisions and order; tools perform repeated checks and processing.** These helpers avoid rewriting identical inspection code and make before/after comparisons under the same conditions possible.

[lida_model_tools.py](../../scripts/lida_model_tools.py) is a distribution-focused reworking of general operations from the Lida Avatar Toolkit used in production. Run it only when needed from a separate Blender session, without registering the whole resident add-on. It does not replace existing add-on settings or production panels.

## Included functions

| Function | When to use | Output |
| --- | --- | --- |
| `rig-audit` | After auto-rig receipt; before/after bone correction | Mechanical checks of an explicit rig's structure and specified humanoid mapping/meshes; explicitly identifies image/motion checks still needed |
| `audit` | After receiving rough 3D; before/after topology, UV, weight, or key adjustments | JSON of named meshes' structure and values |
| `snapshot` | Before correction, after saving/reopening, around part integration | Itemized hashes of base coordinates, connectivity, UVs, deformation weights, key coordinates/deltas, material slots/face assignments, and source-file SHA |
| `compare` | When before/after snapshots exist | Per-target, per-item equality/differences; also runs in ordinary Python |
| `normalize-copy` | Only weight sums need correction and targets/preservation are established | Candidate copies, separate blend file, and inspection JSON |

Weight checks include groups belonging to deforming bones, not ordinary masks. Normalization preserves locks/masks and adjusts the sum of unlocked deform weights. Unassigned, negative, nonfinite, or contradictory locked weights remain unresolved; the tool does not invent a fallback bone assignment.

The tool does not automatically score resemblance to the art, suitability of edge layout, or natural bending. Boundary edges, out-of-range UVs, and unchanged keys may be intentional; use [visual judgment](visual-handoff.md) rather than deleting/repairing from counts alone. Normalization does not correct bone placement, shape, face flow, or wrong target assignments.

## Requirements

- Blender and a saved blend to inspect. See verified versions below.
- Target mesh names; corresponding armature name when handling weights.
- New JSON output paths; a new blend path different from the input for a repair candidate.
- [Stage goal](quality-goals.md), items allowed to change, and preservation requirements.

No API keys, external services, additional Python packages, or network connection are used. The tool neither installs Blender nor obtains source models/reference motion. Reading the skill does not require installing a runtime.

## AI execution order

1. Check available Blender, input version, mesh names, rig, and output paths. Inspect current data/correspondence rather than guessing names.
2. Run `audit` first and read its JSON targets, inspection scope, and untested items. Do not save the source blend for diagnosis alone.
3. Take a pre-change `snapshot` and define fixed items. Repeat after correction and after reopening, then use `compare`.
4. Only when needed, run `normalize-copy` on explicit targets. Check the new candidate and preservation; do not automatically adopt it into the source.
5. Compare images/motion in matching views/poses and report mechanical, visual, saving, and destination acceptance separately.

If Blender is unavailable, do not claim the tools ran. Record the reason and what was checked manually. Do not change an accepted model or art merely to pass a check.

An exit code alone does not close a stage. Follow [mechanical/image/motion roles and assessment](mechanical-visual-review.md) to compare the same saved version with the art, inspect needed intermediate motion, and record outstanding destination work.

## First execution examples

Replace paths/names with actual files. Arguments after `--` belong to this tool. Disable automatic script execution from inputs and launch a separate session from ordinary production.

```sh
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- audit --input source.blend --objects Body --rig Rig --report audit-before.json
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- snapshot --input source.blend --objects Body --rig Rig --report before.json
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- snapshot --input candidate.blend --objects Body --rig Rig --report after.json
python lida_model_tools.py compare --left before.json --right after.json --report difference.json
```

Do not point JSON outputs at existing files. Check `--help` for actual usage. This is not a procedure for repeatedly registering the same script in a UI with an open model.

Use `audit --max-influences N` to match the destination's influence-count conditions. Default 4 is a reporting/comparison baseline, not a universal quality requirement. Exit code 0 means processing completed; 1 means input/execution error; 2 means snapshot differences or unresolved normalization. Read JSON to decide whether differences were intended; do not automatically repeat repairs from the exit code alone.

Usage errors such as missing/unknown arguments also return 2 and stop before generating JSON. Distinguish them using newly generated JSON and its `status`; do not read an older JSON as this run's result.

### Inspect skeleton structure and humanoid mapping

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_model_tools.py -- rig-audit --input source.blend --rig Rig --objects Body --human-bones human-bones.json --report rig-before.json
```

Inspect and specify actual rig/mesh names. Omitting `--objects` leaves mesh/weight correspondence untested; omitting `--human-bones` leaves VRM humanoid mapping untested. The tool does not infer success from bone names. For `rig-audit`, 0 means no issues detected in the specified mechanical items; 2 means mechanical findings; 1 means input/execution error. Read reasons and observations rather than applying uniform corrections without viewing the model.

`human-bones.json` is this tool's own mapping format. Left entries are VRM 1.0 roles; right entries are **actual bone names**. This example covers required roles. Inspect actual data and add eyes, jaw, fingers, shoulders, or other roles needed for the destination.

```json
{
  "schema": "lida.model-tools.humanoid-map.v1",
  "spec_version": "1.0",
  "human_bones": {
    "hips": "Hips", "spine": "Spine", "head": "Head",
    "leftUpperArm": "UpperArm.L", "leftLowerArm": "LowerArm.L", "leftHand": "Hand.L",
    "rightUpperArm": "UpperArm.R", "rightLowerArm": "LowerArm.R", "rightHand": "Hand.R",
    "leftUpperLeg": "UpperLeg.L", "leftLowerLeg": "LowerLeg.L", "leftFoot": "Foot.L",
    "rightUpperLeg": "UpperLeg.R", "rightLowerLeg": "LowerLeg.R", "rightFoot": "Foot.R"
  }
}
```

It checks required/optional roles in the [official VRM 1.0 specification](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md), duplicate assignments, bone existence, and ancestor relationships allowing intermediate auxiliary bones. Some optional roles need a mapped parent: `upperChest` needs `chest`, and thumb `Proximal` needs `Metacarpal`, for example. Fifteen is the number of required roles, not a model's total bone count or a high-quality requirement. This JSON is neither a VRM file's `humanBones` nor glTF node indices; the tool does not write exporter mapping.

It also checks bone values/lengths, reference/current poses, named meshes' Armature references, and deform weights. `--length-epsilon` is a length threshold in rig-local units; `--weight-tolerance` is sum tolerance; `--max-influences` is the reporting limit chosen for the destination. Default 4 is not a fixed VRM-spec requirement. Verify semantic correctness of left/right mappings, art-matching shoulder/knee placement, and natural bending with images/motion.

### Inspect upload-FBX size and identification format

The separate helper [lida_file_check.py](../../scripts/lida_file_check.py) runs in ordinary Python without Blender or extra packages.

```sh
python lida_file_check.py --input upload.fbx --report upload-check.json
```

It checks actual size, extension, FBX identification header, and SHA. The default cap is a conservative 150,000,000 bytes. Also check the current Tripo display during [upload preparation](tripo-autorig.md). Change `--max-bytes` only when a required limit is explicitly established.

0 means the listed file conditions pass; 2 means noncompliance; 1 means input/I/O error. Identification-header checks do not guarantee complete FBX syntax, bone/image preservation, importability, or service acceptance. The source is unchanged and output goes to new JSON; same-as-model/input paths and existing reports are rejected.

### Correct only weight sums on candidate copies

```sh
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- normalize-copy --input source.blend --objects Body --rig Rig --report normalize.json --output-blend weight-candidate.blend
```

The input path and existing output files are rejected. If unresolved weights remain, the tool reports them rather than saving a supposedly repaired candidate. The initial feature set does not include influence-count reduction, nearest-surface transfer, fully automatic rigging, or shape regeneration.

The candidate blend retains both original meshes and new copies. Use source/candidate names in the report to show one at a time. A render with both occupying the same position is not valid correction evidence; decide selection after comparing.

## What the reports establish

Matching `snapshot` contents establishes equality only for the listed base data. It does not establish matching bone reference pose, parenting/constraints, drivers, Geometry Nodes, material-node internals, evaluated shapes, external-image contents, animation, or destination behavior. Check unsupported items separately.

Nondeform groups such as masks, group locks, key values/mutes/playback settings are outside snapshot comparisons. Relative keys record coordinates/deltas/reference keys; absolute-key snapshots are unsupported and rejected. Materials record slot names/order/links and face assignments, not node internals. Lock/mask preservation during normalization is checked separately by that operation.

`compare` checks exact hash equality. It does not report maximum distances or tolerance-based acceptance for differing data. An authorized shape correction is expected to change that item. Compare allowed/fixed items; judge semantic vertex correspondence and appearance on the actual mesh.

Audits inspect base meshes and current saved data. They do not inspect self-intersection, body/clothing contact, or all animation frames. Dedicated eye/wing generation, all production panels, the old Toolkit's secondary-motion handler, gem generation, and shaders are not bundled into this script.

## Verified scope

The initial 2026-10-15 implementation was checked in **Blender 5.2.1 LTS background execution**, using synthetic models: 14 API items, 19 CLI items, and 7 ordinary-Python regression tests. The 2026-10-19 extension checked 15 skeleton-audit API cases, 9 CLI cases, and rechecked the existing 19 CLI items in the same environment. Old Toolkit successes do not substitute for testing this implementation.

Tests cover valid models, degenerate faces, nonfinite coordinates, out-of-range UVs, unchanged keys, unassigned/nonfinite weights, lock contradictions, and changed connectivity with equal vertex counts. They also cover lock/mask preservation on copies, source-file SHA preservation, separate candidate saving/reopening, and existing-output rejection.

The FBX-condition CLI has 19 tests for synthetic headers, size boundaries, existing-output preservation, and related behavior. Two link-creation tests could not run in the source test environment; 17 passed. Same-path and ordinary alias output rejection were checked. One Blender-generated synthetic FBX also passed header/size checks with unchanged source SHA. This does not verify complete FBX syntax or service acceptance.

These are tests of the listed operations on synthetic models, not verification of other Blender versions, GUI add-on installation, all real-model poses, modeling/art fidelity, or destination quality.

## License and installation scope

This Blender script is **GPL-3.0-or-later**. Check its file header and the [bundled GPL text](../../scripts/LICENSE-GPL-3.0-or-later.txt). Keep this separate from document/diagram terms; do not impose this package's custom attribution conditions on GPL code. Retain original copyright notices and applicable license.

Creating models/images/video alone does not require credits on the resulting work. For public apps or new Skills incorporating these documents/instructions, follow [usage and attribution](usage-and-attribution.md).

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
