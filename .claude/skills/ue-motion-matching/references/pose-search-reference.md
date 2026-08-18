# PoseSearch / Chooser Property Reference

Verified against the UE 5.8 Motion Matching, Motion Matching Debugging, and Dynamic Asset Selection doc pages plus the Game Animation Sample's assets on disk (2026-08-18).

## Contents
1. [Pose Search Schema](#pose-search-schema)
2. [Feature channels](#feature-channels)
3. [Pose Search Database](#pose-search-database)
4. [Motion Matching node](#motion-matching-node)
5. [Pose History node](#pose-history-node)
6. [MM Anim Notify states](#mm-anim-notify-states)
7. [Chooser Tables](#chooser-tables)
8. [Selection debugger fields](#selection-debugger-fields)

---

## Pose Search Schema

| Property | Notes |
|---|---|
| Skeleton | the schema is per-skeleton |
| Data Preprocessor | `None` / `Normalize` / `Normalize Only by Deviation`; use `NormalizeWithCommonSchema` variant when several schemas share a normalization set (sample's `PSS_Default` does) |
| Sample Rate | higher = finer matching, more memory; keep as low as accuracy allows |
| Number of Permutations | extra indexing passes per asset; costs memory |
| Add Data Padding | 16-byte alignment; perf micro-opt, auto-injects a Padding channel |
| Inject Additional Debug Channels | adds position channels for the debugger view |
| MirrorDataTable | enables mirrored search entries |

## Feature channels

| Channel | Queries | Key settings |
|---|---|---|
| Trajectory | movement path past+future | per-sample Offset (sec), Flags (Position/Velocity/Acceleration/Facing), Weight |
| Pose | sampled bones in character space | Sampled Bones (+ per-bone Velocity/Position/Rotation/Phase flags), Input Query Pose, Use Character Space Velocities |
| Position | bone position relative to Origin Bone | Component Stripping (None/StripXY/StripZ), Permutation Time Offset |
| Velocity | bone velocity | Normalize, Component Stripping, char/global space |
| Heading | bone facing axis | Heading Axis X/Y/Z, Origin Bone, Component Stripping |
| Phase | limb cycle phase | bone + Input Query Pose |
| Group | bundles sub-channels | — |
| Sampling Time | debug only (weight 0) | — |
| Crashing Legs | anti leg-crossing (Experimental) | thigh/foot angle |
| Permutation Time | (Experimental) | — |

Common per-channel: `Weight` (cost influence; normalized unless preprocessor None), `Debug Color`, `Input Query Pose` (`Use Character Pose` / `Continuing Pose` / `Interpolated Continuing Pose`), `Sample Time Offset`.

Custom channels (`PSC_`): subclass a feature channel to inject gameplay values — the sample's `PSC_DistanceToTraversalObject` / `PSC_Traversal_Pos` / `PSC_Traversal_Head` push the ledge transform (sent from `AC_TraversalLogic` via interface) into the traversal search. Pair with the `Pose Search: Sampling Attribute` notify (matching Sampling Attribute ID) when the data lives in the animation.

## Pose Search Database

| Property | Notes |
|---|---|
| Schema | required |
| Animation assets | Sequences / Composites / Blendspaces; **NO montages**; root motion required for locomotion |
| Continuing Pose Cost Bias | negative = current animation held longer (stickiness) |
| Looping Cost Bias | negative = looping favored |
| Pose Search Mode | `Brute Force` (ground truth) / `PCAKDTree` (production) / `VPTree` (Experimental) |
| Number Of Principal Components | KDTree dims; ↑quality ↑memory |
| KDTree Max Leaf Size / KNNQuery Num Neighbors | tree breadth vs full-cost candidates |
| Pose Pruning Similarity Threshold | dedupe near-identical poses (PCAKDTree) |
| Normalization Set | `PSN_` grouping for comparable scoring |
| Tags | queryable via `GetDatabaseTags` |

## Motion Matching node

| Property | Notes |
|---|---|
| Database | initial; swap sets at runtime via `SetDatabasesToSearch` (node reference function) |
| Blend Time / Blend Profile / Mode | per-selection blend into the internal stack |
| Use Inertial Blend | route blends through Inertialization instead |
| Pose Jump Threshold Time | no re-jump into the same asset within window |
| Pose Reselect History | no reselect of recently-used poses |
| Search Throttle Time | seconds between searches |
| Should Search | gate searching entirely |
| Should Use Cached Channel Data | share query features across schemas |
| Max Active Blends | internal blend stack cap (0 = stack disabled) |
| Store Blended Pose | overflow blends accumulate into a stored pose vs pop |
| Should Filter Notifies / Notify Recency Time Out | duplicate-notify suppression (default 0.2 s; AnimNotifies only) |
| Max Blend in Time to Override Animation | recent blend gets replaced in place |
| Player Depth Blend In Time Multiplier | deeper stack entries blend faster |
| (Experimental) play-rate multiplier, stitch database + StitchBlendMaxCost | post-selection rate scale; stitch-blend via a dedicated database |

Node functions: `OnMotionMatchingStateUpdated` binding (the sample sets blend time/interrupt mode per transition there); `GetMotionMatchingSearchResult`.
The node's **internal graph** instantiates per playing animation — per-animation warping/adjustment goes inside it, "improving warping and blending behaviors" (Epic, in-asset).

## Pose History node

Companion requirement — the MM node references it.

| Property | Notes |
|---|---|
| Generate Trajectory | true = node builds trajectory from TrajectoryData params; false = you feed one (sample generates its own via `GenerateTrajectory` on tick: history samples + prediction samples + sampling interval) |
| Collected Bones | must cover the schema's sampled bones |

Trajectory contract: samples are in the skeletal mesh component's world space; the sample at `AccumulatedSeconds == 0` is the **previous** simulation frame (MM matches the previous pose). `TrajectorySpeedMultiplier < 1` selects slower animations than the raw trajectory implies. `HandleTransformTrajectoryWorldCollisions` exists to stop predicted trajectories from crossing walls.

## MM Anim Notify states

| Notify | Effect |
|---|---|
| Pose Search: Block Transition | window can't be jumped into |
| Pose Search: Exclude From Database | window not indexed |
| Pose Search: Motion Matched Branch In | marks branch-in points |
| Pose Search: Override Base Cost Bias | per-window selection bonus/penalty |
| Pose Search: Override Continuing Pose Cost Bias | per-window stickiness |
| Pose Search: Sampling Attribute | provides position/rotation/velocity to a matching custom channel |

Per-notify `Can Be Filtered Via Request = false` exempts a notify from MM's duplicate filtering.

## Chooser Tables

Setup: `Output Object Type` (e.g. `PoseSearchDatabase`, `AnimMontage`); `Context Data` = your ABP class or a struct, Direction `Read` (structs can also be `Write` — the sample writes outputs back through `S_ChooserOutputs`-style structs). Columns bind context variables: bool, enum, float range; rows pair conditions with assets.

- Evaluation: `Evaluate Chooser` (single) / multi variants; from C++ via `ChooserFunctionLibrary`. Typical binding point: anim node function `On Update`/state entry, or gameplay event → `SetDatabasesToSearch`.
- **PoseMatch column** (rightmost in the sample's traversal tables): scores rows by pose similarity and returns entry frame ("start time") along with the asset — chooser output struct carries both.
- Proxy Assets + Proxy Tables: indirection for swapping whole animation sets (`Evaluate Proxy` in place of direct chooser refs).
- Nested choosers: a row's result can be another chooser (the sample's per-density `CHT_PoseSearchDatabases` → `CHT_PoseSearchDatabases_Dense` chain).

## Selection debugger fields

Rewind Debugger Details → Motion Matching Selection Table; tabs: **Active Pose** / **Continuing Pose** / **Pose Candidates**. Columns: Database, Asset, **Cost** (expandable per-channel breakdown), Trajectory Total, Pose Total, Bias, Frame, Mirror, Loop, Selection Flags (e.g. `PoseReselectHistory` = blocked by reselect history). Heat map: green favorable, red not. Viewport draws candidate skeletons + their ideal trajectories.
Reading it: Trajectory Total dominating everything = pose features underweighted or trajectory garbage; a candidate you expected losing on Bias = a cost-bias notify or looping bias, not the data.
