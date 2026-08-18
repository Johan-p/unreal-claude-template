# The build workflow

A visual map of how a feature travels from idea to shipped. **`/feature-flow` is the authority on state transitions** — it reads the actual frontmatter and tells you what's next; this page is the picture, not the rulebook. If the two ever disagree, the skill wins and this page needs fixing.

```
╔══════════════════════════════════════════════════════════════════════════╗
║  FEATURE LIFECYCLE           /feature-flow reports state + what's next    ║
╚══════════════════════════════════════════════════════════════════════════╝

    IDEA
     │
     │   /brainstorm ....... interview until the design tree is resolved
     │                       main session · Opus earns its keep here
     ▼
    /feature ............... one-page functional brief: why, what, DoD
     │                       → docs/features/NNNN-slug.md    [Draft → Ready]
     ▼
    architect .............. AGENT · opus · writes specs, never code
     │                       → docs/architect/NNNN-slug.md
     │                         options + recommendation · class/asset list
     │                         tuning values · verification step
     ▼
    /to-slices ............. 3–6 vertical tracer-bullet slices, each a
                             complete pass through every layer
                             → docs/slices/NNNN-slug/MM-name.md   [draft]


┌────────────────────────── PER SLICE, IN ORDER ───────────────────────────┐
│                                                                          │
│   [draft] ──── maintainer reviews ────► [ready]                          │
│                                            │                             │
│                                            ▼                             │
│   /tdd  ──dispatches──►  builder ....... AGENT · sonnet                  │
│                          one test → minimal code → green    [in_progress]│
│                          never refactors while red                       │
│                                            │                             │
│                          tests green ──────┘                    [gated]  │
│                                            │                             │
│                                            ▼                             │
│   /release-gate Mode D ......... runs in the MAIN SESSION                │
│   (a subagent can't reliably dispatch subagents)                         │
│            │                                                             │
│            │   ┌──────────────────────────────────────────┐              │
│            └──►│ reviewer ......... AGENT · sonnet         │             │
│                │                    READ-ONLY (enforced)   │             │
│                │  step 0   review_prepass.py — mechanical  │             │
│                │           hygiene scan of ADDED lines     │             │
│                │  lens 1   correctness                     │             │
│                │  lens 2   test quality                    │             │
│                │  lens 3   spec + convention compliance    │             │
│                │  lens 4   visual fidelity (screenshots)   │             │
│                │  lens 5   hygiene                         │             │
│                └────────────────────┬─────────────────────┘              │
│                                     │                                    │
│                   APPROVE ◄─────────┴─────────► findings                 │
│                      │                              │                    │
│                      │              builder fixes ◄─┘                    │
│                      │                    │                              │
│                      │                    └──► re-review                 │
│                      │                          ≤ 5 iterations, then     │
│                      │                          DEADLOCK — stop, report, │
│                      │                          slice stays [gated]      │
│                      ▼                                                   │
│                  [merged] ◄── main session flips the frontmatter         │
│                      │        and commits BOTH repos                     │
└──────────────────────┼───────────────────────────────────────────────────┘
                       │
        more slices? ──┤── yes ──► next [ready] slice
                       │
                       ▼ all slices [merged]

╔══════════════════════════════════════════════════════════════════════════╗
║  FEATURE BOUNDARY — these run ONCE, never per slice                      ║
╚══════════════════════════════════════════════════════════════════════════╝
     │
     ├── tester ........... AGENT · sonnet · token-heavy, never auto-invoked
     │                      real PIE session, screenshots per stage,
     │                      log scan, pass/fail per DoD bullet
     │                      marks NEEDS-HUMAN when skill is required
     │
     ├── documenter ....... AGENT · sonnet
     │                      → docs/handbook/ + README.md, plain English
     ▼
    brief marked Shipped
```

## Where the reference skills come in

They have no stage of their own. The `ue-*` roster and `pcg-authoring` are an **ambient knowledge layer** underneath the pipeline: nothing dispatches them, and no gate depends on them. They load themselves into whichever agent is working, whenever that agent's task matches their description.

```
╔══════════════════════════════════════════════════════════════════════════╗
║  AMBIENT KNOWLEDGE — no stage; loads on description match                 ║
╚══════════════════════════════════════════════════════════════════════════╝

   26 × ue-* skills           pcg-authoring          live-testing-playbook
   UE C++ patterns, one       PCG composition +      (a doc, not a skill —
   per engine domain          MCP authoring          read explicitly)
          │                         │                        │
          └───────────┬─────────────┴────────────────────────┘
                      │   auto-trigger · no dispatch · no wiring
      ┌───────────────┼───────────────┬──────────────────────┐
      ▼               ▼               ▼                      ▼
  architect        builder         reviewer            main session
  "what does       "how do I       "is this the        "is this even
   the engine       write this      idiomatic way?"     feasible?"
   support?"        correctly?"                         (/brainstorm)

              Skills advise. The architect spec decides.
                    On conflict, the spec wins.
```

Verified 2026-08-18: a subagent sees the complete skill list — all 26 `ue-*` and `pcg-authoring` included, under bare names — so the builder really can load them mid-dispatch. Nothing in any agent's prompt points at them, which is by design: matching is the trigger mechanism, not instruction.

Two consequences worth knowing. First, **loading is invisible** — you cannot tell from a builder's report whether `ue-input-system` actually fired for an input slice. Second, **matching cuts both ways**: a skill whose trigger words collide with your project's everyday vocabulary will load hundreds of irrelevant lines mid-task. A skill triggering on "implementing AI" fires on any mention of an AI opponent; one triggering on "state machine" fires on a plain enum state machine. Worth auditing the descriptions of the `ue-*` skills against the words your project actually uses, and narrowing the ones that collide.

`pcg-authoring` is the one skill here written *from* real project work rather than installed off the shelf — extracted from a set-dressing rebuild after dissecting Epic's Electric Dreams sample. It carries composition patterns and verified MCP recipes, and hands raw node/class lookups off to `ue-procedural-generation`. Skills you extract from your own build work belong in the same ambient layer.

## Who may touch what

Ownership is no longer advisory in the two places it matters most — a `PreToolUse` hook enforces it, reading the Unreal project location from `LOCAL.md` so it survives a machine move.

```
  ┌─ SCAFFOLD REPO ────────────────┐   ┌─ UNREAL PROJECT (LOCAL.md) ─────┐
  │ docs/  .claude/  CLAUDE.md     │   │ Source/  Config/  Content/  Art/│
  │                                │   │                                 │
  │ main session ......... all     │   │ builder .............. all      │
  │ architect ... docs/architect/  │   │   (assets via MCP only,         │
  │               ONLY (hook)      │   │    never raw .uasset bytes)     │
  │ documenter .. docs/handbook/   │   │                                 │
  │               + README.md      │   │ Plugins/VibeUE/ — separate repo,│
  │ builder ............. NONE     │   │   nobody edits in feature work  │
  │               (hook)           │   │   (hook)                        │
  └────────────────────────────────┘   └─────────────────────────────────┘

  reviewer + tester ... read-only everywhere (disallowedTools, structural)
  commits ............. main session only, in both repos. Agents never commit.
```

## The rules that keep it honest

- **Skills advise, architect specs decide.** On conflict the spec wins.
- **The gate cannot be talked open.** No reviewer run means no gate. Only the maintainer may accept a finding, and never a `BLOCKER`.
- **Evidence, not assertion.** Every agent reports what it ran and what came back. A green it didn't run is a fabrication, not a mistake.
- **Serialized by the editor.** C++ builds need it closed, asset work needs it open — which is why there is exactly one builder and no parallel split.
