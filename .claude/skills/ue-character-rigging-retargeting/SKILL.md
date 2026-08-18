---
name: ue-character-rigging-retargeting
description: "Use this skill whenever a skeletal character needs to be brought into a game or given someone else's animations: IK Rig setup, retarget chains, IK Retargeter, batch-exporting retargeted animation sequences, runtime retargeting (Retarget Pose From Mesh), fixing foot sliding in retargeted animations (Speed Planting), Control Rig consumption in AnimBPs, post-process Animation Blueprints, and modular characters (Leader Pose, Copy Pose From Mesh, Skeletal Mesh Merge). Trigger on: 'put a character on this pawn', 'replace the placeholder/graybox mesh with a character', 'use these marketplace animations on our skeleton', 'retarget', 'IK Rig', 'the feet slide', 'modular character', 'mesh parts', or reusing animations from Epic samples (Game Animation Sample, Lyra, mannequins) — even when no rigging term is used."
metadata:
  version: 1.0.0
---

# UE Character Rigging & Retargeting

You are an expert in getting skeletal characters working in-game: IK Rigs, animation retargeting between skeletons, runtime retargeting, and multi-part modular characters. This is the consumption side of rigging — authoring Control Rigs from scratch is a separate discipline (flagged at the end).

## Context Check

This workspace runs a spec-driven workflow: read the feature's architect spec (`docs/architect/`) and the active slice doc (`docs/slices/`) before starting — they already answer most scoping questions. CLAUDE.md and LOCAL.md are auto-loaded. Skills advise, specs decide: on conflict, the architect spec wins.

**Check what already exists before creating new assets:** marketplace character packs frequently ship their own IK Rigs, IK Retargeters, Control Rigs, and post-process ABPs — search `<UnrealProjectDir>/Content/` for `IK_`, `IKR_`, `CR_`, and `ABP_*PostProcess` assets first; a pack's own retargeter is a worked example for that skeleton. Epic's Game Animation Sample (free on Fab; optional LOCAL.md key `<GameAnimSampleDir>` if installed) has a 2,132-animation library worth retargeting; see `docs/game-animation-sample-analysis.md` for its 5.8 asset names (the online docs use outdated ones).

---

## Decision map

| You want | Use |
|---|---|
| Play skeleton-B animations on skeleton-A character, shipping assets | IK Retargeter → **batch export** (`_Retargeted` sequences) |
| Same, but live/no new assets (mirror another mesh's pose) | **Retarget Pose From Mesh** anim node (runtime retargeting) |
| Nearly identical hierarchy + proportions | **Compatible Skeletons** (cheaper than IK retargeting; Skeleton asset settings) |
| Character built from interchangeable parts | **Modular character** — pick a method from the table below |
| Procedural pose fix-ups at runtime (ground align, contact points) | **Control Rig node** in the AnimGraph |
| Physics/leaf-bone motion baked per-mesh (hair, cloth-ish, springs) | **Post-process ABP** on the Skeletal Mesh asset |

## IK Rig (per skeleton, prerequisite for retargeting)

Create: Content Browser → Animation → IK Rig → pick the Skeletal Mesh.

1. **Retarget Root**: right-click the pelvis/hips bone → `Set Retarget Root`. This carries root motion and proportional height between characters.
2. **Retarget Chains**: select the bones of each limb start→end → `New Retarget Chain from Selected Bones`. Standard set: Spine, Neck, Head, Left/Right Arm, Left/Right Leg. Single-bone chains are valid (shoulders, head) — start and end are the same bone. Chains match **by name** across rigs, so keep Epic's common names where possible.
3. Say `No Goal` in the chain dialog unless you need IK adjustment during retargeting (you will for Speed Planting — goals can be added later).
4. **IK Goals + Solvers** (optional layer): goals are effector points solved by an ordered solver stack — `Full Body IK`, `Limb IK` (3-bone arm/leg), `Set Transform`. Solver order matters; goals expose Position/Rotation Alpha.

The **IK Rig anim node** exposes goal position/rotation as AnimGraph pins — usable directly for simple runtime IK without a Control Rig.

## IK Retargeter (skeleton A → skeleton B)

Create: Content Browser → Animation → IK Retargeter → pick the **source** IK Rig; set `Target IKRig Asset` in the editor.

Pre-flight checklist (where most retargets go wrong):
- **Chain Mapping**: every source chain mapped to the right target chain (auto-maps by name; verify).
- **Retarget poses match**: T-pose against T-pose, A-pose against A-pose. Mismatch ⇒ edit the retarget pose on one side before judging anything else — a wrong base pose masquerades as "bad retargeting" everywhere.
- Preview any animation by double-clicking it in the Asset Browser.

**Batch export**: select animations in the Asset Browser → `Export Selected Animations` → new sequences with the `_Retargeted` postfix, bound to the target skeleton. This is how you mine a sample project's library — retarget once, migrate the results. Follow the project's naming conventions when renaming outputs (`docs/NamingConventions.md`).

**Foot sliding fix (Speed Planting)** and stylization (root Scale Horizontal / Translate Offset Z): see `references/retargeting-workflow.md` — the fix requires speed curves generated by a Motion Extractor anim modifier and per-chain `Speed Curve Name` + `Speed Threshold` settings.

## Runtime retargeting (Retarget Pose From Mesh)

For live mirroring without exported sequences:

1. Target character gets its own ABP whose entire AnimGraph is: `Retarget Pose From Mesh` → Output Pose. Assign the `IKRetargeter Asset`; enable `Use Attached Parent` so the source mesh is found automatically.
2. In the actor: source Skeletal Mesh Component animates normally; target mesh component is **parented to the source** and uses the retarget ABP.
3. If the source mesh is hidden, set its `Visibility Based Anim Tick Option = Always Tick Pose and Refresh Bones`, or the target freezes.

This is also the pattern behind the Game Animation Sample's character swapping: one `ABP_GenericRetarget` with an `IKRetargeter_Map`, child pawn per character, component tag `RTG_UEFN_to_<asset>` selecting the retargeter. Full 5.8-corrected steps: `docs/game-animation-sample-analysis.md` → "Reusing the sample". Cost note: every retargeted mesh evaluates the retarget per frame — fine for a handful of characters, wrong for crowds (bake sequences instead).

## Modular characters (multi-part meshes)

Three engine-supported methods — pick by cost profile, don't mix blindly:

| Method | Setup | Game thread | Render thread | Physics per part | Morphs |
|---|---|---|---|---|---|
| **Leader Pose Component** | minimal | minimal | high (per-part draws) | no | yes |
| **Copy Pose From Mesh** | medium | high (each part evaluates) | high | yes (RigidBody/AnimDynamics) | yes |
| **Skeletal Mesh Merge** | high | medium | **low** (one draw) | yes | **no** |

- **Leader Pose**: children follow the leader's bone buffer — `SetLeaderPoseComponent` in the Construction Script. Parts can't animate or simulate independently, and must share the skeleton hierarchy.
- **Copy Pose From Mesh**: each part has a tiny ABP with a `Copy Pose From Mesh` node. **Parent parts to the source mesh so it ticks first** — otherwise every part copies *last frame's* pose (classic one-frame-lag bug). Marketplace modular packs that ship an `ABP_CopyPose`-style asset plus per-part post-process ABPs are this method.
- **Mesh Merge**: `Skeletal Merging` plugin; merge parts into one mesh at runtime (`Meshes to Merge` params, leader mesh's Skeleton is used and must own all animations). Best for many characters on screen; no morph targets survive the merge; plan a shared material/texture atlas.

## Control Rig at runtime (consumption)

- **Control Rig node** (AnimGraph → Misc → Control Rig): runs a CR asset inline. Expose CR variables/controls as pins via `Use Pin`; floats can be driven by anim curves. Use for ground alignment, contact points, look-ats beyond a simple Look At node.
- Performance: limit `Input Bones to Transfer`; disable `Transfer Pose in Global Space` when hierarchies match.
- **Post-process ABP** (set on the Skeletal Mesh asset, not the actor): runs after the main ABP for that mesh everywhere it's used — the standard home for physics-ish secondary motion (hair/skirt/backpack ABPs in modular character packs do exactly this) and for full-body IK rigs like the sample's `ABP_UEFN_Mannequin_PostProcess` + `CR_UEFN_Mannequin_FullBodyIK`.

## Common mistakes

| Anti-pattern | Fix |
|---|---|
| Judging a retarget with mismatched base poses | Fix the retarget pose first; everything else is noise until then |
| Feet slide on the retargeted character | Speed Planting (per-chain speed curves + threshold) — `references/retargeting-workflow.md` |
| Copy Pose parts lag one frame | Parent parts under the source mesh (tick order), per the tick-dependency rule |
| Hidden source mesh freezes runtime retarget | `Always Tick Pose and Refresh Bones` on the source |
| Chain mapping silently wrong | Chains map by name — verify the Chain Mapping panel, don't trust auto-map |
| Merged modular mesh loses face morphs | Mesh Merge doesn't support morph targets — use Leader Pose/Copy Pose for morph-bearing parts |
| Retargeting to reuse 2 animations | For near-identical skeletons, Compatible Skeletons is cheaper than the whole IK Rig pipeline |

## Related Skills

- `ue-animation-system` — the ABP the retargeted character ultimately runs.
- `ue-anim-warping-locomotion` — Motion Extractor / anim modifiers used to generate the Speed Planting curves.
- `ue-motion-matching` — the sample's animation library you're probably retargeting.

## Reference Files

- `references/retargeting-workflow.md` — full biped retarget walkthrough, Speed Planting, stylization knobs, runtime setup details.
- `../../docs/game-animation-sample-analysis.md` (repo docs) — sample asset names on 5.8 disk, retarget-into-sample steps.
