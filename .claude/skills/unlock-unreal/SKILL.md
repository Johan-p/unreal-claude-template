---
name: unlock-unreal
description: Unlock any Unreal project for agent control — enables the MCP plugin stack, Python and Remote Control, converts a Blueprint-only project to C++ if the user agrees, installs and builds the Johan-p/VibeUE fork, configures the servers to auto-start with the editor, and verifies the whole pipe with a live round trip. Run it per project, as often as needed: unlocking a second or fifth project in an existing workspace is the normal case, not just first-time setup. Use when the user asks to set up VibeUE, enable unreal-mcp, connect or fix the Unreal MCP connection, enable Python or Remote Control in Unreal, drive a new Unreal project with Claude Code, or asks why an editor isn't responding to MCP.
disable-model-invocation: true
argument-hint: "[path to the Unreal project, if LOCAL.md doesn't name it yet]"
---

# /unlock-unreal — make an Unreal project drivable by an agent

Take a project from "just an Unreal project" to "fully drivable by an agent, and it comes back up that way on every launch."

**This is per-project, not per-workspace.** Most runs will be unlocking a new project inside a workspace that is already set up — skip anything already done rather than re-asking, and don't recommend workspace setup skills to someone who already has a working CLAUDE.md.

**What actually enables what** — keep this straight or the ordering makes no sense:

- **Filesystem + shell** do all the *setup*: enabling plugins is a `.uproject` edit, auto-start is an `.ini` edit, VibeUE is a `git clone` plus a build. None of it needs a live editor.
- **MCP** is the *runtime* channel: driving the editor and, critically, **proving the setup worked**. A build exit code cannot tell you a plugin functions.
- These are mutually exclusive during the build: C++ compilation needs the editor **closed**, which kills MCP. Do all the building first, then launch and verify.

Report evidence at every step. A setup skill that claims success without probing the server is worse than no skill.

## Step 0 — Locate the project and engine

1. **Engine.** Registry `HKLM:\SOFTWARE\EpicGames\Unreal Engine\<ver>` → `InstalledDirectory`, cross-checked against the `.uproject`'s `EngineAssociation`. If the registry is unhelpful, take the path from `LOCAL.md` or ask.
2. **Project.** Resolve from `LOCAL.md`. **If LOCAL.md is missing or incomplete, run `/setup-local-md` and come back** — don't hand-roll a minimal one here. That skill verifies every path exists before writing it, which this one depends on; two places that both know how to create LOCAL.md would drift, and the unverified copy would be the one that lies.

   **Adding a second (or fifth) project to an existing workspace is the normal case**, not an exception. Give it its own LOCAL.md key rather than overloading `<UnrealProjectDir>` — a short name matching the project (`GameAnimSampleDir`, `MyGameDir`) — and record next to it anything that makes this project different: Blueprint-only, no VibeUE, a non-default MCP port. Every later reference then goes through that key, so nothing hardcodes a path.
3. **Close the editor if it is running** — everything below either edits config it has loaded, or needs it closed to build.

## Step 1 — C++ project? Decide before installing anything

VibeUE is a **C++ editor plugin**; it needs a project module to compile against. A Blueprint-only project has none, and no plugin toggle changes that.

**Check:** `Source/` containing `*.Target.cs`, plus a `Modules` array in the `.uproject`. Both present → C++, continue. Either missing → **stop and ask the user**, framing it honestly:

> This project is Blueprint-only, so VibeUE can't be installed as-is. Worth knowing before you decide:
>
> **MCP works without VibeUE.** `unreal-mcp` comes from Epic's built-in `ModelContextProtocol` plugin — VibeUE registers *extra* toolsets into that same server. Without converting you still get ~19 typed Epic toolsets: actors, assets, blueprints, materials, meshes, scene, PIE, and annotated viewport screenshots.
>
> **Converting adds** VibeUE's ~26 authoring toolsets — Blueprint, Widget/UMG + MVVM, Material graphs, MetaSound, Niagara (incl. scratch-pad HLSL), Landscape, Foliage, animation (AnimGraph/Montage/Sequence/Skeleton), UV mapping, undo/redo, and Unreal Insights profiling — plus `execute_python_code` and the `discover_python_*` tools. Epic's set is strong at *inspecting and arranging*; VibeUE is about *authoring*.
>
> **It costs:** a `Source/` module in the project, and from then on every C++ build needs the editor closed.

**Only on a yes**, convert. It is additive — the sole pre-existing file that changes is the `.uproject`:

1. **Back up `<Project>.uproject`** → `.uproject.bak`. Say so out loud if the project has no version control.
2. **Write the module** (names must match the project exactly):
   - `Source/<Project>.Target.cs` / `Source/<Project>Editor.Target.cs` — `TargetType.Game` / `.Editor`, `DefaultBuildSettings = BuildSettingsVersion.V7`, `IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8`, `ExtraModuleNames.Add("<Project>")`
   - `Source/<Project>/<Project>.Build.cs` — `PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs`, public deps `Core, CoreUObject, Engine, InputCore`
   - `Source/<Project>/<Project>.h` (`#pragma once` + `CoreMinimal.h`) and `.cpp` with `IMPLEMENT_PRIMARY_GAME_MODULE( FDefaultGameModuleImpl, <Project>, "<Project>" );`
3. **Add to the `.uproject`** before `Plugins`: `"Modules": [ { "Name": "<Project>", "Type": "Runtime", "LoadingPhase": "Default" } ]`, then re-parse to confirm the JSON is still valid.

The module stays empty deliberately: it exists so the project *is* C++. Project content is untouched.

**To reverse everything:** restore `.uproject.bak`, delete `Source/`, `Plugins/VibeUE`, `Binaries/`, `Intermediate/`.

## Step 2 — Enable the plugins (a `.uproject` edit, not a human step)

Read the `.uproject`'s `Plugins` array and add whatever is missing, as `{ "Name": "<X>", "Enabled": true }`:

| Plugin | Gives you |
|---|---|
| `ModelContextProtocol` | **the `unreal-mcp` server itself** |
| `MCPClientToolset` | client-side toolset plumbing |
| `EditorToolset` | Epic's editor toolsets (actors, assets, scene, PIE, screenshots) |
| `PythonScriptPlugin` | `import unreal` scripting |
| `EditorScriptingUtilities` | editor automation library Python leans on |
| `RemoteControl` | HTTP/WebSocket API (`:30010` / `:30020`) |

Re-parse the JSON afterwards. Plugin *dependencies* auto-enable on load, so expect the first launch after this to be slower.

## Step 3 — Install the VibeUE fork (C++ projects only)

Work from the fork, never upstream — it carries our own edits:

```powershell
git clone https://github.com/Johan-p/VibeUE "<UnrealProjectDir>\Plugins\VibeUE"
```

Already a git repo there → `git pull` instead, and report the before/after commit. Never pull from or push to the upstream `kevinpbuckley` repo.

## Step 4 — Build (editor must be closed)

```powershell
& "<UnrealEngineDir>\Engine\Build\BatchFiles\Build.bat" <Project>Editor Win64 Development -Project="<UnrealProjectDir>\<Project>.uproject" -WaitMutex
```

Success is `Result: Succeeded` / exit 0. Budget ~8 minutes for a fresh module plus the whole VibeUE plugin; run it in the background and tail the log rather than blocking. On failure, report the compile errors verbatim — do not work around them.

## Step 5 — Make the servers come up on their own

The goal is that a plain editor launch is enough — no console commands, ever again.

**MCP does not auto-start by default.** Its settings class is `config=EditorPerProjectUserSettings`, so write to `Config/DefaultEditorPerProjectUserSettings.ini`:

```ini
[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
bAutoStartServer=True
ServerPortNumber=8000
```

**Remote Control already auto-starts** — `bAutoStartWebServer` and `bAutoStartWebSocketServer` both default to `true` (HTTP `30010`, WebSocket `30020`). Nothing to do unless the user wants different ports. There is no need for the `WebControl.StartServer` console command that older guides recommend.

**`.mcp.json`** — the folder Claude Code runs in needs the server registered. Write it if absent:

```json
{ "mcpServers": { "unreal-mcp": { "type": "http", "url": "http://127.0.0.1:8000/mcp" } } }
```

**One editor at a time — by design, not by limitation.** Port 8000 is shared, so only the running editor serves MCP. Don't treat that as something to engineer around: a machine that runs Unreal comfortably usually runs exactly one instance of it, and a second editor competes for the RAM the first one needs. Check `LOCAL.md` for this machine's constraints, and when switching projects, **close the open editor first** rather than reaching for a second port.

## Step 6 — Launch and verify honestly

1. **Launch** the editor. First boot after a plugin change is slow.
2. **Server up:** probe `http://127.0.0.1:8000/mcp` — any HTTP response proves it is listening (a bare GET correctly returns **405**, since it wants POST). Connection refused means auto-start did not take or the editor is not up yet; poll rather than concluding.
3. **Tools bound:** a responding server does not mean this session can use it yet. The harness re-attaches lazily — make a cheap call or two, re-check the tool list, and only fall back to asking the user for `/mcp` reconnect if the tools are still absent after the server is confirmed responding.
4. **Round trip — this is the step that counts.** `list_toolsets`, then a real call returning real data (e.g. `SceneTools.get_current_level`). Expect ~19 Epic toolsets, plus ~26 more if VibeUE is installed.
5. **VibeUE specifically:** confirm `execute_python_code` exists and run something that reads real project data. "The DLL loaded" is not proof the plugin works.
6. **Python:** confirm from the editor log — `LogPython: Using Python <version>`.

## Step 7 — Generate the agent guide (VibeUE only)

```
VibeUE.GenerateAgentConfig ClaudeCode
```

Run it via MCP (`execute_python_code` → `unreal.SystemLibrary.execute_console_command`) or ask the user. It writes a CLAUDE.md into the project folder; suggest importing it (`@<UnrealProjectDir>\CLAUDE.md`) and re-running after plugin updates.

## Optional — open Remote Control for scripting

Only relevant if the user declined the C++ conversion (VibeUE already gives Python), or wants HTTP access from other tools. **Present it as a security decision, not a fix** — Remote Control ships deny-by-default on purpose.

**Trap 1 — one flag is not enough.** `bAllowAnyRemoteFunctionCall` alone does **not** enable Python or console commands; the engine gates those behind their own flags regardless.

**Trap 2 — the listeners are not all on loopback.** `RemoteControlSettings.h` defaults the HTTP server to `127.0.0.1` but the **WebSocket and web-interface bind addresses to `0.0.0.0`**. Combine that with the execution flags and an unmodified config publishes an arbitrary-code-execution surface to the entire local network, leaving the host firewall as the only thing standing in the way. This is easy to miss because the port everyone tests — 30010 — looks correctly bound.

Write all of these together, and never the execution flags without the bind addresses (note the module is **RemoteControlCommon**, not RemoteControl):

```ini
[/Script/RemoteControlCommon.RemoteControlSettings]
bAllowAnyRemoteFunctionCall=True
bEnableRemotePythonExecution=True
bAllowConsoleCommandRemoteExecution=True
bRestrictServerAccess=True
bEnforcePassphraseForRemoteClients=True

; Engine defaults these two to 0.0.0.0 — pin them to loopback.
RemoteControlWebsocketServerBindAddress=127.0.0.1
RemoteControlWebInterfaceBindAddress=127.0.0.1
```

Keep `bRestrictServerAccess=True`: it is the engine's own edit-condition for the execution flags, and it gates off-machine callers behind the allowlist and passphrase. Treat the bind addresses as the real boundary though — an allowlist you have not populated is a policy, while a socket bound to loopback is a fact.

**Verify rather than assume.** After applying, confirm every listener is loopback:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000,30010,30020 | Select-Object LocalAddress, LocalPort
```

Every row must read `127.0.0.1`. A `0.0.0.0` means the change did not take. Applying the bind addresses live via MCP `ObjectTools.set_properties` rebinds the socket immediately — no restart needed — so this is checkable on the spot.

To apply without a restart, set the same properties live via MCP `ObjectTools.set_properties` on `/Script/RemoteControlCommon.Default__RemoteControlSettings`. Call Python with `ExecutePythonCommandEx` and `ExecutionMode: ExecuteFile` — `EvaluateStatement` takes a single expression and throws `SyntaxError` on anything multi-line.

## Report

Close with a checklist: engine found, C++ status (native or converted, with the user's decision recorded), plugins enabled, VibeUE commit, build result, auto-start config written, server probe, **round-trip evidence**, Python confirmed, agent guide, and Remote Control posture. Then what remains for the human — anything that exists only as an editor checkbox with no config equivalent.

**Never report the setup as working without the Step 6 round trip.** "Should work now" is not evidence.

### Hand off — but only where it applies

**This skill runs in two situations, and the common one is the second:**

- **A brand-new workspace** — no CLAUDE.md worth the name, no LOCAL.md. Rare; happens once per machine.
- **An existing workspace unlocking another project** — CLAUDE.md and LOCAL.md are already good, and a new Unreal project just needs the plugin stack, VibeUE and verification. This is the usual case for anyone who works across several projects.

Tell them apart before closing: a CLAUDE.md that exists, has no `[FILL IN]` markers, and already carries build and test commands means the workspace is set up. Do **not** suggest re-running the setup skills in that case — recommending a CLAUDE.md interview to someone who already has a good one is noise at best, and at worst it invites a rewrite of a working file.

**Existing workspace (the usual close):**

> `<Project>` is drivable — MCP verified, VibeUE registered. Its path is in LOCAL.md as `<KeyName>`.
> To work on a different project, close this editor and open that one — only the running editor serves MCP.

**Fresh workspace only:**

> Two things left to make this workspace yours:
> - **`/setup-claude-md`** — writes the CLAUDE.md the agents and skills read: build and test commands, conventions, gotchas, and how you want to be worked with. Without it they run on defaults and guesses.
> - **`/setup-local-md`** — if any key came back unresolved above.
>
> Then `/brainstorm` or `/feature` to start building.
