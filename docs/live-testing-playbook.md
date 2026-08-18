# Live testing playbook

**This project's own verified record of how to drive and observe a live Unreal editor session over MCP** — what works, what is a confirmed dead end, and which plausible-looking approaches produce confidently *wrong* results.

It starts nearly empty **on purpose**. It is meant to grow: every time an agent discovers a technique that works, burns time on one that cannot work, or gets fooled by one that appears to work, that finding lands here in the same change — not in a chat message that evaporates.

## Why this file exists

- **Rediscovery is expensive.** Without a written record, each agent re-derives the same dead ends from scratch, at full token cost, every session.
- **Some wrong approaches look like success.** A verification that reads a property and reports "pass" can be confidently wrong about the thing a human would notice instantly. Those entries are the most valuable ones here — they are the failures that survive review.
- **Agents read this before writing MCP verification code.** Anything not written down is not known.

## Findings

### Never call `time.sleep` in editor Python

**You'd assume:** sleeping inside an `execute_python_code` call lets the game advance so you can observe the next frame.
**What actually happens:** editor Python runs *on the game thread*. Sleeping blocks the thing you are waiting for — the world does not tick, and you get the same frame back after the wait.
**Instead:** sample across separate MCP calls. One call reads state, the next call reads it again; the gap between calls is real wall-clock time in which the game actually ticks.

### A visual or orientation criterion needs a screenshot

**You'd assume:** reading the actor's rotation, camera transform, or widget visibility flags proves the view is correct.
**What actually happens:** facing, camera framing, and orientation bugs pass every property read. The numbers are internally consistent; what the screen shows is wrong.
**Instead:** any acceptance criterion phrased in terms of what something *looks like* is verified with a screenshot, full stop. State the criterion so a screenshot can settle it.

### Verify what the player sees, not the editor viewport

**You'd assume:** the level editor viewport is a fair preview of the running game.
**What actually happens:** the editor viewport uses editor camera, editor visibility, and editor-only actors. It can look right while the player's view is broken (and vice versa).
**Instead:** capture from the running session's player view. If the criterion concerns a shipped build rather than PIE, verify in Standalone or the packaged build — those differ again.

### Scan the newest log after every session

**You'd assume:** if nothing threw visibly, the run was clean.
**What actually happens:** warnings, failed asset loads, and script errors land silently in `<UnrealProjectDir>/Saved/Logs/` while the session looks fine on screen.
**Instead:** after a session, read the newest log file there and scan for errors and warnings. Record any recurring benign noise here so future agents don't chase it.

## Adding an entry

Keep entries short and evidence-backed. Use this shape:

```markdown
### <Short title of the technique or trap>

**You'd assume:** <the plausible approach an agent would reach for>
**What actually happens:** <the real behaviour>
**Instead:** <the approach that actually works, or "confirmed dead end — don't retry">
**Evidence:** <what was run and what came back — command, tool call, screenshot, log line>
**Verified:** <YYYY-MM-DD>
```

Disproving an existing entry is just as valuable as adding one: edit it in place, note the date, and say what changed.
