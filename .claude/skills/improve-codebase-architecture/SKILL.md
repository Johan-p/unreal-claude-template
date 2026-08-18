---
name: improve-codebase-architecture
description: Find deepening opportunities in this codebase — refactors that turn shallow modules into deep ones to improve testability and AI-navigability. Use when the maintainer wants to audit the codebase, find refactoring opportunities, consolidate tightly-coupled modules, or make the code easier for agents to work with. Adapted from mattpocock/skills. Produces an HTML report with before/after diagrams in the OS temp dir — does NOT modify code.
---

# /improve-codebase-architecture — find deepening opportunities

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability. Pocock's argument: *"Your codebase, way more than your prompt or your AGENTS.md file, is the biggest influence on AI's output."* Deep modules give callers leverage and concentrate maintenance locality; shallow modules force every agent session to re-derive the same context.

This skill is **read-only**. It writes one HTML report to the OS temp dir and nothing else. It does not edit code, does not write to `docs/`, does not commit. Refactor work is dispatched separately to this project's builder agent(s), once defined, after the maintainer picks candidates.

---

## Glossary — use these terms exactly

Consistent language is the point. Don't drift into "component," "service," "API," or "boundary."

- **Module** — anything with an interface and an implementation. Scale-agnostic: function, class, file, package, slice. _Avoid_: unit, component, service.
- **Interface** — everything a caller must know to use the module: types, invariants, ordering, error modes, required config, performance characteristics. _Avoid_: API, signature (those refer only to the type-level surface).
- **Implementation** — what's inside a module.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** (Feathers) — a place where behaviour can be altered without editing in place. The *location* where an interface lives. _Avoid_: boundary (overloaded with DDD).
- **Adapter** — a concrete thing that satisfies an interface at a seam. Names a role, not substance.
- **Leverage** — what callers get from depth. More capability per unit of interface they have to learn.
- **Locality** — what maintainers get from depth. Change, bugs, knowledge concentrate at one place.

### Principles

- **Depth is a property of the interface, not the implementation.** A deep module can be internally composed of small, mockable, swappable parts — they just aren't part of the interface.
- **Deletion test.** Imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.** Callers and tests cross the same seam. If you want to test *past* the interface, the module is the wrong shape.
- **One adapter = hypothetical seam. Two adapters = real seam.** Don't introduce a port unless at least two adapters are justified (typically production + test).
- **Internal vs external seams.** A deep module can have internal seams (private, used by its own tests) as well as its external seam at the interface. Don't expose internal seams through the interface just because tests use them.

### Rejected framings

- **Depth as lines-of-implementation ÷ lines-of-interface** (Ousterhout's original): rewards padding the implementation. We use depth-as-leverage instead.
- **"Interface" as the TypeScript `interface` keyword**: too narrow.
- **"Boundary"**: overloaded with DDD's bounded context. Use **seam** or **interface**.

---

## Process

### 1. Explore

Read the project's documented context first:

- `CLAUDE.md` — repo conventions, agent set, file ownership contract.
- `docs/architect/` — every technical spec the `architect` agent has produced. These encode prior deepening decisions.
- `docs/adr/` — load-bearing architectural decisions (e.g. a foundational tenancy or security model). Do not propose refactors that contradict an ADR unless the friction is real enough to warrant reopening the ADR — and even then, flag it explicitly.
- `docs/data-model.md`, if it exists — schema rationale. (Most UE game projects have no database; skip if so.)
- `docs/CONTEXT.md` if it exists — ubiquitous-language glossary. If this file doesn't exist yet and your exploration uncovers candidate domain terms worth naming, list them at the end of the report as "glossary candidates" for the maintainer to fold in once the file exists.

Then use the Agent tool with `subagent_type=Explore` to walk this project's source tree — `<UnrealProjectDir>\Source\<Module>\` (LOCAL.md) — organically. Don't follow rigid heuristics — explore and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

**Likely areas to inspect** (don't limit to these — they're priors, not prescriptions; replace with this project's actual layout):

- **The pure-logic layer** (whatever folder CLAUDE.md designates for engine-independent rules) — deep by design (pure logic, fully unit-tested). Is that still true, or has view/actor logic leaked in?
- **Per-feature gameplay folders** — features built sequentially invite copy-paste drift. Where do near-identical actor classes differ only by constants that belong in a shared header?
- **The shared/common folder** — the designated home for cross-feature constants and helpers. Is it earning its keep, or are features re-declaring what it owns? (In a UE project this matters doubly: unity builds turn two identically-named anonymous-namespace constants in different files into a compile error the moment they land in the same translation unit.)
- **View actors and widgets** — look for actors that exist only to forward properties between the logic layer and a mesh/widget (props-pass-through, no leverage).
- **Config/tunables ownership** — values that should live in config or a tuning settings class but are hardcoded per feature.

### 2. Write the report

Write a single self-contained HTML file to `<tmpdir>/architecture-review-<timestamp>.html`. On this Windows machine, resolve `<tmpdir>` to the session scratchpad directory (preferred) or `$env:TEMP`. Each run produces a fresh file.

After writing, open it (`Start-Process <path>` in PowerShell) and tell the maintainer the absolute path. **Also mention that if the findings will drive follow-up work, the maintainer can archive the report by copying it to `docs/audits/<YYYY-MM-DD>-architecture-review.html`** (create `docs/audits/` on first use) — temp dirs are ephemeral; archived runs survive reboots and stay referenceable across sessions.

**Scaffold:**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review — [project name]</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
    </script>
    <style>
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
      <section id="glossary-candidates">...</section>
    </main>
  </body>
</html>
```

**Header:** repo name, date, compact legend (solid box = module, dashed line = seam, red arrow = leakage, thick dark box = deep module). No introduction paragraph — straight into the candidates.

**Each candidate is one `<article>`:**

- **Title** — short, names the deepening (e.g. "Collapse the request-validation pipeline").
- **Badge row** — recommendation strength (`Strong` = emerald, `Worth exploring` = amber, `Speculative` = slate). Dependency category tag: `in-process`, `local-substitutable`, `ports & adapters`, `mock` (see Dependency strategy below).
- **Files** — monospaced list of the actual paths involved (`font-mono text-sm`).
- **Before / After diagram** — the centrepiece. Two columns, side by side. See patterns below.
- **Problem** — one sentence. What hurts.
- **Solution** — one sentence. What changes.
- **Wins** — bullets, ≤6 words each. e.g. "tests hit one interface", "validation logic stops leaking", "delete 3 shallow wrappers".
- **ADR conflict callout** (if applicable) — one line in an amber-tinted box. e.g. *"contradicts ADR-0007 tenancy-isolation seam — only reopen if friction is severe."*

No paragraphs of explanation. If the diagram needs a paragraph to be understood, redraw the diagram.

**Diagram patterns — mix them, don't make every diagram look the same:**

- **Mermaid `flowchart`** — for dependencies / call flow. Use `classDef` to colour leakage edges red and the deep module dark. Wrap in a Tailwind card.
- **Hand-built boxes + inline SVG arrows** — when you want a thick-bordered "deep module" with greyed-out internals (Mermaid won't render that weight).
- **Cross-section** — stack horizontal bands to show layers a call passes through. Before: many thin layers each doing nothing. After: one thick band.
- **Mass diagram** — two rectangles per module (interface surface vs implementation surface). Before: interface nearly as tall as implementation. After: interface short, implementation tall.
- **Call-graph collapse** — tree of nested boxes before; one box with faded internal calls after.

**Style guidance:**

- Lean editorial, not corporate-dashboard. Generous whitespace.
- Colour sparingly: one accent (emerald or indigo), red for leakage, amber for warnings.
- Diagrams ~320px tall so before/after sit side by side without scrolling.
- Module labels inside diagrams: `text-xs uppercase tracking-wider`.

**Tone — exactly these terms:** module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality.
**Never substitute:** component, service, unit (for module) · API, signature (for interface) · boundary (for seam) · layer, wrapper (for module).

**Wins bullets** name the gain in glossary terms: *"locality: bugs concentrate in one module"*, *"leverage: one interface, N call sites"*, *"interface shrinks; implementation absorbs the wrappers"*. Don't write *"easier to maintain"* or *"cleaner code"* — those aren't in the glossary.

**Top recommendation section:** one larger card. Candidate name, one sentence on why, anchor link to its card. That's it.

**Glossary candidates section (project-specific):** if your exploration surfaced domain terms worth standardizing (e.g. two near-synonym nouns used inconsistently, an ambiguous status enum, a term that means different things in different modules), list them here with a one-sentence proposed definition each. The maintainer will use these when creating `docs/CONTEXT.md`.

### 3. Hand back to the maintainer

After writing the file, **stop and ask:** *"Which of these would you like to explore?"*

Do NOT propose interfaces yet. Do NOT dispatch builders. The maintainer drives the next move.

### 4. Grilling loop (after the maintainer picks a candidate)

Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects happen inline as decisions crystallize:

- **Naming a deepened module after a concept not in `docs/CONTEXT.md`?** Note it as a glossary candidate (the maintainer will add it; this skill does not write to `docs/CONTEXT.md`).
- **Maintainer rejects the candidate with a load-bearing reason?** Offer to record it as an ADR via the architect agent — framed as: *"Want me to ask the architect to record this as ADR-NNNN so future audits don't re-suggest it?"* Only offer when the reason would actually be needed by a future audit to avoid re-suggesting the same thing.
- **Candidate requires a real schema/module-boundary change?** Hand off to the `architect` agent — this skill does not encode load-bearing design decisions.
- **Candidate is ready for implementation?** Hand off to this project's relevant builder agent, once defined, with the deepening described in glossary terms.

---

## Dependency strategy

When assessing a candidate, classify its dependencies. The category determines how the deepened module is tested across its seam.

### 1. In-process

Pure computation, in-memory state, no I/O. Always deepenable — merge the modules and test through the new interface directly. No adapter needed.

**Examples likely to fit:** date/time math, string parsing and formatting, validation logic, diffing/normalization routines — anything that takes plain data in and returns plain data out.

### 2. Local-substitutable

Dependencies with local test stand-ins. Deepenable if the stand-in exists. The deepened module is tested with the stand-in; seam is internal, no port at the external interface.

**Example:** an ORM or database client run against an in-memory database or a containerized test instance. If no such stand-in exists yet, recommendations in this category should note whether one needs to be built first.

### 3. Remote but owned (Ports & Adapters)

Your own services across a network boundary. Define a **port** at the seam. The deep module owns the logic; transport is injected as an adapter. Tests use in-memory; production uses HTTP.

This project currently has no first-party services reached over a network boundary — category 3 is empty. Revisit if online features ever land.

### 4. True external (Mock)

Third-party services (auth providers, payment processors, external APIs). The deepened module takes the dependency as an injected port; tests provide a mock adapter.

**Example:** a third-party auth provider's webhook handling. The handler logic should be deep; the provider's transport thin.

### Seam discipline

- **One adapter = hypothetical seam.** Two adapters = real one. Don't add a port for a single-adapter situation — that's just indirection.
- **Internal seams vs external seams.** Don't expose internal seams through the interface just because tests use them.

### Testing strategy: replace, don't layer

- Old unit tests on shallow modules become waste once tests at the deepened module's interface exist — delete them.
- Write new tests at the deepened module's interface. The **interface is the test surface**.
- Tests assert on observable outcomes through the interface, not internal state.
- Tests should survive internal refactors — they describe behaviour, not implementation.

---

## Interface design (when the maintainer wants alternatives)

If the maintainer wants to explore alternative interfaces for a chosen candidate, use a parallel sub-agent pattern. Based on Ousterhout's "Design It Twice": your first idea is unlikely to be the best.

### 1. Frame the problem space

Write a user-facing explanation of the problem space for the chosen candidate:

- Constraints any new interface must satisfy.
- Dependencies and which category they fall into (see above).
- A rough illustrative code sketch to ground the constraints — not a proposal, just a way to make constraints concrete.

Show this to the maintainer, then immediately proceed to spawn sub-agents — they read while the agents work in parallel.

### 2. Spawn sub-agents

Spawn 3+ agents in parallel via the Agent tool. Each must produce a **radically different** interface for the deepened module. Use `Explore` for read-only analysis and this project's design/architecture agent (e.g. `architect`) for actual design proposals.

Give each agent a different design constraint:

- Agent 1: "Minimize the interface — 1–3 entry points max. Maximise leverage per entry point."
- Agent 2: "Maximise flexibility — support many use cases and future extension."
- Agent 3: "Optimise for the most common caller — make the default case trivial."
- Agent 4 (if applicable): "Design around ports & adapters for cross-seam dependencies."

Each agent outputs:

1. Interface (types, methods, params — plus invariants, ordering, error modes).
2. Usage example showing how callers use it.
3. What the implementation hides behind the seam.
4. Dependency strategy and adapters.
5. Trade-offs — where leverage is high, where it's thin.

### 3. Present and compare

Present designs sequentially. Compare by **depth**, **locality**, and **seam placement**. Give an opinionated recommendation — the maintainer wants a strong read, not a menu. If a hybrid of two designs is strongest, propose it.

---

## When NOT to use this skill

- **In-line with a feature ship.** This is preventive maintenance, not part of the build pipeline. Don't insert it between `/feature` and `/release-gate`.
- **For one obvious refactor.** If a specific shallow module is already known, dispatch the relevant builder directly with the refactor description. This skill is for surfacing candidates, not executing known fixes.
- **Right after a major schema change.** Let the new shape settle for a few features before auditing. A fresh schema looks shallow by definition because no callers have exercised it yet.
- **As a substitute for the architect.** Load-bearing design decisions still go through the `architect` agent, which writes specs to `docs/architect/NNNN-slug.md`. This skill identifies opportunities; the architect decides the shape.

---

## Output contract

After running, the maintainer should see:

1. **Console output:** absolute path to the HTML report, count of candidates by strength (`N strong, M worth exploring, K speculative`), one-line summary of the top recommendation.
2. **HTML file** at `<tmpdir>/architecture-review-<timestamp>.html` containing the full report.
3. **Glossary candidates** section in the report listing domain terms worth standardizing (input to `docs/CONTEXT.md`).
4. **No file changes** under the source tree, `docs/`, or anywhere else in the repo.

Next step after the report is reviewed:

- *"Address candidate N now"* → dispatch the relevant builder or architect agent.
- *"Shelf candidate N for Phase 2"* → no file change; note in the brief / PR description of the relevant work when it lands.
- *"Reject candidate N — ADR worth"* → dispatch `architect` to write the ADR.
