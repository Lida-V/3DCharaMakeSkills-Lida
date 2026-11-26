# Measure the hand and place the finger joints, rolls, and weights from its shape

[日本語](../hand-rig.md) · [English](hand-rig.md)

[Process index](process-index.md) · [Bundled tools](model-tools.md) · [Building the hand](hand-shape.md)

**After you fix or rebuild a hand's shape, this avoids re-fitting the finger joint positions, bend directions (rolls), and per-finger weights by hand every time.** The bundled [lida_hand_rig.py](../../scripts/lida_hand_rig.py) measures the hand mesh, places the joints, bends the hand through grips, and counts crossings between fingers, folds inside a finger, and stretched edges. Before and after are compared by numbers, and images are drawn only when needed. A person looks only at the joints the report marks as estimated and at images of the poses that still have a warning.

The input blend is read only and never saved. `place` and `run` write a new blend.

## When to use it, and when not

| Situation | What to do |
| --- | --- |
| You want to check shape ratios: a large hand, a long palm, a thumb that does not reach | Read `proportions` from `measure`: ratios inside the hand and against the head, forearm, and height |
| The hand shape changed; you want to know whether the current bones still fit | Measure the joints with `measure` and read the offset from the current bones |
| You want the finger bones, rolls, and weights placed to match the shape | Write them into a copy with `place` |
| You want to know whether fingers cross or fold in a grip, a point, or a pinch | Bend and count with `check`; compare the versions before and after |
| You want to know what got better or worse between before and after, or between two versions | Compare the two reports with `compare`; no rendering |
| You want only what got worse than an approved version | Pass the approved version's `check` report to `check --accept` |
| There is no bone map (JSON) | Write one from the rig with `bones` |
| You want to measure, place, check, and compare in one go | `run`; no image by default |
| A shape problem such as a short thumb or thin fingers | Fix the shape in [Building the hand](hand-shape.md) first; joints and weights do not fix it |
| Hard pieces that follow a finger, such as nails | `place --rigid-followers` re-attaches each piece to the one bone under it; `check --followers` measures the slide |
| Soft things or things spanning several bones, such as gloves and rings | This tool does not rebuild their weights. Fit them in [Mesh and weights](mesh-weight.md) |

## How it works

### 1 Split the fingers by surface connectivity

The distance along the surface from the wrist is measured, and the hand is split into five fingers where branches merge from the fingertips toward the palm. Rays or nearest points pick up a neighbouring finger where fingers are close, so only surface connectivity is used. The back of the hand follows from the side, the finger direction, and the thumb, so no bone names or axes are guessed.

### 2 Read the joints where the shape shows them

Each finger is cut into many sections across its axis, and each section measures:

- a palm crease (where the palm-side surface dips)
- a knuckle bump on the back
- a gathering of edge loops (on a quad mesh, loops gather at joints)

Heights are measured from the finger's axis line. Measured from the section centre, a crease also moves the centre, and the crease and the knuckle cancel out.

An expected position for each joint comes from approximate human proportions (proximal : middle : distal phalanx ≈ 1 : 0.6 : 0.45), and the strongest feature near it is chosen. When the feature is weak, the expected position is used and the report says `prior` (estimated). The knuckle joint (MCP) sits inside the palm and rarely shows in the shape, so it is usually estimated. When it is, PIP and DIP are searched as a pair and chosen by whether the distal share looks like a finger (tip-to-DIP is 30–65% of tip-to-PIP).

### 3 Measure the proportions, inside the hand and against the body

Along with the joints, `measure` reports shape ratios.

| Ratio | How it is measured | Human reference |
| --- | --- | --- |
| Palm / hand length `palm_share` | wrist to the middle-finger web / wrist to the middle fingertip | about 0.57 |
| Palm length / width `palm_length_per_width` | width taken just before the finger roots | about 1.25 |
| Thumb reach `thumb_reach` | thumb tip / palm length along the hand; under 1 it ends before the finger webs | about 1.15 |
| Thumb / index `thumb_per_index` | visible lengths | about 0.67 |
| Hand / forearm `hand_per_forearm` | forearm from the elbow bone to the wrist | about 0.73 |
| Hand / head height `hand_per_head` | head from crown to chin of `--head-meshes` (the head without hair or crown) | about 0.78 |
| Heads `heads`, hand / height | height from `--body-meshes` (standing rest pose, Z up) | 7.5 heads, about 0.108 |

Ratios inside the hand depend little on the character's head count, but hand size changes with head count and style. A design with few heads normally has small hands for its head and leaves the human values on purpose. So the human values are only listed for reference, and the warning bands are options. When the design sheet fixes the ratios, set the bands from it.

- The wrist is the wrist point you give (the root of the hand bone when there is a rig). `narrowest_wrist_section_mm` reports how far the mesh's narrowest section is from it, to show a wrist bone placed up the forearm or into the palm.
- Head height and height come from the meshes you name. Without them they are not measured and `notes` says so. You can also pass numbers (`--head-height-mm`, `--height-mm`).
- On a body without legs (a tail, for example) height and heads do not mean what they mean on a human. Rely on the head and forearm ratios.

### The hand-size table by head count

Hand size is compared with a table of hand length / head height by head count. The head count is the measured height / head height, or the design's value passed with `--heads`.

| Heads | Hand / head height | Hand / height (the same value restated) | Basis |
| --- | --- | --- | --- |
| 3 | 0.30 | about 10% | rule of thumb (not measured) |
| 4 | 0.36 | about 9% | rule of thumb (not measured) |
| 5 | 0.42 | about 8.4% | rule of thumb (not measured) |
| 6 | 0.46 | about 7.7% | measured: one stylised design sheet and its model |
| 7 | 0.64 | about 9.1% | measured hand / height on anime-style examples; head count assumed |
| 7.5 | 0.81 | about 10.8% | adult human |
| 8 | 0.86 | about 10.8% | adult human |

**The table is a starting guide, not a rule.** Only the lower four rows rest on measurements, and the stylised rows on one or a few examples. At the same head count, hand size changes with style (the large step between 6 and 7 heads comes from examples in different styles). Values between rows follow straight lines; past the ends the end row is used. The report's `basis` names the rows that were used.

There are four ways to adapt it.

| Goal | How |
| --- | --- |
| Judge by the design's head count (also when a tail or tall shoes change the height) | `--heads 6` |
| Widen or narrow the accepted band (default ±15% of the table value) | `--proportion-tolerance 0.25` |
| Use your own table | `--proportion-table table.json` (form below) |
| Skip the table and set the band directly | `--hand-head-min 0.4 --hand-head-max 0.6` |

```json
[
  {"heads": 5, "hand_per_head": 0.50, "basis": "my design sheet"},
  {"heads": 7, "hand_per_head": 0.60, "basis": "my design sheet"}
]
```

If you have measured the hand and head on the design sheet, a table made from those values is the most reliable. A one-row table works too (it gives that value at every head count). A hand outside the table needs no fix when the size is intended by the design.

### 4 Aim the bend slightly toward the wrist centre

Each bone's roll is set so that bending curls the finger toward the palm and, more toward the fingertip, slightly toward the wrist centre (`--converge`). Too strong pushes the ring finger into the middle finger. The thumb bends across the palm, not into it. Its curl direction sits between "toward the palm" and "toward the little finger" (45°, plus `--thumb-roll` toward the little finger), and the roll is searched so the thumb reaches best in both the fist and the pinch.

### 5 Rebuild the weights as finger chains

Unless `--keep-weights` is given, `place` rebuilds the hand weights as chains along each finger. At each joint the weights change over a band scaled to the finger's thickness (`--joint-band`), and past the wrist they blend back into the old weights (`--fade-mm`).

### 6 Re-attach nails to the fingertip bone

Meshes named in `--rigid-followers`, such as nails, are re-attached piece by piece: each connected piece (one nail) gets weight 1 on the one bone that the skin under it follows most. The skin right under the nail is set to the same bone, so the nail does not slide on the skin when the finger bends. Pieces away from this hand (the other hand's nails) are left alone.

### 7 Bend and count

`check` bends seven poses — relax, grip, fist, point, pinch, spread, and opposition — including in-between steps. The bend is linear blend skinning computed from the rest shape and weights; for the fist pose only, Blender's own deformation is also compared and the difference reported.

The thumb angles are not fixed numbers; they are solved for each hand. In fist, grip, and point the thumb tip aims at the outside of the curled finger; in pinch, at the index fingertip; in opposition, at the little fingertip. Only two numbers are searched: how far the thumb curls (its three joints together, in fixed shares) and how far its base turns toward the palm. Shapes that pass through a finger or the palm are not chosen. The distance left to the goal is reported.

It counts:

- crossing curves between fingers (minus what was already there at rest)
- folds inside a finger (a finger running into itself)
- fingertips entering the palm (for reference; a fist normally does this)
- edges stretched past their rest length
- the distance from the thumb to the index finger (pinch and grip) and how far the thumb stayed from its goal
- how far nails and other meshes named in `--followers` move against the skin under them

### 8 Compare before and after by numbers

`compare` reads two `measure` reports or two `check` reports and compares them value by value. It uses neither Blender nor rendering.

- Two `check` reports: crossing curves, stretched edges, the distance the thumb stayed from its goal, and nail slide are all lower-is-better. Values that rose beyond the tolerance (default 0.5 mm for lengths, 0 for counts) are listed under `worse`, values that fell under `better`.
- Two `measure` reports: lengths and ratios are not judged; values that changed are listed under `changed`. Only warnings that are new count as findings.
- Hands or poses present in only one report appear under `not_compared`.

Even an approved model keeps raw warnings (in a grip the fingertips enter the palm and edges stretch). Pass the `check` report of a version whose look was approved to `check --accept`, and only values worse than that report, and new kinds of warning, remain. All original warnings stay in `accept.warnings_without_accept`. Make the baseline report from a version that was looked at in images and approved.

### 9 Write the bone map from the rig

`bones` writes the map (the JSON passed to `--bones`) from what the rig already carries. Order of reading:

1. The humanoid assignment a VRM add-on stored on the armature. It is read even in a background run that does not load the add-on, as long as it is still in the file.
2. Bone names: thumb, index, middle, ring, little (pinky), plus a left/right mark (Left, L, …). Numbered and worded names both work; three bones are chosen in order of hierarchy depth.
3. The hand bone is the bone the finger chains meet in. Arms are found by name, otherwise by walking up from the hand.
4. When finger names say nothing, the five chains under a named hand bone are ordered from the thumb by position. A note is given then; check the map before using it.

The report's `methods` states how each role was decided. The output has the form `rig-audit` reads.

### 10 Run everything at once

`run` does the map (when `--bones` is omitted) → `measure` → `check` on the current bones → `place` → `check` on the re-placed hand → `compare` in one launch and writes into one new folder.

By default no image is made (`--views none`). If the numbers pass, no rendering is needed.

| `--views` | What is drawn |
| --- | --- |
| `none` (default) | Nothing |
| `findings` | Only the hands and poses that still have a warning after placing, before and after side by side (before on the left, with BEFORE / AFTER written inside the image). With no warning, nothing is drawn |
| `all` | Every pose, before and after side by side |

Rendering is a simple preview (Workbench, 640 px). Images are needed when the user must choose, for the first approval of the look, and when the numbers pass but the shape looks wrong.

## What to prepare

- A saved blend (read only). Do not point at an open production file; use a saved version or a copy.
- The mesh that holds the hand skin (`--mesh`, often the body).
- The rig (`--rig`) and the humanoid bone map (`--bones`): a JSON in the same form as the bundled `rig-audit` in [Bundled tools](model-tools.md), whose `human_bones` maps VRM role names (`leftHand`, `leftIndexProximal`, …) to bone names. If there is no map, write one with `bones` (`run` writes it from the rig when `--bones` is omitted). Without bones, `measure` takes the wrist and finger direction from `--wrist` and `--toward`.
- New paths for the report JSON, for `place` a new blend, and a new folder when images are wanted; `run` takes one new folder. Existing paths stop the tool.
- Blender (background). The numeric core runs with plain Python and numpy.

## Order for the AI

Steps 1–5 can be run at once with `run`. If there is no map, write one with `bones` (`run` does it automatically) and read `methods` in the report.

1. Confirm the hand shape is settled (fix the shape first: [Building the hand](hand-shape.md)).
2. Run `measure`; first read `proportions` and the shape warnings. If a long palm or a short-reaching thumb shows, tell the user before placing joints (fixing the shape means placing them again). Then read each joint's `method` (`mesh` / `prior`) and the offset from the current bones. Look at estimated joints in the images.
3. Run `check` on the current bones to keep the before state.
4. Write a copy with `place`. Leave the thumb roll on `auto`. Name nails in `--rigid-followers`.
5. Run the same `check` on the copy and compare before and after with `compare`. Anything under `worse` is worse after placing.
6. Draw images for poses that still have a warning, when the user must choose, and for the first approval of the look. Look at the drawn images yourself: do they agree with the numbers, and does the grip look natural?
7. Show the results, images, and limits to the user. Fit gloves and other soft meshes separately. If the short-thumb warning appears, report it as a shape problem.

If the root estimates from `place` differ by a few millimetres between the hands and the mesh is mirror-symmetric, you can decide the joints on one hand and mirror them to the other. Then do not assume the mirror plane is x = 0: find it from the left-right centre of the two hands' points. A generated model can sit slightly off centre (about 1 mm in Lida's example), and mirroring at x = 0 doubles that error. Before mirroring, mirror one hand's points and measure the distance to the nearest point of the other hand to confirm the two sides match.

## Examples

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- measure --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report measure.json --render-dir measure_views --head-meshes Head --body-meshes Body Head

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_before.json --render-dir check_before_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- place --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report place.json --output-blend model_hands.blend --rigid-followers Nails

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model_hands.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_after.json --render-dir check_after_views --followers Nails
```

Write the map, run everything at once, compare before and after, and read against an approved version:

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- bones --input model.blend --rig Armature --report bones_report.json --output-map humanoid.json

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- run --input model.blend --mesh Body --rig Armature --side both --out-dir hands_run --rigid-followers Nails --views findings

python lida_hand_rig.py compare --before check_before.json --after check_after.json --report compare.json

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model_next.blend --mesh Body --rig Armature --bones humanoid.json --side both --followers Nails --accept check_approved.json --report check_next.json
```

`compare` does not use Blender, so it runs in plain Python (numpy is required).

## Reading the report

### measure and place

- `hands.<side>.fingers.<finger>.joints`: each joint's position (rig space), `method` (`mesh` from the shape, `prior` estimated, `tip` the fingertip, `estimated` the computed thumb base), `score` and `features` (crease, knuckle, loop strength), `from_web_mm` (distance from the finger web), and `current_bone_offset_mm` (offset from the current bone).
- `back_of_hand`: the measured back-of-hand direction.
- `proportions.hand`: lengths (mm) and ratios inside the hand. `proportions.body`: forearm, upper arm, head height, height, the hand against each, and heads. `human_reference`: human values for reference. `table`: the head count used, the table value and band, the hand length that gives for this head height (mm), and the basis of the rows. `notes`: what was not measured and why the table was not used.
- For `place`, `thumb_roll_deg` (the chosen thumb roll) and `flex_sign` (which rotation curls the finger). `--z-toward` chooses whether bone Z points to the palm or the back. `rigid_followers` lists the re-attached pieces and the count per bone.
- A warning appears when the thumb's visible length is under 55% of the index finger's (roughly two thirds on a human hand). A thumb that cannot reach the fingers is a shape problem; joints and weights do not fix it.

### check

- `poses`: per pose, `crossings` (per pair: curve length, number of spots, the step `at` where it was worst, and `kind`), `stretched_edges_max`, `thumb_to_index_mm` or `thumb_to_index_tip_mm`, and `thumb` (the solved thumb angles, the goal, the distance left `gap_mm`, and crossing `crossing_mm`).
- `kind` is `fingers` (between fingers), `fold` (inside a finger), or `palm` (a fingertip entering the palm; not warned about).
- `blender_vs_numpy_fist_mm`: the difference from Blender's own deformation in the fist pose. Over 0.5 mm it warns; other modifiers, shape keys, or volume preservation change how to read the numbers.
- `weights_in_hand.vertices_without_hand_weights`: vertices in the hand with no bone weight.
- `followers.<name>`: pieces on this hand, pieces spanning more than one bone, and `drift_mm` per pose (movement against the skin underneath). Over 1 mm it warns.

### compare, accept, bones, and run

- `compare`: `worse` and `better` (two `check` reports), `changed` (two `measure` reports), `not_compared`, `new_warnings` and `resolved_warnings`, and the counts in `summary`. A non-zero `summary.findings` gives exit code 2.
- `check --accept`: `warnings` holds only values worse than the baseline and new kinds of warning. `accept` holds the worse values, the better values, items that could not be compared, the original warnings (`warnings_without_accept`), and the tolerance used.
- `bones`: `human_bones` (role → bone name), `methods` (how each role was decided: `declared` = stored assignment, `name`, `where the finger chains meet`, `hierarchy above the hand`, `position under the hand`), and `missing` (hand roles not found). `missing` gives exit code 2.
- `run`: the folder holds `bones.json` (when written), `measure.json`, `check_before.json`, `place.json`, `<input name>_hands.blend`, `check_after.json`, `compare.json`, and `run.json`. In `run.json`, `steps` has the warning count of each step, `files` the hash of each file, `views` the number of images drawn, and `warnings` every step's warnings (prefixed with the step). Images are in `views/before`, `views/after`, and `views/pairs`.

### Exit codes

| Value | Meaning |
| --- | --- |
| 0 | No warnings |
| 2 | Findings or warnings; read the report. A usage error is also 2, and no JSON is written then |
| 1 | Input, output, or execution error; the report JSON holds the reason |

## Main options

| Option | Default | Effect |
| --- | --- | --- |
| `--window` | 0.10 | Search for a joint within this share of the finger length around the expected position |
| `--feature-floor` | 0.12 | Feature strength needed to trust the shape over the estimate |
| `--mcp-prior`, `--pip-prior`, `--dip-prior` | 0.25, 0.49, 0.78 | Expected joint positions (knuckle: share of the visible length before the web; PIP and DIP: shares of knuckle-to-tip) |
| `--thumb-mcp-prior`, `--thumb-ip-prior` | 0.02, 0.55 | Expected thumb joint positions |
| `--palm-share-min`, `--palm-share-max` | 0.48, 0.62 | Palm / hand length outside this band is warned about |
| `--palm-aspect-max` | 1.45 | Palm length / width above this is warned about |
| `--thumb-reach-min` | 1.0 | Thumb reach below this is warned about |
| `--hand-head-min`, `--hand-head-max` | 0.5, 0.95 | Hand / head height outside this band is warned about |
| `--hand-forearm-min`, `--hand-forearm-max` | 0.5, 0.9 | Hand / forearm outside this band is warned about |
| `--head-meshes`, `--body-meshes` (measure) | none | Meshes used for the head height and the height |
| `--head-height-mm`, `--height-mm` (measure) | none | Head height and height as numbers |
| `--heads` (measure) | measured | The design's head count, used to read the table instead |
| `--proportion-table` (measure) | built-in | A table of hand / head height by head count (JSON) |
| `--proportion-tolerance` | 0.15 | Accepted share around the table value |
| `--thumb-metacarpal` | 1.35 | Thumb metacarpal length, as a multiple of the proximal phalanx |
| `--converge` | 0.3 | How strongly bent fingertips aim at the wrist centre (0–1) |
| `--joint-band` | 1.0 | Half-width of the weight change at a joint, times the finger thickness. Narrow bands fold the knuckle |
| `--fade-mm` | 15 | Distance past the wrist over which the new weights blend into the old |
| `--smooth` | 4 | Smoothing passes over the new weights |
| `--steps` | 4 | In-between steps per pose |
| `--stretch`, `--stretch-mm` | 1.5, 3 | An edge longer than this multiple of its rest length and longer by at least this counts as stretched |
| `--cross-tolerance-mm` | 1 | Crossing curves shorter than this are not warned about |
| `--poses` (check) | all 7 | Poses to check |
| `--keep-weights` (place) | off | Fix only bone positions and rolls; leave the weights |
| `--thumb-roll` (place) | auto | The thumb's curl direction; a number is added toward the little finger from the midpoint (45°) between palm and little finger |
| `--rigid-followers` (place) | none | Meshes of hard pieces such as nails; each piece is re-attached to the one bone under it |
| `--followers` (check) | none | Meshes such as nails; drawn in the images, and their slide against the skin is measured |
| `--follower-drift-mm` | 1 | A slide above this is warned about |
| `--accept` (check, run) | none | A `check` report of an approved version; only values worse than it and new kinds of warning remain |
| `--accept-tolerance-mm`, `--accept-tolerance-count` (check, run) | 0.5, 0 | With `--accept`, a rise of a length or a count within this is not counted as worse |
| `--tolerance-mm`, `--tolerance-count`, `--tolerance-ratio` (compare) | 0.5, 0, 0.01 | Only values that changed by more than this are listed |
| `--output-map` (bones) | required | New JSON for the map |
| `--out-dir` (run) | required | New folder for the reports, the candidate, and images |
| `--views` (run) | none | Whether images are drawn: `none`, `findings`, `all` |

The defaults come from examples and are not values that fit every model.

## Example request to the AI

```text
Read the saved <version> without saving it and check the <side> hand with lida_hand_rig.py.
- Mesh <name>, rig <name>, humanoid map <JSON>.
- First run measure, naming the head <name> and the body <names>, and report the hand ratios (palm, thumb, against the head and forearm). The design's ratios are <values>.
- Then run check on the current bones. Then write <new blend> with place and compare with the same check.
- Put the reports and images in <new folder>. Do not save the input.
- Report separately: estimated joints, crossings, folds and stretched edges before and after, places where the images disagree with the numbers, and limits.
- Re-attach <nails> with --rigid-followers and confirm the slide with --followers in check. Do not change the weights of other meshes.
```

Example for running everything at once:

```text
Read the saved <version> without saving it and re-place both hands with `run` of lida_hand_rig.py.
- Mesh <name>, rig <name>. Write the map from the rig, and tell me if `methods` shows anything other than name or declared.
- Name the nails <name> in --rigid-followers. Write the output to <new folder>.
- Use --views findings (only poses that still have a warning).
- Report `worse` from compare.json and the warnings that remain after placing. If anything is worse after placing, tell me before the candidate is used.
```

## Verified scope

- In Blender 5.3.0 background runs, `measure`, `place`, and `check` were run read-only on a copy of a saved file from another production. PIP and DIP agreed with the hand-fitted bones within about 1 mm on most fingers. In the written copy, stretched edges in the fist and point poses fell below the hand-fitted version, and the thumb base no longer collapsed. The nails' slide in the fist went from about 6 mm to 0. A palm too long for the thumb to reach the finger webs was reported as ratio warnings. The input did not change.
- On the same copy, `bones`, `run`, `compare`, and `check --accept` were run. The humanoid assignment stored on the armature was read in a background run that does not load the add-on; names alone gave the same map. `run` (both hands, no images) took about one minute. The `check` after placing inside `run` and a separate `check` of the saved candidate differed in 0 items under `compare`. `--views findings` produced before/after images for only the poses that still had a warning.
- Plain-Python tests on a synthetic hand check the finger split, left/right mirroring, PIP and DIP from creases, bend directions, the weight chains, linear blend skinning, the thumb solve, bone choice and slide of hard pieces, report comparison and reading against an approved version, the bone map from names, hierarchy, and position (five naming styles), the before/after image composition, and protection of existing outputs.

Not verified: on fingers whose joints barely show in the shape, such as the little finger, whether the estimate or the hand fit is right (look at the images); whether grips look natural; grips on a hand with a short thumb; how well the hand-size table holds (low head counts are unmeasured rules of thumb; stylised rows rest on few examples); pieces spanning several bones; the bone map on Japanese bone names or rigs with many control bones; `--accept` in real production use; other Blender versions; volume-preserving skinning; how it looks in the target application. Example numbers are not a quality standard.

## Terms of use

`lida_hand_rig.py` is GPL-3.0-or-later (author: Lida). It is treated like the [bundled tools](model-tools.md#license-and-installation-scope); keep the GPL text and the notice at the top of the file. This document follows [Usage and attribution](usage-and-attribution.md).
