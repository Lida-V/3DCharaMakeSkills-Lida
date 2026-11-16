# Measure the hand and place the finger joints, rolls, and weights from its shape

[日本語](../hand-rig.md) · [English](hand-rig.md)

[Process index](process-index.md) · [Bundled tools](model-tools.md) · [Building the hand](hand-shape.md)

**After you fix or rebuild a hand's shape, this avoids re-fitting the finger joint positions, bend directions (rolls), and per-finger weights by hand every time.** The bundled [lida_hand_rig.py](../../scripts/lida_hand_rig.py) measures the hand mesh, places the joints, bends the hand through grips, and counts crossings between fingers, folds inside a finger, and stretched edges. A person looks only at the joints the report marks as estimated and at the bent images.

The input blend is read only and never saved. `place` writes a new blend.

## When to use it, and when not

| Situation | What to do |
| --- | --- |
| You want to check shape ratios: a large hand, a long palm, a thumb that does not reach | Read `proportions` from `measure`: ratios inside the hand and against the head, forearm, and height |
| The hand shape changed; you want to know whether the current bones still fit | Measure the joints with `measure` and read the offset from the current bones |
| You want the finger bones, rolls, and weights placed to match the shape | Write them into a copy with `place` |
| You want to know whether fingers cross or fold in a grip, a point, or a pinch | Bend and count with `check`; compare the versions before and after |
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

## What to prepare

- A saved blend (read only). Do not point at an open production file; use a saved version or a copy.
- The mesh that holds the hand skin (`--mesh`, often the body).
- The rig (`--rig`) and the humanoid bone map (`--bones`): a JSON in the same form as the bundled `rig-audit` in [Bundled tools](model-tools.md), whose `human_bones` maps VRM role names (`leftHand`, `leftIndexProximal`, …) to bone names. Without bones, `measure` takes the wrist and finger direction from `--wrist` and `--toward`.
- New paths for the report JSON, for `place` a new blend, and a new folder when images are wanted. Existing paths stop the tool.
- Blender (background). The numeric core runs with plain Python and numpy.

## Order for the AI

1. Confirm the hand shape is settled (fix the shape first: [Building the hand](hand-shape.md)).
2. Run `measure`; first read `proportions` and the shape warnings. If a long palm or a short-reaching thumb shows, tell the user before placing joints (fixing the shape means placing them again). Then read each joint's `method` (`mesh` / `prior`) and the offset from the current bones. Look at estimated joints in the images.
3. Run `check` on the current bones to keep the before state.
4. Write a copy with `place`. Leave the thumb roll on `auto`. Name nails in `--rigid-followers`.
5. Run the same `check` on the copy; see whether crossings, folds, and stretched edges dropped and whether anything new appeared.
6. Look at the images yourself: do they agree with the numbers, and does the grip look natural?
7. Show the results, images, and limits to the user. Fit gloves and other soft meshes separately. If the short-thumb warning appears, report it as a shape problem.

## Examples

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- measure --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report measure.json --render-dir measure_views --head-meshes Head --body-meshes Body Head

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_before.json --render-dir check_before_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- place --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report place.json --output-blend model_hands.blend --rigid-followers Nails

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model_hands.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_after.json --render-dir check_after_views --followers Nails
```

## Reading the report

### measure and place

- `hands.<side>.fingers.<finger>.joints`: each joint's position (rig space), `method` (`mesh` from the shape, `prior` estimated, `tip` the fingertip, `estimated` the computed thumb base), `score` and `features` (crease, knuckle, loop strength), `from_web_mm` (distance from the finger web), and `current_bone_offset_mm` (offset from the current bone).
- `back_of_hand`: the measured back-of-hand direction.
- `proportions.hand`: lengths (mm) and ratios inside the hand. `proportions.body`: forearm, upper arm, head height, height, the hand against each, and heads. `human_reference`: human values for reference. `notes`: what was not measured.
- For `place`, `thumb_roll_deg` (the chosen thumb roll) and `flex_sign` (which rotation curls the finger). `--z-toward` chooses whether bone Z points to the palm or the back. `rigid_followers` lists the re-attached pieces and the count per bone.
- A warning appears when the thumb's visible length is under 55% of the index finger's (roughly two thirds on a human hand). A thumb that cannot reach the fingers is a shape problem; joints and weights do not fix it.

### check

- `poses`: per pose, `crossings` (per pair: curve length, number of spots, the step `at` where it was worst, and `kind`), `stretched_edges_max`, `thumb_to_index_mm` or `thumb_to_index_tip_mm`, and `thumb` (the solved thumb angles, the goal, the distance left `gap_mm`, and crossing `crossing_mm`).
- `kind` is `fingers` (between fingers), `fold` (inside a finger), or `palm` (a fingertip entering the palm; not warned about).
- `blender_vs_numpy_fist_mm`: the difference from Blender's own deformation in the fist pose. Over 0.5 mm it warns; other modifiers, shape keys, or volume preservation change how to read the numbers.
- `weights_in_hand.vertices_without_hand_weights`: vertices in the hand with no bone weight.
- `followers.<name>`: pieces on this hand, pieces spanning more than one bone, and `drift_mm` per pose (movement against the skin underneath). Over 1 mm it warns.

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

## Verified scope

- In Blender 5.3.0 background runs, `measure`, `place`, and `check` were run read-only on a copy of a saved file from another production. PIP and DIP agreed with the hand-fitted bones within about 1 mm on most fingers. In the written copy, stretched edges in the fist and point poses fell below the hand-fitted version, and the thumb base no longer collapsed. The nails' slide in the fist went from about 6 mm to 0. A palm too long for the thumb to reach the finger webs was reported as ratio warnings. The input did not change.
- Plain-Python tests on a synthetic hand check the finger split, left/right mirroring, PIP and DIP from creases, bend directions, the weight chains, linear blend skinning, the thumb solve, bone choice and slide of hard pieces, and protection of existing outputs.

Not verified: on fingers whose joints barely show in the shape, such as the little finger, whether the estimate or the hand fit is right (look at the images); whether grips look natural; grips on a hand with a short thumb; a hand-size standard per head count (only human values and the bands you set are compared); pieces spanning several bones; other Blender versions; volume-preserving skinning; how it looks in the target application. Example numbers are not a quality standard.

## Terms of use

`lida_hand_rig.py` is GPL-3.0-or-later (author: Lida). It is treated like the [bundled tools](model-tools.md#license-and-installation-scope); keep the GPL text and the notice at the top of the file. This document follows [Usage and attribution](usage-and-attribution.md).
