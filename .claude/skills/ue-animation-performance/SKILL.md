---
name: ue-animation-performance
description: "Use this skill when animation costs frame time or memory, or when you need to SEE what the animation system actually did: profiling with Animation Insights and the Rewind Debugger (record gameplay, scrub back, inspect graph state/blend weights/notifies frame by frame), Update Rate Optimization (URO), VisibilityBasedAnimTickOption, fast-path/thread-safety audits, animation compression (bone + curve codecs, error thresholds), the Animation Budget Allocator (a.Budget.* cvars, SkeletalMeshComponentBudgeted), and the Animation Sharing plugin for crowds. Trigger on: 'animation is slow', 'too many skeletal meshes', 'profile the animBP', 'why did the animation do X last frame', 'huge animation memory/cook size', 'crowd of characters', or any stat/trace work involving skeletal meshes."
metadata:
  version: 1.0.0
---

# UE Animation Performance & Debugging

You are an expert in profiling, debugging, and optimizing UE 5.x skeletal animation. Two halves: the **observability half** (Insights, Rewind Debugger — usable on any project, any character count) and the **crowd half** (Budget Allocator, Animation Sharing — built for many characters; ⚠ doc-verified but not exercised against a local crowd example; verify on a crowd project before speccing against details).

## Context Check

This workspace runs a spec-driven workflow: read the feature's architect spec (`docs/architect/`) and the active slice doc (`docs/slices/`) before starting. CLAUDE.md and LOCAL.md are auto-loaded. Skills advise, specs decide.

---

## Observability first: see what happened before optimizing

### Rewind Debugger (the animation time machine)

Enable the **Animation Insights** plugin → `Tools → Debug → Rewind Debugger` (+ `Rewind Debugger Details`). Record gameplay, pause, eject, scrub:

- Timeline tracks per object: ABPs, sequence playback, variables, notifies, montage state, blend weights.
- Double-click an ABP track → the Blueprint editor opens **synchronized to the recording**: node activity, variable values, state-machine position at the scrubbed frame.
- **Pose Watch**: inspect any node's effect on the output pose over the recording.
- Motion-matching users get the Selection Table here (see `ue-motion-matching`).

This replaces guesswork about "why did it blend/flicker/not fire" — record the repro once, scrub to the frame. It also replaces most uses of `showdebug animation`.

### Animation Insights / Unreal Insights

Plugins: Animation Insights + Insights Data Source Filters + Trace Data Filtering → `Tools → Profile`. Records `.utrace` (poses, curves, blend weights, montages, notifies, graph timing + CPU/GPU/frame tracks). Filter **what** (Trace Data Filtering preset "Animation") and **who** (Trace Source Filtering: class/world filters) — traces get big fast; don't leave tracing on. Open traces in Unreal Insights for the full timeline.

Quick console-level checks before reaching for traces: `stat anim` (UpdateAnimation/EvalAnim costs, counts), `stat skeletalmesh`.

## The standing cost levers (any character count)

1. **Threading & fast path** — the biggest structural win. AnimGraph evaluates on worker threads *if you let it*: EventGraph logic → `Blueprint Thread Safe Update Animation` / Property Access; enable **Warn About Blueprint Usage** on the ABP to catch fast-path regressions (lightning-bolt icons on nodes). Details in `ue-animation-system`.
2. **Visibility-based ticking** — `VisibilityBasedAnimTickOption` per mesh component: default only ticks bones when rendered; `Always Tick Pose and Refresh Bones` is the *expensive* end, needed only when something reads the pose while hidden (e.g. runtime retarget sources — see `ue-character-rigging-retargeting`).
3. **URO (Update Rate Optimizations)** — `bEnableUpdateRateOptimizations` on the skeletal mesh component: distance/size-based tick-rate throttling with optional interpolation. Epic's guidance: aim for update rates of 15 Hz and under at appropriate distances for most characters. Cheap, ships everywhere; superseded by the Budget Allocator when you adopt that (registering with the budgeter disables URO).
4. **Component Use Fixed Skel Bounds** — skip per-frame bounds recalc for culling; right for characters whose animation never leaves an approximate box.
5. **LOD thresholds on AnimGraph nodes** — expensive nodes (IK, warping, physics nodes) expose `LOD Threshold`; stop evaluating them past the LOD where nobody can see the difference.
6. **Non-Blueprint notifies** — native notifies over Blueprint ones on hot paths.

## Compression (memory + cook size)

Two settings-asset types (Content Browser → Animation → Advanced): **Bone Compression Settings** (a codec *list*; engine tries each, error threshold default 0.1; `Force Below Threshold` trades size for accuracy) and **Curve Compression Settings** (single codec; Max Curve Error; sample-rate options).

- Defaults live in `Engine/Content/Animation`; per-sequence assignment in Asset Details → Compression; the toolbar `Compress` button re-applies to all users of the settings asset.
- Recompression triggers automatically on settings change and at cook.
- **A gotcha worth knowing up front:** curves that must be *indexed at runtime* (distance matching) need Codec = **Uniform Indexable** — the default curve codec silently breaks `Distance Match to Target` (full setup in `ue-anim-warping-locomotion`).
- High-motion animations degrade visibly under aggressive bone compression; spot-check pivots and fast swings after changing thresholds.

## Crowd tools ⚠ *doc-verified, not exercised in this workspace*

### Animation Budget Allocator (dynamic per-frame budget)

Plugin; swap mesh components to **`SkeletalMeshComponentBudgeted`** (`SetDefaultSubobjectClass<USkeletalMeshComponentBudgeted>()` in the constructor), enable `Auto Calculate Significance` + `Auto Register with Budget Allocator`, call `Enable Animation Budget` once. The budgeter owns ticking from then on (default tick disabled, URO disabled, parallel tasks re-routed) and keeps skeletal work under a fixed ms budget by stopping/slowing/interpolating ticks by significance.

Key cvars: `a.Budget.Enabled`, `a.Budget.BudgetMs` (default 1.0), `a.Budget.MaxTickRate` (default 10), `a.Budget.InterpolationMaxRate`, `a.Budget.Debug.Enabled` (graph overlay); per-platform via `DefaultScalability.ini` `[ViewDistanceQuality@N] a.Budget.BudgetMs=...`. Stats: `Stat AnimationBudgetAllocator`; per-mesh overlay shows Hi/Lo/I (interpolating).

### Animation Sharing plugin (one evaluation, N characters)

For crowds of same-skeleton characters in coarse states: an `AnimationSharingManager` + Setup asset defines states (enum) and per-state animations; a **State Processor** (implement in C++ — Blueprint versions cost more) maps each actor to a state; actors become Leader-Pose followers of per-state master components, with playback-offset randomization for variety. Blend transitions cost per-instance — cap concurrent blends. Additive overlays need extra setup. Pair with the Significance Manager to cull distant tick work.

**When NOT to bother:** any character needing individual animation logic. The crossover is crowds (dozens+) doing shared, coarse-grained things.

## Diagnosis playbook

| Symptom | First move |
|---|---|
| Game thread bound, `stat anim` high | Warn About Blueprint Usage → fast-path the graph; move EventGraph to thread-safe update |
| Many characters, cost scales linearly | URO first; Budget Allocator when URO isn't enough; Animation Sharing if states are coarse |
| Hitch when characters enter view | `VisibilityBasedAnimTickOption` + bounds settings; pre-stream animations |
| "Why did it play/blend X?" | Rewind Debugger recording, scrub, open the ABP synchronized |
| Notify fired twice / never | Rewind Debugger notify track (and see inertialization's notify rule in `ue-animation-system`) |
| Animation memory / cook size ballooning | Bone-compression codec list + error threshold audit; check unreferenced curves |
| Distance matching broken after compression pass | Uniform Indexable on those sequences (`ue-anim-warping-locomotion`) |

## Related Skills

- `ue-animation-system` — thread-safe update, Property Access, the fast-path rules this skill audits.
- `ue-motion-matching` — MM-specific debugging (selection table) and database memory tuning.
- `ue-testing-debugging` — general profiling (Unreal Insights, stat commands, automation).
- `ue-character-rigging-retargeting` — leader-pose modular characters (the mechanism Animation Sharing builds on).

## Reference Files

- `../../docs/game-animation-sample-analysis.md` (repo docs) — the sample's density-tier databases: a worked example of data-side LOD.
