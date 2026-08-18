---
name: skill-audit
description: Audit one or more existing Claude Code skills against Anthropic's documented best practices and improve them with the user's approval. Use whenever the user asks to audit, review, improve, clean up, optimize, or health-check a skill or the skills folder, asks whether a skill is well written or triggers correctly, or wants skills brought in line with Claude Code best practices — even if they don't say "audit". Never edits a skill without approval — it always presents planned changes with risks vs rewards first and waits for the go-ahead.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/skill_stats.py *)
---

# Skill Audit

Audit existing skills against Claude Code's documented best practices, then improve them — but only after the user has seen exactly what would change and said yes.

**The one hard rule of this skill: no skill file is edited before the user approves that specific change in this conversation.** The value of an audit is trust in the auditor. A skill that silently "improves" other skills can quietly break their triggering, their commands, or hard-won project knowledge embedded in them — and the user finds out weeks later when something misfires. Propose first, edit second, always.

## Step 1 — Scope

Establish which skills are in scope:

- A named skill → audit that one skill directory.
- A folder (e.g. `.claude/skills/`) → enumerate the skill directories inside it (any directory containing a `SKILL.md`, at any depth).
- "All my skills" / no target given → enumerate the project's `.claude/skills/` tree and confirm the list with the user before auditing, so a 40-skill sweep isn't a surprise.

Note anything third-party in scope (an attribution line, a LICENSE file, an "adapted from" note). Third-party skills get audited like any other, but their attribution and license files are never touched, and heavy rewrites of them deserve an explicit warning in the proposal.

## Step 2 — Audit

Read `references/best-practices.md` in this skill's directory — it is the checklist, distilled from Anthropic's documentation with the concrete limits and the reasoning. Audit against that list, not from memory: memory drifts, the checklist carries citations.

For each skill in scope:

1. Run the mechanical pass: `python ${CLAUDE_SKILL_DIR}/scripts/skill_stats.py <skill-dir> [<skill-dir> ...]` — it reports body line count, description length, unknown frontmatter fields, and reference files missing a pointer from SKILL.md. These are facts; don't re-derive them by hand. It needs only a stdlib Python 3 — if `python` isn't on PATH, use any bundled interpreter on the machine (game engines and DCC tools ship one); with no interpreter at all, perform the same checks manually per the checklist.
2. Read the full SKILL.md and skim every bundled file. You cannot judge progressive disclosure, triggering, or dead weight without seeing what's actually there.
3. Record findings, each tied to a checklist item (use the checklist IDs, e.g. `T2`, `C1`). A finding without a checklist anchor is an opinion — leave it out or label it explicitly as a judgment call.

What a finding is NOT: house style. Rewording that doesn't change behavior, restructuring that saves no tokens, and preference-level phrasing changes create diff noise and risk without reward. The checklist's own advice applies to this skill too — flag only what affects triggering, context cost, correctness, or maintainability.

## Step 3 — Propose (before touching anything)

Present one proposal report covering all audited skills. For every proposed change, the user must be able to judge it without opening the files. Use this structure:

```
## Audit: <skill-name>
Health: <one line — solid / minor issues / needs work>

### Proposed change 1: <short title>   [checklist: T2]
- What: <the concrete edit — quote the current text and the replacement when short,
  describe the shape of the change when long>
- Reward: <what improves, tied to the documented practice>
- Risk: <what could regress — changed triggering, changed /command, lost nuance,
  behavior drift in a skill that currently works>
- Recommendation: apply / optional / skip (and why)
```

Rules for the proposal:

- **Quantify the reward where possible** ("removes ~120 always-loaded lines", "description currently 1,900 chars — over the 1,536 cap, the tail is invisible to the model").
- **Be honest about risk.** Every edit to a working skill risks changing behavior that someone relies on. "Low risk" is a claim — say why (e.g. "pure move of reference material, instructions unchanged"). Changes that alter the `description` of a frequently-auto-triggered skill, rename anything, or delete content are never low risk.
- **Findings you recommend skipping still belong in the report.** The user may weigh the tradeoff differently.
- If a skill is healthy, say so and propose nothing. A clean bill of health is a valid, useful result — do not invent changes to look productive.

## Step 4 — The approval gate

Ask for the go-ahead and **stop until it arrives**. If the `AskUserQuestion` tool is available, use it — offer at minimum: apply all recommended, let me pick per change, apply none. For per-change picking, walk the changes with individual approve/skip questions. In an environment without that tool, ask in plain text and wait for the reply.

Only the changes the user approved get applied. "Apply the recommended ones" does not include the ones marked optional or skip. If the user's reply is ambiguous about a specific change, ask about that change rather than guessing — this gate is the skill's whole contract.

## Step 5 — Apply and verify

For approved changes only:

- Ensure the work is revertible before editing: in a git repo, confirm the skill files are committed or the working tree state is noted; outside git, copy the skill directory to a backup location first.
- Never change a skill's directory name, and never change a plugin skill's `name:` field, unless that rename was itself an explicitly approved change — the directory name IS the command users type.
- Preserve attribution lines and LICENSE files in third-party skills verbatim.
- After editing, re-verify mechanically: run `skill_stats.py` again on the touched skills — frontmatter must still parse, the description must be within limits, and every reference file must still be pointed to.
- Report what was changed per skill, what was deliberately not changed, and remind the user that live change detection picks up SKILL.md edits in-session, but a brand-new top-level skills directory needs a session restart.

If an approved change turns out to be wrong mid-application (e.g. the "unused" reference file is actually load-bearing), stop, say so, and return to the gate with the corrected proposal rather than improvising a different edit.
