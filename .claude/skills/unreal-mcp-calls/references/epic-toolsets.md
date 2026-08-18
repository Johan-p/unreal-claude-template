# Epic's stock MCP toolsets — full call reference

Schemas captured live from UE 5.8 on 2026-08-18. Read a section here instead of calling `describe_toolset` on that toolset.

**Contents:** [SceneTools](#scenetools) · [ActorTools](#actortools) · [AssetTools](#assettools) · [ObjectTools](#objecttools) · [EditorAppToolset](#editorapptoolset) · [ProgrammaticToolset](#programmatictoolset) · [Not yet captured](#not-yet-captured)

Shared shapes: object references are `{"refPath": "..."}`; transforms are `{location:{x,y,z}, rotation:{pitch,yaw,roll}, scale:{x,y,z}}` with every field optional.

---

## SceneTools

`editor_toolset.toolsets.scene.SceneTools` — the currently loaded level: placing and removing actors, level camera, outliner folders.

| Tool | Arguments | Returns |
|---|---|---|
| `get_current_level` | — | level asset path |
| `load_level` | `level_path` | — |
| `find_actors` | `name`*, `tag`*, `collision_channels`*, `root`, `actor_type`, `bounds` | actor[] |
| `add_to_scene_from_asset` | `asset_path`*, `name`*, `xform`*, `parent`, `snap_to_ground` | actor |
| `add_to_scene_from_class` | `actor_type`*, `name`*, `xform`*, `parent`, `snap_to_ground` | actor |
| `remove_from_scene` | `actor`* | bool |
| `save_actor` | `actor`* | — |
| `is_checked_out` / `can_edit` | `actor`* | bool |
| `get_folders` | — | string[] (includes intermediate paths) |
| `get_actors_in_folder` | `folder_path`*, `recursive` | actor[] |
| `set_actor_folder` | `actor`*, `folder_path`* (`""` = root) | — |
| `rename_folder` | `old_path`*, `new_path`* | count moved |
| `delete_folder` | `folder_path`* | count moved |
| `trace_world` | `start`*, `end`* | distance, or null if no hit |
| `merge_actors` | `actors`*, `output_path`*, `name`*, `destroy_source_actors` | StaticMeshActor |
| `create_level_instance` | `level_path`*, `name`*, `xform`*, `parent` | LevelInstance |
| `edit_level_instance` / `commit_level_instance` | `level_instance`* / +`discard` | — |
| `get_collision_channels` | — | `ObjectTypeQuery1..64` |

`*` = required. `find_actors` requires the three filter args even when unused — pass `""`, `""`, `[]`.

Level instance editing is modal: while one is open, `add_to_scene_*` and `remove_from_scene` operate inside its sub-level. Only one at a time; always `commit_level_instance`.

---

## ActorTools

`editor_toolset.toolsets.actor.ActorTools` — transforms, labels, hierarchy, components, tags.

| Tool | Arguments | Returns |
|---|---|---|
| `get_actor_transform` | `actor` | transform (world space) |
| `set_actor_transform` | `actor`, `xform`, `worldspace` (default true) | bool |
| `get_actor_bounds` | `actor` | `{min, max, isValid}` world-space box |
| `look_at` | `actor`, `target` | — |
| `get_label` / `set_label` | `actor` / +`label` | string / bool |
| `add_tag` / `remove_tag` / `has_tag` / `get_tags` | `actor` (+`tag`) | — / bool / string[] |
| `get_components` | `actor`, `component_type` | component[] |
| `add_component` | `owner`, `component_type`, `name` | component |
| `remove_component` | `component` | bool |
| `get_root_component` | `actor` | SceneComponent or null |
| `get_parent_component` | `component` | SceneComponent or null |
| `set_parent_component` | `component`, `parent` (null detaches) | bool |
| `get_component_actor` | `component` | actor |

Inside a Blueprint, `worldspace` has no effect — blueprint actors only carry a default relative transform. Making a component the parent of the root promotes it to scene root, and Unreal removes a `DefaultSceneRoot` automatically.

---

## AssetTools

`editor_toolset.toolsets.asset.AssetTools` — project assets and text files on disk.

| Tool | Arguments | Returns |
|---|---|---|
| `find_assets` | `folder_path`*, `name`*, `asset_type`, `recursive` (true), `tags` | path[] |
| `exists` | `path` | bool |
| `load_asset` | `asset_path` | object |
| `save_assets` | `asset_paths` (empty list = all dirty) | bool |
| `is_dirty` / `is_checked_out` / `can_edit_asset` | `asset_path` | bool |
| `duplicate` / `move` | `path`, `new_path` | bool |
| `delete` | `path` (asset or folder) | bool |
| `get_asset_class` | `asset_path` | class name string |
| `get_asset_tags` / `get_metadata_tags` | `asset_path` | dict |
| `update_metadata_tags` | `asset_path`, `set_tags`, `remove_tags` | — |
| `get_dependencies` / `get_referencers` | `asset_path` | path[] |
| `list_folders` | `root_path`, `recursive` | path[] |
| `create_folder` | `path` | bool |
| `get_plugin_content_paths` | `include_engine` | root path[] |
| `read_file` / `write_file` | `file_path` (+`content`) | text / — |

`find_assets` with `folder_path=""` searches the whole project including plugin content. `read_file`/`write_file` are restricted to `/Game/`, enabled plugin `Content/`, and the project `Saved/` directory, plain text only.

---

## ObjectTools

`editor_toolset.toolsets.object.ObjectTools` — properties on any UObject or UClass, including inside Blueprints, plus class discovery.

| Tool | Arguments | Returns |
|---|---|---|
| `get_properties` | `instance`, `properties[]` | JSON string |
| `set_properties` | `instance`, `values` — **a JSON string** | bool |
| `list_properties` | `instance` | JSON string |
| `reset_properties` | `instance`, `properties[]` | bool |
| `get_class` | `instance` | class |
| `search_subclasses` | `base_class`, `class_name` (substring filter) | class[] |

The `values`-as-a-string detail is the usual failure. Correct form:

```json
{"instance": {"refPath": "/Script/RemoteControlCommon.Default__RemoteControlSettings"},
 "values": "{\"bAllowAnyRemoteFunctionCall\":true}"}
```

This is also the route to developer-settings singletons — `/Script/<Module>.Default__<Class>` — which is how config can be changed live without an editor restart.

---

## EditorAppToolset

`EditorToolset.EditorAppToolset` — **PascalCase tool names.** Editor state, PIE, imaging.

| Tool | Arguments | Returns |
|---|---|---|
| `CaptureViewport` | `captureTransform`, `annotations`, `bShowUI` (false) | image + camera + `labeledActors` |
| `CaptureEditorImage` | — | image |
| `CaptureAssetImage` | `assetPath` | image |
| `StartPIE` | `options{bSimulate*, playMode*, warmupSeconds*, startTransform}` | null |
| `StopPIE` / `IsPIERunning` | — | null / bool |
| `GetSelectedActors` / `SelectActors` | — / `actors` | actor[] / — |
| `GetSelectedAssets` / `SelectAssets` | — / `assetPaths` | path[] / — |
| `GetCameraTransform` / `SetCameraTransform` | — / `transform` | transform / — |
| `FocusOnActors` | `actors` | — |
| `GetVisibleActors` | — | actor[] in frustum |
| `SearchCVars` | `name` | JSON string |
| `WorldPosToScreenCoords` | `position` | normalized `{x,y}` |
| `ScreenCoordsToWorld` | `coords`, `traceDistance` (100000) | world `{x,y,z}` |
| `SetContentBrowserPath` / `GetContentBrowserPath` | `path` / — | — / string |
| `OpenEditorForAsset` / `GetOpenAssets` | `assetPath` / — | — / path[] |

**`CaptureViewport` annotations** are the standout feature — they project a world-space ground grid through the camera with coordinate labels in metres, and draw a crosshair plus leader-line callout for each visible actor. Config: `gridSpacing` (cm, 0 disables the grid), `gridExtent`, `gridHeight`, `maxLabelDistance` (0 disables labels), `classFilter`, `maxLabels` (nearest wins — too many makes the image unreadable). The returned `labeledActors` array gives each label's canonical name, class, screen position, world location and distance, so you can act on what you see.

**`StartPIE`** waits for `PostPIEStarted` plus `warmupSeconds` before returning, which removes the usual race against initialization. `PlayMode_InNewProcess`, mobile preview, VR and QuickLaunch all silently downgrade to `PlayMode_InViewPort`, because completion tracking needs in-process PIE. `FocusOnActors` cannot be called while PIE is active.

---

## ProgrammaticToolset

`editor_toolset.toolsets.programmatic.ProgrammaticToolset` — batches other toolset calls through a sandboxed script.

- `get_execution_environment` — call once before first use; returns instructions and the allowed module list.
- `execute_tool_script(script)` — the script must define `run()` returning a dict.

Inside the script, `execute_tool(tool_name, json_input)` calls any registered tool by its full name and returns a dict-like result, raising `RuntimeError` on failure. Allowed imports are only `json, math, datetime, copy, re, time` — **there is no `unreal` module here.** This orchestrates tools; it does not script the engine.

```python
import json

def get_selected():
    return execute_tool("EditorToolset.EditorAppToolset.GetSelectedActors", "{}")["returnValue"]

def run():
    actors = get_selected()
    return {"count": len(actors)}
```

Where VibeUE is installed, `execute_python_code` is almost always the better choice — it has the real `unreal` module and no sandbox.

---

## Not yet captured

These exist and work; their schemas simply haven't been paid for yet. If you need one, call `describe_toolset` once and add a section here so the next session doesn't have to.

`BlueprintTools` · `MaterialTools` · `MaterialInstanceTools` · `StaticMeshTools` · `SkeletalMeshTools` · `TextureTools` · `DataTableTools` · `CurveTableTools` · `DataAssetTools` · `StringTableTools` · `PrimitiveTools` · `EditorToolset.LogsToolset` · `ToolsetRegistry.AgentSkillToolset`

Note that several overlap with a VibeUE service that is usually richer — materials, meshes and blueprints especially. Check `references/vibeue-services.md` first.
