# Warping Node Property Reference

Verified against UE 5.8 docs (Pose Warping, Motion Warping pages) and the Game Animation Sample's graphs/in-asset comments (2026-08-18). All pose-warping nodes: **Animation Warping** plugin. Common to all: `Mode = Manual` (static, user-fed values; no transition smoothing — static scenarios only) vs `Graph` (dynamic, root-motion-driven — requires root motion enabled); `IK Foot Root Bone` must point at the skeleton's IK root.

## Contents
1. [Orientation Warping](#orientation-warping)
2. [Stride Warping](#stride-warping)
3. [Slope Warping](#slope-warping)
4. [Foot Placement](#foot-placement)
5. [Offset Root Bone](#offset-root-bone)
6. [Steering](#steering)
7. [Motion Warping notify-state settings](#motion-warping-notify-state-settings)

---

## Orientation Warping

Rotates the lower body toward locomotion direction; counter-rotates the spine to hold facing. `Orientation = RotationBetween(RootMotionDirection, LocomotionDirection)`.

| Property | Notes |
|---|---|
| Orientation Angle | Manual mode input |
| Locomotion Angle | Graph mode input (from velocity vs actor rotation) |
| Location Angle Delta Threshold | default 90°; beyond it the locomotion direction inverts rather than warping 180° |
| Spine Bones | tapered array; **index 0 rotates least** |
| IK Foot Bones | the IK feet to reorient |
| Rotation Axis | usually Z |
| Distributed Bone Orientation Alpha | how much of the warp the spine distribution absorbs |
| Rotation Interp Speed | alpha/sec toward the final warp angle |
| Min Root Motion Speed | below it, no warping |

Sample-verified behaviors: interpolation compensation is skipped when the instantaneous root-motion delta is large (treated as a pivot); disable that smoothing only if root motion is clean. **Gate the node's alpha with a baked straight-motion curve** — Epic's own workaround for curved-motion artifacts ("should be fixed in future releases").

Debug: `Enable Debug Draw` (Red = input, Blue = root motion, Green = simulated), `Debug Draw Scale`.

## Stride Warping

Scales stride to capsule speed: `StrideScale = LocomotionSpeed / RootMotionSpeed`.

| Property | Notes |
|---|---|
| Stride Direction / Stride Scale | Manual mode |
| Locomotion Speed | Graph mode input |
| Min Locomotion Speed Threshold | below it, node idles |
| Pelvis Bone | required |
| Foot Definitions | per leg: IK foot, FK foot, thigh |
| Stride Scale Modifier | clamp + interp on the computed scale |
| Floor/Gravity Direction | for slope-aware stride orientation (`Orient Stride Direction Using Floor Normal`) |
| Pelvis IK Foot Solver | Adjustment Interp, Alpha, Max Distance, Error Tolerance, Max Iter |
| Compensate IK Using FK Thigh Rotation / Clamp IK Using FK Limits | keep IK legs plausible |

Debug draws exist for every stage: capsule speed vector, IK foot origin/adjustment/final, pelvis and thigh adjustments — use them before touching tuning values.

## Slope Warping

Feet-to-floor-normal warping for inclines/stairs. **Epic: "still in development, don't trust a project to its functionality"** — testing only; ship Foot Placement + Leg IK instead.
Key properties: Pelvis Bone; per-foot definitions (IK/FK bones, Number of Bones, Foot Size in uu); pelvis/floor-normal/floor-offset interpolators (stiffness, damping); Gravity Dir; Max Step Height; `Keep Mesh Inside Of Capsule`; `Pull Pelvis Down`; optional custom floor offset.

## Foot Placement

(Used in the sample's CMC ABP; absent from the 5.8 Locomotion doc page — properties from asset inspection.)
Two jobs: (1) lock feet when the *source animation's* foot speed and height are low — Graph evaluation mode reads per-foot speed **curves** by name (bake with Motion Extractor / `AM_FootSpeed_*`), Manual mode takes values; (2) trace each foot to the ground and shift the pelvis down so the planted foot reaches. Pair with Leg IK after it; the IK foot bones it moves are what Leg IK pins to.

## Offset Root Bone

(Experimental; sample + sample-doc caveats.) Consumes root motion and lets the mesh root drift from the capsule, interpolating back per settings. Enables turn-in-place and distance-matched stops under motion matching without capsule pops.
Known limits: **no collision checks** (mesh can clip geometry when offset), translation-offset release during montages can cause pops, interpolation behavior is hard-coded. Downstream Steering consumes the root rotation it exposes.

## Steering

(Experimental; sample in-asset comments.) Applies additional rotation to root motion toward a Target Rotation each frame.
- Feed Target Rotation from the **predicted future facing** (trajectory sample at +N sec), not current actor rotation — Epic's comment: steering toward current rotation "could cause it to lag too far behind".
- Two speed cutoffs: below one, all steering off; below the other, only the additive spring-based correction is disabled.
- The sample uses **two Steering nodes** (locomotion + turn-in-place) because some properties are not pinnable yet; expect consolidation in later engine versions.

## Motion Warping notify-state settings

Plugin: **Motion Warping**; component: `UMotionWarpingComponent`.

| Setting | Options / notes |
|---|---|
| Warp Target Name | must EXACTLY match the name passed to `AddOrUpdateWarpTarget*` |
| Root Motion Modifier | `Skew Warp` (align location+rotation; the usual choice), `Scale` (uniform scaling) |
| Warp Point Anim Provider | None / Static / Bone |
| Warp Translation / Warp Rotation | independent toggles |
| Ignore Z Axis | constrain to horizontal |
| Rotation Type | `Default` (match target rotation) / `Facing` (face the target) |

Blueprint API: `AddOrUpdateWarpTargetFromLocationAndRotation(Name, Loc, Rot)`, `AddOrUpdateWarpTargetFromTransform`, `RemoveWarpTarget(Name)`; windows can also be created in code via `Add Root Motion Modifier Skew Warp` (start/end time + target name) instead of notify states.

Multi-window pattern (sample's traversal): FrontLedge → BackLedge → BackFloor windows in one montage; update BackLedge only for hurdle/vault actions, remove it otherwise; derive BackFloor's XY from the animation's baked distance-from-back-ledge curve value (animations travel different distances). Sliding-scale caution from Epic: deriving floor warp points from animated distance can clip on non-flat floors — fixed metrics per animation family avoids the whole class of problem if you control the animation authoring.
