---
name: diagnose
description: Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use when a bug is reported, something is broken/throwing/failing/slow, or a previously-working flow regressed. Anchor to this project's actual test surfaces, documented in CLAUDE.md. Adapted from mattpocock/skills.
---

# /diagnose — disciplined bug diagnosis

A discipline for **hard bugs and performance regressions** — bugs where the cause isn't obvious from reading the code and the fix isn't a 1-line patch.

For trivially obvious bugs (typo in a string, missing await, undefined variable), skip this skill and fix directly. For bugs where you've already burned 15 minutes guessing, **stop guessing and run this**.

The maintainer's no-fabrication rule applies with extra weight: if you can't reproduce, say so; do not synthesize a fix for a bug you haven't seen fire.

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. With a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause — bisection, hypothesis-testing, and instrumentation all just consume that signal. Without one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — try them in roughly this order

1. **A failing test at whatever seam reaches the bug.** This project: UE C++ automation tests (`IMPLEMENT_SIMPLE_AUTOMATION_TEST`, names `<YourProject>.<Area>.<Behaviour>`) run headless via `UnrealEditor-Cmd.exe` — exact command and pass/fail signals in CLAUDE.md → Testing. That's the seam for anything in the sim layer. For user-facing flows there is no e2e framework — the equivalent is a live PIE session driven over MCP; **read `docs/live-testing-playbook.md` before building that kind of loop** (it records which observation methods are confirmed dead ends).
2. **Curl / HTTP script** against a running dev server. Useful when the bug is on a server action or route handler and a full browser-driven e2e run's overhead is wasteful.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot. Good for pure-logic regressions in isolated modules (here: whichever pure-logic layer CLAUDE.md designates under `<UnrealProjectDir>\Source\<YourProject>\` — a narrow automation-test filter is this project's version of that loop).
4. **Headless e2e script** asserting on DOM/console/network. Useful when the bug is a UI race or a missing-translation/config-key miss.
5. **Replay a captured trace.** Save a real HAR / payload / event log to disk; replay through the code path in isolation.
6. **Throwaway harness** — a minimal script that imports the suspect module plus a lightweight/in-memory test fixture (whatever this project's test DB or fixture strategy is) and exercises the bug path with a single function call. Fast.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode. For numeric conversions, permutation-heavy business rules, state-machine transitions — fuzzing finds what enumeration misses.
8. **Bisection.** If the bug appeared between two known states (a commit, a dataset migration), `git bisect run` it against a unit test or an e2e test — both are agent-runnable.
9. **Differential loop.** Same input through old-version vs new-version (or against the deployed app) — diff outputs.
10. **HITL bash script** — last resort. If a human must click, document the steps; do not pretend you can verify without them.

Build the right feedback loop, and the bug is 90% fixed.

### Iterate on the loop itself

Treat the loop as a product. Once you have *a* loop, ask:

- Can I make it faster? Cache fixture setup; skip unrelated init; narrow the scope to the suspect module.
- Can I make the signal sharper? Assert on the specific symptom, not "didn't crash."
- Can I make it more deterministic? Pin time, seed RNG, isolate the test database/fixture instance per case, freeze network calls.

A 30-second flaky loop is barely better than no loop. A 2-second deterministic loop is a debugging superpower. A fast in-process test runner paired with a lightweight or in-memory data layer gives you that for most backend bugs, if this project has one — lean on it.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; a 1%-flake bug is not — keep raising the rate until it is.

In this project, non-determinism usually comes from frame timing and physics tick order in PIE — overlap/hit events whose outcome depends on which actor ticks first, or editor-side quirks like `set_actor_location` intermittently no-oping on a possessed `ACharacter` (see the playbook). Loop the scenario across many PIE runs or many simulated frames, log per-tick state, and raise the reproduction rate before hypothesising.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the maintainer for: (a) access to whatever environment reproduces it, (b) a captured artifact (HAR, log dump, screen recording with timestamps), or (c) permission to add temporary production instrumentation. **Do not proceed to hypothesise without a loop.** That's the failure mode this skill exists to prevent.

## Phase 2 — Reproduce

Run the loop. Watch the bug appear.

Confirm:

- [ ] The loop produces the failure mode the **maintainer** described — not a different failure that happens to be nearby. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, reproducible at a high enough rate to debug against).
- [ ] You have captured the exact symptom (error message, wrong output, slow timing) so later phases can verify the fix actually addresses it.

Do not proceed until you reproduce.

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: *"If `<X>` is the cause, then `<changing Y>` will make the bug disappear / `<changing Z>` will make it worse."*

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

Common hypothesis families for this project (UE 5.8 C++; verified traps live in CLAUDE.md and `docs/live-testing-playbook.md`):

- **Collision channel response missing on one side.** Symptom: two things pass through each other, or a hit/overlap event never fires. Prediction: set the response explicitly on BOTH sides of the pair and the bug disappears — a new custom channel is NOT auto-blocked by stock profiles like Pawn (verified trap).
- **Stale binary / Live Coding drift.** Symptom: a C++ change appears to have no effect in the editor. Prediction: close the editor, full rebuild, relaunch — behaviour changes. (Live Coding blocks UBT; an open editor can run old code.)
- **Asset defaults vs C++ defaults.** Symptom: a recompiled C++ default doesn't show up in game. Prediction: the Blueprint/asset overrides the property — inspect the asset via MCP; resetting the override fixes it.
- **Tick/physics ordering race.** Symptom: intermittent overlap/hit outcomes, actors "sometimes" mispositioned. Prediction: forcing an ordering (tick group, dependency) collapses the flake rate.
- **Property reads lie about visual state.** Symptom: every state check passes but the screen is wrong (direction, facing, camera). Prediction: a screenshot shows the defect a property read can't — orientation bugs need a visual criterion (verified project lesson).
- **Editor-vs-headless divergence.** Symptom: a test behaves differently under `-nullrhi` than in the editor. Prediction: the code path depends on rendering/init that headless runs skip; also remember the two known startup `Condition failed` noise lines are NOT test failures (see CLAUDE.md → Testing).

**Show the ranked list to the maintainer before testing.** They often have domain knowledge that re-ranks instantly ("we just changed the auth webhook"), or know hypotheses they've already ruled out. Cheap checkpoint, big time saver. Don't block on it — proceed with your ranking if the maintainer is AFK.

## Phase 4 — Instrument

Each probe maps to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:

1. **Inspecting via a one-off automation test** — write a UE automation test that exercises the suspect path; the assertion expresses the prediction. Reusable, fast, deterministic. The best tool for pure-logic bugs.
2. **`UE_LOG` at the boundaries that distinguish hypotheses** — tag every debug log: `UE_LOG(LogTemp, Warning, TEXT("[DEBUG-a4f2] ..."))`. Cleanup at the end becomes one grep.
3. **Live PIE inspection over MCP** — get the live game world and read actor/component properties per `docs/live-testing-playbook.md` (it names which world-access and `call_method` routes actually work). The live state is the truth when code-reading and logs disagree.
4. **Screenshots via the playbook's working method** — for anything visual/orientation-shaped, where property reads pass while the screen is wrong.
5. Never "log everything and grep."

**Tag every debug log.** Untagged logs survive; tagged logs die in a single `grep -rn '\[DEBUG-' <UnrealProjectDir>/Source | wc -l` confirmation that cleanup happened.

**Performance branch.** For perf regressions, logs are usually wrong. Instead: establish a baseline measurement (this project's benchmark mode if it has one, `performance.now()`, or a query plan from the DB layer's query log), then bisect. Measure first, fix second.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (a unit test that can't replicate the chain that triggered the bug), a regression test there gives false confidence.

The load-bearing seams in this project (see CLAUDE.md → Testing):

- **UE automation tests** for pure-logic code — fast, headless, deterministic. The default seam.
- **Automation tests that spawn a world/actors** for actor-level behaviour that doesn't need rendering.
- **No automated seam exists for visual/input-driven behaviour** — those criteria are verified by build + editor evidence (screenshots, PIE play-through) at the release gate. Synthetic keypresses often fail to reach a running Unreal session (confirm on your machine before relying on them); where they don't land, input-gated repros need a human playtest. If the bug lives there, the regression "test" is a gate criterion plus a playbook note, and that's the honest answer.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down — flag it for `/improve-codebase-architecture`.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail (RED).
3. Dispatch the builder with the fix (one test → one fix, per `/tdd` discipline).
4. Watch the test pass (GREEN).
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

## Phase 6 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop).
- [ ] Regression test passes (or absence of seam is documented and flagged).
- [ ] All `[DEBUG-…]` instrumentation removed (`grep -rn '\[DEBUG-' <UnrealProjectDir>/Source` returns nothing).
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location, never under the real source tree).
- [ ] The hypothesis that turned out correct is stated in the commit / PR message — so the next debugger learns.

**Then ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling, missing tenant scoping, racy lock ordering) hand off to `/improve-codebase-architecture` with the specifics. Make the recommendation **after** the fix is in, not before — you have more information now than when you started.

If the answer involves an ADR-worthy decision (the bug surfaced an undocumented invariant that future code shouldn't violate), recommend the `architect` agent draft an ADR under `docs/adr/`.

## Phase boundary check

A diagnosed bug should also surface:

- **Does the bug exist in the shipped package?** If yes, the fix isn't done until the package is rebuilt (clean `Packaged/StagedBuilds` first) and smoke-tested — a source-only fix that never re-ships is an open bug.
- **Did a verification method lie?** If the bug survived because a check gave a confidently-wrong signal (a property read that missed a visual defect, an observation route the playbook warns about), add the lesson to `docs/live-testing-playbook.md` in the same change.
- **New engine trap?** If the root cause is a non-obvious UE behaviour, add it to CLAUDE.md's verified-traps material so the next builder doesn't rediscover it.

## Output

For the maintainer, after each phase, a compact update:

```
## Phase <N> — <name>

**State:** <building loop | reproduced | hypotheses ranked | instrumented | fix applied | done>
**Loop:** <command + duration + signal sharpness>
**Top hypothesis:** <description + prediction>
**Status:** <on track | stuck — see below>
```

Final report:

```
# Diagnosis — <bug description>

**Reproduction:** <how, where, how reliably>
**Root cause:** <one sentence>
**Hypothesis history:** <ranked list, which one was correct, why others were wrong>
**Fix:** <what changed, file + line>
**Regression test:** <path, what it asserts, or "no correct seam — flagged">
**Cleanup:** [<x>] debug logs removed, [<x>] throwaway code deleted
**Prevention recommendation:** <none | /improve-codebase-architecture for <X> | ADR for <Y>>
```

## What this skill does NOT do

- **Does not skip to the fix.** No fixing without a reproducible loop.
- **Does not fabricate a test result.** If a test passes inconsistently, that IS the report; do not paper over it.
- **Does not write code itself.** Fixes are dispatched to this project's relevant builder agent, once defined — `/diagnose` is the orchestrator.
- **Does not commit.** The fix's commit is the maintainer's call.
- **Does not edit test-infrastructure config** (e.g. `*.Build.cs`, `*.Target.cs`, `Config/*.ini` test-relevant settings). Test infrastructure changes are spec-level.
- **Does not edit `docs/architect/` or `docs/adr/`.** Recommendations go to the appropriate agent.
