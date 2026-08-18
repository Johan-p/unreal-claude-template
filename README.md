# Claude Code Scaffold for Unreal Engine Projects

A ready-to-adopt set of **Claude Code subagents and skills** for building Unreal Engine games with an AI-driven workflow: a feature goes from a fuzzy idea, through a functional brief and a technical spec, into thin vertical build slices, each built test-first and passed through a review gate before it ships.

Clone it, run two skills to record your machine's paths and your project's conventions, and the pipeline is usable as-is.

## The workflow

```
/brainstorm  →  /feature  →  architect  →  /to-slices  →  /tdd  →  /release-gate
 (interview      (one-page     (technical      (3–6 thin      (red-green    (build → review →
  the idea)       brief)        spec doc)       slices)        per slice)     fix loop)
```

Each stage reads and writes plain Markdown docs (`docs/features/`, `docs/architect/`, `docs/slices/`) with state tracked in frontmatter, so progress survives across sessions and the orchestrating skill (`/feature-flow`) can always tell you what's next.

**[docs/workflow.md](docs/workflow.md)** has the full map — which agent runs at each stage, the per-slice review loop and its deadlock rule, the feature-boundary steps, and who is allowed to write where.

## What's included

### Subagents (`.claude/agents/`)

| Agent | Role |
|---|---|
| `architect` | Designs before code — writes the technical spec (options, recommendation, class/asset list). Never writes code. |
| `builder` | The single builder — owns the Unreal project's C++ source, config, and editor assets (via MCP tooling). Dispatched one red-green iteration at a time. |
| `reviewer` | Read-only release-gate reviewer — verifies the diff against spec, acceptance criteria, and conventions by actually running builds and tests. |
| `tester` | Smoke playtester — drives real play sessions via MCP and reports pass/fail per acceptance bullet. Feature boundaries only. |
| `documenter` | Plain-English handbook writer for non-developer readers. |

The pipeline deliberately has **one** builder: an Unreal project is serialized through one live editor (C++ builds need it closed, asset edits need it open), so parallel builders would fight over it.

### Skills

All skill folders sit **flat** under `.claude/skills/` — one folder per skill, invoked by bare name (`/tdd`, `/ue-input-system`, …). Don't group them into category subfolders: that silently unregisters every nested skill (verified 2026-08-18). The groups below are documentation only.

| Group | Skills | What they're for |
|---|---|---|
| **Lifecycle** | `brainstorm`, `feature`, `feature-flow`, `to-slices`, `tdd`, `release-gate`, `diagnose`, `improve-codebase-architecture`, `architecture-diagram`, `doc-coauthoring` | The feature pipeline: idea → brief → spec → slices → red-green build → release gate, plus debugging and doc workflows |
| **Setup & maintenance** | `unlock-unreal` (full project bootstrap: plugins, Python, Remote Control, C++ conversion, VibeUE, auto-start, verification), `setup-local-md` (machine variables → LOCAL.md), `setup-claude-md` (CLAUDE.md interview), `skill-audit` (audit skills against best practices, propose → approve gate), `skill-creator` (build your own skills) | Bootstrapping the workspace and keeping the skills themselves healthy |
| **Unreal Engine reference** | 26 `ue-*` skills covering the engine's major systems — C++ foundations, gameplay framework, actors/components, input, UI, audio, materials, Niagara, physics, data assets, save games, AI/navigation, state trees, animation, character movement, async/threading, networking, GAS, editor tools, sequencer, world/streaming, PCG, game features, Mass Entity, testing/debugging, module/build system | Pattern references; they also load automatically when their domain comes up |
| **Production-verified Unreal** | `pcg-authoring` — authoring PCG graphs programmatically the way Epic's Electric Dreams sample does, built and verified against a live editor | Deep-dive techniques verified in production use, not just read from docs |

**Rule of thumb baked into the pipeline:** skills advise, architect specs decide — on conflict, the spec wins.

## Setting up the workspace

**Two things you do, then you ask Claude to do the rest.**

### 1. Install Unreal Engine 5.8 and Claude Code

Install UE 5.8 through the Epic Games Launcher and create or open a project. Then install [Claude Code](https://code.claude.com/docs/en/setup#install-claude-code), copy this repo's `.claude/` directory and `LOCAL.md.example` into your workspace root, and start `claude` there.

### 2. Ask Claude to set up the project

```
/unlock-unreal
```

That's the whole setup. The skill enables the plugin stack (MCP, EditorToolset, Python, Remote Control), configures the MCP server to start automatically with the editor, installs and builds the [VibeUE fork](https://github.com/Johan-p/VibeUE), writes the `.mcp.json` Claude Code needs, and then **proves it works** with a live round trip rather than assuming it does.

If your project is Blueprint-only it will stop and ask before converting it to C++, explaining what you already have without VibeUE and what converting adds and costs. Nothing irreversible happens without your say-so.

> Prefer to do it by hand, or want to understand what the skill is doing first? Every step is written out in **[manualsetup.md](manualsetup.md)**, with the editor-UI route and the config-file equivalent side by side.

### 3. Fill in your local variables and CLAUDE.md

```
/setup-local-md      # interviews you for machine paths → gitignored LOCAL.md (verified, never guessed)
/setup-claude-md     # interviews you to write an effective CLAUDE.md per Anthropic's best practices
```

Machine-local facts (engine install, project path, verified commands) live in `LOCAL.md` — gitignored, imported into every session, referenced by skills as `<UnrealProjectDir>`-style keys. `LOCAL.md.example` is the committed template. CLAUDE.md holds only what's true of the project itself.

The agents also expect a `docs/` folder for the pipeline's outputs (`docs/features/`, `docs/architect/`, `docs/slices/`, `docs/handbook/` — all start empty) plus two convention docs. Those two ship with the template as working defaults built on Epic's recommendations: `docs/NamingConventions.md` (asset prefixes) and `docs/FolderStructure.md` (content layout). Adapt them to your project rather than starting from a blank page.

Then start building: `/brainstorm` or `/feature`, and let `/feature-flow` guide you from there.

## Read more

- **Manual setup** — every setup step by hand, if you'd rather not let the skill do it: [manualsetup.md](manualsetup.md)
- **Workflow map** — how a feature travels from idea to shipped: [docs/workflow.md](docs/workflow.md)
- **Live-testing playbook** — what actually works when driving and observing a running game over MCP, and which obvious-looking approaches give confidently wrong answers: [docs/live-testing-playbook.md](docs/live-testing-playbook.md)
- **Conventions to adapt** — [docs/FolderStructure.md](docs/FolderStructure.md) (where content lives) and [docs/NamingConventions.md](docs/NamingConventions.md) (asset prefixes). Both ship as working defaults following Epic's recommendations; edit them to match your project.
- **Feature brief template** — the shape every brief takes: [docs/features/0000-template.md](docs/features/0000-template.md)
- **Pipeline outputs** — `docs/features/`, `docs/architect/`, `docs/slices/`, `docs/handbook/` fill up as you run the workflow; they start empty.
- **Working with your repo** — [CLAUDE.md](CLAUDE.md) ships as a `[FILL IN]` starting point and is imported into every session. `/setup-claude-md` fills it in, and knows which of its entries the agents, skills and hooks actually depend on.

## Credits

- Several lifecycle skills (`brainstorm`, `to-slices`, `tdd`, `diagnose`, `improve-codebase-architecture`) are adapted from [mattpocock/skills](https://github.com/mattpocock/skills).
- The `ue-*` reference skills originate from [quodsoler/unreal-engine-skills](https://github.com/quodsoler/unreal-engine-skills).
- `skill-creator` is Anthropic's official skill from [anthropics/skills](https://github.com/anthropics/skills) (license included in its directory).
