---
name: to-slices
description: Decompose a Ready architect spec into 3–6 thin tracer-bullet vertical slices, each a complete pass through every architectural layer this project has (e.g. schema → repo → API → UI → tests), saved as `docs/slices/NNNN-slug/MM-name.md` files with frontmatter state. Use after the architect spec is written, before the build begins. Adapts Pocock /to-issues to a docs-not-GitHub flow. Refuses to slice without a corresponding `docs/architect/NNNN-slug.md`.
---

# /to-slices — decompose an architect spec into tracer-bullet vertical slices

This skill exists because **the unit of release-gate is too big**. A whole feature takes 30–60 min through the gate; a thin slice takes 10–15. Slicing also forces the deepening discipline — each slice must work end-to-end, which surfaces unclear interfaces early instead of at integration time.

## Hard preconditions

Refuse to run if:

- The architect spec at `docs/architect/NNNN-slug.md` doesn't exist or hasn't been written by the architect agent.
- The corresponding feature brief at `docs/features/NNNN-slug.md` is not `Status: Ready`.
- The feature is trivially small (a one-file change, a copy edit, a single repo function with no UI). In that case, recommend skipping slicing and shipping as one commit.

If any precondition fails, **say so plainly and tell the maintainer what's missing**. Do not synthesize slices against a draft brief — slices commit to a design that hasn't been pinned down.

## Process

### 1. Read inputs

In one pass, read:

- `docs/features/NNNN-slug.md` — the functional brief (the WHY/WHAT)
- `docs/architect/NNNN-slug.md` — the technical spec (the HOW)
- The project's context/glossary doc (e.g. `docs/CONTEXT.md`), if one exists — domain vocabulary; slice titles + descriptions use its terms exactly. This project currently keeps none; use the briefs' established vocabulary instead.
- The brief's `What` and `Definition of Done` bullets — these are the surfaces the slices collectively cover

### 2. Draft tracer-bullet slices

Each slice is a **thin vertical pass through every integration layer it touches** — schema → repository/service → API/action → UI → tests, or whatever this project's actual layers are (see `CLAUDE.md`). Not a horizontal layer of one tier.

```
WRONG (horizontal):
  slice 1: all schema changes
  slice 2: all repository/service changes
  slice 3: all UI changes

RIGHT (vertical):
  slice 1: thinnest end-to-end path proving the seam works
  slice 2: next narrow vertical adding one capability
  slice 3: …
```

**Slice rules:**

- **3–6 slices per feature.** Fewer = each slice too thick = release-gate cycles get long. More = the feature is too big and probably crosses scope; flag it back to `/feature`.
- **Each slice is demoable or verifiable on its own.** "Demo or assert what works" is the test for whether the slice is truly vertical.
- **Each slice has a single load-bearing seam.** If a slice introduces two new interfaces, split it.
- **Order by dependency.** A slice whose prerequisites aren't merged stays `blocked_by`. The first slice has no blockers.
- **First slice = walking skeleton.** The thinnest end-to-end path proving the design holds — one write to the data layer, one call through the service/API layer, one test asserting the path works. Often deliberately ugly UI. The point is to prove the seam.
- **Prefer AFK over HITL.** AFK = a builder can finish without maintainer input. HITL = needs maintainer in the loop (UI design decisions, architectural calls during build, manual data shaping). Mark each slice.

**Naming.** Slice files: `MM-kebab-case-verb.md`, ≤40 chars total. Examples: `01-schema-and-walking-skeleton.md`, `02-validate-pure-core.md`, `03-action-and-ui-wiring.md`. The verb is the *outcome*, not the layer.

### 3. Quiz the maintainer

Before writing any file, present the proposed breakdown as a numbered list. Each entry shows:

- **Title** — kebab-case slug + plain-language description (one line).
- **Type** — `AFK` or `HITL`. If HITL, name what needs the maintainer.
- **Touches** — the layers it cuts through (e.g. "schema · repo · API · e2e" — use this project's actual layer names).
- **Blocked by** — slice numbers that must merge first, or "none".
- **Spec section** — which §N of the architect spec this slice implements.
- **Covered DoD bullets** — which `Definition of Done` items from the brief this slice closes (by quote or number). The union across all slices must cover every DoD bullet; flag any DoD bullet that no slice covers.

Then ask:

- Does the granularity feel right? (Too coarse → split. Too fine → merge. 3–6 is the band.)
- Are the dependency relationships correct?
- Is the AFK/HITL classification right?
- Any DoD bullet not covered? Any slice covering nothing demoable?

**Iterate until approved.** Do not write files until the maintainer says yes.

### 4. Write slice files

For each approved slice, write to `docs/slices/NNNN-slug/MM-name.md`. Create the directory if it doesn't exist. Use this template exactly:

```markdown
---
feature: NNNN
slice: MM
title: <plain-language title>
status: ready          # draft | ready | in_progress | gated | merged
type: AFK              # AFK | HITL
blocked_by: [list of slice numbers, e.g. 01]
created: YYYY-MM-DD
---

# MM — <plain-language title>

**Feature brief:** [NNNN functional](../../features/NNNN-slug.md)
**Architect spec:** [NNNN technical](../../architect/NNNN-slug.md)
**Spec section:** §<N> "<section title verbatim>"

## What to build

<End-to-end behaviour this slice delivers. User-facing where possible, system-facing where the slice is internal (e.g. walking-skeleton slices). One paragraph or short bullet list. NOT layer-by-layer.>

## Acceptance criteria

- [ ] <observable criterion 1 — verifiable by a test or a demo>
- [ ] <observable criterion 2>
- [ ] <…>
- [ ] /release-gate passes (gate scope: this slice's files only)

## Blocked by

- <slice 01 link, or "none — can start immediately">

## Notes

<Anything the builder/reviewer needs that isn't in the architect spec. Often empty. Examples: a one-line CLAUDE.md addition this slice should propose; a specific glossary candidate that lands with this work; an explicit "do not refactor X" guard if scope creep is plausible.>
```

**Status default:**

- `ready` for AFK slices with no unmerged blockers — the most common case.
- `ready` for HITL slices the maintainer is actively driving.
- `draft` for slices whose acceptance criteria you couldn't pin down in the quiz — surface the gap and ask before writing.

**`blocked_by` is enforced by `/feature-flow`** — a slice with unmerged blockers won't be picked up. So get it right.

**Write in dependency order** so the file you write last can reference earlier-written files by path.

### 5. Update the architect spec (optional, ask first)

Offer to append a small **Slices** section at the bottom of `docs/architect/NNNN-slug.md`:

```markdown
## Slices

The implementation is decomposed into N slices. Each is a thin vertical pass through every layer it touches. Status and detail in each slice file.

- [01 — <title>](../slices/NNNN-slug/01-name.md) — <one-line description> · `AFK` · blocked by: none
- [02 — <title>](../slices/NNNN-slug/02-name.md) — <one-line description> · `AFK` · blocked by: 01
- …
```

This is a maintainer convenience pointer; the slice files are the canonical state. Architect-spec ownership belongs to the `architect` agent — ask the maintainer before editing. If they say yes, edit. If they say no, leave the spec untouched and report the slice paths in chat so the maintainer can append manually or dispatch the architect to do it.

### 6. Report and hand off

Final output to the maintainer:

- Count of slices written (e.g. *"4 slices written under `docs/slices/0023-example-feature/`"*).
- One-line summary per slice with status, type, blockers — same shape as the quiz table.
- The first slice that has `status: ready` and no blockers — that's the next move.
- The closing next-step pointer.

## Next step

**Always close with both lines, in this order:**

> *⚠️ Before running `/tdd`: switch the main session to Sonnet via `/model sonnet`. `/tdd` is orchestration work — Sonnet handles it fine and saves a large multiple of the Opus token cost over a multi-slice feature. Switch back to Opus for `/brainstorm`, `architect`, or `/improve-codebase-architecture` work.*
>
> *Next: pick the first `ready` slice and run `/tdd <slice-file>` to build it through red-green-refactor. After the slice is implemented, `/release-gate Mode D` (scoped to the slice) audits it.*

If `/feature-flow` is installed, suggest invoking it: *"or `/feature-flow status NNNN` to see the slice board for this feature."*

## When NOT to use this skill

- **No architect spec yet.** Refuse — slicing without a design is fabricating it.
- **Trivial single-commit work.** Recommend skipping; ship as one commit.
- **Across-feature refactors.** This skill operates on one feature's spec. Cross-feature work needs its own brief + spec first.
- **Already-sliced features.** If `docs/slices/NNNN-slug/` exists, surface the existing slices and ask whether to add, replace, or leave alone — don't silently overwrite.

## What this skill does NOT do

- **Does not write the brief or the spec.** Those are `/feature` and the `architect` agent.
- **Does not implement slices.** Each slice is picked up by `/tdd` → builder → `/release-gate`.
- **Does not edit `docs/features/`.** The brief is frozen at `Status: Ready`.
- **Does not commit.** The slice files are written; the commit is the maintainer's call.
- **Does not modify test-framework config.** Slice-test conventions are spec-level, not slice-level.
