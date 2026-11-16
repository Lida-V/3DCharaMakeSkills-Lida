# Check by script what is easy to miss

[日本語](../automated-checks.md) · [English](automated-checks.md)

[Process index](process-index.md) · [Bundled tools](model-tools.md) · [Mechanical checks and visual review](mechanical-visual-review.md)

**An export said "success" while settings were missing; an ornament split when a joint bent; an expression broke only at an intermediate value; a video of an older version was shown as the new one; a kept file still read from a deleted folder.** Each of these was checked by eye and memory and was actually missed. This chapter gathers the bundled tools that check those five things by a fixed procedure.

Every tool only measures and lists. Inputs are read-only; nothing is saved, deleted, or moved. Reports go only to new paths. Passing numbers do not replace checking the appearance and the behavior at the destination.

| What to check | Tool | Runs in | When |
| --- | --- | --- | --- |
| [1 Settings of an exported VRM](#1-settings-of-an-exported-vrm) | `lida_vrm_check.py` | Ordinary Python | After every VRM export; before loading it into an app |
| [2 Hard ornaments moving as one piece](#2-hard-ornaments-moving-as-one-piece) | `lida_rigid_group_check.py` | Blender | After assigning or changing weights |
| [3 Shape keys between values and in combination](#3-shape-keys-between-values-and-in-combination) | `lida_shape_key_sweep.py` | Blender | After making or changing keys; before export |
| [4 Review media and the saved version](#4-review-media-and-the-saved-version) | `lida_evidence_manifest.py` | Ordinary Python | When review images or videos are made, and before showing them |
| [5 References before clean-up or moving](#5-references-before-clean-up-or-moving) | `lida_reference_check.py` | Blender and ordinary Python | Before deleting work files or moving folders |

Shape contact is covered elsewhere: [fitting accessories](accessory-fit.md) and [find penetration by numbers and decide the repair](penetration-check.md). Version comparison, weight sums, and skeleton/humanoid mapping are in the [bundled tools](model-tools.md).

## Shared rules

- Name saved files as input. Tools that use Blender open them in a separate background process and do not save.
- JSON reports are written only to new paths. The command stops if the path exists.
- Exit codes: 0 = nothing found, 2 = findings or warnings, 1 = input or execution error.
- Usage errors such as a missing argument also stop with 2 and write no JSON. Tell them apart by the `status` of the JSON written in this run.
- The report's `unverified` lists what the tool did not check. Copy it into the completion report.
- The AI reads the result, looks for the cause, and compares any repair with the user's instructions. A tool's 0 is not a basis for calling the work complete.

## 1 Settings of an exported VRM

An export can report success while settings inside the file are missing. `lida_vrm_check.py` reads only the JSON and the image headers inside the VRM (glb) and checks the following. It needs neither Blender nor numpy.

| Area | Examples that raise a warning |
| --- | --- |
| Materials | Materials that are not MToon and came out as PBR. Blend materials that write depth (on feathers or hair cards, transparent pixels then hide what is behind) |
| Spring bones | Gravity that does not point down (0, −1, 0 in VRM's Y-up axes). A spring that uses colliders while every joint has hit radius 0. Collider groups that are empty, refer to nothing, or are used by no spring |
| Humanoid | Any of the 15 required bones missing. Two bones pointing to one node |
| Look-at | An origin behind or below the head bone (swapped axes) |
| Expressions | Missing preset expressions (5 vowels, 3 blinks, 5 emotions). A morph index beyond the mesh's target count. Expressions without content |
| Meshes | Parts without UVs. Joints without weights or the reverse |
| Images | Larger than the limit (2048 by default). Formats other than PNG and JPEG |
| Extensions | Required extensions that loaders may not support |

```sh
python lida_vrm_check.py check --input model.vrm --report vrm_check.json
```

- Adapt to the production's rules with `--max-texture 4096`, `--expect-mtoon any|ignore`, `--expect-expressions aa ih …`, and `--allow-extension NAME`.
- `springs`, `materials`, `meshes`, and `images` hold counts. Placing them beside the previous version's report shows unintended changes.
- For VRM 0.x, only materials, gravity, hit radius, and images are checked.
- When gaze is driven by bones, empty lookUp and similar expressions are normal and raise no warning.
- The look-at origin is written in the head bone's own space. It is turned into model space with the rotations of the head bone and its parents before judging whether it lies behind or below (`look_at.offset_in_model_space` in the report). With exports that keep bone rotations, a negative z in the file can be correct.

Not checked: appearance and sway at the destination, the content of shapes, weights, and morphs, and whether collider sizes suit the body.

## 2 Hard ornaments moving as one piece

When parts that must move together, such as a gem and its setting or a star and its stone, carry different weights, they separate when the joint bends. `lida_rigid_group_check.py` reads the weights of the parts in a group, turns each influencing bone alone by ±30°, fits the best rigid motion to the whole group, and reports in mm how far any vertex strays from it.

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_rigid_group_check.py -- check --input model.blend --rig Armature --group Gem Setting --group Tiara --group Bodice@GemMaterial --report rigid.json
```

- Repeat `--group` for each group. `Object@Material` selects only the faces of that material (a gem inside a merged object).
- `weight_rows` is the number of distinct weight combinations in the group. `largest_deviation_mm` is the stray distance and `worst_pose` the bone and axis where it happens.
- How to read it:

| State | Meaning | Action |
| --- | --- | --- |
| One bone, one row | Exactly rigid | Keep |
| Several bones, one row | Stays together, but shears slightly when those bones move apart | Acceptable if the stray is small. Check sinking and floating against the surface below separately |
| Several rows | Parts or vertices follow different bones and split when bent | Give every vertex of the group the same row. The report's `mean_row` is a starting point |

- Do not include parts that are meant to bend, such as chains and connecting links. They would be reported as splits.
- Defaults: tolerance 0.3 mm, angle 30° (`--tolerance-mm`, `--angle`).

Not checked: real poses and motion, volume-preserving skinning, and sinking or floating against the surface below. The computation uses linear skinning and does not pose the scene.

## 3 Shape keys between values and in combination

A key that looks right at 0 and 1 can fold at 0.35, and two keys that are fine alone can break when mixed. `lida_shape_key_sweep.py` moves keys and combinations in fine steps (20 by default) and reports the worst value and where it happens.

| Measure | Meaning |
| --- | --- |
| `folds` | Faces folded back onto a neighbor (faces below 120° at rest that exceed 150°) |
| `collapsed` | Faces whose area fell below 5 % of the rest area |
| `stretch` | Largest growth of an edge (edges under 1 mm at rest are left out) |
| `new_crossing_spots` | Crossing spots with a partner (eyeball, teeth) beyond the number at rest |

A lid rim touches the eyeball along one loop even at rest. The tool therefore counts separate spots, not curve length. When an eyeball pokes through a lid on the way, one spot is added.

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_shape_key_sweep.py -- sweep --input model.blend --object Face --all --combo happy+blink happy=1+blink aa+happy --partners Eye_L Eye_R Teeth --report sweep.json
```

- Combinations are `a+b` (both run 0→1) and `a=1+b` (a held at 1 while b runs). List the combinations that the destination's rules (VRM overrides and similar) can really produce.
- **Use an approved version as the baseline.** Intended folds, such as overlapping lids of a closed eye, also appear in the counts. Pass the report of a version whose look was approved as `--accept`; only values worse than that become problems. The first time, check every item in images and keep the approved report as the baseline.
- A partner that has keys of the same names moves with the same values (teeth, shadow layers).
- `driven_keys` lists keys moved by drivers.
- A key that moves nothing is reported as `the key moves nothing`, and stays reported with `--accept`. Read the report to decide about keys left empty on purpose.
- Thresholds are options: `--steps` (20), `--fold-from-degrees` / `--fold-degrees` (120 / 150), `--collapse-ratio` (0.05), `--stretch-limit` (3.0), `--min-edge-mm` (1.0), `--moved-mm` (0.01), `--spot-mm` (3.0), `--fold-limit`, `--collapse-limit` and `--spot-limit` (0 each). `--keys` limits the keys examined. These are values of the worked example, not quality criteria.

Not checked: the look of expressions, a slit left by a closed eye, drivers and slider limits, and modifiers after the keys (subdivision) and normals. The tool does not change key values in the file.

## 4 Review media and the saved version

After a model is saved again under the same name, an older video can be taken as a review of the new version. `lida_evidence_manifest.py` records the size and SHA-256 of review images and videos and of the saved versions they came from, and verifies them later.

```sh
python lida_evidence_manifest.py record --sources model.blend model.vrm --media sheet.jpg turn.mp4 --manifest evidence.json --note "front and expressions"

python lida_evidence_manifest.py verify --manifest evidence.json
```

| Result | Meaning | Action |
| --- | --- | --- |
| `same` | As recorded | Use as is |
| `stale` | The media are intact, but the source model changed | Render again from the current version, or label them as the old version |
| `changed` | The image or video was replaced | Record again |
| `missing` | The file is not there | Check the location |

- Run `record` when the media are made. Run `verify` before showing them to the user and before writing an adoption record.
- Paths are stored relative to the manifest. A moved folder still verifies, and no absolute local path enters the manifest.
- Keep the manifest on the same drive as the files.

Not checked: whether the media show what needs to be seen. A match proves only which file was shown.

## 5 References before clean-up or moving

Deleting work files or moving folders can drop images from kept blends or stop kept scripts. `lida_reference_check.py` lists what still depends on the targets before anything is removed.

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_reference_check.py -- blend-refs --inputs keep_a.blend keep_b.blend --report refs.json

python lida_reference_check.py impact --targets stage/work stage/raw --refs refs.json --scan stage/scripts notes --report impact.json
```

1. `blend-refs` opens each kept blend read-only and lists its external files (images, libraries, sounds, fonts, caches, movie clips): location, whether the file exists, and whether it is packed. Files already missing appear here too.
2. `impact` takes the targets to delete or move (`--targets`) and lists
   - external files of kept blends that lie inside a target (`would_break`),
   - lines of kept scripts, notes, and configs that write a target's path or its last two path parts (`path_mentions`),
   - lines that write only the name of a file inside a target (`name_mentions`, weaker evidence).
- Delete only when `would_break` and `path_mentions` are 0. Read the lines of `name_mentions` and decide.
- Before moving a blend, check its relative external files with `blend-refs`. Opening and saving it after the move rewrites the broken paths.
- Reports contain local paths. They are working notes and do not belong in published material.
- The tool deletes and moves nothing. Removal is a separate step after the user's approval.

Not checked: blends, folders, and other projects that were not listed, paths assembled from variables at run time, and files read by applications other than Blender.

## Example requests to an AI

```text
Check the VRM exported from <version> with lida_vrm_check.py and report each warning with its cause.
Place the counts of materials, springs, meshes, and images beside the previous version's report at <location>. Do not change the input.
```

```text
Sweep every key of the face <object> of <version> with lida_shape_key_sweep.py. Partners are the eyeballs and teeth.
Include the combinations <those the destination's rules produce> and pass the approved report <location> as --accept.
Report worsened items with an image at that value, and ask me before repairing.
```

```text
Before deleting <folder>, check the kept blends <list> and the kept script folders <list> with lida_reference_check.py.
While would_break or path_mentions is not 0, delete nothing and report the lines. Delete only after my approval.
```

## Verified scope

- `lida_vrm_check.py`: read three really exported VRM 1.0 files (about 52–217 MB). 48 springs, 169 joints, 25 colliders, 11 groups, 77 MToon materials, and 205 images up to 2048 matched the production records. A version that still had 14 feather materials writing depth while blending raised that warning.
- `lida_rigid_group_check.py`: Blender 5.3.0 in background, five groups of a model with 109 bones, read-only. Head ornaments strayed 0 mm, a choker containing a link that is meant to bend 11.7 mm, and a part containing ankle ornaments 5.7 mm, in line with the recorded weights.
- `lida_shape_key_sweep.py`: the face of the same model (14 keys, 5,917 vertices) with eyeballs and teeth; 14 single keys and 4 combinations in about 9 seconds. Passing the same report as `--accept` gave no problems.
- `lida_evidence_manifest.py` and `lida_reference_check.py`: recording, verifying, detecting an external image, and detecting script lines were run on a small self-made blend and image.
- All five have ordinary-Python regression tests ([test notes](model-tools.md#verified-scope)).

Not verified: other Blender versions, real VRM 0.x files, comparison with what UniVRM or viewers load, results of repairing items found by the sweep, and use in a real clean-up. Example counts are not quality criteria.

## Terms

The five scripts are GPL-3.0-or-later (author: Lida). They follow the same [terms as the bundled tools](model-tools.md#license-and-installation-scope); retain the GPL text and file-header notices. This document follows [usage and attribution](usage-and-attribution.md).
