---
name: ue-physics-animation
description: "Use this skill when animation meets physics simulation on a character: ragdolls (entering, tuning, and — the hard part — getting back OUT via Pose Snapshot or motion-matched get-ups), partial physics blending (SetAllBodiesBelowSimulatePhysics / physics blend weights), hit reactions, the Physical Animation Component (motor-driven animation tracking), the Physics Control Component (profile-driven ragdoll/drive-to-animation, PCA assets), and the Rigid Body / AnimDynamics AnimGraph nodes for secondary motion (ponytails, scarves, pouches, antennas, dangly bits). Trigger on: 'ragdoll', 'knock down / get up', 'death animation', 'hit reaction', 'make the hair/cloth/prop bounce', 'the character goes limp', 'physics on bones', or any blend between simulated and animated poses."
metadata:
  version: 1.0.0
---

# UE Physics Animation

You are an expert in combining physics simulation with skeletal animation in UE 5.x: full and partial ragdolls, motor-driven animation tracking, and lightweight secondary motion. API signatures below are verified against the UE 5.8 engine headers; the Physics Control recipe is verified against Epic's Game Animation Sample implementation (its doc page was unfetchable — the sample is the better source anyway).

## Context Check

This workspace runs a spec-driven workflow: read the feature's architect spec (`docs/architect/`) and the active slice doc (`docs/slices/`) before starting. CLAUDE.md and LOCAL.md are auto-loaded. Skills advise, specs decide.

**Worked example:** Epic's Game Animation Sample (free on Fab; optional LOCAL.md key `<GameAnimSampleDir>` if installed) ships a complete Physics-Control ragdoll with motion-matched get-ups (`SandboxCharacter_Mover_Ragdoll`, `BP_MovementMode_Ragdoll`, `CHT_GetUpMontages`, `E_RagdollInjuryState`) and six `PA_Echo_*` physics assets driving Rigid-Body secondary motion. `docs/game-animation-sample-analysis.md` maps the project.

---

## Decision map

| Goal | Tool | Cost |
|---|---|---|
| Ponytail/pouch/antenna wiggle, no Physics Asset wanted | **AnimDynamics node** | cheapest — box approximations, no collision |
| Same, but colliding with the character/world, PA exists | **Rigid Body node** | light — simulates the PA inside the AnimGraph |
| Character keeps animating but reacts physically to hits | **Physical Animation Component** | medium — motors drive bodies toward the animated pose |
| Full ragdoll + controllable stiffness + clean recovery | **Physics Control Component** (5.1+, what the 5.8 sample uses) | medium — profile-driven |
| Quick-and-dirty full ragdoll (death, no recovery) | **Classic**: simulate + blend weight | trivial |

Everything below needs a **Physics Asset** on the mesh (except AnimDynamics) — bodies on the bones that should simulate, sensible mass/damping, collision enabled between the right pairs.

## Classic ragdoll (verified `USkeletalMeshComponent` API)

```cpp
// Enter
Mesh->SetCollisionProfileName(TEXT("Ragdoll"));
Mesh->SetAllBodiesBelowSimulatePhysics(TEXT("pelvis"), true, /*bIncludeSelf*/ true);
Mesh->SetAllBodiesBelowPhysicsBlendWeight(TEXT("pelvis"), 1.f);
GetCharacterMovement()->SetMovementMode(MOVE_None);   // or a dedicated mode
Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);
```

- **Partial ragdoll** = simulate below a bone with blend weight < 1 (`SetPhysicsBlendWeight`, `AccumulateAllBodiesBelowPhysicsBlendWeight` for ramping): upper body flops, legs keep walking.
- The capsule no longer follows the mesh — each frame, move the capsule to the pelvis body's location if gameplay still needs a position (and beware: mesh is now the authority, not the actor).

### Getting OUT (the part everyone underestimates) — Pose Snapshot

1. While still simulated: `Mesh->GetAnimInstance()->SavePoseSnapshot(FName("Ragdoll"))` (or `SnapshotPose` into a variable).
2. AnimGraph: a `Pose Snapshot` node (same name) blends into a get-up state/montage — pick a "get up from front" vs "from back" animation by checking the pelvis bone's up-vector.
3. Turn physics off (`SetAllBodiesSimulatePhysics(false)`, restore collision profile, movement mode), blend snapshot → get-up over ~0.2–0.5 s.
4. **LOD caveat**: snapshots capture at the current LOD; bones missing from a different LOD revert to ref pose.

The sample's upgrade on this: it also **overrides the Pose History node with the physical pose** so motion matching can select the best get-up entry (`CHT_GetUpMontages` chooser picks per injury state) — see `references/ragdoll-patterns.md`.

## Physics Control Component (the 5.8 sample's ragdoll)

Plugin `PhysicsControl`. Controls = per-body motors with linear/angular strength+damping; Body Modifiers = per-body kinematic/simulated switches; a **Physics Control Asset (PCA)** stores named profiles you switch between at runtime.

Verified API (engine headers): `CreateControlsAndBodyModifiersFromPhysicsControlAsset`, `CreateControlsFromSkeletalMesh[Below]`, `CreateControlsFromLimbBones`, `CreateBodyModifier[s...]`, `InvokeControlProfile(Name)`, `SetControlData`, `SetControlTarget*`, `GetControlNamesInSet`.

Pattern: default profile = fully kinematic (or animation-tracking); "Ragdoll" profile = low/no motor strength; hit-reaction profile = strong motors + brief impulse. `InvokeControlProfile` switches live.

**Two hard-won sample gotchas** (from Epic's in-asset comments, verbatim knowledge):
1. **Frame-delay the profile switch on exit.** PCC multiplies motor strengths by bone velocities; blending instantly to a pose snapshot makes those velocities spike for one frame → physical jitter. Disable the multipliers, wait a frame, then switch profiles (unnecessary only if the default profile is fully kinematic).
2. **Queued mode changes aren't guaranteed.** The sample queues the Ragdoll movement mode, then verifies next frame that it actually happened — reverting physics settings if not. Exit goes through the movement-mode change (single choke point), never by poking physics settings directly, because mode changes come from multiple sources.

Full step recipe: `references/ragdoll-patterns.md`.

## Physical Animation Component (hit reactions on an animated character)

Verified API: `ApplyPhysicalAnimationSettingsBelow(BoneName, Data, bIncludeSelf)`, `ApplyPhysicalAnimationProfileBelow(BoneName, ProfileName, ...)` (profiles authored in the Physics Asset Editor), `SetStrengthMultiplyer(float)` [sic — engine spelling].

Hit-reaction recipe: bodies below spine simulate with blend weight ~0.3–0.6 + physical animation profile driving them toward the animated pose → `AddImpulseAtLocation` on the hit body → ramp blend weight back to 0 over ~0.5 s. Character never stops playing its animation; the physics rides on top.

## Rigid Body node (secondary motion with a Physics Asset)

Docs-verified: simulates the PA *inside the AnimGraph* (component space — convert spaces around it). Key settings: `Simulation Space` (Component/World/Base Bone — World transfers mesh motion into the sim), `Override Physics Asset` (author a dedicated PA with only ponytail/pouch bodies — the sample's `PA_Echo_Ponytail` etc. are exactly this), External Force pin, `Component Linear Acc/Vel Scale`, Sim Space Settings (Master Alpha, velocity clamps, `Velocity Scale Z` for jump feel, external velocities for wind).
- Jitter fixes: taper masses down the chain, raise linear/angular damping, align centers of mass.
- Teleporting the character → `Reset Dynamics` node/call or the sim explodes.
- Bodies must be **Simulated**; bodies they collide against **Kinematic**.

## AnimDynamics node (secondary motion without a Physics Asset)

Docs-verified: self-contained box-approximation solver, no collision detection — constraints only. Per node: Bound Bone + Box Extents + Local Joint Offset; linear/angular constraints (springs for bounce), spherical limits (Inner/Outer) as pseudo-collision, planar limits as floors; `Chain` mode (Bound Bone → Chain End) is much more expensive and needs constraint tuning to avoid flailing (solver iterations pre≈4× post). Gravity override, wind support. Defaults pin everything in place — you must open the constraints before anything moves.

## Common mistakes

| Anti-pattern | Fix |
|---|---|
| Ragdoll enters fine, exit pops | Pose Snapshot blend (and the PCC frame-delay gotcha above) |
| Capsule left behind / camera detaches | Reposition capsule to pelvis each simulated frame, or accept mesh authority |
| Get-up plays the wrong way round | Branch on pelvis up-vector (face-down vs face-up) |
| Rigid Body explodes on teleport | Reset Dynamics |
| Rigid Body jitters at rest | Mass taper + damping + center-of-mass alignment; check bodies aren't fighting kinematic partners |
| AnimDynamics does nothing | Default constraints are locked — widen linear/angular limits |
| Whole-PA simulation for one ponytail | Dedicated override PA with just those bodies |
| Hit reaction snaps animation off | Physical Animation profile + partial blend weight, not full simulate |
| Physics profile switch on the same frame as snapshot blend (PCC) | Wait one frame (bone-velocity multiplier spike) |

## Related Skills

- `ue-animation-system` — Pose Snapshot node placement, state machines the ragdoll states live in, montages for get-ups.
- `ue-motion-matching` — the sample's motion-matched get-up selection (`CHT_GetUpMontages`, pose-history override).
- `ue-physics-collision` — collision profiles, impulses, Chaos bodies underneath all of this.
- `ue-character-movement` — movement modes; a ragdoll should be a mode, not a flag.

## Reference Files

- `references/ragdoll-patterns.md` — the sample's full PCC ragdoll step recipe (enter/update/exit), classic-ragdoll checklist, injury-state pattern.
- `../../docs/game-animation-sample-analysis.md` (repo docs) — where the ragdoll sits in the sample's architecture.
