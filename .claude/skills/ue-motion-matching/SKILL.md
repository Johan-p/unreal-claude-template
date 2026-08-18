---
name: ue-motion-matching
description: "Use this skill for Motion Matching / PoseSearch work in Unreal Engine: Pose Search Schemas, Databases, Normalization Sets, feature channels, the Motion Matching and Pose History AnimGraph nodes, trajectory generation, Chooser Tables / Proxy Tables (Dynamic Asset Selection) driving database or asset selection, Blend Stack, motion-matching Anim Notifies (Block Transition, Exclude From Database, Override Cost Bias), database density/LOD tiers, and the Motion Matching selection debugger. Trigger on: 'motion matching', 'pose search', 'PSD/PSS/CHT assets', 'chooser', 'blend stack', 'make locomotion feel like the Game Animation Sample', 'why did it pick this animation', or building high-fidelity responsive locomotion from a large animation set. For the warping nodes that post-process the MM output see ue-anim-warping-locomotion; for classic state-machine locomotion see ue-animation-system."
metadata:
  version: 1.0.0
---

# UE Motion Matching

You are an expert in UE 5.x Motion Matching — the PoseSearch plugin's query-based pose selection, the Chooser plugin's data-driven control layer, and the Blend Stack that plays the results.

## Context Check

This workspace runs a spec-driven workflow: read the feature's architect spec (`docs/architect/`) and the active slice doc (`docs/slices/`) before starting. CLAUDE.md and LOCAL.md are auto-loaded. Skills advise, specs decide.

**Reference implementation:** Epic's Game Animation Sample (UE 5.8, dual CMC/Mover stacks; free on Fab — optional LOCAL.md key `<GameAnimSampleDir>` if installed). `docs/game-animation-sample-analysis.md` is the verified map — asset inventory, graph wiring, Epic's in-asset caveats, and where the online docs diverge from the 5.8 disk. Read it before copying anything from the sample.

## Should you even use motion matching?

Honest gate before any MM work: it needs a **large root-motion animation set** (starts, stops, pivots, loops, turns — per gait, per stance), and its quality ceiling comes from data coverage, not tuning. Epic: "weights will not always solve incorrect pose selection" when the data doesn't cover the movement model. A handful of clips + a state machine + warping (`ue-anim-warping-locomotion`) beats MM on thin data every time. Plugins required: **PoseSearch** (+ **Chooser** for the control layer, **AnimationWarping** for post-processing).

---

## The mental model

```
Gameplay state (enums/structs) ──▶ CHOOSER TABLE: which databases are legal now
Trajectory + pose history      ──▶ MOTION MATCHING node: best pose in those databases
Selected animation             ──▶ BLEND STACK (internal): blends winners as they change
                               ──▶ warping / IK post-process (other skill)
```

Selection quality = query (trajectory + pose features) × data (databases) × permission (choosers). Debug in that order.

## Asset types (naming per the sample; add prefixes to NamingConventions.md if authoring)

| Asset | Prefix | Role |
|---|---|---|
| Pose Search **Schema** | `PSS_` | What to compare: feature channels, sample rate, skeleton, preprocessor |
| Pose Search **Database** | `PSD_` | A pool of animations indexed under one schema + cost biases |
| Pose Search **Normalization Set** | `PSN_` | Groups databases that must score on a comparable scale |
| **Feature Channel** (custom) | `PSC_` | Injects gameplay data into the query (e.g. distance-to-ledge) |
| **Chooser Table** | `CHT_` | Rows of (conditions → asset); the control layer |

### Schema essentials
- Channels: **Trajectory** (positions/velocities/facings at time offsets — past *and* future), **Pose** (sampled bones; the sample uses `pelvis`, `foot_l`, `foot_r`), Position/Velocity/Heading (per-bone, with `Component Stripping` e.g. StripZ), Phase, Group. Weights bias the cost per channel.
- `Data Preprocessor = Normalize` (or `NormalizeWithCommonSchema` when multiple schemas share a normalization set).
- Use as **few channels/samples as accuracy allows** — every channel costs memory and search time.

### Database essentials
- Only Sequences/Composites/Blendspaces — **montages are not supported** in the MM node (experimental Character-BP workaround exists; don't build on it).
- **Every animation needs root motion enabled.**
- Cost knobs: `Continuing Pose Cost Bias` (negative = stickier current animation), `Looping Cost Bias`, per-section `Override Base Cost Bias` notify.
- Search mode: `PCAKDTree` for production (set `Number Of Principal Components`, `KDTree Max Leaf Size`, `KNNQuery Num Neighbors`); Brute Force to establish ground truth when debugging selection; VPTree experimental.
- Split databases by state/gait (`PSD_Dense_Stand_Run_Loops`…), not one mega-database — choosers then gate which are searched. The sample runs 169 databases across 4 density tiers (a data-LOD scheme worth copying for perf work).

## Graph wiring

```
[EventGraph/thread-safe update: GenerateTrajectory + state enums]

Pose History node  (Generate Trajectory = true, Collected Bones = schema's bones)
   … anywhere before Output Pose; the MM node references it
Motion Matching node
   Database(s) ◀── SetDatabasesToSearch(...) from a Chooser evaluation on state change
   → its INTERNAL graph runs per-animation (per-anim warping goes here)
   → blend settings: Blend Time, Blend Profile, Inertial blend option, Max Active Blends
   → post-process chain (ue-anim-warping-locomotion) → Inertialization → Output Pose
```

Key node settings: `Pose Jump Threshold Time` / `Pose Reselect History` (anti-flicker), `Search Throttle Time` (perf), `Should Search` (gate), `Should Use Cached Channel Data` (multi-schema sharing), `Should Filter Notifies` + `Notify Recency Time Out` (default 0.2 s — stops duplicate notify fires when adjacent poses reselect the same section; **AnimNotifies only, not NotifyStates**).

**Interrupt mode matters:** force a re-search when the database *set* changes (the sample's `Get_MMInterruptMode`), otherwise the continuing pose can outlive its legality.

## Choosers (Dynamic Asset Selection — the control layer)

Chooser Tables map context values → assets. Context = your ABP class (Direction: Read) or a struct; columns test bools/enums/float ranges; output type = `PoseSearchDatabase` (or montage, or any asset/class). Evaluate via `Evaluate Chooser` (Blueprint/anim node function) — the sample evaluates on state change and calls `SetDatabasesToSearch` on the MM node reference.

- **PoseMatch column**: rows scored by pose similarity — returns the best *montage and entry frame* for the current pose. This is how the sample picks traversal montages (chooser decides, MM never sees montages).
- Proxy Tables/Assets add an indirection layer (swap whole animation sets per context) — worth it only past a certain scale.
- Chooser plugin is **Experimental** in 5.8 by classification, though the sample leans on it heavily; note that status in specs.

## MM-specific Anim Notifies

`Pose Search: Block Transition` (no jumping into this window) · `Exclude From Database` (don't index) · `Motion Matched Branch In` · `Override Base Cost Bias` · `Override Continuing Pose Cost Bias` · `Sampling Attribute` (feeds a matching custom channel).

## Data preparation (do this or MM will be mediocre)

1. Root motion on everything; Root Motion property enabled on each sequence.
2. Bake helper curves with **Animation Modifiers** (see `ue-anim-warping-locomotion`): foot speeds (foot locking), warping-alpha gates, per-anim speed (play-rate scaling), traversal distances.
3. Tag database membership deliberately: dense loops vs starts vs pivots vs transitions — the schema/database split IS the design.
4. Events that must be frame-exact (jump SFX): fire from gameplay/movement events, not anim notifies — MM enters clips at variable frames (sample's `JustLanded` multi-frame flag pattern).

## Debugging (in selection-quality order)

1. **Rewind Debugger** (Tools → Debug → Rewind Debugger + Rewind Debugger Details; needs Animation Insights plugin): record gameplay, scrub, open the **Motion Matching Selection Table** — Active Pose / Continuing Pose / Pose Candidates tabs, cost broken down per channel (green = favorable), trajectory + query drawn on the skeleton in viewport.
2. Wrong pose picked → check the *query* first (trajectory garbage in = garbage out), then data coverage ("consistently chooses the max-speed animation" = your movement speed exceeds the data's), then weights, then cost biases. Weights last, not first.
3. Flickering selection → `Pose Jump Threshold Time`, `Pose Reselect History`, raise `Continuing Pose Cost Bias` magnitude.
4. Establish ground truth with Brute Force search mode before blaming KDTree settings.

## Performance

Search cost: `Search Throttle Time`, chooser-gated database sets (search less, not smarter), `Should Use Cached Channel Data`. Memory: sample rate, channel count, `Pose Pruning Similarity Threshold`, `Add Data Padding` (16-byte alignment), database density tiers as LODs. Blend cost: `Max Active Blends` caps the stack.

## Caveats ledger

- Montages unsupported in the MM node (workaround experimental).
- Chooser plugin Experimental; Blend Stack's stitch database, VPTree, Crashing Legs / Permutation Time channels Experimental.
- The sample's "State Machine + Chooser + MM + Blend Stack" hybrid is a tooling preview — Epic's own comments say the workflow "is far from ideal"; don't copy it into production.
- Notify filtering only covers AnimNotifies, never NotifyStates.
- Mover-stack MM (sample's second ABP) adds `StrideWarping`/`BlendStack` differences — the analysis doc maps both.

## Related Skills

- `ue-anim-warping-locomotion` — Offset Root Bone, Orientation/Stride Warping, Foot Placement, Steering: the post-process chain and the anim-modifier data bakes.
- `ue-animation-system` — Inertialization node placement, slots for the traversal montages, sync concepts.
- `ue-character-rigging-retargeting` — retargeting the sample's 2,132-clip library onto your character.

## Reference Files

- `references/pose-search-reference.md` — full property tables: schema channels, database settings, MM node, chooser columns.
- `../../docs/game-animation-sample-analysis.md` (repo docs) — the seven-layer sample map and Epic's in-asset caveats.
