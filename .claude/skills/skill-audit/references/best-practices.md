# Skill best-practices checklist

Distilled from Anthropic's Claude Code documentation, retrieved 2026-08-18:
- BP = https://code.claude.com/docs/en/best-practices
- SK = https://code.claude.com/docs/en/skills

Each item has an ID for citing in audit findings. When a documented limit and this file disagree with the live docs, the live docs win — re-check them if a finding is contested.

## T — Triggering (frontmatter `description`)

- **T1 — Description states what AND when.** The description is the primary triggering mechanism; Claude sees only name + description when deciding whether to load the skill. It must say what the skill does and the concrete contexts/user phrasings that should trigger it. All "when to use" information belongs in the description, not the body — the body is invisible until after the trigger decision. (SK, skill-creator)
- **T2 — Front-load and respect the cap.** The combined `description` + `when_to_use` text is truncated at 1,536 characters in the skill listing. Put the key use case in the first sentence; anything past the cap literally cannot influence triggering. (SK)
- **T3 — Counter undertriggering.** Claude tends to undertrigger skills. Descriptions should be a little pushy: name the trigger phrases, synonyms, and adjacent requests, including cases where the user doesn't use the skill's own vocabulary. (skill-creator guidance)
- **T4 — Side-effect workflows are manual.** A skill that performs actions with side effects the user should initiate (deploys, mass edits, publishing) should set `disable-model-invocation: true` so it only runs via `/name`. Background-knowledge skills users should never type can set `user-invocable: false`. (BP, SK)
- **T5 — File-scoped skills declare `paths`.** If a skill only applies when working on certain files (e.g. `**/*.tsx`), the `paths` frontmatter keeps it from loading elsewhere. (SK)

## C — Context economy

- **C1 — The body is a recurring token cost.** Once a skill loads, its content stays in context for the rest of the session. Keep SKILL.md under ~500 lines; state what to do rather than narrating; apply the CLAUDE.md test to every line: "would removing this cause mistakes?" If not, cut it. (BP, SK)
- **C2 — Progressive disclosure.** Detail that's only sometimes needed belongs in `references/` files, clearly pointed to from SKILL.md with guidance on when to read them. Reference files over ~300 lines need a table of contents. A skill supporting multiple variants/domains should split per-variant reference files so only the relevant one is read. (skill-creator, SK)
- **C3 — No orphaned or dead files.** Every bundled file should be referenced from SKILL.md; a reference/script nothing points to is either dead weight or silently unused. Conversely, SKILL.md must not point to files that don't exist.
- **C4 — Repeated work becomes a script.** If the skill makes Claude re-derive the same deterministic procedure every run (a conversion, a validation, a report format), bundle it once in `scripts/` and instruct to run it. (skill-creator)
- **C5 — Right home for the content.** Facts needed in *every* session belong in CLAUDE.md; procedures and sometimes-needed knowledge belong in skills; actions that must happen *every time without exception* belong in hooks, not skill prose. A skill instruction like "always run X after every edit" is a hook wearing a skill costume. (BP)

## W — Instruction quality

- **W1 — Explain why, not just MUST.** Rigid ALWAYS/NEVER walls degrade compliance; instructions that carry their reasoning generalize better and survive novel situations. All-caps emphasis is a yellow flag unless it's guarding something genuinely dangerous. (skill-creator, BP)
- **W2 — Imperative, specific, example-backed.** Prefer imperative form; name exact files, commands, and formats instead of describing them vaguely; include input/output examples for formats the skill must produce. (skill-creator, BP "provide specific context")
- **W3 — Build in verification.** A workflow skill should give Claude a check it can run (a test, a build, a script, a screenshot comparison) and require evidence of success rather than assertion. Without a check, "looks done" is the only signal. (BP "give Claude a way to verify its work")
- **W4 — Don't overfit.** Instructions tuned to one past example (hardcoded filenames from a single incident, one project's quirks in a general-purpose skill) make the skill worse everywhere else. Generalize the principle, keep the example as an example. (skill-creator)
- **W5 — Scope investigations.** A skill that tells Claude to "explore" or "investigate" without bounds invites context flooding. Scope the exploration or direct it into a subagent. (BP "infinite exploration" failure pattern)

## F — Frontmatter and mechanics

- **F1 — Only real fields.** Valid Claude Code fields: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility`. Unknown fields are at best ignored; a typo'd field name (e.g. `tool-allowlist`) silently does nothing. (SK frontmatter reference)
- **F2 — Name is display-only; the directory is the command.** For personal/project skills the directory name IS the `/command`; frontmatter `name` only changes the listing label. Renaming a directory breaks every habit and doc that references the old command. (SK)
- **F3 — Pre-approve bundled scripts properly.** A skill whose body says "run `${CLAUDE_SKILL_DIR}/scripts/x.sh`" should mirror that in `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/x.sh *)` so it runs without a prompt; the substitution works in both places. (SK)
- **F4 — Arguments used correctly.** If the skill expects arguments, declare `argument-hint` (autocomplete) and use `$ARGUMENTS` / named `arguments` in the body. `$ARGUMENTS` absent from content means arguments get appended as a bare `ARGUMENTS:` line — fine, but only if the instructions read that way.
- **F5 — Portability if it leaves Claude Code.** Skills destined for claude.ai upload / the Skills API / `package_skill.py` may use only `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` — anything else fails the upload with a hard error. Dynamic context (`` !`cmd` ``), `@` references, and `${CLAUDE_*}` substitutions don't function outside Claude Code. Only flag this for skills actually intended to be distributed that way. (SK)

## M — Maintenance signals

- **M1 — Stale facts.** Version pins, URLs, tool names, and paths inside a skill rot. Anything that names a file, flag, or command that no longer exists is a defect, not a nitpick.
- **M2 — Attribution intact.** Third-party or adapted skills keep their attribution lines and LICENSE files verbatim. Their absence after an edit is a regression.
- **M3 — Duplication across skills.** Two skills carrying divergent copies of the same procedure will drift. Prefer one owner and a pointer.

## Not findings

House style, tone preference, synonym swaps, reordering that saves nothing, and "I would have written it differently." The audit exists to catch documented-practice violations and real defects, not to homogenize voice. When in doubt, the test is: *which checklist item does this violate, and what concretely improves if changed?* No answer → not a finding.
