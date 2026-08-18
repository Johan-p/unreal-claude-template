---
name: feature
description: Help the maintainer draft a one-page functional feature brief — why, what, definition of done — and save it to docs/features/NNNN-slug.md. Use this when the user runs /feature, asks to "write a brief" or "spec out a feature" functionally (not technically), or starts describing a new piece of user-facing behavior that doesn't yet have a brief. For substantial briefs that warrant collaborative drafting (multi-screen flows, briefs that lock in major product direction, briefs that will outlive the conversation), invokes the `doc-coauthoring` skill to guide context gathering → refinement → reader testing. Do NOT use for technical design (that's the architect subagent) or for bugfixes, renames, dep bumps, single-file tweaks (no brief needed).
---

# /feature — feature brief drafting

You are helping the maintainer draft a **one-page functional brief**. The brief answers **why**, **what**, and **definition of done** — never **how**. Technical design is the architect's job and happens *after* the brief is `Ready`.

The lean flow this skill anchors:

```
/brainstorm  →  shared understanding              (precursor, only if the idea is fuzzy)
   ↓
/feature   →  docs/features/NNNN-slug.md        (functional: why / what / DoD)
   ↓ (only if load-bearing)
architect  →  docs/architect/NNNN-slug.md       (technical: how)
   ↓ (only if non-trivial — small briefs ship directly)
/to-slices →  docs/slices/NNNN-slug/MM-*.md     (tracer-bullet decomposition)
   ↓ (per slice)
/tdd       →  red-green-refactor build
   ↓
/release-gate Mode D  →  reviewer loop, slice merges
   ↓ (all slices merged)
documenter → ship
```

`/feature-flow NNNN` shows the current state of any feature across this lifecycle.

## Precursor — is the idea fuzzy?

Before drafting, gauge whether the maintainer already has shared understanding with you. If the idea is fuzzy (multiple unresolved branches in the design tree, vague domain vocabulary, open product questions), **recommend `/brainstorm` first** and stop. `/brainstorm` is the unbounded one-question-at-a-time interrogation that produces the shared understanding this brief crystallizes.

You'll know to recommend `/brainstorm` when:
- You'd have to ask more than ~5 questions to draft confidently.
- The maintainer's description uses vocabulary not in the project's context/glossary doc (e.g. `docs/CONTEXT.md`), if the project keeps one.
- The feature crosses multiple screens or flows whose interaction isn't clear.
- The maintainer says *"I'm not sure exactly what I want"* or equivalent.

When the idea is already crisp (a tightly-scoped enhancement, a copy change, a small flow), skip `/brainstorm` and proceed to the modes below.

## Two modes — pick the right one

**Fast path** (the default): the maintainer has a clear-enough idea, the brief is one screen / one flow / a small enhancement, you can draft it after at most 3 sharp questions. Stay lean; the rest of this skill is the fast path.

**Coauthor path** (`doc-coauthoring` skill): the brief is substantial enough that getting it right matters more than getting it fast. Triggers:
- The feature spans **multiple screens or flows** that need to make sense together.
- The brief will **lock in product direction** beyond a single phase (e.g., the shape of how core entities relate to each other, how a key workflow maps end-to-end, how third-party integrations will plug in later).
- The brief will be **read by stakeholders who aren't in this conversation** — investors, future contributors, a non-maintainer co-founder.
- The maintainer explicitly asks for "the full workflow" or "let's coauthor this properly."

When you hit any of those triggers, **invoke `doc-coauthoring` before drafting**:

```
Skill(skill="doc-coauthoring")
```

That skill walks the maintainer through three stages — context gathering, refinement & structure, reader testing — and is built exactly for this kind of substantial collaborative drafting.

**How the two skills compose:**
- `doc-coauthoring` guides the *writing process* (how to surface context, brainstorm options, refine sections, test with a fresh reader).
- This `feature` skill owns the *output shape and home* (the one-page brief template at `docs/features/0000-template.md`, the `NNNN-slug.md` filename convention, the Status / Phase / Out-of-scope / Open-questions constraints below).

When you invoke `doc-coauthoring`, tell it explicitly that the final deliverable is a one-page feature brief in the shape of `docs/features/0000-template.md`, saved to `docs/features/NNNN-slug.md`. Don't let the coauthoring workflow drift into producing a multi-page spec — the one-page constraint is load-bearing for this artifact.

**If `doc-coauthoring` is not available in the environment**, fall back to the fast path with the question count relaxed (up to ~8 questions instead of 3, batched into a coherent context-gathering message) — and tell the maintainer the skill wasn't available so they can install it if they want the full workflow next time. Do not silently pretend you used it.

**If unsure which mode**, ask the maintainer once in one short sentence: "Quick fast-path brief, or the full coauthored workflow (about 15–20 min)?" — then proceed with their answer.

## Process (fast path)

### 1. Crystallize before drafting

If the user's request is already specific enough to draft (clear user problem + clear behavior in mind), skip straight to drafting.

Otherwise ask **at most 3 sharp questions** — never more, never an interrogation. Good probes:

- **Why now?** What costs us if we don't ship this in the current phase?
- **Who exactly, in what moment, doing what?**
- **What does done look like?** One concrete behavior you could demo.

Do not ask about tech, schema, edge cases, or implementation. Those are not the brief's job.

### 2. Draft the brief

Use `docs/features/0000-template.md` (path relative to the scaffold repo root) as the shape. Fill every section. Constraints:

- **One page when rendered.** If it overflows, it has drifted into implementation — cut it back.
- **`What` is user-facing behavior**, not implementation. No file names, no API names, no library names. Write so a non-technical reader understands.
- **`Definition of Done` is testable.** Each bullet starts with a verb and describes something an observer could verify. "Feature works" is not a DoD. "User can add an item to their list in ≤2 taps and it appears without a page reload" is.
- **`Out of scope` is not optional.** Naming what this is NOT is how briefs stay lean.
- **`Open questions` carry a default.** Each question states the fallback if it goes unanswered. No question stays open without a default — that's how progress survives ambiguity.
- **Status starts at `Draft`.** Only the maintainer moves it to `Ready`.
- **Phase** applies only if the project keeps a phase/roadmap doc (e.g. `PLAN.md`) — this project currently doesn't, so skip the check. If phased and the request crosses phases, flag it and ask which phase this brief is scoped to.

### 3. Pick a filename

- Use `Glob` or `ls docs/features/` to find the highest existing number; the next brief is that + 1, zero-padded to 4 digits.
- Slug: kebab-case, user-facing name, not technical. Whole filename ≤ ~50 chars.
- Examples: `0007-quick-add-item.md`, `0012-export-list-pdf.md`.

### 4. Write the file

Write the brief to `docs/features/NNNN-slug.md` using the `Write` tool. Don't ask for permission — writing the file is the point of the skill. If a file already exists at the chosen path, increment the number.

### 5. Show the maintainer

Output:
- The path written.
- A 1–2 sentence summary of what the brief says.
- The next concrete step. Either:
  - *"Review the brief; if it's right, mark status `Ready`. The `architect` agent then produces the technical spec at `docs/architect/NNNN-slug.md`, `/to-slices` decomposes it into 3–6 vertical slices under `docs/slices/`, and `/tdd` builds each slice through red-green-refactor."* — when the feature has load-bearing technical decisions (schema change, new module boundary, cross-cutting refactor, anything that locks in Phase 2/3 shape).
  - *"Review the brief; if it's right, this is small enough to implement directly — dispatch the relevant builder and run `/release-gate Mode B` when done."* — when there are no load-bearing technical decisions.
- A pointer to `/feature-flow NNNN` as the state tracker for the lifecycle if the maintainer wants the board view at any point.

Do not paste the brief back into the chat — the maintainer reads the file.

## What this skill does not do

- **Does not write technical specs.** That's the architect.
- **Does not estimate or schedule.** That's the maintainer's call.
- **Does not implement.** The brief is the trigger; code follows separately.
- **Does not write briefs for bugfixes, renames, dep bumps, or single-file tweaks.** Those earn a commit, not a brief.
- **Does not recommend the architect by default.** Most briefs don't need one. Recommend it only when the brief contains a load-bearing technical decision.
