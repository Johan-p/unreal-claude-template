# Game Animation Sample (UE 5.8) — analysis

Static analysis of Epic's **Game Animation Sample** (UE 5.8 build; free on Fab — if installed locally, record its path as the optional `<GameAnimSampleDir>` key in LOCAL.md), performed 2026-08-18 by extracting `.uasset` name tables and Epic's embedded Blueprint comments with a string dumper — the editor was not running. Cross-checked against the official docs (Motion Matching, Pose Warping, Dynamic Asset Selection, the sample's own doc page). This doc is the shared source for the animation skill group (`ue-motion-matching`, `ue-anim-warping-locomotion`, `ue-character-rigging-retargeting`, `ue-animation-system`) — skills point here instead of duplicating the sample map.

**Why this doc exists:** the docs are authoritative but incomplete (Offset Root Bone, Foot Placement, Steering, Blend Stack are load-bearing in the sample yet absent from the Locomotion and node-reference doc pages), and the sample is complete but undocumented (its knowledge lives in embedded Blueprint comments). Neither alone gets you to a working result.

## Doc-vs-disk discrepancies (5.8)

The sample's official doc page describes the 5.4/5.5 build. On the 5.8 disk:

| Docs say | 5.8 disk has |
|---|---|
| `CBP_SandboxCharacter` | `SandboxCharacter_CMC` (+ a parallel `SandboxCharacter_Mover`, `SandboxCharacter_Mover_Ragdoll`) |
| `ABP_SandboxCharacter` | `SandboxCharacter_CMC_ABP` / `SandboxCharacter_Mover_ABP` |
| one character stack | **two full stacks**: classic CMC and the Mover plugin (`Mover`, `ChaosMover`, `NetworkPrediction`, movement modes as Blueprints: `BP_MovementMode_Walking/Falling/Slide/Ragdoll`, `BP_MovementTransition_To/FromSlide`) |
| (not mentioned) | `Locomotor` plugin isolated example, `AnimationLayering`, SmartObjects/StateTree NPC demo, MetaHuman Kellan |

`ABP_GenericRetarget` (at `Content/Blueprints/RetargetedCharacters/`) still exists as documented; the retarget flow (child BP + component tag `RTG_UEFN_to_<asset>`) still applies with the corrected class names.

## The seven layers

The sample's animation system is layered; every layer depends on the one before it.

### 1. Data authoring — Anim Modifiers (the invisible load-bearing layer)
18 Anim Modifier Blueprints (`Content/Blueprints/AnimModifiers/`) bake data *into* the 2,132 animation sequences: `AM_FootSpeed_L/R` (foot speed curves for foot locking), `AM_OrientationWarpingAlpha` / `AM_RateWarpingAlpha` / `AM_WarpingAlpha` (curves that *gate* warping to straight-motion sections), `AM_DistanceFromLedge` (traversal warp distances), `AM_MoveData_Speed` (play-rate scaling), `AM_BakePhaseCurveFromFootstepNotifies`, `AM_FootSteps_*` (foley notifies). Runtime nodes read these curves; nothing downstream works without them.

### 2. Motion-matching data (PoseSearch plugin)
- **33 schemas** (`PSS_*`): feature channel definitions. `PSS_Default` samples Position/Velocity/Heading on `pelvis`, `foot_l`, `foot_r` + a Trajectory channel; `NormalizeWithCommonSchema`, `StripZ` component stripping, HeadingAxis=Y.
- **169 databases** (`PSD_*`): animation pools, one per state/gait/density combination (`PSD_Dense_Stand_Run_Loops`, `PSD_Relaxed_Slide_FeetOut_ExitToSprint`, …).
- **4 normalization sets** (`PSN_*_All`): one per density tier, so databases in a tier score on a comparable scale.
- **3 custom channels** (`PSC_*`): `PSC_DistanceToTraversalObject`, `PSC_Traversal_Pos`, `PSC_Traversal_Head` — gameplay data (ledge transform) injected into the pose query.
- Density tiers: `Dense` / `Sparse` / `ExtremeSparse` / `Relaxed` / `Mover` — same locomotion at different data budgets, switchable live in the demo widget.

### 3. Choosers as the control layer (Chooser plugin)
17 `CHT_*` Chooser Tables decide *which databases are legal to search this frame* from enum'd character state (`E_Gait`, `E_Stance`, `E_MovementState`, …). `CHT_PoseSearchDatabases_*` per density tier; `CHT_TraversalMontages_CMC/_Mover` use a **PoseMatch column** to pick both the montage *and its entry frame*. Gameplay logic lives in data rows, not in AnimGraph transitions — that's what makes it scale.

### 4. AnimGraph node chain
Confirmed node inventory of `SandboxCharacter_CMC_ABP` (4 MB) and `SandboxCharacter_Mover_ABP` (6 MB):

```
PoseSearchHistoryCollector  (trajectory + pose history; GenerateTrajectory feeds it)
  → MotionMatching          (searches the chooser-selected databases; has an
                             INTERNAL per-animation graph — anything done there
                             applies per animation before blending)
  → BlendStack              (Mover ABP; the experimental SM+Chooser+MM hybrid)
  → OffsetRootBone          (root drifts from capsule; experimental)
  → OrientationWarping / StrideWarping (Mover only) / Steering (×2, experimental)
  → FootPlacement (CMC ABP) + LegIK
  → Inertialization / DeadBlending
```
State machines exist only for ragdoll and for the explicitly experimental "State Machine + Choosers + Motion Matching + Blend Stack" hybrid (`ExperimentalStateMachineData/`). Core locomotion pose selection is data-driven, not state-driven.

### 5. Character→ABP contract
Enum state model (`E_Gait`, `E_Stance`, `E_RotationMode`, `E_MovementState`, `E_MovementDirection`, `E_TraversalActionType`) + structs per consumer: `S_CharacterPropertiesForAnimation` / `...ForCamera` / `...ForTraversal` / `...ForRagdoll`, pushed through Blueprint interfaces `BPI_SandboxCharacter_Pawn` / `_ABP`. The ABP never casts to the character class.

### 6. Tick ordering as an explicit mechanism
`AC_PreCMCTick` / `AC_PostABPTick` are components that exist purely to use the tick-prerequisite system — Epic's own comment: *"allows us to execute certain functions on the CBP before the CMC."* Trajectory generation and state capture have hard ordering requirements relative to CMC and ABP ticks.

### 7. Traversal (`AC_TraversalLogic`)
Epic documents it in numbered steps inside the asset:
1. (2.1–2.2) Forward capsule trace → find "Traversable Level Block" → get front/back ledge transforms from the block's own function.
2. (3.2–3.6) Room checks: trace up to front ledge; save obstacle height; trace across the top (no room ⇒ save depth, invalidate back ledge); trace down for back floor.
3. (4.1) Send front-ledge transform to the ABP via interface → used by the custom PoseSearch channel.
4. (4.2) Evaluate `CHT_TraversalAnims*` with a **PoseMatch column** → best montage **and entry frame** given distance-to-ledge and current pose.
5. (5.x) Fire the traversal event → montage into a Slot node → Motion Warping (`AddOrUpdateWarpTargetFromLocationAndRotation`) with warp distances read from the `AM_DistanceFromLedge`-baked curves ("no fixed metrics" — Epic calls fixed metrics "an improvement").

Plus: foley system — 305 audio assets driven by 14 `BP_AnimNotify_FoleyEvent_*` variants; jump/land sounds fired from movement-component events (not anim notifies) because MM picks variable entry frames — with a multi-frame `JustLanded` flag consumed by a chooser to keep landing databases valid if conditions change on impact.

## Epic's own caveats (quoted from inside the assets)

- **Orientation warping breaks on curved motion**: "there is an issue with orientation warping when the animation is not moving in a straight line, which is why we use an anim curve to only enable orientation warping during sections of the animations where the motion is straight."
- **Steering is experimental and needs TWO nodes**: "A second steering node is needed for turn in places, since certain properties on this node are not yet pinnable."
- **Gamepad variable gait hurts MM selection**: "currently, this can cause issues with motion matching selection. For the safest implementation, use the Fixed Speed - Single Gait option for now."
- **Offset Root Bone** (per official doc page): no collision checks (can clip geometry); translation release during montages can pop; interpolation hard-coded.
- **The SM+Chooser+MM+BlendStack hybrid** is "highly experimental… the current workflow is far from ideal" — a tooling preview, not a pattern to copy.
- **Steering target rotation** comes from the *predicted future* facing direction of the trajectory, not current actor rotation ("could cause it to lag too far behind").
- **Play-rate scaling**: blend-stack play rate is scaled from capsule speed vs. speed curves baked into the animations (`AM_MoveData_Speed`).

## Reusing the sample (5.8-corrected)

1. Import your character (FBX), create its IK Rig.
2. Create an IK Retargeter UEFN_Mannequin → your character; add it to `ABP_GenericRetarget`'s `IKRetargeter_Map`.
3. Child BP of `SandboxCharacter_CMC` (docs say `CBP_Sandbox_Character` — wrong on 5.8 disk); hide the original mesh; add your mesh as child; component tag `RTG_UEFN_to_<your asset name>`.
4. Or batch-export: retarget the `Content/Characters/UEFN_Mannequin/Animations` library through the IK Retargeter (`Export Selected Animations`, `_Retargeted` postfix) and migrate.

**Machine note:** the built-in MCP server binds port 8000 per machine — only one running editor can serve it, so close your game project's editor before driving the sample (and vice versa).

## Asset-type prefix map (observed)

| Prefix | Type | Count |
|---|---|---|
| `PSS_` | Pose Search Schema | 33 |
| `PSD_` | Pose Search Database | 169 |
| `PSN_` | Pose Search Normalization Set | 4 |
| `PSC_` | Pose Search custom Feature Channel | 3 |
| `CHT_` | Chooser Table | 17 |
| `AM_` | Anim Modifier | 18 |
| `STT_`/`ST_` | StateTree task / tree | 6/3 |
| `AC_` | Actor Component (Blueprint) | 4 |

(If you author these asset types in your own project, add the prefixes to your `docs/NamingConventions.md` in the same change.)
