---
name: setup-local-md
description: Interview the user to create or update LOCAL.md — the gitignored file holding this machine's paths and verified commands (Unreal project dir, engine install, build script, Python, tool installs). Auto-discovers what it can, asks only to confirm, and verifies every path actually exists before recording it. Use when setting up this workspace on a new machine, when LOCAL.md is missing or a skill reports a <KeyName> it can't resolve, or when the user asks to set up, fix, or add local variables/paths.
argument-hint: "[key to add or fix, e.g. UnrealProjectDir — omit to run the full setup]"
---

# /setup-local-md — machine-local variables, verified

LOCAL.md is the single home for machine-local facts: skills, agents, and docs reference its keys (`<UnrealProjectDir>`, `<UnrealEngineDir>`, `<BuildScript>`, …) instead of hardcoding paths. This skill fills it in correctly on a new machine — and "correctly" means **every path is verified to exist before it's written**. A LOCAL.md full of guessed paths silently breaks every skill that trusts it.

## Process

### 1. Establish the key set

- If `LOCAL.md` exists: read it; the job is filling gaps or fixing the key the user named.
- Else if `LOCAL.md.example` exists: its keys are the required set.
- Else: use the standard set below.

| Key | What it is | How to auto-discover |
|---|---|---|
| `UnrealProjectDir` | Folder containing the `.uproject` | Glob common roots (`C:\Unreal\*`, user folders) for `*.uproject`; else ask |
| `UnrealEngineDir` | Engine install root | Registry `HKLM:\SOFTWARE\EpicGames\Unreal Engine\<ver>` → `InstalledDirectory` |
| `BuildScript` | Build-and-relaunch script | `<UnrealProjectDir>\Plugins\VibeUE\BuildAndLaunchGame.ps1` (exists only after `/unlock-unreal`) |
| `Python3` | A Python 3 interpreter | `Get-Command python` — if it's only the Microsoft Store stub, fall back to the engine-bundled one: `<UnrealEngineDir>\Engine\Binaries\ThirdParty\Python3\Win64\python.exe` |
| `PackagedBuilds` | Where packaged builds land | `<UnrealProjectDir>\Packaged` if present; else mark "not set up yet" |

Project-specific extras in the example file (tool installs like Blender, archive paths) follow the same pattern: discover → confirm → verify.

### 2. Discover first, then ask — one key at a time

For each unresolved key: attempt auto-discovery, then present the candidate to the user as a recommendation to confirm or correct (use `AskUserQuestion` when available — one key per question, with the discovered path as the recommended option). Only ask open-endedly when discovery found nothing. Never fill a key with a plausible-looking path the user hasn't confirmed and you haven't verified.

### 3. Verify, then write

- Every path: `Test-Path` must pass. A key whose path fails verification is written as unresolved (`<not found — re-run /setup-local-md>`), never as a guess.
- Executables (`Python3`): run a trivial invocation (`--version`) and record that it worked.
- Verified commands section: carry over the command templates from `LOCAL.md.example` with the confirmed paths substituted. Mark them "unverified on this machine" until one has actually been run — don't inherit a "verified" label from another machine.

Write `LOCAL.md`, ensure `.gitignore` contains `LOCAL.md`, and ensure CLAUDE.md imports it (`@LOCAL.md`) — add the import if missing. If `LOCAL.md.example` doesn't exist yet, generate it from the finished LOCAL.md with values replaced by placeholders, and note it should be committed.

### 4. Report

Close with the key → value table, marking each ✔ verified / ✋ user-asserted / ✘ unresolved, plus the natural next step: `/unlock-unreal` if `BuildScript` is unresolved (VibeUE not installed yet), or `/setup-claude-md` if CLAUDE.md still has `[FILL IN]` markers.
