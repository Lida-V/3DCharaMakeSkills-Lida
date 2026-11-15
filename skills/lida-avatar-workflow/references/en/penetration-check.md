# Find penetration by numbers and decide the repair

[日本語](../penetration-check.md) · [English](penetration-check.md)

[Process index](process-index.md) · [Bundled tools](model-tools.md) · [Hair workflow](hair-workflow.md)

**This method lists every place where hair, ribbons, or cloth pass through the body or accessories by calculation before anyone looks for them, and names for each place which repair fits: delete, cut, push out, or reroute.** Rotating the view by eye misses the back, the armpits, and the inside of overlapping locks. The bundled [lida_penetration_check.py](../../scripts/lida_penetration_check.py) produces the list and close views, so a person looks only at the marked places.

The tool only measures and suggests. It opens the input blend read-only and never saves it. Repairs are done separately, after a person and the AI decide from the suggestions.

## When to use it, and when not

| Situation | Action |
| --- | --- |
| Generated hair or cloth has just been placed on the body; the crossings are unknown | Make the list with `check` |
| Deciding whether to remove, cut, or move a lock that passes through | Get a suggestion per place with `advise` |
| After a repair: did it shrink, and did another place appear? | Compare `check` reports from before and after with `compare` |
| Penetration and floating of ring- or arc-shaped accessories (crowns, armlets, chokers) | [Fitting accessories](accessory-fit.md), which also brings the band to a target gap |
| Penetration during sway | Check baked frames with `--frame`. Tune colliders in [secondary motion and export](secondary-motion.md) |
| Missing faces, holes, wrong connections | [Mesh repair and completion](mesh-repair-completion.md) |

## Ideas

### 1  Compute the crossing curves

The curves where triangles of the examined part (hair) cross triangles of a partner (body, accessory) are computed directly. Testing only whether vertices are inside misses places where the middle of a face pierces through on a coarse mesh. A crossing curve always appears for those.

### 2  Separate what can be seen from what is hidden

Rays leave each piece of curve in 48 directions. If at least two leave the model without hitting any object, the piece counts as visible from outside. Crossings inside the body or deep between overlapping locks are counted apart as hidden curve and can be left out of the repair. The number of crossing faces does not tell whether something can be seen.

### 3  Group nearby curves into spots

Pieces whose ends are closer than 8 mm form one spot. Spots are numbered by visible length. A close view can be rendered for each spot from the direction that sees it best.

### 4  For closed partners, measure depth too

For closed partners such as body, head, or tail (`--solid`), rays leave each sample point in several directions; a majority vote on odd or even numbers of surface crossings decides inside or outside. For inside points, the distance to the nearest face is the depth. Open partners such as fins, chains, or thin plates (`--thin`) have no inside, so only their crossing curves are examined.

### 5  Keep intended overlaps apart

Hair roots inside the head are not a fault. Partners named in `--allow` stay in the list but leave the counts and warnings. Real faults inside an allowed partner (a scalp line on the crown, for example) are not counted, so check those by eye.

## Repair suggestions (advise)

`advise` splits the part's faces for analysis only (the model is not changed), takes each stretch buried in a closed partner, and measures the following.

| Measure | Meaning |
| --- | --- |
| Depth `depth_mm` | Distance from the partner's surface to the farthest point of the buried stretch |
| Buried extent `buried_extent_mm` | End to end of the buried stretch |
| Entries `entries` | 1: it goes in and stays (a buried tip). 2 or more: it passes through the partner |
| Entry width `entry_width_mm` | A guide to the thickness of the lock |
| Visible entry `visible_entry_percent` | Share of the entry curve that can be seen from outside |
| Island size and inside share | How much of one connected piece of the part is buried |

From these, each stretch gets one suggestion.

| Suggestion | Condition (default thresholds) | Work |
| --- | --- | --- |
| `delete` | The whole island is inside, or more than 60 % of a small island (under 40 cm²) is inside | Remove the island |
| `delete_scrap` | The surroundings are buried and less than 1.5 cm² shows outside | Remove the flake on the skin, or push it in |
| `trim` | One entry, buried longer than 35 mm | Cut at the entry and close the end thinly. The outside shape stays |
| `pull_tip` | One entry, buried extent 35 mm or less | Change the direction of the tip slightly to bring it out |
| `push` | Depth 4 mm or less; or depth at most 0.6 × entry width and at most 15 mm | Move the stretch smoothly outward |
| `reroute_or_cut` | None of the above (deep for the thickness of the lock) | Rebuild the path outside, or cut the buried stretch and close both ends. A person decides by appearance |
| `leave` | Less than 5 % of the entry can be seen | Do nothing |

- All thresholds are options (`--shallow-mm`, `--tip-extent-mm`, `--push-ratio`, `--push-max-mm`, `--hidden-share`, `--small-island-cm2`, `--island-inside-share`, `--scrap-cm2`). They are example values, not values that suit every model.
- A suggestion depends on sizes only. It does not know which lock matters in the original art. For `reroute_or_cut`, and for `trim` or `delete` of a featured lock, a person decides from the images.
- When the part's edges are coarse (median edge over 10 mm), the report's `notes` says so. Subdivide locally before a `push` repair.
- Where contact changes with pose (shoulders, armpits, crotch), do not decide the repair from the reference pose alone; check the poses that will be used.
- Thin partners (fins, chains) are outside `advise`. Decide from the spot sizes and images of `check`.

## What to prepare

- A saved blend (read-only). Do not use an open working file directly; name a saved version or a copy.
- Names of the parts to examine (`--parts`) and of the partners (`--solid`, `--thin`). Name partners explicitly.
- A new path for the JSON report and, for images, a new folder (`--render-dir`). The command stops if either already exists.
- Blender (background). `compare` and the numeric core run in ordinary Python with numpy.

## Order for the AI

1. Decide parts, partners, intended overlaps (`--allow`), and the pose or frame from the user's instructions and production records.
2. Run `check` and read the summary (number of spots, visible curve per partner).
3. Run `advise` and read the counts per suggestion and the note about coarse edges.
4. Look at the close views yourself: do they agree with the numbers, and did an intended overlap slip in?
5. Show the suggestions, images, and limits to the user. Wait for the user's decision on `reroute_or_cut` and on featured locks.
6. Save the repaired version under another name, run the same `check` again, and compare with `compare`. Fix new or grown spots.
7. Finally review the same saved version in renders. Zero findings do not grade the shape ([mechanical checks and visual review](mechanical-visual-review.md)).

## Example commands

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_penetration_check.py -- check --input model.blend --parts Hair --solid Body Head --thin Fin Chain --allow Head --report check.json --render-dir check_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_penetration_check.py -- advise --input model.blend --parts Hair --solid Body --report advise.json --render-dir advise_views

python lida_penetration_check.py compare --before check.json --after check_fixed.json --report compare.json
```

Inside Blender, `check(parts, solid, thin, allow, options)` and `advise(parts, solid, options)` return `(report, marks)` and leave the scene unchanged. `render_marks()` adds a camera and marks to the scene, so use it only in a separate process that will not save.

## Reading the reports

### check

- `summary.visible_spots`, `visible_curve_mm`: number of visible spots and total visible curve; `by_partner` breaks them down.
- `summary.hidden_curve_mm`: total hidden curve. `allowed_spots`: spots kept apart.
- `pairs`: per part and partner, the curve length, share of samples inside, deepest sample, and share of samples with a split vote.
- `spots`: per spot, `center` (scene coordinates), `size_mm`, `visible_curve_mm`, `depth_mm`, `view` (best direction), `image`.
- A warning appears when more than 5 % of the votes are split. It signals open borders or inner shells in the partner; read the depth with doubt (`open_edges` gives the number of open edges).

### advise

- `parts`: per part, the number of islands, median edge, number of check points, and share of area inside.
- `summary`: counts per suggestion. `items`: per stretch, `advice`, `reason`, the measures above, `entry_center`, `view`, `image`.
- Mark colors in images: red = delete, orange = trim, yellow = pull tip, green = push, purple = reroute or cut.

### compare

- `changes`: `new`, `worse` (visible curve grew by more than 5 mm), `same`, `better`, `gone`.
- New visible spots or grown spots give exit code 2.

### Exit codes

| Value | Meaning |
| --- | --- |
| 0 | Nothing found (for compare: nothing got worse) |
| 2 | Findings or warnings. Read the report and decide |
| 1 | Input, output, or execution error. The JSON report holds the reason |

## Main options

| Option | Default | Effect |
| --- | --- | --- |
| `--tolerance-mm` | 0.5 | A sample deeper than this counts as inside |
| `--cluster-mm` | 8 | Curves closer than this form one spot |
| `--view-directions` | 48 | Directions used for visibility |
| `--seen-directions` | 2 | Seen from at least this many directions means visible |
| `--vote-directions` | 11 | Rays used for the inside vote |
| `--levels` | 2 | Face splits in `advise` (each multiplies faces by 4; the model is not changed) |
| `--frame` | saved frame | Frame to evaluate, for baked sway or poses |
| `--top` | 24 | Number of close views |

The evaluated shape is used, with modifiers and pose applied. Objects shown in render count as occluders even when hidden in the viewport.

## Example request to an AI

```text
Open the saved <version> read-only and examine penetration between hair <name> and body <name> / accessories <name> with check and advise of lida_penetration_check.py.
- The head holds the hair roots: pass it as --allow.
- Pose: <reference pose / frame number>.
- Write the reports and close views to <new folder>. Do not save the input.
- Report separately: visible spots per partner, counts per suggestion, places where the images disagreed with the numbers, and limits.
- Ask me before repairing "reroute or cut" items and locks around the face.
- After the repair, run the same check and compare before and after; confirm that nothing new appeared.
```

## Verified scope

- Blender 5.3.0 in background, reading a copy of a saved file from another new character production (T-pose, no armature). `check` on two hair objects (about 9,000 vertices) against 3 closed and 15 thin partners took about 5 seconds, `advise` about 9 seconds. The input SHA256 was the same before and after.
- `check`, with the head allowed, found 46 visible spots and about 2.5 m of visible curve. Close views confirmed that locks vanishing into the body, tips piercing fins, and flakes on the skin match the marks.
- `advise` found 18 stretches in body and tail: reroute or cut 6, trim 6, pull tip 2, push 3, leave 1. Entry positions were confirmed in images.
- Ordinary-Python tests cover crossing length, spot grouping, suggestion conditions, threshold changes, before/after comparison, and protection of existing outputs.

Not verified: results of repairs made from the suggestions, other Blender versions, models with armature and pose, frames in motion, individual depth values, repair decisions for thin partners, and appearance at the destination. Example counts are not quality criteria.

## Terms

`lida_penetration_check.py` is GPL-3.0-or-later (author: Lida). It follows the same [terms as the bundled tools](model-tools.md#license-and-installation-scope); retain the GPL text and file-header notices. This document follows [usage and attribution](usage-and-attribution.md).
