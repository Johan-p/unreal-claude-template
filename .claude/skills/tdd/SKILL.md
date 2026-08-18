---
name: tdd
description: Run a per-slice test-driven build for one slice file under `docs/slices/`. Plans the test list from the slice's acceptance criteria, dispatches the relevant builder(s) with explicit red-green-refactor instructions, verifies tests run and pass, then hands off to /release-gate (Mode D). Wires this project's unit and end-to-end test runners per CLAUDE.md. Refuses to start a slice with unmerged `blocked_by` predecessors. Adapted from mattpocock/skills.
---

# /tdd — per-slice red-green-refactor

> ⚠️ **Before doing anything, check the main session's model.** `/tdd` is orchestration work — planning a test list, dispatching builders, verifying via Bash, looping. It does **not** need Opus reasoning. If the main session is running on Opus, recommend the maintainer switch to Sonnet first:
>
> *"This session is on Opus. `/tdd` orchestration runs well on Sonnet at ~⅓ the cost. Switch via `/model sonnet`, then re-invoke `/tdd <slice-file>`. Switch back to Opus afterward for `/brainstorm`, `architect`, or `/improve-codebase-architecture` work."*
>
> Don't refuse — the maintainer can decline. But raise it once, at the top, before any other work. It's the largest avoidable token cost across a multi-slice feature.

This skill takes **one slice file** and drives it through TDD to "gated" status. Pocock's claim: *"Doing really good TDD has been the most consistent way to improve agent outputs."* The discipline below is what makes that true — without it, "TDD" collapses into "write tests after the code, post-hoc."

## Hard preconditions

Refuse to run if:

- No slice file path is provided. Ask: *"Which slice? Path or `feature/slice` shorthand."*
- The slice file's `status: blocked_by` lists a slice that isn't `merged`. Surface the blocker and stop.
- The slice file's `status` is already `merged` or `gated`. Don't re-run completed slices.
- The slice's architect spec section is unreachable (broken link, missing section). Fix the slice file or escalate to the architect.

If a precondition fails, **say so plainly and stop**. Do not start building against a slice you can't read end-to-end.

The whole `ue-*` reference roster is installed, so there is no pre-flight install step — the builder loads whichever skills its domain triggers. Skills advise the builder; the architect spec wins on conflict.

## Core discipline — what makes this TDD and not "tests later"

**Tests verify behaviour through the public interface, not implementation details.** A good test reads like a specification — *"user can checkout with valid cart"*. It survives refactors. A test that breaks when you rename an internal function is testing implementation, not behaviour.

**Anti-pattern: horizontal slicing.** Do NOT write all tests first, then all implementation. That produces tests of *imagined* behaviour, not *actual* behaviour — tests that pass when behaviour breaks and fail when behaviour is fine. The corruption is invisible at write time.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1 → impl1
  RED→GREEN: test2 → impl2
  RED→GREEN: test3 → impl3
```

**One test, one implementation, repeat.** Each test responds to what was learned from the previous. The builder you dispatch must understand this rule — it's stated in their brief.

**Never refactor while RED.** Get to GREEN first. Refactoring under a red test invites changing both behaviour and implementation at once, hiding regressions.

## Process

### 1. Plan the test list (without writing any test yet)

Read the slice file. Read the architect spec section it references. Read this project's domain/vocabulary reference (per CLAUDE.md) if one exists.

Then **list the tests** the slice's acceptance criteria imply. For each criterion, one or more tests; for each test, name:

- **The behaviour** in one sentence — readable as a `it('…', …)` description.
- **The surface** — per CLAUDE.md → Testing: UE C++ automation tests (`<UnrealProjectDir>\Source\<YourProject>\**\Tests\*.cpp`, run headless) for pure logic code; build + editor evidence (screenshots, live PIE state via MCP) for view actors, widgets, and assets, which have no unit surface.
- **The fixture** — pure logic (no DB), an in-process test database/tenancy-context helper if this project has one, or a browser-driven fixture.
- **The interface under test** — the function/component name and its signature shape.

**Show the test list to the maintainer.** This is the cheap checkpoint where domain knowledge re-orders the list ("we just deployed a change that breaks #3 — start there"). Don't block on a response longer than ~30s if the maintainer is AFK; proceed with your order.

**Interface-before-test.** If the slice introduces a new interface (a new library module, a new server action/handler), pin the interface shape with the maintainer before writing the first test — Pocock's "design the testable interface" step. Ask something like: *"For the deepened `<module>` module, recommended shape: `<fn>(<args>): Promise<Result>` where `Result` is `{ ok: true, <data> } | { ok: false, reason: '<code>' }`. Confirm?"*

The interface IS the test surface. If the interface is wrong, every test that follows is wrong.

### 2. Tracer bullet — the first test

Write **one** test that proves the path works end-to-end. Not the easiest test, not the most comprehensive — the test that proves the seam holds. Often the "happy path" assertion.

Dispatch the builder for this single test (and the minimal implementation to make it pass). This project has ONE builder — there is no parallel routing, because the pipeline is serialized through one live editor (C++ builds need it closed, asset work needs it open):

| Slice touches | Builder |
|---|---|
| Anything in `<UnrealProjectDir>` (LOCAL.md) — sim C++, framework/view C++, tests, Config, Content assets via MCP | `builder` (the only one) |
| `docs/**` in the scaffold repo | main session — never a builder dispatch |

Batching note: because each verify cycle costs an editor-close → build → headless-test round (~3–5 min), it is acceptable to group 2–3 tests of the SAME behaviour cluster into one dispatch/build cycle — writing each test-then-impl in order within it — rather than paying a full build per test. Keep the red-green ordering honest inside the batch and say in the iteration report that cycles were grouped.

The builder's brief MUST include:

- The single test to write first (its name, its shape, the assertion).
- The interface to implement (the signature, what's behind the seam).
- The discipline rule: *"This is iteration 1 of TDD on slice MM. Write the test, then the **minimal** implementation to make it pass. Don't anticipate later tests. Don't refactor while red. Return when the test is green."*
- The fixture conventions for this project (data-access tests use whatever test-database/tenancy-context helper exists; pure inputs for pure code; browser fixtures for UI).
- Latest stable for any new dep (per CLAUDE.md).

After the builder returns, **verify** by running the test yourself via Bash. Run the fast/unit suite unconditionally; for a slow browser/e2e suite, **ask the maintainer first** — that kind of suite is typically heavy on tokens/time and is often reserved for phase-boundary regression by maintainer policy.

Fast suite — run unconditionally (headless, editor may be open or closed; ~1–2 min boot): the exact command is in `LOCAL.md` → Verified commands. Narrow the filter per CLAUDE.md → Testing (e.g. `RunTests <YourProject>.<Area>`); pass = all `Result={Success}` + `EXIT CODE: 0`. The heavy equivalent here is a tester-agent smoke session — feature boundaries or explicit approval only.

For UI-touching slices, when the slice's acceptance criteria can only be verified through a browser, ask: *"Slice MM has a UI acceptance criterion that needs the e2e runner to verify. Run it once? Default no — that suite is reserved for phase boundaries."* If declined, mark the criterion as "verified at phase boundary" and proceed; do not silently skip it.

If green: proceed to step 3. If red: dispatch the builder again with the failure output, stating *"the previous iteration left this test red, fix the implementation — do not change the test unless the test is itself wrong"*.

### 3. Incremental loop — one test at a time

For each remaining test on the plan list:

```
RED:   builder writes next test → fails
GREEN: builder writes minimal code to pass → passes
```

Discipline rules to repeat in the builder's brief every iteration:

- One test at a time.
- Only enough code to pass the current test.
- Don't anticipate future tests.
- Don't refactor while red.
- Tests describe observable behaviour through the public interface.

After each iteration, verify by running the test. If the iteration's test passes AND the previously-green tests still pass, proceed. If a previously-green test broke, that's a regression — dispatch the builder with the regression as the next problem to solve.

**Maximum dispatches per slice: 12** (a tracer bullet + 10 tests + 1 stuck-recovery). If you hit 12 and the slice still isn't done, the slice is too big — surface this and ask the maintainer to split it via `/to-slices`.

### 4. Refactor pass (after all tests green)

When every test on the plan list is green AND every acceptance criterion in the slice file is observably satisfied, dispatch the builder one more time for a **refactor pass**:

- Extract duplication.
- Deepen modules (move complexity behind simple interfaces — see `/improve-codebase-architecture` glossary: depth, locality, leverage).
- Apply SOLID where natural — not religiously.
- Run tests after each refactor step.

The refactor must not change behaviour. Every test must stay green. If a refactor breaks a test, the refactor was wrong — revert that step.

### 5. Verify the slice is done

Final checks before handing off to `/release-gate`:

- [ ] Every acceptance criterion in the slice file is observably satisfied (verifiable by a test or a demo — or marked "verified at phase boundary" if the slow/e2e suite was declined for the slice).
- [ ] The headless automation run for the slice's test filter passes: every test reports `Result={Success}` and the run ends `EXIT CODE: 0` (command in CLAUDE.md → Testing).
- [ ] The C++ build succeeds (`Result: Succeeded`, exit 0) — in this project the build is also the type-check; there is no separate lint step.
- [ ] Any heavy verification (tester-agent smoke session, packaged-build check) runs **only if the maintainer explicitly approved it** for this slice — otherwise note "deferred to feature boundary" in the iteration report.

Update the slice file's frontmatter: `status: gated`. (Use `Edit` on the file; this is the only file under `docs/slices/` this skill writes.)

### 6. Hand off to release-gate

Close with:

> *Slice MM is built and verified. Status → `gated`. Next: `/release-gate Mode D` scoped to `docs/slices/NNNN-slug/MM-name.md` to dispatch this project's reviewer agent(s), once defined, against this slice's diff.*

If `/feature-flow` is installed, suggest it: *"or `/feature-flow next NNNN` to advance to the next ready slice once this gate opens."*

## Output

Per iteration (compact, so the maintainer can see progress without reading every builder report):

```
## Iteration <N> — <test description>

**Surface:** <unit | integration/data-access | e2e>
**Builder:** <this project's builder agent(s) that ran>
**Test added:** `<file>:<line>` — `<test name>`
**Verdict:** RED → GREEN | RED → still RED (re-dispatching) | GREEN → broke prior test (regression)
```

Final report:

```
# Slice <MM> — <title> — gated

**Tests written:** <N> in <files>
**Iterations:** <N>
**Acceptance criteria covered:** <list>
**Refactor pass:** <yes/no>

**Status updated:** `ready` → `gated`
**Next:** /release-gate Mode D --scope <slice-file-path>
```

## When to stop and escalate

- **Slice criteria reveal an architecture question** — pause, hand to `architect`, do not improvise.
- **Stuck on the same test for 3 iterations** — the test or the interface is wrong. Stop and surface; the maintainer (or `/brainstorm`) decides.
- **A "passing" test fails when you run it manually** — fabrication risk. Re-verify. If still inconsistent, report honestly: *"the builder claims green; my verification run shows red. Investigating."*
- **A criterion can't be expressed as a test** — that's a sign the criterion isn't observable enough. Sharpen the criterion in the slice file (or escalate to `/to-slices` for a re-slice). Don't ship a "tested" slice that misses a real DoD bullet.

## What this skill does NOT do

- **Does not write code itself.** Every code change is a builder dispatch. The `/tdd` skill plans, dispatches, and verifies.
- **Does not edit the brief, the architect spec, or other slice files.** Only the current slice's `status` frontmatter, only to advance it to `gated`.
- **Does not run `/release-gate`.** Hands off explicitly.
- **Does not change test-runner config.** Test infra is spec-level (see the relevant architect spec if one exists, or CLAUDE.md's testing section).
- **Does not skip the maintainer's interface-shape check** when a new module is introduced. That's the load-bearing input.
- **Does not commit.** The slice's commit is the maintainer's call after `/release-gate` opens.
