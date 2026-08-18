# VibeUE services — what each one owns

Captured from a live editor on 2026-08-18 (VibeUE 5.0, UE 5.8). These are **Python classes on `unreal.*`**, reached through `execute_python_code`. All methods are static and thread-safe, and C++ out-parameters come back as Python return values.

**Discover the real API with `dir()`, not documentation:**

```python
import unreal
print([m for m in dir(unreal.WidgetService) if not m.startswith('_')])
```

That costs ~200 tokens. `describe_toolset` on the same service costs thousands, and the docstrings are occasionally wrong — `AssetDiscoveryService.search_assets` is documented but does not exist. `dir()` reflects what is actually bound.

**Contents:** [Content authoring](#content-authoring) · [Animation](#animation) · [World building](#world-building) · [VFX and audio](#vfx-and-audio) · [Project and engine](#project-and-engine) · [Diagnostics](#diagnostics) · [Division of labour](#division-of-labour-with-epics-toolsets)

---

## Content authoring

**`BlueprintService`** — introspection: `get_blueprint_info` (parent class, variables), `list_variables`, `list_components`.

**`WidgetService`** — 41 actions over Widget Blueprints. Hierarchy (`get_hierarchy`, `list_components`, `add_component`, `remove_component`, `rename_widget`), properties (`get_property`, `set_property`, `list_properties`, `set_font`/`get_font`, `set_brush`/`get_brush`), events (`get_available_events`, `bind_event`), MVVM (`list_view_models`, `add_view_model`, `add_view_model_binding`, `remove_view_model_binding`), animation (`create_animation`, `add_animation_track`, `add_keyframe`), and live PIE inspection (`spawn_widget_in_pie`, `get_live_property`, `remove_widget_from_pie`). `capture_preview` renders a widget to PNG.

**`MaterialService`** — lifecycle and properties Epic's `MaterialTools` doesn't cover: `save`, `compile`, `refresh_editor`, `open`, `get_info`, `summarize`, `list_parameters`, `set_property`/`set_properties`, `set_instance_parameters_bulk`, plus existence checks.

**`MaterialNodeService`** — material graph node authoring.

**`EnumStructService`** — full CRUD for UserDefinedEnum and UserDefinedStruct (`create_enum`, `add_enum_value`, `create_struct`, `add_struct_property`). Native C++ enums and structs are read-only.

**`UVMappingService`** — channel lifecycle (`add_uv_channel`, `copy_uv_channel`, `set_uv_channel_count`), generation (`generate_lightmap_uvs`, `auto_unwrap_uvs`, `pack_uvs`), transforms (`transform_uvs`, `flip_uvs`), lightmap settings, health reports, and `export_uv_layout_image` for visual inspection.

**`AssetDiscoveryService`** — asset search returning native types instead of JSON. Introspect before use; the docstring lists methods that aren't bound.

**`FabService`** — Fab library and free-catalog import. Built on reverse-engineered fab.com endpoints, so treat it as fragile.

---

## Animation

The strongest reason to install VibeUE on an animation-heavy project — Epic's stock toolsets have nothing equivalent.

**`AnimSequenceService`** — keyframes, curves, notifies (`add_notify`, `add_notify_state`, `add_notify_track`), sync markers, root motion, and data extraction (`get_pose_at_time(path, time, bool)` returns per-bone transforms).

**`AnimMontageService`** — sections (`add_section`, `set_next_section`), slot tracks, segments, branching points (`add_branching_point`), blend settings, `create_montage_from_animation`, `find_montages_for_skeleton`. Exists because Python's `set_editor_property()` returns read-only copies of internal arrays like `CompositeSections`.

**`AnimGraphService`** — AnimBlueprint introspection and navigation: `list_state_machines`, `list_states_in_machine`, `open_anim_state`.

**`SkeletonService`** — bone hierarchy (`list_bones`), sockets (`add_socket`), retargeting, curve metadata, blend profiles.

> **Path trap, stated twice in VibeUE's own docs:** these take the **full asset path** (`package_name` from AssetData), not the folder (`package_path`). `/Game/…/Animations/Run/AS_Run_Forward` — not `/Game/…/Animations/Run`.

> **Property trap, verified 2026-08-18:** several montage/sequence fields are *not* reachable as Python editor properties — `composite_sections`, `rate_scale` and `loop_count` all fail, and `Notifies` is protected. Use the accessors instead: `get_num_sections()`, `get_section_name(i)`, `get_play_length()`. A run that guessed from documentation burned three round trips rediscovering this; `dir()` would have answered it in one.

---

## World building

**`LandscapeService`** — 68 actions. Lifecycle, heightmaps (import/export/region read-write), sculpting (`sculpt_at_location`, `flatten_at_location`, `smooth_at_location`, `apply_noise`), paint layers, weight maps, holes, splines (`create_spline_point` takes `world_location=`, **not** `location=`), mesh projection, terrain analysis (`analyze_terrain`, `get_slope_at_location`, `find_flat_areas`), batch line traces, and semantic features (`create_mountain`, `create_valley`, `create_ridge`, `create_plateau`, `create_crater`, `create_terraces`, `apply_erosion`).

**`LandscapeMaterialService`** — 20 actions for layer-blend graphs, layer info objects, grass output, and height/slope-driven auto-blending (`create_height_mask`, `create_slope_mask`, `setup_height_slope_blend`).

**`FoliageService`** — foliage types, Poisson-disk `scatter_foliage`, `scatter_foliage_rect`, layer-aware `scatter_foliage_on_layer`, radius removal, and queries.

**`MapBlockoutService`** — procedural FPS-map blockout pipeline: roads, POIs, fields, foliage, railway, final pass, then `Materialize*` methods that turn the plan into real geometry.

**`RuntimeVirtualTextureService`** — RVT assets, volumes, landscape assignment.

**`ActorService`** — deliberately trimmed to what Epic's ActorTools/SceneTools lack: transform lock/constraints, absolute-transform flags, preserve-scale-ratio, viewport camera framing (`get_actor_view_camera`), and `get_all_properties`.

**`ViewportService`** — view type (perspective/top/front/…), FOV, clip planes, exposure, game view, cinematic control, realtime, camera speed, layout (`FourPanes2x2`, `OnePane`). **Read-only for camera pose** — set position via `EditorAppToolset.SetCameraTransform` or `UnrealEditorSubsystem.set_level_viewport_camera_info`.

---

## VFX and audio

**`NiagaraService`** — rapid-iteration parameters and diagnostics (`compare_systems`, `get_emitter_lifecycle`, `debug_activation`). System/emitter CRUD moved to the engine's `NiagaraToolsets` — reach those with `call_tool`.

**`NiagaraEmitterService`** — colour authoring including `ColorFromCurve` (`set_color_tint`, `get_color_curve_keys`, `shift_color_hue`) and module management.

**`NiagaraScratchPadService`** — node-graph authoring inside scratch-pad modules, including Custom HLSL nodes, typed pins, and wiring. Call `apply_changes()` once at the end.

**`MetaSoundService`** — `create_meta_sound`, `list_available_nodes`, `add_node`, `connect_nodes`, `save_meta_sound`. Use `list_nodes()` to get the built-in interface node IDs created with the asset.

**`SoundCueService`** — cue creation and graph editing. Audio flows **from leaf nodes toward the root**: `connect_nodes(parent, child, slot)` means the child feeds the parent. Node indices are invalidated by any structural change — re-call `list_nodes()` after each mutation.

---

## Project and engine

**`ProjectSettingsService`** — categories, `get_setting`/`set_setting`, direct INI access (`get_ini_value`), and `discover_settings_classes` across all `UDeveloperSettings` subclasses.

**`EngineSettingsService`** — rendering, physics, audio, GC, threading, platform settings, and console variables (`get_console_variable`, `set_console_variable`, `search_console_variables`).

**`GameplayTagService`** — `list_tags`, `add_tag`/`add_tags`, `has_tag`, `get_tag_info`, `get_children`. Single-tag rename and remove live on the engine's GameplayTags toolset, not here.

**`InputService`** — Enhanced Input: actions, mapping contexts, key mappings, modifiers, triggers, plus `discover_types` and `get_available_keys`.

**`StateTreeService`** — StateTree asset creation, inspection and editing. State paths use `/` from the subtree root: `Root/Walking/Idle`.

**`TransactionService`** — the editor undo stack. `begin_transaction(name)` … `end_transaction()` groups several edits into one undo step; `undo`, `redo`, `get_state`, `get_history`, `reset`. Most VibeUE edits already wrap themselves in a transaction, so a bare `undo()` reverts a whole operation.

---

## Diagnostics

**`PerformanceService`** — genuinely net-new: UE 5.8's native toolsets have no performance or tracing tools. Recommended flow is `FrameTiming()` first for a CPU-vs-GPU-bound verdict, then `StartTrace` → reproduce → `StopTrace` → `Analyse`. Profile under PIE or standalone, not the bare editor viewport. Returns JSON strings.

---

## Division of labour with Epic's toolsets

Epic's stock set is strong at **inspecting and arranging** — actors, assets, transforms, selection, PIE, screenshots. VibeUE is about **authoring** — constructing Blueprints, widgets, material graphs, MetaSounds, Niagara systems, terrain, and animation data.

Where both cover a domain, VibeUE's service is usually the richer one but is deliberately trimmed to avoid duplicating the engine's own tools. Several services say so explicitly in their docstrings and point at the engine toolset for the rest — read the docstring's notes before assuming a method is missing, then confirm with `dir()`.
