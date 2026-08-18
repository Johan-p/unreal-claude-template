---
name: ue-animation-system
description: "Use this skill when working with Unreal Engine animation: AnimInstance, Animation Blueprints, montage playback, blend space, state machine, transition rules, conduits, state aliases, anim notify, AnimGraph, skeletal mesh, animation slots, slot groups, sync groups, sync markers, inertialization, dead blending, linked anim graphs/layers, root motion, aim offset, layered blend per bone, mirroring, Mirror Data Table, Property Access, thread-safe animation update, or anim node functions. Use it even when the request is phrased as 'make the character play X' or 'hook up these animations' without naming a system. For motion matching/pose search see ue-motion-matching; for pose/motion warping and distance matching see ue-anim-warping-locomotion; for IK Rig retargeting and modular characters see ue-character-rigging-retargeting."
metadata:
  version: 2.0.0
---

# UE Animation System

You are an expert in Unreal Engine's animation system — the AnimInstance/AnimGraph runtime, its threading model, and the classic animation toolset (state machines, blend spaces, montages, notifies, sync, mirroring, linked layers).

## Context Check

This workspace runs a spec-driven workflow: read the feature's architect spec (`docs/architect/`) and the active slice doc (`docs/slices/`) before starting — they already answer most scoping questions (classes, assets, tuning values, what's in and out of scope). CLAUDE.md and LOCAL.md are auto-loaded. Skills advise, specs decide: on conflict, the architect spec wins. Ask the developer only what remains genuinely ambiguous after reading the spec, the slice doc, and the code.

---

## Choosing your stack

Two viable locomotion architectures in UE 5.x. Pick deliberately:

| | Classic (this skill) | Motion Matching (`ue-motion-matching`) |
|---|---|---|
| Pose selection | State machine + blend spaces | Database search per frame (PoseSearch) |
| Animation data needed | Small (one clip per state) | Large (starts/stops/pivots/loops per gait), root motion required |
| Authoring cost | Low; per-transition logic | High data prep; logic lives in Chooser tables |
| Fidelity ceiling | Foot sliding at unplanned speeds/angles | Near-mocap responsiveness |
| Right for | Small games, stylized characters, few animations | Realistic humanoids with a big mocap library |

The classic stack still benefits from the warping/distance-matching layer — see `ue-anim-warping-locomotion` for fixing foot sliding without motion matching.

---

## Architecture and threading

```
ACharacter / AActor
  └── USkeletalMeshComponent
        └── UAnimInstance subclass
              ├── Game thread:   NativeUpdateAnimation / EventGraph
              ├── Worker thread: NativeThreadSafeUpdateAnimation /
              │                  Blueprint Thread Safe Update Animation,
              │                  AnimGraph evaluation, FAnimInstanceProxy
              └── Montage API / Linked Layers
```

The AnimGraph evaluates on a **worker thread** by default; the EventGraph and `NativeUpdateAnimation` run on the **game thread**. Everything you write should respect that split: gather gameplay state on the game thread, consume it on the worker thread. Heavy EventGraph logic serializes the frame — keep it minimal or move it to the thread-safe update.

### The three data-flow options (prefer the first two)

1. **Property Access** (Blueprint): bind a getter chain (e.g. `TryGetPawnOwner → GetVelocity`) directly to a node pin or via a Property Access node. The engine copies the value at a safe sync point — thread-safe by construction, and eligible for the **fast path** (no Blueprint VM execution; watch for the lightning-bolt icon and enable *Warn About Blueprint Usage* to catch regressions).
2. **Blueprint Thread Safe Update Animation** (override in My Blueprint → Functions): the worker-thread replacement for the EventGraph's Update Animation event. Only call thread-safe things here (member variables, pure math, functions marked BlueprintThreadSafe). The compiler warns on violations.
3. **C++ `NativeUpdateAnimation` → cached UPROPERTYs** (pattern below): still correct, still the right call for C++-heavy projects.

### Anim Node Functions

Any asset-player or logic node exposes three bindable functions in Details — they run only while the node is relevant, which beats polling in the update:

- **On Initial Update** — once, first time the node becomes relevant.
- **On Become Relevant** — every time it (re-)becomes relevant.
- **On Update** — every tick while relevant.

Use them to set a Sequence Evaluator's asset/time, drive distance matching, or fire state-entry logic without a state machine event.

---

## AnimInstance (C++)

```cpp
UCLASS()
class MYGAME_API UMyAnimInstance : public UAnimInstance
{
    GENERATED_BODY()

    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    virtual void NativeThreadSafeUpdateAnimation(float DeltaSeconds) override;

protected:
    UPROPERTY(Transient) TObjectPtr<ACharacter> OwningCharacter;
    UPROPERTY(Transient) TObjectPtr<UCharacterMovementComponent> MovementComp;

    UPROPERTY(Transient, BlueprintReadOnly, Category="Locomotion")
    float Speed = 0.f;
    UPROPERTY(Transient, BlueprintReadOnly, Category="Locomotion")
    float Direction = 0.f;
    UPROPERTY(Transient, BlueprintReadOnly, Category="Locomotion")
    bool bIsInAir = false;
};
```

```cpp
void UMyAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation(); // ALWAYS call super
    OwningCharacter = Cast<ACharacter>(TryGetPawnOwner());
    if (OwningCharacter)
        MovementComp = OwningCharacter->GetCharacterMovement();
}

void UMyAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if (!OwningCharacter || !MovementComp) return;

    const FVector Velocity = MovementComp->Velocity;
    Speed    = Velocity.Size2D();
    bIsInAir = MovementComp->IsFalling();
    if (Speed > 3.f)
        Direction = UKismetMathLibrary::NormalizedDeltaRotator(
            Velocity.ToOrientationRotator(),
            OwningCharacter->GetActorRotation()).Yaw;
}

void UMyAnimInstance::NativeThreadSafeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeThreadSafeUpdateAnimation(DeltaSeconds);
    // Only read the UPROPERTY copies written above. Never call UObject
    // functions here unless they are marked BlueprintThreadSafe.
}
```

For heavy worker-thread logic, use an `FAnimInstanceProxy` subclass (copy state in `PreUpdate` on the game thread, compute in `Update` on the worker) — see `references/locomotion-setup.md` for the full proxy pattern.

---

## Montages and Slots

Key API (`UAnimInstance`): `Montage_Play`, `Montage_Stop`, `Montage_Pause/Resume`, `Montage_JumpToSection`, `Montage_SetNextSection`, `Montage_IsPlaying`, `Montage_GetCurrentSection`, `Montage_GetPosition`.

```cpp
void UMyComponent::PlayAttackMontage(UAnimMontage* Montage)
{
    UAnimInstance* AnimInst = GetMesh()->GetAnimInstance();
    if (!AnimInst || !Montage) return;

    // Play FIRST — Montage_SetEndDelegate needs the active instance that
    // Montage_Play creates.
    if (AnimInst->Montage_Play(Montage) <= 0.f) return;

    FOnMontageEnded EndDelegate;
    EndDelegate.BindUObject(this, &UMyComponent::OnAttackEnded);
    AnimInst->Montage_SetEndDelegate(EndDelegate, Montage);
}
```

Dynamic slot montage from a plain sequence:
`AnimInst->PlaySlotAnimationAsDynamicMontage(Seq, FName("UpperBody"), 0.25f, 0.25f);`

### Slots and slot groups (the interruption mechanism)

- Montages **only** play through Slot nodes in the AnimGraph. Slots live **on the Skeleton** (Window → Anim Slot Manager; remember to Save there).
- Every skeleton ships `DefaultGroup.DefaultSlot`. Create named slots (`UpperBody`, `FullBody`) instead of piling everything on DefaultSlot.
- **Playing a montage whose slot is in the same group as a running montage stops the running one.** That's the designed interrupt path — put mutually-exclusive actions in one group, independent layers (upper-body reload vs. full-body sprint) in different groups.
- One montage can target multiple slots, but only within one group.
- Multiplayer: with GAS use `UAbilitySystemComponent::PlayMontage` (replicates); without, server plays and clients replay via OnRep. Never fire `Montage_Play` independently on every net role.

---

## Blend Spaces

Data assets sampled in the AnimGraph; drive them with AnimInstance properties.

- **1D**: single axis (Speed). **2D**: Direction × Speed. **Aim Offset (1D/2D)**: *additive mesh-space* — apply after the base pose; clamp inputs (±90 yaw/pitch).
- Smoothing lives on the asset (Axis Settings): `Smoothing Time` + type (`Spring Damper` with damping <1 gives natural overshoot). Don't combine Weight Speed with Smoothing Time — pick one.
- Default sample interpolation is **triangulation**; the legacy grid mode only matters for Wrap Input axes (e.g. a -180..180 direction axis should wrap).
- Aim offset inputs in C++: `NormalizedDeltaRotator(GetBaseAimRotation(), GetActorRotation())`, clamp, feed Yaw/Pitch.

Full axis/sample configuration: `references/locomotion-setup.md`.

---

## State Machines

States are sub-AnimGraphs; transitions are boolean rule graphs. Beyond the basics:

- **Blend Logic per transition**: `Standard Blend` (duration/curve/blend profile) or **`Inertialization`** — see the next section; prefer it for locomotion transitions, keep durations < 0.4 s, and note it *requires a downstream Inertialization node*. `Custom` gives you a hand-authored blend graph.
- **Priority Order** breaks ties when several rules pass the same frame (lower wins). Set `Max Transitions Per Frame = 1` if the machine "skips through" states in one tick.
- **Automatic Rule Based on Sequence Player**: transition fires when the state's player nears its end — the zero-logic way to chain one-shots (Land → Idle).
- **Conduits**: one rule fanning out to many destinations (3+ states sharing an entry condition). Enable `Allow Conduit Entry States` to use one as a variable entry point.
- **State Aliases**: stand-in for "from any of these states" — kills transition spaghetti. A **global alias** covers all states; best for finite one-shots (hit reactions), risky for indefinite states.
- **Transition events**: Start/End/Interrupt Transition events, plus `Promote to Shared` to reuse one rule or one blend setting across transitions.

Native C++ bindings (no Blueprint):

```cpp
// In NativeInitializeAnimation()
AddNativeTransitionBinding(FName("LocomotionSM"), FName("Idle"), FName("Walk"),
    FCanTakeTransition::CreateUObject(this, &UMyAnimInstance::CanStartMoving));
AddNativeStateEntryBinding(FName("LocomotionSM"), FName("Land"),
    FOnGraphStateChanged::CreateUObject(this, &UMyAnimInstance::OnLandEntered));
```

---

## Inertialization and Dead Blending

Inertial blending replaces crossfades: at the switch the source pose **stops being evaluated entirely**; the node captures the pose offset and decays it. Cheaper than evaluating two graphs, and it's the blend behind modern transition logic.

**The three rules that cause real bugs:**
1. **A request without a node is a runtime error, not a compile error.** Any transition/blend node set to Inertialization, any inertial layer link, needs an `Inertialization` (or `Dead Blending`) node *downstream* of it — usually just before Output Pose. Missing ⇒ error spam in the Message Log at runtime only.
2. **Anim notifies on the source animation stop firing the moment the inertial blend starts.** Don't hang gameplay-critical notifies near the end of clips that get inertially interrupted.
3. Requests are also issued by: blend nodes with `Transition Type = Inertialization`, state-machine transitions with `Blend Logic = Inertialization`, linked-layer graph blending (layers can *only* blend inertially), and the Mirror node's blend-on-toggle.

One Inertialization node serves all requests that reach it (shortest requested duration wins). Additive graphs need the node placed *before* the additive is applied.

**Dead Blending** extrapolates the outgoing pose instead of storing an offset — better with large pose gaps, but it is **experimental**: Epic says "we do not recommend shipping projects that rely on its functionality." Fine to test, don't gate a release on it.

---

## Sync Groups

Blending walk↔run without sync gives you gait "skating" — sync groups keep the cycles phase-aligned by making followers match the leader's normalized time or markers.

- Set `Group Name` + `Group Role` on asset players. Roles: `Can Be Leader` (default; highest blend weight leads), `Always Leader`, `Always Follower`, `Transition Leader/Follower` (excluded while blending in).
- **Marker-based sync** (via `Sync Markers` on the sequences, e.g. `foot_l`/`foot_r` at foot plants) is what you want when cycles have different step counts or stride timings; markers only match within the same group. Foot-plant markers can be auto-generated (see Anim Modifiers in `ue-anim-warping-locomotion`).
- Blend Space Graphs sync all their samples automatically; sequence players inside them default to graph-based sync.
- Keep grouped animations similar in body movement; big length ratios cause visible playrate warble.

---

## Anim Notifies

- **`UAnimNotify`** (point): override the UE5 3-arg `Notify(MeshComp, Animation, EventReference)`.
- **`UAnimNotifyState`** (duration): `NotifyBegin` (has `TotalDuration`) / `NotifyTick` / `NotifyEnd`.
- **Branching points**: `bIsNativeBranchingPoint = true` + `BranchingPointNotify()` — fires synchronously during montage advance (section jumps, precise timeline control). Regular notifies are queued (fire post-tick; right for VFX/SFX).
- **Named montage notify delegate**: `AnimInst->OnPlayMontageNotifyBegin.AddDynamic(...)` and branch on `NotifyName` — no notify subclass needed.
- Notifies stop firing once inertial blending begins on their clip (see above), and a mirrored animation triggers the same notifies — use `Is Triggered By Mirrored Animation` to branch.

Catalog + patterns: `references/anim-notify-reference.md`.

---

## IK and procedural adjustment

- **Trace on the game thread** (`NativeUpdateAnimation` or an actor component), cache targets, consume in the graph:

```cpp
FVector UMyAnimInstance::GetFootTarget(FName Socket) const
{
    const FVector Foot = GetOwningComponent()->GetSocketLocation(Socket);
    FHitResult Hit;
    FCollisionQueryParams P(SCENE_QUERY_STAT(FootIK), true);
    P.AddIgnoredActor(OwningCharacter);
    return GetWorld()->LineTraceSingleByChannel(Hit, Foot + FVector(0,0,50),
        Foot - FVector(0,0,75), ECC_Visibility, P) ? Hit.ImpactPoint : Foot;
}
```

- Skeletal control nodes: `Two Bone IK` (arm/leg), `FABRIK` (chains), `Look At`, `Copy Bone`, `Spline IK`. For grounded feet on uneven terrain prefer the dedicated `Leg IK`/`Foot Placement` nodes — covered in `ue-anim-warping-locomotion`.
- **Control Rig node** (Misc → Control Rig in the AnimGraph): run a Control Rig asset inline — expose its instance-editable variables/controls as pins (`Use Pin`), optionally drive floats from anim curves. Right tool for ground alignment and contact-point fixes; trimming `Input Bones to Transfer` and disabling global-space transfer saves cost. Consuming rigs is covered here and in `ue-character-rigging-retargeting`; *authoring* rigs is its own discipline.

### Layered Blend Per Bone (upper/lower split)

State machine → Base Pose; `UpperBody` slot → Blend Poses 0; Layer Setup Bone=`spine_01`, Blend Depth=0 (or use a Blend Mask). Attack montages target the `UpperBody` slot; legs keep walking.

---

## Linked Anim Graphs and Layers

- **Linked Anim Layer** (recommended for anything multi-mode): define a `UAnimLayerInterface`, place Linked Anim Layer nodes in the main ABP, implement per-mode AnimInstances, swap at runtime:

```cpp
AnimInst->LinkAnimClassLayers(UClimbingLayer::StaticClass()); // nullptr resets
```

- **Linked Anim Graph** references a concrete ABP; retarget by tag with `LinkAnimGraphByTag`.
- Layers in the same *non-default* group share one instance — give shared layers a named group.
- Layer blend in/out is **inertial only** (needs the Inertialization node), and unlinked ABPs stay in memory unless you add streaming logic.
- Notify propagation is opt-in: `SetReceiveNotifiesFromLinkedInstances` / `SetPropagateNotifiesToLinkedInstances`.

---

## Root Motion

- `RootMotionMode`: `RootMotionFromMontagesOnly` (default-ish, gameplay-safe) vs `RootMotionFromEverything`.
- Per-montage disable: `GetActiveInstanceForMontage(M)->PushDisableRootMotion()`.
- Networked: smoothing `ENetworkSmoothingMode::Exponential`; server is authoritative, clients correct via `FRootMotionMovementParams`. Enable `bAllowPhysicsRotationDuringAnimRootMotion` if rotation comes from animation.
- Root motion is a *prerequisite* for motion matching and distance matching — see those skills.

---

## Mirroring

Halve your directional animation count with a **Mirror Data Table** (Content Browser → Animation → Mirror Data Table, per Skeleton):

- Auto-populate with Find/Replace expressions (`_l` → `_r`, Prefix/Suffix/Regex). Central bones (pelvis/spine/neck/head) must appear with Name == Mirrored Name or their rotations won't flip. Mirror axis is almost always X.
- Table rows cover bones, notifies, curves, and sync markers; the AnimGraph **Mirror node** toggles per-category and takes a bool + blend time (blend requires — again — a downstream Inertialization node).

---

## Common Mistakes

| Anti-pattern | Fix |
|---|---|
| Gameplay reads in thread-safe update / worker thread | Property Access or cached `UPROPERTY Transient` written on the game thread |
| Heavy EventGraph logic | Blueprint Thread Safe Update Animation, or Property Access pins |
| Inertialization transition with no Inertialization node | Add the node near Output Pose; watch the Message Log |
| Gameplay-critical notify never fires | Inertial blend started before it — move the notify earlier or drive from gameplay code |
| Two montages fighting | Same slot group = interrupt by design; separate groups for independent layers |
| Walk↔run blend "skates" | Sync group + foot-plant sync markers |
| Polling `Montage_IsActive` | `Montage_SetEndDelegate` after `Montage_Play` |
| Skipping `Super::NativeInitializeAnimation()` | Always call super — proxy/skeleton init |
| Slot edited but montage can't find it | Slots live on the Skeleton — save in Anim Slot Manager |
| State machine tunnels several states in one frame | `Max Transitions Per Frame = 1`, check Priority Order |

---

## Build.cs

```csharp
PublicDependencyModuleNames.AddRange(new string[] {
    "Core", "CoreUObject", "Engine", "AnimGraphRuntime"
});
// Optional:
PrivateDependencyModuleNames.Add("ControlRig");        // Control Rig node/IK
PrivateDependencyModuleNames.Add("AnimationCore");
PrivateDependencyModuleNames.Add("GameplayAbilities"); // GAS montage tasks
```

---

## Related Skills

- `ue-motion-matching` — PoseSearch schema/database/chooser stack, blend stack, trajectory.
- `ue-anim-warping-locomotion` — orientation/stride/slope warping, motion warping, distance matching, foot placement, anim modifiers.
- `ue-character-rigging-retargeting` — IK Rig, IK Retargeter, runtime retargeting, modular characters, post-process ABPs.
- `ue-gameplay-abilities` — `PlayMontageAndWait`, GAS montage replication.
- `ue-actor-component-architecture` — SkeletalMeshComponent setup, tick ordering.

## Reference Files

- `references/anim-notify-reference.md` — built-in notify catalog and custom notify patterns.
- `references/locomotion-setup.md` — classic locomotion: blend space axes, state machine wiring, the FAnimInstanceProxy pattern, layered blends.
- `../../docs/game-animation-sample-analysis.md` (repo docs) — how Epic's Game Animation Sample assembles the modern stack; read before copying any pattern from that sample.
