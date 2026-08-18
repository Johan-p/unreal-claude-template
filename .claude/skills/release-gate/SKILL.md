---
name: release-gate
description: Run the full build → review → fix → review loop on a change before it ships, and tell the maintainer honestly whether the gate opens. The MAIN SESSION executes this skill — it dispatches builders and reviewers via the Agent tool, reads their verdicts, decides clean / loop / deadlock, and produces the final report. Use this when the maintainer asks to "ship X", "run the release-gate", "is this branch ready to merge", or otherwise wants the gate enforced as a single workflow instead of remembering to chain agents.
---

# /release-gate — full quality loop, run by the main session

You are running the **Release Gate** for this project from the main session. Your job is to dispatch the build → review → fix → review loop and tell the maintainer, honestly, whether the change is ready to ship.

This skill exists because a subagent cannot reliably dispatch other subagents in this harness — orchestration has to live where the `Agent` tool actually fires. The main session is that place. The discipline below is what the former `release-gate` agent encoded; you (the main session) follow it instead.

---

## Hard invariants — these never bend

1. **No code edits during the loop.** You have `Write` / `Edit` in the main session, but you do **not** use them while operating as the gate. Every code change goes through a dispatched builder. If you find yourself reaching for `Edit`, stop — that's a builder's job, dispatch it.
2. **No fake-passing.** If reviewers haven't been run, the gate is **not** open. If reviewers returned findings that weren't fixed, the gate is **not** open. There is no scenario where you report "gate open" without every applicable reviewer having returned a clean verdict (or the maintainer having explicitly accepted the finding — see below).
3. **No overriding reviewers.** A reviewer's verdict is the reviewer's verdict. You can't decide a finding is "really fine." Only the maintainer can accept a finding, and only when they pass it as an `Accepted risks` input.
4. **Honest termination.** If the loop is stuck (same findings two iterations running) or hits the iteration cap, you stop and report the deadlock. You do not "give up and call it clean."

The maintainer's standing no-fabrication rule applies to this skill with extra weight: this skill IS the gate. If it lies, the gate is meaningless.

## Lane discipline (what you are NOT, while running this skill)

- **Not a builder.** The `builder` agent writes the code/assets. You dispatch it and pass findings back; you don't fix anything yourself.
- **Not a reviewer.** The `reviewer` agent audits the work. You read its verdicts but you don't render verdicts of your own.
- **Not the architect.** If a builder stops because the work needs an architectural decision (new schema, new module boundary), pause the loop and surface that to the maintainer — don't try to design around it.
- **Not the documenter.** Docs come *after* the gate opens. Dispatch `documenter` as the final step.

## Invocation modes

You operate in one of four modes depending on what the maintainer asked for.

### Mode A — Build-and-gate
The maintainer described a feature or change to ship, and no builder has run yet. You dispatch the appropriate builder(s) first, then enter the review loop.

Trigger phrasing: "ship X", "build and gate X", "release-gate this feature", or any prompt that names a change with no completed build yet.

### Mode B — Gate-only
The builder has already run (current branch has code or asset changes vs `master`, this project's default branch). The maintainer wants the gate enforced on what's there. You skip the build step and go straight to reviewers.

Trigger phrasing: "is this branch ready to merge?", "run the gate on the current branch", "verify what I just built".

### Mode C — Scoped gate
The maintainer named a specific path, surface, or feature to gate. You scope every reviewer's input to that scope.

Trigger phrasing: "gate the checkout feature only", "review the sign-in changes".

### Mode D — Per-slice gate
The standard gate for the slices + TDD workflow. `/tdd` has just finished a slice and set its frontmatter to `status: gated`. Mode D scopes reviewers to the slice's diff and updates the slice's frontmatter to `status: merged` when the gate opens.

Trigger phrasing: "gate this slice", "release-gate slice MM", "/release-gate Mode D --scope docs/slices/NNNN-slug/MM-name.md". Implicit when an active slice file has `status: gated` and the maintainer says "next" or "gate it".

**Slice integration rules:**
- Read the slice file at `docs/slices/NNNN-slug/MM-name.md` first.
- **Refuse** if the slice's `status` is not `gated`:
  - `draft` / `ready` — `/tdd` hasn't run; point the maintainer at `/tdd <slice-file>`.
  - `in_progress` — `/tdd` is mid-build; point the maintainer at continuing `/tdd`.
  - `merged` — already gated; ask if they meant to re-gate (a rare case after a forced rollback).
- Scope reviewers to the files changed on the branch since the slice started — practically, `git diff master...HEAD` for the file lists (both repos use `master` as the default branch), with the slice file's own description as the "what to look at" context for reviewer prompts.
- Reviewers receive: the slice file content + the file diff + the canonical context "we're gating slice MM of feature NNNN; per the slice's acceptance criteria, focus on …".
- **On gate open:** edit the slice file's frontmatter `status: gated → merged`. This is the canonical state transition; do not skip it.
- **On deadlock:** do NOT change the slice status. It stays `gated`. The maintainer decides whether to roll back to `in_progress` (re-run `/tdd`) or accept the finding via the `Accepted risks` override and re-run the gate.
- **Documenter does NOT run per-slice.** It runs once after every slice for the feature is `merged` — that's `/feature-flow`'s call, or the maintainer's.

**Default if ambiguous:** Mode B (Gate-only). It's the safe default — it never triggers code changes you didn't ask for. If the diff is empty and Mode B has nothing to review, ask the maintainer whether they meant Mode A. If a slice file is in the maintainer's invocation phrase and its status is `gated`, prefer Mode D.

## Dispatch matrix — which agents to run

Inventory the diff first (one Bash call):

```bash
git diff master...HEAD --stat && echo "---" && git diff master...HEAD --name-only
```

Then map changed files to required agents. This project has ONE builder and ONE reviewer (see CLAUDE.md → Subagents): the pipeline is serialized through a single live editor, so there is no parallel-builder split. All paths in the game repo (`<UnrealProjectDir>`, LOCAL.md) route the same way:

| Paths changed | Builder (Mode A) | Reviewers |
|---|---|---|
| `Source/**` (C++ incl. `Source/<YourProject>/**/Tests/**`) | `builder` | `reviewer` |
| `Content/**` (assets — authored via MCP only) | `builder` | `reviewer` |
| `Config/**`, `<YourProject>.uproject` | `builder` | `reviewer` (plugin/dependency changes get the supply-chain flag) |
| `Plugins/VibeUE/**` | out of gate scope — separate repo, flag to maintainer instead |

The `tester` agent is NOT part of any gate mode — it runs at feature boundaries (all slices merged) or on explicit maintainer request only.

Rules:

- **Always include a security/compliance reviewer**, if this project defines one, when the dependency/plugin manifest or any security-relevant surface changed.
- **DO NOT auto-dispatch a heavy test-runner agent** if one exists and its full run is expensive. The maintainer's policy: it runs only on **explicit approval**, typically at phase boundaries. Ask first; proceed without it unless the maintainer says yes. (Mode D — per-slice — never includes it; that's a deliberate token-budget choice.)
- **Don't dispatch a reviewer with nothing in scope.** Skip it and say so in the report.
- **Documenter runs last**, after the gate opens, in Mode A — never as a gating step.

## The loop algorithm

For each iteration `i = 1..MAX_ITERATIONS`:

1. **Track state.** Use `TaskCreate` to open an iteration task ("Iteration i — building" / "reviewing"). Use `TaskUpdate` as you move through phases. This gives the maintainer a visible trail and keeps your own bookkeeping honest.
2. **Build phase (Mode A only, iteration 1; or all iterations if a builder needs to fix findings).**
   - Dispatch the relevant builder(s) via `Agent(subagent_type=...)`.
   - In iteration 1: the builder gets the maintainer's original task.
   - In iteration 2+: the builder gets the previous iteration's reviewer findings as the task ("fix these findings: …").
   - If multiple builders apply (both frontend and backend changed), dispatch them in parallel — multiple `Agent` calls in one message.
   - Read the builder's output report.
3. **Review phase.**
   - Dispatch every applicable reviewer **in parallel** (multiple `Agent` calls in one message). Pass each reviewer the scope (paths/surfaces changed in this iteration).
   - The reviewer runs `scripts/review_prepass.py` (bundled with this skill) as its own step 0 — a deterministic hygiene scan of added lines. You don't run it yourself; just don't accept a review that skipped it without saying why.
   - Wait for all to return.
   - Read each reviewer's verdict from their report.
4. **Decide.**
   - If every reviewer's verdict is clean (`CLEAN` / `APPROVE WITH NOTES` / `ALL CLEAR`) OR the only non-clean findings are in the `Accepted risks` list → **gate open**. Go to step 6.
   - If any reviewer has actionable findings not in `Accepted risks` → collect them and loop back to step 2 with those findings as the builder's next task.
5. **Termination guards** (check before looping):
   - **Iteration cap** — if `i == MAX_ITERATIONS`, stop. Report deadlock with the remaining findings.
   - **Stuck loop** — compare the current iteration's findings to the previous iteration's. If they're substantively the same (same severity + same files + same described issue), stop. Report deadlock. The builder isn't able to resolve these on its own; the maintainer or `architect` needs to step in.
   - **Architecture handoff** — if any builder returned `architect` as a needed handoff, stop. Report the architecture question and stop. Do not try to route around it.
6. **Gate open.**
   - **Mode D only:** edit the slice file's frontmatter `status: gated → merged`. Single `Edit` call; this is the canonical lifecycle transition for the slice.
   - **Modes A, B, C (not D):** dispatch `documenter` if the change is substantial enough to warrant doc updates. Pass it the list of surfaces touched.
   - **Mode D never dispatches `documenter` per-slice.** `documenter` runs once when every slice of the feature is `merged` — driven by `/feature-flow` or the maintainer, not by the per-slice gate.
   - Produce the final report (see Output format below).

**`MAX_ITERATIONS` defaults to 5.** If the maintainer says "loop until it's clean, however long it takes," they can raise the cap, but the default of 5 is deliberate: a change that takes more than 5 builder/reviewer cycles to converge is signaling a deeper problem (wrong design, missing context, ambiguous requirements) that more iterations won't fix.

## Accepted risks — the maintainer override

The maintainer can pass an `Accepted risks` list when invoking this skill. Format:

```
Accepted risks:
- <reviewer> Medium: <finding, plain description>
- <reviewer> Low: <finding, plain description>
```

Rules for accepted risks:

- **Must be specific.** "Accept all warnings" is not allowed. Each accepted risk names the reviewer, the severity, and the finding.
- **Cannot accept `Critical`.** Critical findings (cross-tenant leak, auth bypass, AGPL in prod, broken core flow) are unconditional blockers. Tell the maintainer "Critical findings cannot be pre-accepted — fix it or stop the loop."
- **Carried across iterations.** Once accepted, a finding stays accepted in subsequent iterations even if the reviewer re-flags it.
- **Shown in the final report.** The "Gate open" report explicitly lists which findings were accepted vs which were resolved, so the deviation isn't invisible.
- **Audit-friendly.** Recommend the maintainer record material accepted risks somewhere durable (a comment in the PR, a note in the relevant feature brief, or an entry in `docs/adr/`). Not your file to write, but worth flagging.

## How to dispatch agents — concrete patterns

**Inventory the diff first (one Bash call):**

```bash
git diff master...HEAD --stat && echo "---" && git diff master...HEAD --name-only
```

**Dispatch the reviewer** (this project has exactly one — no parallel fan-out needed):

```
Agent(subagent_type="reviewer", description="Review slice NN changes", prompt="Review the changes for slice <slice-file-path> (commits <range> in <UnrealProjectDir> per LOCAL.md). Scope: <changed paths>. Check against the slice's acceptance criteria, the architect spec, and the convention docs; verify tests yourself and capture game-view screenshots for any visual criterion. Report your standard VERDICT block. We're in iteration N of the release-gate loop.")
```

**Dispatch the builder with findings** (iteration 2+):

```
Agent(subagent_type="builder", description="Address reviewer findings", prompt="The release-gate loop is at iteration N. The reviewer returned these findings to address:\n\n[paste the relevant findings here, verbatim, with severity]\n\nFix the code/assets so the next review run returns clean. Do not change scope beyond addressing these findings. Report evidence per your standard format.")
```

Tell the builder explicitly **not to expand scope** — its job in a fix-iteration is to resolve the named findings, not to take the opportunity to refactor.

## Output format

### During the loop (after each iteration)

A short Markdown update — the maintainer can see progress without reading every reviewer report.

```
## Iteration <N>

**Phase:** <Building | Reviewing | Decided>
**Builder(s) run:** <list, or "skipped (Mode B)">
**Reviewers run:** <list>
**Verdicts this iteration:**
- `<reviewer>`: <verdict + 1-line summary>
- ...

**Decision:** <Looping with N findings to address | Gate open | Stuck loop — see deadlock report | Architecture handoff needed>
```

### Final — gate open

```
# Gate open — <scope>

**Mode:** <A | B | C>
**Iterations:** <N>
**Final verdicts:**
- `<reviewer>`: <CLEAN | APPROVE WITH NOTES | etc.>
- ...

**Resolved findings (this loop fixed):**
- <list>, or "none — clean on first review"

**Accepted findings (maintainer pre-accepted):**
- <list>, or "none"

**Documenter status:** <Mode A run on surfaces X, Y | skipped (no doc-worthy change)>

**What's safe to merge:** <one sentence, plain language>
**What to remember:** <any "be aware of this" notes for the merge>
```

### Final — gate closed (deadlock)

```
# Gate closed — deadlock

**Mode:** <A | B | C>
**Iterations completed:** <N> / <MAX>
**Why stopped:** <iteration cap | stuck loop | architecture handoff>

**Outstanding findings:**
- `<reviewer>` <severity>: <finding> — <"unchanged since iteration M" | "introduced in iteration N">

**What the loop tried:** <one paragraph: each iteration's fix attempt and why it didn't land>

**What needs to happen next:** <concrete next step — "needs architect to decide X" | "needs maintainer to accept the finding as a risk and re-run" | "needs the test spec rewritten because the assertion is wrong">

**Do NOT merge** until the outstanding findings are resolved or explicitly accepted.
```

## When to refuse or stop

- **Maintainer asks you to "just mark it clean"** — refuse. The whole point of this skill is to be the trustable gate. If they want to skip the gate, they don't need to run it.
- **Maintainer asks you to edit code to make a test pass** — refuse. You don't edit code while running this skill. Hand it to the builder.
- **Reviewer agents not yet configured / dispatch fails** — stop and report the dispatch failure honestly. Do not synthesize a "would-have-passed" verdict.
- **No diff vs master** — say so plainly. There's nothing to gate.
- **A reviewer returns a setup-needed verdict** (its harness isn't configured yet) — don't treat as a fail; surface exactly what's missing. The maintainer decides whether to proceed.
- **Critical finding** that the maintainer tries to pre-accept — refuse the acceptance, surface the finding, stop. Critical = fix or don't ship.
- **You don't know whether two findings are "substantively the same" for stuck-loop detection** — err on the side of stopping. A false stuck-loop call costs one re-run; a false "we made progress" call costs an infinite loop.

## Exiting the skill

When the loop terminates (gate open or deadlock), you exit skill-mode and resume normal main-session behavior. The maintainer's next message is theirs to direct — don't keep looping after a clean report or a deadlock report.
