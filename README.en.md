# 3DCharaMakeSkills-Lida

[日本語](README.md) · English

**Version 1.7.0**, a Japanese/English skill pack for creating 3D characters from reference illustrations. It covers input materials, production planning, mesh and rig corrections, expressions, materials, reusable CLI checks, and instructions for AI agents. It includes 24 diagram pairs and images rendered from Lida's actual model.

## See a production example

These are Blender renders of Lida's 3D model. The generated starting model was refined through modeling, expression, weight, material, hair, clothing, and wing work.

| Full body, clothing, and wings | Face, hair, and accessories |
| --- | --- |
| ![Blender render of Lida's full model, including layered skirt, long hair, wings, and shoes](media/lida-finished-body.png) | ![Blender bust render of Lida's face, hair, crown, collar, and pendant](media/lida-finished-face.png) |

[Watch the 10-second turntable and expression preview](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.2.2/lida-model-turntable-attributed.mp4). The left view rotates the full model; the right shows a smile, surprise, the “aa” mouth shape, and a blink. There is no audio.

The previews use Blender 5.2.1 LTS / EEVEE and the production model's toon materials. They demonstrate a refined production result, not the output of one generation or a guarantee of identical results. See [preview conditions](media/README.en.md).

The original diagrams retain their Japanese labels. English captions, numbered descriptions, and legends accompany them in the English guides. Diagrams and previews retain visible Lida/source attribution in the margins.

## Production assumptions

**The image-to-model workflow assumes a 3D generation service such as Tripo. Commercial use is permitted.** Prepare reference illustrations, generate a base model and any needed part or expression references, then refine them in Blender or another suitable modeling application.

For a new animated humanoid, first check the neutral form and joint topology, then use **an FBX within 150 MB → Tripo auto-rig with the VRM 1.0 skeleton → preservation checks → rig and weight adjustment**. A skeleton convention is one step toward a finished VRM; expressions, materials, look direction, secondary motion, metadata, and target behavior still need their own checks. Reuse a good existing rig where appropriate.

Applications, generation services, API credentials, reference images, and model data are not bundled. Another generation service can be used when its inputs and outputs meet the project requirements. Repairing an existing model does not require regenerating it.

## Install and start

1. Download and extract the repository ZIP or a supplied distribution ZIP.
2. Copy the entire `skills/lida-avatar-workflow` folder to your agent's skill location, including references, assets, scripts, LICENSE, and NOTICE. Do not copy only `SKILL.md`.
3. Ask the agent to load the skill. English requests route to [SKILL.en.md](skills/lida-avatar-workflow/SKILL.en.md) and the [English reference index](skills/lida-avatar-workflow/references/en/README.md). You do not need Python or the shader merely to read the workflow.

> Load lida-avatar-workflow and respond in English. Before operating on the model, propose a short production plan covering materials, recommended quality, dependencies, stage goals, and deliverables. Include diagnostics for mesh repair, penetration, material corrections, hand movement, and eyes. State which material properties may change. This request is an introduction check only; do not run services or process model files yet.

Where supported, invoke `$lida-avatar-workflow`. If loading fails, check the folder location, duplicate skill installations, and missing references or assets. See [updating an installed copy](UPDATING.en.md).

## Choose the guide for the current stage

| Task | Guide |
| --- | --- |
| Plan scope, quality, dependencies, and stage completion | [Production plan](skills/lida-avatar-workflow/references/en/production-plan.md), [quality goals](skills/lida-avatar-workflow/references/en/quality-goals.md), [process index](skills/lida-avatar-workflow/references/en/process-index.md) |
| Prepare consistent images and three-view references | [Input materials](skills/lida-avatar-workflow/references/en/input-materials.md), [multi-angle and paired heads](skills/lida-avatar-workflow/references/en/multiangle-threeview.md) |
| Learn from a separate new-model production | [Generation and repair feedback](skills/lida-avatar-workflow/references/en/generation-feedback.md) |
| Introduce the initial humanoid skeleton | [Tripo auto-rig and FBX preparation](skills/lida-avatar-workflow/references/en/tripo-autorig.md) |
| Diagnose mesh damage, missing parts, and deformation | [Repair and completion](skills/lida-avatar-workflow/references/en/mesh-repair-completion.md), [mesh and weights](skills/lida-avatar-workflow/references/en/mesh-weight.md), [adjustment methods](skills/lida-avatar-workflow/references/en/adjustment-methods.md) |
| Build eyes, mouth shapes, and expressions | [Eyes](skills/lida-avatar-workflow/references/en/eye-modeling.md), [expression sheets](skills/lida-avatar-workflow/references/en/expression-sheets.md), [expression adjustment](skills/lida-avatar-workflow/references/en/expression-adjustment.md), [mouth shapes](skills/lida-avatar-workflow/references/en/mouth-shapes.md), [winks](skills/lida-avatar-workflow/references/en/wink-closure.md) |
| Work on hands, hair, clothing, and wings | [Hands](skills/lida-avatar-workflow/references/en/hand-shape.md), [hair](skills/lida-avatar-workflow/references/en/hair-workflow.md), [hidden clothing/body](skills/lida-avatar-workflow/references/en/skirt-hidden-modeling.md), [wings](skills/lida-avatar-workflow/references/en/wing-workflow.md), [feather terminology](skills/lida-avatar-workflow/references/en/wing-feather-terms.md) |
| Correct accessory materials and cross-engine appearance | [Accessory materials](skills/lida-avatar-workflow/references/en/accessory-materials.md), [cross-engine appearance](skills/lida-avatar-workflow/references/en/cross-engine-look.md) |
| Run repeatable checks and assess the actual result | [CLI tools](skills/lida-avatar-workflow/references/en/model-tools.md), [mechanical versus visual review](skills/lida-avatar-workflow/references/en/mechanical-visual-review.md) |
| Handle secondary motion, evidence, and handoff | [Secondary motion](skills/lida-avatar-workflow/references/en/secondary-motion.md), [visual handoff](skills/lida-avatar-workflow/references/en/visual-handoff.md), [AI instructions](skills/lida-avatar-workflow/references/en/ai-instructions.md), [trial and error](skills/lida-avatar-workflow/references/en/trial-and-error.md) |
| Find diagrams and worked knee examples | [Diagram index](skills/lida-avatar-workflow/references/en/diagram-index.md), [knee edge placement](skills/lida-avatar-workflow/references/en/knee-edge-placement.md) |

Use example dimensions and settings as evidence from a particular production, not universal defaults. Lida's design preferences are separated into a [short design note](skills/lida-avatar-workflow/references/en/lida-design.md).

## Use the CLI and visual review together

The pack contains `audit`, `snapshot`, `compare`, `normalize-copy`, and read-only `rig-audit` helpers. A separate standard-library tool checks an upload FBX's extension, identifying header, actual byte count, and SHA. It does not contact Tripo or validate the complete FBX scene.

CLI success covers only the command's stated scope. **Mechanical results, reference-matched images, intermediate motion, saved-file reproduction, and target-application behavior are assessed separately.** A numerically improved model that looks worse is not adopted. The [tool guide](skills/lida-avatar-workflow/references/en/model-tools.md) lists commands, limits, exit codes, and tested conditions.

These tools do not bundle the complete production add-on, its panels, automatic eye/wing modeling, or every original simulation handler. Processing requires an explicitly authorized model task; reading the skill does not install software or alter a project.

## Usage and attribution

Commercial and noncommercial use are permitted, including commissioned models, model sales, and commercial apps or derivative skills. Requirements from generation services and third-party assets remain separate.

| Use | Attribution |
| --- | --- |
| Read the workflow to create a model, image, or video | No credit is required on that output merely for using this workflow |
| Publish an app or new skill incorporating or adapting the materials | Keep the source name, Lida, original URL, and a description of use/modifications in a readable README, About, or NOTICE |
| Redistribute the materials themselves | Retain the applicable LICENSE and NOTICE |

See the [usage guide](skills/lida-avatar-workflow/references/en/usage-and-attribution.md), [English explanation of distribution scope](LICENSE-POLICY.en.md), and informational translations of [LICENSE](LICENSE.en.md) and [NOTICE](NOTICE.en.md). Original Japanese [LICENSE](LICENSE) and [NOTICE](NOTICE.md) are retained. The Blender helper `lida_model_tools.py` is GPL-3.0-or-later; do not add the documentation license's conditions to that code.

The attribution helper can create new English notice blocks with `--language en`; existing Japanese or English entries are preserved. It is unnecessary when only making a model output. The materials do not grant rights to Lida's character design, avatar data, or third-party works.

## Optional shader

[LidaAngelToon](https://github.com/Lida-V/LidaAngelToon) is distributed separately. Choose Blender, Unity, or Unreal packages from the [published 0.2.1 release](https://github.com/Lida-V/LidaAngelToon/releases/tag/v0.2.1). It is not required to use the workflow.

The documented test environments are Blender 5.2.1 LTS / EEVEE, Unity 6000.6.0f1 / URP 17.6, and UE 5.8 on Windows. Check [setup and limitations](skills/lida-avatar-workflow/references/en/shader-setup.md), including the production Blender material versus the generic add-on, the UE lighting limits, and the absence of automatic VRM conversion. Local or test-only shader features are not represented as published features.

## Distribution and maintenance

The pack contains documentation, original diagrams, preview images, the skill, and helper code. **It does not include models, source assets, credentials, reference dance FBX files, renamed copies, or converted reference motions.** Use motion for which you have the necessary rights.

Reading users need not run the validation tools. Maintainers can follow [updating](UPDATING.en.md), [contributing](CONTRIBUTING.en.md), and the [change history (Japanese)](CHANGELOG.md):

```sh
python scripts/validate.py
python -m unittest discover -s tests
python scripts/build_package.py
```

The package validator checks links, allowed contents, image hashes, language coverage, and the recorded source version for each translation. It cannot prove translation accuracy or visual quality. ZIP building audits the completed archive and does not publish a release or change repository visibility.
