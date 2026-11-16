# Measure the hand and place the finger joints, rolls, and weights from its shape

[日本語](../hand-rig.md) · [English](hand-rig.md)

[Process index](process-index.md) · [Bundled tools](model-tools.md) · [Building the hand](hand-shape.md)

**After you fix or rebuild a hand's shape, this avoids re-fitting the finger joint positions, bend directions (rolls), and per-finger weights by hand every time.** The bundled [lida_hand_rig.py](../../scripts/lida_hand_rig.py) measures the hand mesh, places the joints, bends the hand through grips, and counts crossings between fingers, folds inside a finger, and stretched edges. A person looks only at the joints the report marks as estimated and at the bent images.

The input blend is read only and never saved. `place` writes a new blend.

## When to use it, and when not

| Situation | What to do |
| --- | --- |
| The hand shape changed; you want to know whether the current bones still fit | Measure the joints with `measure` and read the offset from the current bones |
| You want the finger bones, rolls, and weights placed to match the shape | Write them into a copy with `place` |
| You want to know whether fingers cross or fold in a grip, a point, or a pinch | Bend and count with `check`; compare the versions before and after |
| A shape problem such as a short thumb or thin fingers | Fix the shape in [Building the hand](hand-shape.md) first; joints and weights do not fix it |
| Other meshes that follow the finger bones, such as nails, gloves, rings | This tool does not rebuild their weights. Fit them in [Mesh and weights](mesh-weight.md) |

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

### 3 Aim the bend slightly toward the wrist centre

Each bone's roll is set so that bending curls the finger toward the palm and, more toward the fingertip, slightly toward the wrist centre (`--converge`). Too strong pushes the ring finger into the middle finger. The thumb turns toward the palm about the hand's long axis before it bends; its roll is searched so the pinch reaches the index finger and the fist does not pass through the other fingers.

### 4 Rebuild the weights as finger chains

Unless `--keep-weights` is given, `place` rebuilds the hand weights as chains along each finger. At each joint the weights change over a band scaled to the finger's thickness (`--joint-band`), and past the wrist they blend back into the old weights (`--fade-mm`).

### 5 Bend and count

`check` bends seven poses — relax, grip, fist, point, pinch, spread, and opposition — including in-between steps. The bend is linear blend skinning computed from the rest shape and weights; for the fist pose only, Blender's own deformation is also compared and the difference reported. It counts:

- crossing curves between fingers (minus what was already there at rest)
- folds inside a finger (a finger running into itself)
- fingertips entering the palm (for reference; a fist normally does this)
- edges stretched past their rest length
- the distance from the thumb to the index finger (pinch and grip)

## What to prepare

- A saved blend (read only). Do not point at an open production file; use a saved version or a copy.
- The mesh that holds the hand skin (`--mesh`, often the body).
- The rig (`--rig`) and the humanoid bone map (`--bones`): a JSON in the same form as the bundled `rig-audit` in [Bundled tools](model-tools.md), whose `human_bones` maps VRM role names (`leftHand`, `leftIndexProximal`, …) to bone names. Without bones, `measure` takes the wrist and finger direction from `--wrist` and `--toward`.
- New paths for the report JSON, for `place` a new blend, and a new folder when images are wanted. Existing paths stop the tool.
- Blender (background). The numeric core runs with plain Python and numpy.

## Order for the AI

1. Confirm the hand shape is settled (fix the shape first: [Building the hand](hand-shape.md)).
2. Run `measure`; read each joint's `method` (`mesh` / `prior`) and the offset from the current bones. Look at estimated joints in the images.
3. Run `check` on the current bones to keep the before state.
4. Write a copy with `place`. Leave the thumb roll on `auto`.
5. Run the same `check` on the copy; see whether crossings, folds, and stretched edges dropped and whether anything new appeared.
6. Look at the images yourself: do they agree with the numbers, and does the grip look natural?
7. Show the results, images, and limits to the user. Fit nails, gloves, and other meshes that follow the fingers separately.

## Examples

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- measure --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report measure.json --render-dir measure_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_before.json --render-dir check_before_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- place --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report place.json --output-blend model_hands.blend

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model_hands.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_after.json --render-dir check_after_views
```

## Reading the report

### measure and place

- `hands.<side>.fingers.<finger>.joints`: each joint's position (rig space), `method` (`mesh` from the shape, `prior` estimated, `tip` the fingertip, `estimated` the computed thumb base), `score` and `features` (crease, knuckle, loop strength), `from_web_mm` (distance from the finger web), and `current_bone_offset_mm` (offset from the current bone).
- `back_of_hand`: the measured back-of-hand direction.
- For `place`, `thumb_roll_deg` (the chosen thumb roll) and `flex_sign` (which rotation curls the finger). `--z-toward` chooses whether bone Z points to the palm or the back.

### check

- `poses`: per pose, `crossings` (per pair: curve length, number of spots, the step `at` where it was worst, and `kind`), `stretched_edges_max`, and `thumb_to_index_mm` or `thumb_to_index_tip_mm`.
- `kind` is `fingers` (between fingers), `fold` (inside a finger), or `palm` (a fingertip entering the palm; not warned about).
- `blender_vs_numpy_fist_mm`: the difference from Blender's own deformation in the fist pose. Over 0.5 mm it warns; other modifiers, shape keys, or volume preservation change how to read the numbers.
- `weights_in_hand.vertices_without_hand_weights`: vertices in the hand with no bone weight.

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
| `--thumb-roll` (place) | auto | The thumb roll; a number gives the angle |

The defaults come from examples and are not values that fit every model.

## Example request to the AI

```text
Read the saved <version> without saving it and check the <side> hand with lida_hand_rig.py.
- Mesh <name>, rig <name>, humanoid map <JSON>.
- First run measure and check on the current bones. Then write <new blend> with place and compare with the same check.
- Put the reports and images in <new folder>. Do not save the input.
- Report separately: estimated joints, crossings, folds and stretched edges before and after, places where the images disagree with the numbers, and limits.
- I fit the weights of <nails> and other meshes separately. Do not change them.
```

## Verified scope

- In Blender 5.3.0 background runs, `measure`, `place`, and `check` were run read-only on a copy of a saved file from another production. PIP and DIP agreed with the hand-fitted bones within about 1 mm on most fingers. In the written copy, stretched edges in the fist and point poses fell below the hand-fitted version, and the thumb base no longer collapsed. The input did not change.
- Plain-Python tests on a synthetic hand check the finger split, left/right mirroring, PIP and DIP from creases, bend directions, the weight chains, linear blend skinning, and protection of existing outputs.

Not verified: on fingers whose joints barely show in the shape, such as the little finger, whether the estimate or the hand fit is right (look at the images); whether grips look natural; other Blender versions; volume-preserving skinning; how it looks in the target application. Example numbers are not a quality standard.

## Terms of use

`lida_hand_rig.py` is GPL-3.0-or-later (author: Lida). It is treated like the [bundled tools](model-tools.md#license-and-installation-scope); keep the GPL text and the notice at the top of the file. This document follows [Usage and attribution](usage-and-attribution.md).
