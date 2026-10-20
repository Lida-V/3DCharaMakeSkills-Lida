# Creating and exporting secondary motion for hair and feathers

[Japanese original](../secondary-motion.md)

Secondary motion is the delayed movement of hair or feather tips after the body moves. Establish shape and basic following first. Before starting, briefly record required movements, fixed regions, moving regions, and acceptance criteria for settling.

If hair shape, roots, topology, or basic following are unresolved, start with [the hair workflow](hair-workflow.md). Identify the affected strand or chain and its collision partner when checking interference during movement.

If wing shape, feather rows, attachment, or basic movement are unresolved, use [the wing workflow](wing-workflow.md) first. Review opening/closing and flapping controls separately from delayed secondary motion.

For sleeve folding or inversion, see [pivot and current-parent-frame diagnostics](generation-feedback.md). Distinguish rest coordinates from the parent frame during motion.

## What to prepare

- Adopted meshes and rig, with images of the neutral shape, connections, and problem movements.
- A list of fixed roots, knots, and boundaries, and the tips that should move.
- Bone correspondence between working and export rigs, destination, required movements, and unacceptable failures.

## Work order

1. Make roots follow the body. With secondary motion disabled, inspect shape, connections, and weights.
2. Test tip-side bones and motion on a few strands or neighboring feathers.
3. Check root detachment, boundary splits, stretching, and contact at rest, intermediate positions, holds, and returns before expanding the scope.
4. If the output format requires rig integration, merge on a duplicate or in-memory export data. Compare shape, weights, parenting, and bone assignments. Do not overwrite the original.
5. Check save/reopen, exported contents, and destination playback separately.

## How to adjust it

Give fixed regions zero influence from secondary-motion bones and make them follow body-side parent bones. Blend only the moving regions toward tip-side bones while preserving total weights. Corresponding vertices at connection boundaries should follow together. Merely weakening the roots does not separate secondary motion into the free ends.

Hair and wings have different roles, as do long flight feathers and the smaller feathers covering them. Separate the moving extent, return strength, and damping; change one at a time and compare. Bone counts, angles, gravity, and radii have no universal correct values. Derive them from shape and movement.

## Difficulties and verification scope

“Bones exist,” “settings persist in the saved file,” “a script can rebuild the setup,” “a baked Action contains keyed motion,” and “it actually moves in the destination” are separate checks. Do not describe a temporary scripted setup as present in the saved original.

Custom angle limits, inertia, and one-sided restrictions preventing inward motion are not equivalent to standard spring settings. Exporting settings to VRM does not automatically transfer custom controls. Verify the corresponding implementation and actual movement.

Distinguish natural settling from forcibly reducing or zeroing motion at the video's end. Record collision-test targets, sampled times, actual video duration, and motion range. Passing representative poses does not establish all-time safety.

Use [visual handoff and saved-version checks](visual-handoff.md) to match review materials to saved versions, and [goal setting](quality-goals.md) for start and exit conditions.

## Separate a layered-cloth proxy from rendering issues

For heavy layered clothing, consider simulating a shared proxy mesh with fewer points and binding each visible layer to it. In Lida's example, skirt layers followed a common proxy, while preserved regions at the waist and front opening retained skinning and corrective deformation. Neither its proxy point count nor the paid asset used is mandatory for every production.

Review proxy-to-display correspondence, layer spacing and order, doubled deformation with correctives, normals/tangents, outlines, and routes for legs, shoes, and ornaments together. A common proxy alone does not resolve all self-intersections or inter-layer contact in every movement.

Alongside normal movement, compare required turns, crouches, leg raises, and settling after stopping. Measure load under the same runtime conditions. For gray stains or missing-looking areas, isolate [outline shells and corrective rendering](cross-engine-look.md) as well as physics. Do not include paid cloth assets or reference motions in this documentation's distribution.

## A short AI request

> Use [adopted shape], keep [roots, knots, boundaries] fixed, and distribute secondary motion only to [tips].
> Compare intermediate motion, holds, and returns for [required movements]. Record adjusted regions and values.
> Separate working/export correspondence, saved settings, custom controls, baking, and actual destination behavior. Report tested objects, times, and remaining work.
