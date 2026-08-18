# CLAUDE.md

Guidance for Claude Code when working in this repository.

> **This is a starting point, not a finished doc.** Sections marked `[FILL IN]` describe *what kind of information belongs there* â€” replace the bracketed guidance with real facts about your project. Delete sections that don't apply.
>
> **The fastest way to fill this in is `/setup-claude-md`** â€” it interviews you, verifies commands before recording them, splits machine paths into a gitignored `LOCAL.md`, and knows which entries the agents and skills below actually depend on.
>
> A CLAUDE.md that is *wrong* is worse than one that is incomplete. Don't leave placeholder text in place once you know the real answer, and don't paste values from another machine â€” a build command that looks verified but isn't is the worst of both.

## Machine-local paths

**Hard rule: nothing in this repo hardcodes an absolute local path.** Engine installs, project directories and tool locations live in `LOCAL.md` (gitignored; copy `LOCAL.md.example` to start). Skills, agents and docs reference its keys â€” `<UnrealProjectDir>`, `<UnrealEngineDir>`, `<BuildScript>`, `<Python3>` â€” so the repo stays shareable and a machine move is a one-file edit.

The import below is **load-bearing**: without it those keys resolve to nothing and every reference becomes dead text.

@LOCAL.md

If you use the VibeUE plugin, it generates its own agent guide into the project folder; import it here too so its tool documentation is in context:

<!-- @<UnrealProjectDir>/CLAUDE.md -->

## Repo layout

`[FILL IN]` Where source lives, what the top-level directories are for, and which directory belongs to whom. One paragraph, not a tree dump.

This repo is the **scaffold** â€” docs, conventions and Claude Code configuration. The Unreal project itself normally lives in a separate directory (see `LOCAL.md`) with its own version control.

If an authoritative design document exists (GDD, spec, PRD), name it here and say it wins on design questions. This file should carry only the load-bearing engineering facts, never a duplicate of it.

## Commands

`[FILL IN]` The exact commands, verified on this machine. Put the machine-specific strings in `LOCAL.md` â†’ Verified commands and describe here only what survives a machine move.

- **Build C++** â€” the command, plus its preconditions. For Unreal: **the editor must be closed**, because Live Coding holds a lock that blocks UnrealBuildTool. This is the single most common build failure with a non-obvious cause.
- **Build and relaunch** â€” if you use a helper script, name it and its useful flags.
- **Run tests** â€” see Testing below.

## Testing

`[FILL IN]` The test command, **what a pass looks like**, and what noise to ignore. "The tests pass" is not a checkable claim without the exact success signature â€” the `/tdd` and `/release-gate` flows verify by reading this output, so be precise.

Worth recording once you know them: how long a cold run takes, which startup warnings are known noise, and any gotcha in the runner's argument handling.

**Policy:** `[FILL IN]` which code ships with tests in the same change (typically pure logic), and which surfaces are verified by build plus evidence instead (typically view actors, widgets and assets).

## Tech stack quirks

`[FILL IN]` The non-obvious, load-bearing facts a competent newcomer would get wrong. These are the highest-value lines in the file. Add verified traps as you hit them â€” each a short "what you'd assume" versus "what actually happens".

Starting points worth keeping:

- **Official engine documentation** â€” link the version-specific root, and the scripting API reference if you automate the editor. Invented APIs are a recurring failure mode; a URL is what turns "I think this exists" into a check.
- **Asset naming and content-folder structure** â€” see [`docs/NamingConventions.md`](docs/NamingConventions.md) and [`docs/FolderStructure.md`](docs/FolderStructure.md). Treat both as hard rules; the release-gate pre-pass script parses the naming table, so keep its format.
- **MCP drops when the editor closes** â€” a C++ build closes the editor, which kills the MCP server. Relaunching and making a call or two lets the harness re-attach; asking a human to reconnect is the fallback, not the first move.
- **Live testing** â€” record what actually works in [`docs/live-testing-playbook.md`](docs/live-testing-playbook.md) as you learn it, especially approaches that look right and produce wrong answers.

## Project context

`[FILL IN]` The facts that aren't derivable from the code:

- Who works on it, how much time is available, and what that implies for scope.
- Status and any hard phase gates â€” work that is *not authorized* until a milestone passes.
- The ownership split: what Claude Code owns end to end versus what you own.
- Platform and scope targets, including what *not* to build ahead of schedule.
- Decisions and cuts already made â€” link the doc that records them so they aren't relitigated.

## Subagents & skills

Checked in under `.claude/`. See [`docs/workflow.md`](docs/workflow.md) for how they fit together.

**Agents** (`.claude/agents/`): `architect` (design specs, no code) Â· `builder` (the single builder) Â· `reviewer` (read-only release gate) Â· `tester` (smoke playtests, feature boundaries only) Â· `documenter` (plain-English docs).

Models are pinned explicitly in each agent's frontmatter rather than inheriting the session model, so switching your own model doesn't silently change what tier the agents run at. Change a pin only with a stated reason.

**Skills** (`.claude/skills/`) â€” **the layout is FLAT.** One folder per skill, no category subfolders: nesting them silently unregisters every skill inside, which looks tidy and breaks everything.

The lifecycle skills are `/brainstorm`, `/feature`, `/feature-flow`, `/to-slices`, `/tdd`, `/release-gate`, plus `/diagnose`, `/doc-coauthoring`, `/architecture-diagram` and `/improve-codebase-architecture`. Setup lives in `/unlock-unreal`, `/setup-local-md` and `/setup-claude-md`. The `ue-*` skills are Unreal C++ references that load automatically by domain. **Rule: skills advise, architect specs decide â€” on conflict the spec wins.**

**File ownership** `[FILL IN]` the actual table for your project. A `PreToolUse` hook (`.claude/hooks/guard-agent-paths.ps1`) enforces the architect and builder lanes structurally; everything else is advisory.

## Working style

`[FILL IN]` How you want to be worked with. `/setup-claude-md` asks the questions that produce this well â€” the useful answers are behavioural rules, not descriptions of you. "Lead with the recommendation; I'll ask for detail" is actionable; "I'm a decisive person" is not.

Two that transfer to almost everyone:

- **Deliver, then prove it.** Don't claim a task is done without verifying it works. Plans are not outcomes.
- **Mistakes are allowed. Fabrication is not.** An honest mistake from a real attempt gets corrected and you move on. Inventing a function, file, flag, command output or test result â€” to look productive or to dodge "I don't know" â€” is a breach of trust.
