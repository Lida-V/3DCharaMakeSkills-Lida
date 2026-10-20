# Build a wink closure

[日本語 / Japanese](../wink-closure.md)

**For beginners: separate ordinary blink from expressive one-eye closure.** A good existing smiling-eye motion can be split into left/right keys. Do not make the mouth smile or move the opposite eye. Inspect closing motion and the actual app as well as the fully closed shape.

Choose a smiling arc, flat line, or another accepted shape from the reference/use case; smiling closure is not correct for every character. See [Lida-specific choices](lida-design.md), [eyelid bands and adjacent rows](expression-adjustment.md), and [eyeballs/gaze](eye-modeling.md).

## Inputs and starting goal

If target references are missing, use [expression-sheet generation](expression-sheets.md) to distinguish normal blink and left/right winks. Start by reusing good smiling-eye references or keys where available.

- Accepted neutral face, ordinary-blink and target-wink references; front and both oblique views showing inner/center/outer heights, brows, and mouth.
- Baseline and existing keys from the same face; reference keys such as joy, lash/line/shadow layers, drivers, and export bindings.
- Destination, face distance, method of receiving left/right closure amounts, and actual expression/gaze combinations.

Briefly state target shape, affected region, and completion checks. Example: **Preserve ordinary blink; close one eye along the reference arc while preserving the opposite eye, brows, and mouth. Compare both sides through intermediate values, return, and practical combinations; verify save/reload and the specified destination.**

Inspect key roles first. A name such as `blinkLeft` does not prove it is wink-only. Map which inputs drive which face/part/VRM-expression keys and at what weights. If an app also uses left/right keys for ordinary blinking, changing their shapes changes both-eye blink too.

![W1 isolates eye-only delta from baseline; W2 smoothly splits it by side; W3 checks intermediates, dependent parts, and destination](../../assets/wink-eye-isolation.png)

The shared Japanese diagram is a schematic, not an actual mesh, required row count, or guarantee for every combination. **W1** selects eye motion, **W2** separates model-left/model-right, and **W3** verifies motion/dependencies/output. Sides refer to the character; in a front image they appear opposite screen-left/right.

## W1: select only the required eye motion

1. Set all keys to 0, save the neutral face, and identify the left/right keys to modify and ordinary blink to preserve. Diagnose incorrect neutral roundness, eyeballs, or openings first.
2. Match **inner corner, center, and outer corner** of the target closure line. For smiling eyes, choose central rise and endpoint positions separately from closure percentage.
3. Move upper/lower lids toward the same curve, including lashes and neighboring face bands. Do not raise only the lower lid into a straight line across the iris or move only the rim and create holes. Establish eye-local up and depth directions.
4. When reusing smiling eyes, **extract only eye-region deltas from the same face, vertex correspondence, and baseline**. Color-code and exclude mouth corners, mouth, brows, etc. Never reuse unrelated generated-face indices or whole-face deltas.

In production, connected groups of joy-moving vertices were examined, and groups containing ordinary-blink vertices could be selected as eyes. This worked because eye/mouth motion regions were separate. It may not work when cheeks connect them. If automatic identification is unclear, visualize and define an eye-region mask.

## W2: split sides and prevent double deformation at the center

Example delta notation for the AI:

```text
dHappy = happy - Basis
dL = E * WL * dHappy
dR = E * WR * dHappy
leftKey  = Basis + dL
rightKey = Basis + dR
```

- `Basis` is the shared neutral face and `happy` the accepted reference key. Names are examples. Confirm existing keys' `relative_key` uses the same baseline; do not directly add deltas with different bases.
- `E` is an eye-only influence mask: 0 elsewhere, smoothly returning to 0 in the required surrounding band. Inspect it alone to ensure fixed mouth, brows, nose tip, etc. are excluded.
- `WL`/`WR` are character-side masks. Smoothly join their nose-bridge transition so `WL + WR = 1`. Setting both to 1 centrally double-deforms the center when both keys activate.
- Evaluate side position in the same baseline coordinates. Choose transition width from face size and motion range; do not copy a fixed production millimeter value to another face.

Because `dL + dR = E * dHappy`, both keys at 1 reconstruct the original eye-only delta. Separately measure whether one key at 1 preserves opposite-eye opening, mouth, and brows. The central transition can move slightly; do not describe half the face as completely fixed.

**A sum of 1 proves neither closure in blends nor safe contact with the eyeball.** Source smiling-eye gaps and intermediate folds are inherited; inspect them in W3.

## W3: check intermediates, dependent parts, save, and destination

Include lashes, painted lines, and shadow layers whenever skin moves. Do not copy face vertex deltas to another mesh by index alone. Use each layer's own baseline and corresponding expression delta or skin correspondence; evaluate side masks in common coordinates. Preserve drivers/expression bindings and verify matching values at 0, intermediate, and 1.

| Check | Inspect |
| --- | --- |
| Each side at 0, 25, 50, 75, 100% and return | Closure line, corner holes, straight-cut sclera, folded lashes, neutral at key 0 |
| Practical combinations with normal blink, smile, vowels, gaze | Double-added closure, unwanted mouth/brow/opposite-eye motion, exposed eyeball |
| Front, both oblique, side; actual materials and plain display | Visible inner walls/backfaces, sinking into eyeball, line/shadow floating or sinking under skin |
| Save under a new name and reopen | Deltas only in intended keys; preservation of other keys, neutral face, UVs, materials, bones, image references, drivers |
| Reimport output and apply inputs in the specified app | Key/expression binding, distinction from ordinary blink, swapped sides, intermediate values and return |

Refine sampling in suspicious intervals and inspect normal distance as well as close-ups. Distinguish combinations suppressed by real inputs from unrestricted additive tests. Record visible leakage, hidden intersections, and everyday appearance separately.

## Possible face-tracking routing

If receiving left/right closure amounts `L`/`R` (0=open, 1=closed) with a setup that can separate an ordinary both-eye blink and expressive side closures, this can be an **operating proposal**:

```text
m = min(L, R)
ordinaryBlink = m
leftWink  = L - m
rightWink = R - m
```

| Input | Ordinary both-eye blink | Left wink | Right wink |
| --- | --- | --- | --- |
| L=1, R=1 | 1 | 0 | 0 |
| L=1, R=0 | 0 | 1 | 0 |
| L=0.8, R=0.3 | 0.3 | 0.5 | 0 |

This **replaces** original side inputs with residuals. Retaining those inputs and adding the both-eye blink doubles motion. It does not apply directly without a both-eye key, with binary expressions, or with custom override rules. First inspect input range, relative deltas, VRM override/addition, and app bindings.

Another option is a custom wink expression, but the app's ordinary wink action may not call it. App implementation changes are a separate scope. Updating this document does not instruct changes to external apps.

## Verified results and remaining issues

Production split existing joy-eye deltas into sides and changed only four left/right keys across face and shadow layers. Ordinary blink, neutral, other expressions, mouth, and brows were preserved. Matched one-eye closure and short motion were checked in Blender, VRM/FBX reimports, and Unity/UE test projects. Distinguish a production candidate from the accepted original.

The specified fine gaze samples showed no visible eyeball leakage on the closing side at either side's 100% value. However, straight-looking intermediate sclera edges, a tiny inner-corner gap in a particular blink/left-wink mixture, and floating or sinking shadow layers in some mixtures were inherited from joy. Fine inspection sometimes detected issues missed by coarse zero findings. If a summary conflicts with detailed results, prioritize the detailed result with its conditions.

Do not extend these findings to every combination/view or completion in the production app. Recheck extraction and contact for a new face or different eye structure. The [bundled helper](model-tools.md) supports preservation/key comparisons; it does not automatically generate or approve this wink.

## First request

> Build ordinary blink and the reference one-eye closure separately. Start by planning the closure line, eye region to move, opposite eye/brows/mouth to fix, destination input binding, and completion criteria. If a good smiling-eye key is reusable, select only eye deltas relative to the same face/baseline and smoothly join side masks centrally with sum 1. Preserve ordinary blink and excluded keys; make lines, lashes, and shadows follow through their own correspondence. Compare each side at 0, 25, 50, 75, 100% and return, plus practical blink/smile/gaze combinations, in plain and actual materials from front, oblique, and side views. Preserve the original, verify save/reload and output/destination input assignments, and report changed keys, preservation, accepted samples, and open issues separately.

© 2026 Lida · Source: [3DCharaMakeSkills-Lida](https://github.com/Lida-V/3DCharaMakeSkills-Lida)
