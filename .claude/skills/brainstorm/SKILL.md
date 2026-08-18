---
name: brainstorm
description: Interview the maintainer relentlessly about a feature idea, one question at a time with your recommended answer, until shared understanding crystallizes — then hand off to /feature for the brief. Use at the very start of feature ideation, before /feature, when the idea is fuzzy and the design tree has unresolved branches. Adapted from mattpocock/skills. Anchored to your project's context/glossary doc and existing ADRs/architect specs.
---

# /brainstorm — relentless one-question-at-a-time brainstorming

You are interviewing the maintainer about an idea. Goal: **shared understanding sufficient to draft a one-page functional brief**. Not "shared understanding sufficient to ship" — that's later. Just enough that the next step (`/feature`) can produce a brief without guessing at intent.

## Core discipline

Interview the maintainer relentlessly about every aspect of this plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. **For each question, provide your recommended answer.**

**Ask the questions one at a time.** Wait for the answer before the next question.

**If a question can be answered by exploring the codebase, explore the codebase instead.** Don't ask the maintainer what a given module or file does — read it.

The recommended-answer rule is load-bearing: it's not an interview, it's a co-design. A bare question shifts the burden to the maintainer; a question with your recommendation invites a yes/no/redirect. Faster, sharper, less mental load. Even when you're 60% sure of the answer, name it.

## What to ground every question against

Before asking anything, **read these — every time** (adapt the exact paths to your project; the pattern is what matters):

- **Your project's context/glossary doc** (e.g. `docs/CONTEXT.md`) — the canonical vocabulary. Every term you use should map to one defined here. If you find yourself using a word that isn't in the glossary, either reach for one that is, or surface it as a glossary candidate at the end of the session.
- **A phase/roadmap doc** (e.g. `PLAN.md`), if your project has one — [FILL IN: your phase boundaries]. A feature must land in one phase; cross-phase features need to be split. Skip this check entirely if your project isn't phased.
- **`docs/architect/`** (or wherever technical specs live) — every prior technical spec. Existing decisions you should not re-litigate; existing seams the new feature must compose with.
- **`docs/adr/`** (or wherever architectural decision records live) — load-bearing architectural decisions (e.g. a foundational choice about data isolation, auth model, or storage). Hard constraints, not preferences.
- **`docs/features/`** — prior briefs. The shape of "what we say yes to" and "what we leave out of scope."
- **`CLAUDE.md`** — tech stack quirks and any standing project rules (e.g. a scoping/isolation rule that every feature must respect, a dependency-versioning policy).

Cross-reference inline as questions land. *"Your glossary defines `<Term A>` as `<precise definition>`; you're using `<Term B>` to mean the same thing — should we standardise on `<Term A>`, or are these different states?"* That kind of cross-check IS the brainstorming.

## What questions look like

Good questions are **dependency-resolving** and **decision-shaped**:

- *"For X, do we want behaviour A or behaviour B? Recommended: A, because <one-sentence reason from your context doc or an ADR>. If A, then Y becomes free; if B, then Y needs its own answer next."*
- *"Your idea references `the container`. Your context doc has two related concepts — `Workspace` (the whole collection) and `Item` (one entry within it). Which level is this feature operating at? Recommended: `Item`, because <…>."*
- *"This sounds like it touches tenant-scoped data. Per your tenancy ADR, every read/write must run under the scoping guard. Confirm the feature is tenant-scoped (recommended: yes) — if no, name the cross-tenant data it touches."*

Bad questions are:
- **Open-ended without a recommendation.** *"How should this work?"* No.
- **Implementation-detail-fishing.** *"Should this be a server action or a route handler?"* That's the architect's call, not /brainstorm's. Surface that an architect handoff will be needed; don't decide it here.
- **Multi-part.** Two questions = two turns. Atomic questions are answerable; compound questions invite ambiguity.

## When to stop

Stop when you can answer "yes" to all of these:

- [ ] The **user problem** is clear. Who hurts, when, how often.
- [ ] The **observable behaviour** is clear. A non-technical reader could describe what's being built.
- [ ] The **scope** is clear. You know what's IN and what's OUT.
- [ ] The **phase** is clear. Cross-phase ambitions are flagged or split.
- [ ] **Open questions** are named with stated defaults — not buried.
- [ ] **Domain vocabulary** is consistent with your project's context/glossary doc (or new terms are listed as glossary candidates).

You do NOT need:
- The technical design (that's the architect — invoke `/feature` first, then the architect agent after the brief is `Ready`).
- The slice decomposition (that's `/to-slices` — runs against the architect spec, not the brief).
- The implementation plan (that's `/tdd` per slice).

## Length discipline

The session is *bounded by the maintainer's tolerance*, not by a fixed question count. Pocock notes sessions of 16 questions on simple features and 30–50+ on complex ones. Both are fine. **The brainstorming ends when shared understanding is reached, not when a counter hits a number.**

A session that takes 5 questions because the idea is well-formed is a success. A session that takes 40 because the maintainer is exploring a multi-screen multi-phase feature is also a success. A session that takes 5 questions on a complex feature is *not* a success — you've stopped too early.

If the maintainer signals impatience ("ok, ok, just write the brief"), do **not** silently continue brainstorming — surface the gap honestly: *"I can draft now. Two open questions I haven't pinned down: <X>, <Y>. I'll list them as open-questions-with-defaults in the brief unless you want to resolve them first."*

## What to escalate, not decide

- **Schema changes** → architect, after `/feature` produces a `Ready` brief.
- **Module-boundary decisions** → architect.
- **Cross-cutting refactor implications** → architect.
- **Naming a new domain concept** → flag as a glossary candidate; the maintainer adds it to the project's context/glossary doc. Do not write to that file from this skill.
- **A feature that crosses two phases** → ask the maintainer to scope to one phase; surface the leftover as a future brief.

## Output

The brainstorming itself is the output. Each question is a turn; each answer crystallizes a decision. At the end of the session, **summarize**:

- 5–10 bullets capturing the resolved decisions, in plain language.
- 1–3 open questions with stated defaults (carried into the brief).
- Any glossary candidates you uncovered.
- A one-sentence next-step pointer.

Do NOT write a brief from this skill. The brief is `/feature`'s job and uses a specific template (`docs/features/0000-template.md`). Letting `/brainstorm` write a brief blurs the seam.

## Next step

**Always close with:**

> *Next: run `/feature` to crystallize this into a one-page brief at `docs/features/NNNN-slug.md`.*

If during brainstorming you discovered the feature is too small to need a brief (a one-file tweak, a bugfix, a copy change), say so explicitly and recommend skipping `/feature`. The brainstorming output goes straight into the commit message.

## What this skill does NOT do

- **Does not write the brief.** That's `/feature`.
- **Does not write the technical spec.** That's the `architect` agent.
- **Does not decompose into slices.** That's `/to-slices`, against the architect spec.
- **Does not edit the context/glossary doc.** Surface candidates; the maintainer lands them.
- **Does not commit anything.** It's an interview; output is conversation, not files.
