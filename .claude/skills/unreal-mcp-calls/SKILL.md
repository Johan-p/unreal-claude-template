---
name: unreal-mcp-calls
description: Exact call reference for driving the live Unreal Editor over MCP — the toolset names, argument shapes, and verified gotchas, so you never spend thousands of tokens on describe_toolset. Use this whenever you are about to touch a running Unreal editor: placing or moving actors, creating or finding assets, reading or setting properties, running Python in the editor, starting PIE, taking screenshots, or inspecting a level. Use it even when the request is phrased as plain work ("move that crate", "screenshot the level", "what's in this map") without naming MCP or Unreal tooling. Also covers VibeUE's authoring services and when to reach for Python instead of a typed tool.
---

# Driving Unreal over MCP

`describe_toolset` is the single most expensive call in this workflow — one call can cost 8k tokens because it returns full JSON schemas for every tool in a toolset. Everything documented here has already been paid for once. Read this instead.

**If a call is documented here, don't call `describe_toolset`.** Only reach for it when you need a toolset this file doesn't cover, and then note what you learned so it can be added.

## Which door to use

The server exposes three top-level tools — `list_toolsets`, `describe_toolset`, `call_tool` — plus VibeUE's `execute_python_code` and friends. Choosing well is most of the token savings:

| Situation | Use | Why |
|---|---|---|
| One or two operations on Epic's toolsets | `call_tool` | Typed and validated; bad args are rejected before reaching the engine |
| Many operations, or logic between them | `execute_python_code` | Arbitrary batching in one round trip — the cheapest way to do bulk work |
| Anything on a **VibeUE** service | `execute_python_code` | They are Python classes (`unreal.WidgetService`, …), not really typed tools |
| Discovering a VibeUE method | `dir()` in Python | ~200 tokens, versus thousands for `describe_toolset` |
| Batching Epic tools without Python | `ProgrammaticToolset` | Sandboxed glue; no `unreal` module |

**The single highest-value habit:** when you need more than about three operations, write one Python script rather than a chain of `call_tool` invocations. Each round trip costs a request, a result, and your reasoning about it; a script costs one of each regardless of how much it does.

## The `call_tool` envelope

```
call_tool(toolset_name="<full dotted toolset name>",
          tool_name="<bare tool name>",
          arguments={...})
```

`tool_name` is the **last segment only** — `get_current_level`, not the full dotted path.

Two naming conventions coexist, which is a real trip hazard:

- `editor_toolset.toolsets.*` and `VibeUE.*` → **snake_case** tools (`get_actor_transform`)
- `EditorToolset.*` → **PascalCase** tools (`StartPIE`, `CaptureViewport`)

### Argument shapes that appear everywhere

**Object/actor/class references** are never plain strings:

```json
{"refPath": "/Game/Levels/DefaultLevel.DefaultLevel:PersistentLevel.MyActor"}
```

Get one from a tool that returns actors (`find_actors`, `GetSelectedActors`) and pass it straight back. For classes, `refPath` is the class path: `/Script/Engine.PointLight`.

**Transforms** — every field optional; unset means "identity" when creating and "don't change" when modifying:

```json
{"location": {"x": 0, "y": 0, "z": 100},
 "rotation": {"pitch": 0, "yaw": 90, "roll": 0},
 "scale":    {"x": 1, "y": 1, "z": 1}}
```

**`ObjectTools.set_properties` takes `values` as a JSON *string*, not an object** — a stringified JSON blob inside the arguments object. Easy to get wrong and it fails unhelpfully.

## The calls you'll actually reach for

### Level and actors — `editor_toolset.toolsets.scene.SceneTools`

| Tool | Arguments |
|---|---|
| `get_current_level` | — → level path string |
| `load_level` | `level_path` |
| `find_actors` | `name`, `tag`, `collision_channels` (all required, use `""`/`[]`), optional `root`, `actor_type`, `bounds` |
| `add_to_scene_from_asset` | `asset_path`, `name`, `xform`, optional `parent`, `snap_to_ground` |
| `add_to_scene_from_class` | `actor_type`, `name`, `xform`, optional `parent`, `snap_to_ground` |
| `remove_from_scene` | `actor` |
| `get_folders` / `get_actors_in_folder` | — / `folder_path`, `recursive` |
| `set_actor_folder` | `actor`, `folder_path` (`""` = root) |
| `trace_world` | `start`, `end` → distance to first hit, or null |
| `save_actor`, `merge_actors`, `create_level_instance`, `edit_level_instance`, `commit_level_instance` | see `references/epic-toolsets.md` |

### Actor detail — `editor_toolset.toolsets.actor.ActorTools`

`get_actor_transform` / `set_actor_transform` (`worldspace` defaults true) · `get_label` / `set_label` · `get_actor_bounds` · `look_at(actor, target)` · `get_components(actor, component_type?)` · `add_component(owner, component_type, name)` · `remove_component` · `get_root_component` · `get_parent_component` / `set_parent_component` · `get_component_actor` · `add_tag` / `remove_tag` / `has_tag` / `get_tags`

### Assets — `editor_toolset.toolsets.asset.AssetTools`

`find_assets(folder_path, name, asset_type?, recursive=true, tags?)` — `folder_path=""` searches everything · `exists` · `load_asset` · `save_assets(asset_paths)` — empty list saves all dirty · `duplicate` / `move` / `delete` · `get_asset_class` · `get_asset_tags` / `get_metadata_tags` / `update_metadata_tags` · `get_dependencies` / `get_referencers` · `list_folders` / `create_folder` · `read_file` / `write_file` (only under `/Game/`, plugin content, or `Saved/`)

### Properties and classes — `editor_toolset.toolsets.object.ObjectTools`

`get_properties(instance, properties[])` → JSON string · `set_properties(instance, values)` — **`values` is a JSON string** · `list_properties(instance)` · `reset_properties` · `get_class` · `search_subclasses(base_class, class_name)`

This is also how you reach engine settings objects: `{"refPath": "/Script/<Module>.Default__<Class>"}`.

### Editor, PIE and screenshots — `EditorToolset.EditorAppToolset` (PascalCase)

| Tool | Notes |
|---|---|
| `CaptureViewport` | Optional `annotations` overlays a projected world grid plus actor name/position labels, and returns `labeledActors` metadata. `bShowUI` defaults false (hides gizmos). The best spatial-awareness tool available — **see the exact argument shape below, it is easy to get wrong.** |
| `CaptureEditorImage` | The whole editor as the user sees it |
| `CaptureAssetImage` | `assetPath` → rendered thumbnail |
| `StartPIE` | `options`: `bSimulate`, `playMode`, `warmupSeconds` (all required). Completes after `PostPIEStarted` + warmup. Out-of-process play modes silently downgrade to in-viewport. |
| `StopPIE` / `IsPIERunning` | — |
| `GetSelectedActors` / `SelectActors` / `GetSelectedAssets` / `SelectAssets` | — |
| `GetCameraTransform` / `SetCameraTransform` / `FocusOnActors` | `FocusOnActors` fails during PIE |
| `GetVisibleActors` | Actors intersecting the viewport frustum |
| `SearchCVars` | Partial name → JSON of matching console variables |
| `WorldPosToScreenCoords` / `ScreenCoordsToWorld` | Normalized screen space |
| `SetContentBrowserPath` / `GetContentBrowserPath` / `OpenEditorForAsset` / `GetOpenAssets` | — |

#### Annotated top-down capture — the exact shapes

Two argument traps here cost a real run 31 tool calls and a `describe_toolset`. `ViewportAnnotationConfig` requires **all six** fields — there are no optional ones — and `SetCameraTransform` wraps its transform in a `transform` key:

```jsonc
// SetCameraTransform — note the wrapper
{"transform": {"location": {"x": 3100, "y": -1150, "z": 15500},
               "rotation": {"pitch": -90, "yaw": -90, "roll": 0}}}

// CaptureViewport with annotations — all six fields required
{"annotations": {"gridSpacing": 1000,        // cm between grid lines; 0 disables the grid
                 "gridExtent": 20000,        // cm the grid reaches from origin
                 "gridHeight": 0,            // world Z of the ground plane
                 "maxLabelDistance": 30000,  // cm; 0 disables labels
                 "classFilter": null,        // or {"refPath": "/Script/Engine.PointLight"}
                 "maxLabels": 25},           // nearest-to-camera wins
 "bShowUI": false}
```

Looking straight down means `pitch: -90`. Read the returned `labeledActors` for each label's world location rather than inferring screen orientation — the axis mapping depends on yaw. Keep `maxLabels` modest; labels overlap and the image becomes unreadable well before you run out of actors. Viewport aspect ratio is whatever the editor window is, so a wide, short viewport frames a square level poorly — crop afterwards rather than fighting it.

**Screenshots of a running game** have caveats that live in [`docs/live-testing-playbook.md`](../../../docs/live-testing-playbook.md) — read it before concluding a UI is broken from a blank-looking capture.

### Python — `execute_python_code` (VibeUE only)

```python
import unreal
subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = subsys.get_all_level_actors()
print(len(actors))
```

Must start with `import unreal` (lowercase). Returns stdout, stderr, and status — so `print()` is how you get data back.

Also available: `discover_python_class`, `discover_python_function`, `discover_python_module`, `list_python_subsystems`, `deep_research`, `terrain_data`.

The authority for every `unreal.*` API is the [UE 5.8 Python API reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/?application_version=5.8). Check it rather than guessing — invented `unreal.*` calls are a recurring failure mode.

### VibeUE authoring services

Roughly 26 Python classes on `unreal.*` covering what Epic's toolsets don't: Blueprints, Widgets/UMG + MVVM, Materials and material graphs, MetaSounds, Niagara (including scratch-pad HLSL), Landscape and landscape materials, Foliage, animation (AnimGraph, AnimMontage, AnimSequence, Skeleton), UV mapping, gameplay tags, input, transactions (undo/redo), and Unreal Insights profiling.

Discover a service's real API in one cheap call rather than describing the toolset:

```python
import unreal
print([m for m in dir(unreal.WidgetService) if not m.startswith('_')])
```

Names and groupings are in [`references/vibeue-services.md`](references/vibeue-services.md). **Trust `dir()` over any docstring** — some documented method names don't exist (`AssetDiscoveryService.search_assets` is one).

## The safety rules live elsewhere — and they are not optional

Editing behaviour (log every change for rollback, check-before-create, compile after structure changes, verify with re-read evidence, never remove-and-recreate to change a value, stop after two failed attempts, no blocking calls, full asset paths, colours 0.0–1.0) is owned by **§9 "Critical rules" of the VibeUE agent guide**, imported into CLAUDE.md and therefore already in context.

They are deliberately not repeated here: that file is regenerated by `VibeUE.GenerateAgentConfig` when the plugin updates, so a copy in this skill would drift away from the authority and quietly become wrong. This file covers *which call to make*; that one covers *how to behave while making it*.

## Verified gotchas

- **`describe_toolset` costs ~2–8k tokens.** That is the thing this file exists to avoid.
- **`dir()` beats `describe_toolset`** for VibeUE services by roughly 20×, and it reflects reality rather than documentation.
- **VibeUE docstrings can be wrong** about method names. Introspect before trusting.
- **`set_properties`' `values` argument is a JSON string**, not a nested object.
- **`find_actors` requires `name`, `tag` and `collision_channels`** even when you don't filter — pass `""`, `""`, `[]`.
- **Never `time.sleep`** in editor Python: it blocks the game thread and freezes the world. Sample across separate calls instead.
- **`ProgrammaticToolset` has no `unreal` module** — only `json, math, datetime, copy, re, time`. It orchestrates tools; it does not script the engine.
- **A bare GET of `:8000/mcp` returning 405 means the server is healthy** — it wants POST.
- **Port 8000 is shared.** Only one editor serves MCP at a time; whichever is running is the one you reach.

## When MCP isn't there

If tools are unbound, don't conclude failure: the harness attaches lazily. Make a cheap call or two and re-check. If the editor is down, launch it (`<BuildScript> -SkipBuild -WaitForReady` where a build script exists) and re-probe. `/mcp` reconnect is the fallback, not the first move.

On a Blueprint-only project there is no VibeUE and therefore no `execute_python_code`; Epic's toolsets still work, and Remote Control can run Python over HTTP if it has been unlocked. See `/unlock-unreal`.
