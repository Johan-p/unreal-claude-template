# Ragdoll Patterns Reference

Primary source: Epic's Game Animation Sample (UE 5.8) — `SandboxCharacter_Mover_Ragdoll` + `BP_MovementMode_Ragdoll`, whose embedded comments document the workflow step by step (extracted 2026-08-18; the Physics Control doc page itself was not retrievable). Classic-ragdoll APIs verified against `SkeletalMeshComponent.h` / `PhysicalAnimationComponent.h` in the 5.8 engine source.

## Contents
1. [The sample's Physics Control ragdoll, step by step](#1-the-samples-physics-control-ragdoll-step-by-step)
2. [Classic ragdoll checklist](#2-classic-ragdoll-checklist)
3. [Injury / behavior states while simulated](#3-injury--behavior-states-while-simulated)
4. [Choosing between the approaches](#4-choosing-between-the-approaches)

---

## 1. The sample's Physics Control ragdoll, step by step

Setup: a `PhysicsControlComponent` on the character; a **Physics Control Asset (PCA)** defines named profiles; a function at init "creates controls and modifiers on the PCC from the PCA" (`CreateControlsAndBodyModifiersFromPhysicsControlAsset`). The default (non-ragdoll) profile is configurable; ragdoll is a movement mode, not a bool.

**Enter:**
1. Gameplay event (or `BP_AnimNotify_TriggerRagdoll` from an animation) fires the enter event.
2. Set the ragdoll physics profile (`InvokeControlProfile`).
3. **Queue** the movement-mode change to Ragdoll. Mover has already updated this frame and queued changes are not guaranteed → schedule a safety check next frame: if the mode didn't actually become Ragdoll, revert the physics profile.
4. To prevent erratic capsule rotation in the first frames, set a flag consumed by the capsule-orientation logic (`Get_RagdollTargetOrientation`) that freezes capsule rotation, and clear it after a short delay.

**While ragdolled (per tick):**
- The movement mode (`BP_MovementMode_Ragdoll`) owns simulation-side logic; the pawn tracks ragdoll velocity.
- A component set to **tick after the skeletal mesh**, bound to its post-ABP event dispatcher, gives a "runs after the ABP updated" hook (same tick-prerequisite trick as `AC_PostABPTick`).

**Exit (velocity-gated):**
1. When ragdoll velocity stays under a threshold across a delayed re-check, request exit (the sample notes this gate belongs in an AI behavior tree in a real game).
2. Exit only **queues a movement-mode change** — physics settings are restored by the mode-change handler (`On_MovementModeChanged_PostFinalize`, "whenever the previous mode was Ragdoll"), because mode changes can come from any gameplay source and every path must blend out correctly.
3. Cache the current *physical* pose: `SavePoseSnapshot` **and** override the Pose History node with the physical pose, so motion matching can search get-up databases against the actual lying pose (`CHT_GetUpMontages` chooser selects the montage per pose/injury state).
4. **The jitter gotcha:** PCC multiplies motor linear/angular strengths by bone velocities so physics can keep up with animation. Blending instantly to a pose snapshot makes those velocities spike for one frame. So: disable the velocity multipliers, wait one frame, *then* switch back to the default profile. (Skippable only if the default profile is fully kinematic.)

## 2. Classic ragdoll checklist

Enter:
- [ ] `Mesh->SetCollisionProfileName("Ragdoll")`
- [ ] `Mesh->SetAllBodiesBelowSimulatePhysics(PelvisBone, true, true)`
- [ ] `Mesh->SetAllBodiesBelowPhysicsBlendWeight(PelvisBone, 1.f)`
- [ ] Capsule collision off; movement mode → `MOVE_None` or a dedicated ragdoll mode
- [ ] Stop active montages (`Montage_Stop`)

While down:
- [ ] If gameplay needs the actor position: set actor/capsule location from the pelvis body each tick (watch for wall clipping when sweeping)

Exit:
- [ ] `SavePoseSnapshot("Ragdoll")` while still simulated
- [ ] Face-up vs face-down: pelvis (or root) bone rotation up-vector dot world-up → pick get-up animation
- [ ] `SetAllBodiesSimulatePhysics(false)` (or blend weight → 0 over a few frames), restore collision profile + capsule + movement mode
- [ ] AnimGraph: Pose Snapshot node → blend into the get-up montage/state

Partial ragdoll (upper-body flop, legs animate): simulate below `spine_01` with blend weight < 1; ramp with `AccumulateAllBodiesBelowPhysicsBlendWeight`.

Hit reaction without ragdoll: `PhysicalAnimationComponent->ApplyPhysicalAnimationProfileBelow(Bone, Profile)` + partial blend weight + `AddImpulseAtLocation`, ramp weight back to zero. Global intensity: `SetStrengthMultiplyer` (engine's spelling).

## 3. Injury / behavior states while simulated

The sample tracks `E_RagdollInjuryState` and a blend curve (`Ragdoll_Fall_to_Ground_BlendCurve`) rather than treating ragdoll as one state: falling-limp, on-ground, recovering each get different motor strengths and different get-up databases. If your design has "stunned but stirring" or "dragged" states, model them as profiles on the PCC/PCA — that's exactly what profiles are for.

## 4. Choosing between the approaches

| | Classic simulate+blend | Physical Animation Comp | Physics Control Comp |
|---|---|---|---|
| Ships since | UE4 | UE4 | 5.1+ (the 5.8 sample's choice) |
| Stiffness control | blend weight only | per-profile motor strengths | per-profile motors + per-body modifiers, runtime-switchable sets |
| Recovery quality | pose snapshot | n/a (never fully limp) | pose snapshot + velocity-multiplier handling |
| Best for | one-shot deaths | hit reactions on live characters | ragdolls you come back from, staged injuries |

When first touching PCC in code, confirm signatures in `Engine/Plugins/Animation/PhysicsControl/Source/PhysicsControl/Public/PhysicsControlComponent.h` — the doc page for it renders empty and the API is newer than most training data.
