# Distance Matching Setup — complete walkthrough

Verified against the UE 5.8 Distance Matching doc page (2026-08-18). Plugin: **Animation Locomotion Library** (Edit → Plugins → Animation). Root motion must be enabled on the sequences.

## Concept

A Distance curve maps each frame of an animation to a distance value (distance travelled since start, or distance to a landmark like the stop point / the ground). At runtime you compute the *actual* distance (from movement prediction or a trace) and ask the curve "which frame corresponds to this distance?" — playback position then tracks reality regardless of speed. Classic uses: run-stops (distance to predicted stop location), run-starts (distance travelled), jump/fall (distance to ground = Z axis curve), landings.

## Step 1 — bake the Distance curve

Per sequence (or via the Skeleton for bulk):
1. Animation Sequence Editor → `Windows → Animation Data Modifiers` → `Add Modifier → Distance Curve Modifier`.
2. Settings:
   - **Sample Rate**: 30 covers most cases.
   - **Curve Name**: e.g. `Distance` (keep one convention project-wide; the node needs the exact name).
   - **Stop Speed Threshold**: velocity below which the character counts as stopped (default 0). For stop animations, this defines the zero point — the curve runs negative approaching the stop and hits 0 at the plant.
   - **Axis**: `XY` for ground locomotion, `Z` for jump/fall.
   - **Stop at End**: only declare "stopped" on the final frame.
3. `Apply All Modifiers`. Inspect in the Curve Editor — a stop animation should sweep from a negative distance up to 0.

## Step 2 — curve compression (the silent killer)

Runtime curve *indexing* needs a compression codec that supports it:
1. Content Browser → right-click → `Create Advanced Asset → Animation → Curve Compression Settings`.
2. Set **Codec = Uniform Indexable**.
3. On every distance-matched sequence: Asset Details → Compression → assign this asset.

Skip this and the default codec silently returns wrong/unusable values — the node "does nothing" with no error. This is the #1 distance-matching failure.

## Step 3 — the graph

```
Sequence Evaluator ──▶ (rest of graph)
  Should Loop = false
  Teleport to Explicit Time = false
  Start Position = 0
  Reinitialization Behavior = Explicit Time
  Explicit Time pin = Dynamic Value
```

Bind an **On Update** anim node function on the evaluator (Details → Functions → On Update → +Create Binding). Inside it:

```
Get Anim Node Reference → Convert to Sequence Evaluator
Distance Match to Target(
    UpdateContext, SequenceEvaluator,
    DistanceToTarget = <your distance variable>,
    DistanceCurveName = "Distance")
```

The distance variable comes from gameplay (thread-safe path — Property Access or a variable set in Blueprint Thread Safe Update Animation):
- **Stop**: `PredictGroundMovementStopLocation` (Animation Locomotion Library / CMC braking values) → distance from current location (negative while approaching).
- **Jump/fall**: distance to ground from a downward trace, or apex-relative Z.

## The three library nodes

| Node | What it does | Use for |
|---|---|---|
| `Distance Match to Target` | Sets evaluator time so curve(distance) matches your target-distance variable | stops, lands, approach-to-mark |
| `Advance Time by Distance Matching` | Advances evaluator by distance travelled this frame | starts, in-cycle speed sync |
| `Set Playrate to Match Speed` | Scales a Sequence Player's rate to speed (assumes uniform clip velocity) | cheap loops without an evaluator |

## Interaction with the rest of the stack

- Distance-matched starts/stops usually pair with **Orientation Warping** (direction) and **Stride Warping** (residual speed error) — distance matching fixes *when* in the clip you are; warping fixes *where the limbs are*.
- Under motion matching, the MM node replaces most of this — but the sample still play-rate-scales blend-stack animations from baked speed curves (same curve-driven philosophy, see `docs/game-animation-sample-analysis.md`).
- Distance-matched nodes have no natural sync-group phase; be deliberate when mixing them into sync groups (a follower evaluator being time-forced fights the leader).
