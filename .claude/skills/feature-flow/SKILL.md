---
name: feature-flow
description: Orchestrate the full feature lifecycle (grill → brief → spec → slice → tdd → gate → ship) for one feature in this project. Reads state from the feature brief, architect spec, and slice files; tells the maintainer what's next; refuses invalid transitions. Dispatches the next step on request. Invoke without args to survey all in-flight features; with NNNN to drill into one. Pure orchestrator — does not write code. Adapt the lifecycle stages and doc paths below to whatever this project actually uses.
---

# /feature-flow — feature-lifecycle orchestrator

The state machine over `docs/features/`, `docs/architect/`, `docs/slices/`, and the working tree. Knows where you are in any feature's lifecycle, what's blocking the next step, and what to invoke to advance. **Default mode is *advisory*: it tells you what to do, you decide.** With `--auto` it dispatches the next step itself.

This skill is the "Layer 2" enforcement of the workflow restructure: each individual skill names its next step ("Layer 1"), and `/feature-flow` provides the state-machine view across the whole lifecycle so nothing is forgotten or done out of order.

## The lifecycle this skill enforces

```
       ┌──────────────────────────────────────────────────────────────┐
       │                                                              │
       │   /brainstorm     →  shared understanding of the idea           │
       │                                                              │
       │   /feature      →  docs/features/NNNN-slug.md  [Status:Draft] │
       │                          ↓ maintainer marks Ready             │
       │                                                              │
       │   architect     →  docs/architect/NNNN-slug.md                │
       │                                                              │
       │   /to-slices    →  docs/slices/NNNN-slug/MM-name.md (×3-6)    │
       │                          ↓ maintainer (or skill) marks ready  │
       │                                                              │
       │   /tdd          →  per-slice TDD build  [status: in_progress] │
       │                                          [status: gated]      │
       │                                                              │
       │   /release-gate →  per-slice reviewer loop  [status: merged]  │
       │       Mode D                                                 │
       │                                                              │
       │   all merged    →  documenter agent  →  ship                  │
       │                                                              │
       └──────────────────────────────────────────────────────────────┘
```

## Invocation

```
/feature-flow                       # board view: all in-flight features
/feature-flow NNNN                  # detailed view for one feature
/feature-flow NNNN next             # what step to invoke next (default mode)
/feature-flow NNNN next --auto      # dispatch the next step automatically
/feature-flow NNNN status MM ready  # mark slice MM as ready (out of `draft`)
```

`NNNN` is the four-digit feature number. Slugs are inferred — if multiple features share a number prefix (they shouldn't, but defensive), error and ask.

## Process

### Reading state

State is read from files, never cached. Authoritative locations:

| Lifecycle stage | Read from |
|---|---|
| Brief existence | `docs/features/NNNN-slug.md` exists |
| Brief status | `**Status:** <Draft\|Ready\|Shipped>` line in the brief body |
| Architect spec existence | `docs/architect/NNNN-slug.md` exists |
| Slice plan existence | `docs/slices/NNNN-slug/` directory exists with ≥1 file |
| Per-slice status | YAML frontmatter `status:` field in each `docs/slices/NNNN-slug/MM-*.md` |
| Per-slice blockers | YAML frontmatter `blocked_by:` field |
| Per-slice type | YAML frontmatter `type:` field (`AFK` / `HITL`) |

A slice with `status: merged` but unmerged blockers is an inconsistency — flag it, do not silently advance.

### State machine — the full table

| Brief | Spec | Slices | Slice statuses | Next step the skill recommends |
|---|---|---|---|---|
| ✘ | ✘ | ✘ | — | **`/brainstorm` (if idea is fuzzy) then `/feature`** |
| Draft | ✘ | ✘ | — | Maintainer reviews + marks Ready |
| Ready | ✘ | ✘ | — | **`architect` agent** to produce the spec (only if the brief implies a load-bearing technical decision; small briefs ship directly without slicing) |
| Ready | ✓ | ✘ | — | **`/to-slices`** against the spec |
| Ready | ✓ | ✓ | all `draft` | Maintainer reviews + marks ready (or this skill with `status MM ready`) |
| Ready | ✓ | ✓ | ≥1 `ready` with no unmerged blockers | **`/tdd <first-ready-slice>`** — and recommend `/model sonnet` first |
| Ready | ✓ | ✓ | some `in_progress` | Continue `/tdd` on the in-progress slice; finish before starting another (Sonnet) |
| Ready | ✓ | ✓ | a slice is `gated` | **`/release-gate Mode D --scope <slice-file>`** |
| Ready | ✓ | ✓ | all `merged` | **`documenter` agent**, then maintainer marks brief `Shipped` |
| Shipped | ✓ | ✓ | all `merged` | Feature complete; recommend nothing |

### Special cases

- **Trivial feature (no architect spec, no slicing).** A brief whose `What` bullets are obviously implementable as one commit (e.g. a copy change, a one-file tweak, a renamed function) skips slicing. Detect by reading the brief's `Definition of Done` — if all bullets describe a single observable behaviour, recommend a direct dispatch to the relevant builder, then `/release-gate Mode B`. Do not force the slice ceremony.
- **Pure refactor / deepening.** The brief may not exist (refactors aren't user-facing features). The architect spec drives. Slices and `/tdd` still apply. Surface in the board view under a "refactors" section.
- **Cross-feature work.** Refuse to orchestrate. Cross-feature work needs its own brief + spec first.
- **Mixed state in a slice file** (`status: gated` but `blocked_by` not all merged) → STOP. Refuse to advance. Surface as a consistency error.

### Refusing invalid transitions

Block these and explain:

| Maintainer tries | Why it's blocked | What to do instead |
|---|---|---|
| `/tdd MM` on a slice with unmerged blockers | Out-of-order dependency | Show the unmerged blocker and recommend it first |
| `/release-gate` on a slice still `in_progress` | TDD not done | Continue `/tdd` until the slice's acceptance criteria are met |
| `documenter` while any slice is `< merged` | Premature documentation | Surface which slices remain; the `documenter` runs once |
| Marking a brief `Shipped` with unmerged slices | Inconsistent state | Show the unmerged slices |

Refusals are firm but not preachy. State the rule, name the gap, name the fix.

## Output

### Board view — `/feature-flow` (no args)

Compact table of in-flight features (brief exists, status ≠ `Shipped`):

```
## In-flight features

| NNNN | Title                        | Brief    | Spec | Slices               | Next step                                       |
|------|------------------------------|----------|------|----------------------|-------------------------------------------------|
| 0023 | Bulk record import          | Ready    | ✓    | 1m · 1ip · 2r · 0d   | continue /tdd on slice 02                       |
| 0024 | Settings-page icon polish    | Draft    | ✘    | —                    | maintainer reviews + marks Ready                |

(slice tallies: m=merged, ip=in_progress, r=ready, d=draft)
```

Plus a section for refactor-only work-in-flight (architect spec exists with no brief):

```
## In-flight refactors

| Spec                                  | Slices          | Next step                  |
|---------------------------------------|-----------------|----------------------------|
| 0000b-unit-test-coverage              | none yet        | /to-slices                 |
```

### Detailed view — `/feature-flow NNNN`

For one feature:

```
# Feature NNNN — <title>

**Brief:** docs/features/NNNN-slug.md · Status: <…>
**Spec:**  docs/architect/NNNN-slug.md · <created date>
**Slices:** docs/slices/NNNN-slug/ · <N> total

## Slice board

| #  | Title              | Status      | Type | Blocked by | Touches                |
|----|--------------------|-------------|------|------------|------------------------|
| 01 | walking skeleton   | merged      | AFK  | none       | schema · repo · e2e    |
| 02 | core-calc pure     | in_progress | AFK  | 01         | lib · unit tests       |
| 03 | action + UI wiring | ready       | HITL | 02         | action · components    |
| 04 | edge cases polish  | draft       | AFK  | 03         | lib · unit tests · e2e |

## Next step

`/tdd docs/slices/NNNN-slug/02-core-calc-pure.md`

(slice 02 is in_progress; finish it before starting 03. slice 03 is HITL — maintainer will be in the loop.)
```

### Advance — `/feature-flow NNNN next`

In default mode: name the exact command to run and stop. No dispatching. **If the next step is `/tdd`, prepend the Sonnet recommendation** — `/tdd` is orchestration work; the main session running it on Opus is the largest avoidable token cost in the workflow.

```
⚠️ The next step is /tdd — recommend switching the main session to Sonnet first (`/model sonnet`) to save Opus budget over the slice's iterations. Switch back to Opus afterward for /brainstorm or architect work.

**Next step:** `/tdd docs/slices/0023-bulk-record-import/02-core-calc-pure.md`

**Why:** slice 02 is `ready` and unblocked (slice 01 merged). Vertical build through red-green-refactor.
```

For non-`/tdd` next steps the Sonnet warning is omitted — `/release-gate`, `architect`, `/to-slices`, `documenter` each have their own model expectations.

In `--auto` mode: invoke the next skill/agent yourself (via the Skill tool or `Agent`) and report the dispatch. **Confirm with the maintainer before dispatching for the first time in a session** — `--auto` is sticky for the rest of the session once confirmed.

### Mark — `/feature-flow NNNN status MM <state>`

Updates the `status:` frontmatter field of the slice file. Allowed transitions:

- `draft → ready` (maintainer signals slice is ready to pick up)
- `gated → in_progress` (only if the gate found issues — explicit rollback)
- `in_progress → ready` (slice abandoned; explicit rollback)
- `merged → anything` — REFUSED. Merged is terminal.

Any other transition routes through the natural skill (`/tdd` sets `in_progress` and `gated`; `/release-gate` sets `merged`).

## What this skill does NOT do

- **Does not write code.** Pure orchestrator. Every code change is a builder dispatch (via `/tdd`, `/release-gate`, or a direct skill).
- **Does not write briefs or specs.** Points at `/feature`, `architect` — never substitutes for them.
- **Does not write slice content.** Only updates slice frontmatter `status` field via the `status MM` invocation.
- **Does not commit.** All commits are the maintainer's call.
- **Does not enforce a phase boundary.** The brief's `Phase` field is the source of truth; this skill reads it but doesn't police it.
- **Does not run the architecture audit or grill.** Recommends them when state is ambiguous; doesn't substitute.
- **Does not bypass `/release-gate`.** A slice transitions to `merged` only via the gate. The skill refuses to set `status: merged` directly.

## Edge cases worth knowing

- **No `docs/features/` directory.** Project hasn't started; recommend the maintainer run `/feature` for any current work.
- **A brief without a number** (some legacy briefs predate the convention). Match by slug fuzzy-search; ask if multiple match.
- **A slice file with malformed frontmatter.** Refuse to act on it; surface the file and the parse error; recommend fixing the file before invoking the skill again.
- **A slice's `blocked_by` references a slice that doesn't exist.** Refuse to act on the dependent slice; surface the dangling reference; recommend correcting the slice file.
- **A slice that's both `gated` and has a passing `/release-gate` already recorded.** That's the `merged` state — recommend the maintainer commit and the skill updates `status: merged`.

## When NOT to use this skill

- **Bugs.** Use `/diagnose` for bug work — the lifecycle is bug-specific, not feature-shaped.
- **Architecture audits.** Use `/improve-codebase-architecture`; the output isn't a feature.
- **Tiny commits** that don't earn a brief (a typo fix, a dep bump, a copy edit). Skip the lifecycle entirely.

## Next step

This skill's own "next step" is whatever it recommends for the current feature. The skill itself has no fixed follow-up — its job is to be the durable map of where you are.

If you want a different feature's status, invoke again with a different `NNNN`. If you want the board, invoke without args.
