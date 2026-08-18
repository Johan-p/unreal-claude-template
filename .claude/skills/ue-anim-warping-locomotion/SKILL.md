---
name: ue-anim-warping-locomotion
description: "Use this skill when animation playback must be bent to match actual character movement: Orientation Warping, Stride Warping, Slope Warping, Motion Warping (warp targets, montage alignment to ledges/objects), Distance Matching, Offset Root Bone, Foot Placement, Leg IK, Steering, root-motion-driven locomotion, and Animation Modifiers (baking distance/speed/alpha curves, auto foot-plant sync markers). Trigger on complaints and goals, not just node names: 'the feet slide', 'the stop/start looks floaty', 'the character clips into the wall on the vault', 'align the montage to the ledge/target', 'strafe animations look wrong at angles', 'the walk doesn't match the speed', or any jump/land/vault/mantle alignment work. Works on classic state-machine locomotion AND under motion matching (see ue-motion-matching for pose selection itself)."
metadata:
  version: 1.0.0
---

# UE Anim Warping & Locomotion

You are an expert in the runtime warping layer of UE 5.x animation — the nodes and data that make finite animation data track *actual* capsule movement: pose warping, motion warping, distance matching, foot placement, and the anim-modifier data prep they depend on.

## Context Check

This workspace runs a spec-driven workflow: read the feature's architect spec (`docs/architect/`) and the active slice doc (`docs/slices/`) before starting. CLAUDE.md and LOCAL.md are auto-loaded. Skills advise, specs decide: on conflict, the architect spec wins.

**Worked example:** Epic's Game Animation Sample (free on Fab; optional LOCAL.md key `<GameAnimSampleDir>` if installed) uses every node in this skill in a shipping-quality graph; `docs/game-animation-sample-analysis.md` maps it (node order, curve gating, traversal warp recipe). Read that before copying sample patterns.

---

## Which tool for which symptom

| Symptom / goal | Tool |
|---|---|
| Feet slide because capsule speed ≠ animation speed | **Stride Warping** (continuous) or **Distance Matching** (starts/stops/lands) |
| Strafe/diagonal movement looks wrong with only 4–8 directional anims | **Orientation Warping** |
| Feet float/clip on slopes and stairs | **Foot Placement** + **Leg IK** (Slope Warping is still in development — test-only) |
| Montage must land exactly on a ledge/target (vault, takedown, door) | **Motion Warping** (warp targets) |
| Character turns too slowly/robotically toward movement direction | **Steering** (experimental) |
| Mesh must drift from the capsule (turn-in-place, distance-matched stops) | **Offset Root Bone** (experimental) |
| Animations lack the curves these nodes read | **Animation Modifiers** (bake once, per skeleton) |

All pose-warping nodes need the **Animation Warping** plugin; Motion Warping needs **Motion Warping**; distance matching needs **Animation Locomotion Library**. Root motion enabled on the animations is a prerequisite for the whole layer.

## Graph placement (order matters)

Warping nodes are component-space; the canonical chain:

```
pose source (state machine or Motion Matching)
  → Local To Component
  → [Offset Root Bone]
  → Orientation Warping → [Stride Warping] → [Steering]
  → Foot Placement → Leg IK
  → Component To Local  →  (Inertialization)  →  Output Pose
```

`Leg IK` goes AFTER warping — warp nodes move IK foot bones; Leg IK then pins the FK legs to those IK bone positions. Foot Placement before Leg IK: it locks slow feet and ground-aligns them (per-foot trace, pelvis drops so feet reach).

## Node cheat sheet (details in `references/warping-node-reference.md`)

- **Orientation Warping** — rotates lower body to the locomotion direction, counter-rotates spine bones (tapered list, index 0 least rotated) to keep facing. Inputs: Locomotion Angle (Graph mode) or Orientation Angle (Manual). `Orientation = RotationBetween(RootMotionDirection, LocomotionDirection)`. **Caveat (Epic, in-asset):** breaks when the source animation's motion isn't straight — the sample gates its alpha with a baked `AM_OrientationWarpingAlpha` curve so it only engages on straight segments. Do the same.
- **Stride Warping** — scales foot spacing: `StrideScale = LocomotionSpeed / RootMotionSpeed`. Needs pelvis + per-leg IK/FK foot and thigh definitions. Has debug draw for every adjustment stage.
- **Slope Warping** — feet-to-floor-normal on inclines. Epic: "still in development, don't trust a project to its functionality." Prefer Foot Placement.
- **Foot Placement** — locks feet when source-animation foot speed is low (Graph mode reads per-foot speed *curves* — bake them with `AM_FootSpeed_*`-style modifiers), traces each foot to ground, shifts pelvis.
- **Offset Root Bone** — lets the root drift from the capsule then interpolates back; the enabler for MM-style turn-in-place. Experimental: no collision checks (can clip walls), montage release can pop, interpolation hard-coded.
- **Steering** — adds rotation to root motion toward a target rotation; feed it the *predicted future* facing from a trajectory, not current actor rotation (lags otherwise). Experimental; the sample needs **two** Steering nodes because some properties aren't pinnable yet. Below configured speed thresholds it disables itself.

## Motion Warping (montage alignment)

Aligns a montage's root motion window to a gameplay-supplied transform:

1. Plugin on; animation has `EnableRootMotion`.
2. `UMotionWarpingComponent` on the character.
3. In the montage: `Add Notify State → Motion Warping` spanning the movement section. Set **Warp Target Name**, Root Motion Modifier = `Skew Warp` (or `Scale`), toggles for translation/rotation/`Ignore Z`, Rotation Type `Default|Facing`.
4. Before playing: `MotionWarpingComp->AddOrUpdateWarpTargetFromLocationAndRotation(FName("Target"), Loc, Rot);` — the name must match the notify's exactly (silent no-op otherwise).
5. Multi-window montages (vault = front ledge → back ledge → back floor) chain several notify states with different target names; update/remove targets as the action progresses.

**Variable-distance animations:** when animations move different distances (no fixed metrics), bake "distance from ledge" curves into them (anim modifier) and set warp-target offsets from the curve values at each window's end — this is the sample's traversal recipe (`docs/game-animation-sample-analysis.md` step list). Epic notes fixed metrics would be simpler if you author your own animations.

## Distance Matching (starts, stops, jumps, lands)

Drive a Sequence Evaluator by *distance* instead of time — playback position always matches how far the character actually travelled (or how far to the stop point / ground).

Setup that actually works (full detail in `references/distance-matching-setup.md`):
1. **Bake a Distance curve**: Animation Data Modifiers → `Distance Curve Modifier` (root motion required). Axis XY for locomotion stops/starts, Z for jumps/falls.
2. **Compression gotcha — the silent killer**: the curve must be readable at runtime ⇒ create a Curve Compression Settings asset with Codec = **Uniform Indexable** and assign it to those sequences. Default compression reads garbage and the node quietly misbehaves.
3. Graph: Sequence Evaluator (`Should Loop` off, `Reinitialization Behavior = Explicit Time`, dynamic Explicit Time pin) + **On Update** anim node function calling `Distance Match to Target` (curve name + your distance variable, e.g. predicted stop distance from CMC braking, or distance-to-ground).
4. `Advance Time by Distance Matching` = same idea for distance-*travelled*; `Set Playrate to Match Speed` = the cheap cousin (uniform speed assumption).

## Animation Modifiers (the data-prep layer)

Blueprint class, parent `AnimationModifier`; implement `OnApply`/`OnRevert` (both receive the sequence). Apply per-sequence or **on the Skeleton to hit every sequence** (Window → Animation Data Modifiers → Add → Apply). Mark variables Instance Editable to tune per-asset.

Standard bakes for this layer: Distance curve (built-in Distance Curve Modifier), foot `Translation Speed` curves (Motion Extractor — also used by Speed Planting in `ue-character-rigging-retargeting`), warping-alpha gate curves, foot-plant **sync markers** (detect lowest foot-bone Z via `GetBonePoseForFrame`, add markers — kills walk↔run phase skating together with sync groups).

Key Blueprint library calls: `AddCurveTrack/AddFloatCurveKeys`, `AddNotifyTrack/AddAnimationNotifyEvents`, `AddAnimationSyncMarkers`, `GetBonePoseForFrame/ForTime` (local space — convert manually for component space), `GetTimeAtFrame/GetFrameAtTime`, `FindBonePathToRoot`.

## Common mistakes

| Anti-pattern | Fix |
|---|---|
| Distance matching "does nothing" | Uniform Indexable curve compression missing (step 2 above) |
| Orientation warping wobbles on turns | Gate its alpha with a baked straight-motion curve (sample pattern) |
| Warp target set but montage ignores it | Target name ≠ notify's Warp Target Name (exact FName match) |
| Leg IK before warping nodes | Order: warp → Foot Placement → Leg IK |
| Slope Warping in production | It's in-development; Foot Placement + Leg IK instead |
| Steering toward current actor rotation | Feed predicted/future facing; current rotation lags |
| Warping on non-root-motion anims (Graph mode) | Root motion is required for Graph-driven warping math |
| Offset Root Bone through walls | It does no collision checks — bound the offset or accept it |

## Related Skills

- `ue-motion-matching` — the pose-selection layer these nodes post-process in the modern stack.
- `ue-animation-system` — sync groups/markers, Inertialization placement, anim node functions used above.
- `ue-character-rigging-retargeting` — Motion Extractor curves shared with Speed Planting.
- `ue-character-movement` — the CMC values (speed, braking, predicted stop) these nodes consume.

## Reference Files

- `references/warping-node-reference.md` — full property tables and debug-draw options per node.
- `references/distance-matching-setup.md` — complete distance-matching walkthrough incl. compression and node functions.
- `../../docs/game-animation-sample-analysis.md` (repo docs) — how the sample chains all of this, with Epic's in-asset caveats.
