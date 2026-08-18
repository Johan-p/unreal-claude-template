# Retargeting Workflow Reference

Verified against the UE 5.8 docs (Retargeting Bipeds with IK Rig, Fix Foot Sliding with IK Retargeter, Runtime IK Retargeting) and Epic's Game Animation Sample assets on disk. Sections in order of the actual workflow.

## Contents
1. [Full biped retarget, step by step](#1-full-biped-retarget-step-by-step)
2. [Speed Planting — the foot-sliding fix](#2-speed-planting--the-foot-sliding-fix)
3. [Stylization knobs](#3-stylization-knobs)
4. [Runtime retargeting details](#4-runtime-retargeting-details)
5. [Retarget profiles](#5-retarget-profiles)

---

## 1. Full biped retarget, step by step

### Per skeleton (source AND target): IK Rig

1. `Add (+) → Animation → IK Rig → IK Rig`, pick the Skeletal Mesh.
2. Hierarchy panel → right-click pelvis/hips → **Set Retarget Root**. Root motion and proportional scaling flow through this bone.
3. For each limb: select bones start→end → right-click → **New Retarget Chain from Selected Bones**. Recommended chain set: `Spine`, `Neck`, `Head`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg` (+ optional `LeftClavicle`/`RightClavicle` as single-bone chains). Accept the auto-suggested common names — cross-rig mapping is by chain name.
4. Choose **No Goal** in the dialog for a plain retarget. Goals are only needed for IK-corrected retargeting (Speed Planting, stylization) and can be added later.

### The IK Retargeter

1. `Add (+) → Animation → IK Retargeter`, pick the **source** IK Rig; open it; set **Target IKRig Asset**.
2. **Chain Mapping panel**: verify every source chain maps to the intended target chain. Auto-mapping matches names; anything unmapped simply doesn't retarget (a commonly-missed clavicle chain reads as "shoulders look dead").
3. **Retarget poses**: both characters must be in equivalent reference poses. If one is A-posed and the other T-posed, edit a retarget pose (pose editing mode in the retargeter) until limb directions match. Do this BEFORE evaluating quality — a base-pose mismatch contaminates every animation identically.
4. Preview: double-click any source-skeleton animation in the Asset Browser.
5. **Export**: select animations → `Export Selected Animations` → target-skeleton sequences with `_Retargeted` postfix. Rename per project naming conventions.

### Retarget phases (what the retargeter actually computes)

Root motion scales through the Retarget Root; FK copies chain rotations; IK (goals, if present) corrects end-effector positions afterwards. That's why chains-only retargets can slide feet — FK rotation copy on different leg proportions puts the feet in different places.

---

## 2. Speed Planting — the foot-sliding fix

Foot sliding on a retargeted character = leg-proportion mismatch making FK-retargeted feet drift while the source's were planted. Speed Planting pins the target's IK foot goals whenever the *source animation* says the foot is stationary.

### Prerequisites
- Target IK Rig has leg chains **with IK goals** solved by Full Body IK (or Limb IK).

### Step 1 — bake speed curves into the SOURCE animations

Per animation (batch via the Skeleton to hit all sequences):
1. Animation Sequence Editor → `Window → Animation Data Modifiers`.
2. `Add Modifier → Motion Extractor Modifier`, one per foot:
   - **Bone Name**: the foot/ball bone (`ball_l`, `ball_r`)
   - **Motion Type**: `Translation Speed`
   - **Axis**: `XYZ`
3. `Apply All Modifiers` → curves like `ball_l_translation_speed_XYZ` appear.
4. Check the curve in the Curve Editor: flat near-zero regions = planted phases.

### Step 2 — enable per leg chain in the IK Retargeter
On each leg chain's settings:
- **Speed Planting: enabled**
- **Speed Curve Name**: the generated curve name (exact match)
- **Speed Threshold**: just above the flat regions' value; raise it if feet unplant too early (Epic's example uses 30)

### Tuning
If planted legs look rotationally stiff, adjust the FBIK per-bone settings on the target rig (preferred angles, stiffness, limits, mass multiplier). Thresholds are character-specific — expect iteration.

---

## 3. Stylization knobs

For mocap-realistic source → stylized target (the usual marketplace-character case):

- **Root Scale Horizontal** (root settings): amplifies vertical bounce, but lifts the character off the floor…
- **Root Translate Offset Z**: …so pair it with a negative Z offset to plant them again. The two together = more cartoon bounce without floating.
- Foot IK goals (Limb IK per leg, `Set Root Bone on Selected Solver` = thigh) give the retargeter something to correct against when proportions are extreme.

---

## 4. Runtime retargeting details

ABP for the target mesh — entire AnimGraph:

```
Retarget Pose From Mesh ──▶ Output Pose
  IKRetargeter Asset = IKR_...
  Use Attached Parent = true
```

Actor setup:
- Source Skeletal Mesh Component runs the real animation (ABP or `Use Animation Asset`).
- Target mesh component **is a child of the source component** (required by `Use Attached Parent`; otherwise assign `Source Mesh Component` manually).
- Hidden source mesh: set its `Visibility Based Anim Tick Option = Always Tick Pose and Refresh Bones` (Optimizations category) or the pose stops updating.

Costs: the retarget runs every frame per target mesh. A couple of swappable player skins — fine. Crowds or shipping the same 20 animations forever — export sequences instead and delete the runtime path.

Game Animation Sample's implementation (worked example): `ABP_GenericRetarget` holds an `IKRetargeter_Map`; each character is a child pawn of `SandboxCharacter_CMC` (5.8 name) with the original mesh hidden, the new mesh added as a child component, and a component tag `RTG_UEFN_to_<asset>` that selects the map entry. See `docs/game-animation-sample-analysis.md`.

---

## 5. Retarget profiles

Retarget profiles store per-chain/per-root settings overrides so one Retargeter asset can serve multiple animation families (e.g. relaxed idles need different root offsets than sprints). The 5.8 doc page for profiles was not retrievable when this reference was written — verify specifics against the editor UI (IK Retargeter → profiles section) before relying on details beyond: profiles exist, they override chain settings, and they can be swapped per export batch. Flag uncertainty in any spec that depends on them.
