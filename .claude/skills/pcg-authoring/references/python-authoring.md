# PCG graph authoring via Python/MCP — verified API recipes

All snippets below were executed against a live UE 5.8 editor (2026-08-17) via `execute_python_code`. Where something is *not* verified it says so. Batch related operations into one `execute_python_code` call; always `import unreal` first.

## Create a graph asset

```python
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
g = at.create_asset("PCG_Dressing", "/Game/MyFeature/PCG", unreal.PCGGraph, unreal.PCGGraphFactory())
```

Gotcha: a freshly created PCGGraph could **not** be deleted afterwards (`delete_asset` returns False even after `collect_garbage()` — the editor holds references). Create experiments in a disposable folder, and get the name right the first time for real assets.

## Add nodes — returns a (node, settings) TUPLE

```python
node, settings = g.add_node_of_type(unreal.PCGSurfaceSamplerSettings)
settings.set_editor_property('points_per_squared_meter', 0.01)
settings.set_editor_property('point_extents', unreal.Vector(150, 150, 150))
```

Settings classes follow the pattern `unreal.PCG<NodeName>Settings`: `PCGDifferenceSettings`, `PCGSplineSamplerSettings`, `PCGStaticMeshSpawnerSettings`, `PCGBoundsModifierSettings`, `PCGAttributeNoiseSettings`, `PCGDensityFilterSettings`, `PCGTransformPointsSettings`, `PCGProjectionSettings`, `PCGDataFromActorSettings`, `PCGGetActorPropertySettings`, `PCGMergeSettings`, `PCGCopyPointsSettings`, `PCGFilterByTagSettings`, `PCGNormalToDensitySettings` … Nested params live in sub-structs, e.g. `PCGSplineSamplerSettings.sampler_params` (`dimension`, `fill`, `mode`, `distance_increment`, `unbounded`), `PCGDifferenceSettings.density_function`/`mode`, `PCGProjectionSettings.projection_params.project_positions/project_rotations`.

Also on `PCGGraph`: `add_node_instance` (share settings between nodes), `add_node_copy`, `remove_node`, `remove_nodes`, `remove_edge`, `get_all_edges`, `get_input_node`/`get_output_node` (also as properties `input_node`/`output_node`).

## Connect nodes — pin labels are strings

```python
g.add_edge(node, "Out", spawn_node, "In")
```

**Trap — `add_edge` with a nonexistent pin label no-ops while returning an apparently-successful value.** A fresh 5.8 graph's input node exposes only `In` — there is NO `Landscape` pin on it (Electric Dreams' graphs use an explicit `Get Landscape Data` node, and so should you: `g.add_node_of_type(unreal.PCGGetLandscapeSettings)`). After wiring, ALWAYS verify edges landed by walking the downstream node's `input_pins[*].edges` (see inspection recipe below); never trust `add_edge`'s return value. In some cases the engine DOES log the failure — `LogPCG: Error: To node X does not have the Y label` — so scanning the log after a build/generate pass is a second reliable detector. Label gotchas confirmed in production use: override pins use the exact property name with no spaces (`"PointsPerSquaredMeter"`, not `"Points Per Squared Meter"`); `Projection`'s source pin is labeled `In`, not `Source`.

**Trap — output attribute selectors silently refuse Python mutation.** `PCGAttributePropertyOutputSelector.set_point_property()` / `.set_attribute_name()` return True but do NOT mutate the struct (re-read `.get_selection()` to confirm — it won't have changed). Input selectors (`PCGAttributePropertyInputSelector`) DO work, but only on a struct fetched live from the settings object (`s.get_editor_property('input_source')`), not on a freshly constructed bare instance. Practical consequence: constant-threshold `AttributeFilter` configs are currently not reliably scriptable — get the effect via `AttributeNoise` writing Density (spawners treat Density as spawn probability) or configure the filter by hand in the editor.

**Trap — a PCGComponent can get stuck reporting `generated=True` with valid `last_generated_bounds` while spawning ZERO ISM instances** (observed after graph-asset save → deleting unrelated level actors → level save). `cleanup()` + `generate(True)`, spline nudges, and full level reload do NOT fix it. Fix: destroy the host actor instance and respawn a fresh one (new PCGComponent), reconfigure, regenerate — works immediately. Always verify real ISM instance counts (`actor.get_components_by_class(unreal.InstancedStaticMeshComponent)` → `get_instance_count()`), never trust the component's generated flag.

Common pin labels: `In` / `Out` (default), `Source` / `Differences` (Difference), `Source` / `Target` (CopyPoints, Distance), `Spline` (SplineSampler input), `Surface` (SurfaceSampler), `InsideFilter` / `OutsideFilter` (attribute/point filters), `Overrides` (parameter override input on any node).

## Static Mesh Spawner weighted entries — the trap

`descriptor.static_mesh` is a SoftObjectProperty that wants the **loaded UStaticMesh object**; passing `unreal.SoftObjectPath(...)` throws `NativizeProperty: Cannot nativize 'SoftObjectPath'`.

```python
spawn_node, spawn = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
sel = spawn.get_editor_property('mesh_selector_parameters')   # PCGMeshSelectorWeighted by default
entries = sel.get_editor_property('mesh_entries')
e = unreal.PCGMeshSelectorWeightedEntry()
d = e.get_editor_property('descriptor')
d.set_editor_property('static_mesh', unreal.EditorAssetLibrary.load_asset('/Game/Art/SM_Tree'))  # LOADED asset
e.set_editor_property('descriptor', d)
e.set_editor_property('weight', 3)
entries.append(e)
sel.set_editor_property('mesh_entries', entries)               # write the array back
```

Repeat entry-append for each variant mesh; weights are relative ints.

## Reading an existing graph (inspection / verification)

```python
for n in g.get_editor_property('nodes'):
    s = n.get_editor_property('settings_interface')   # settings object or None
    # type(s).__name__ → 'PCGSurfaceSamplerSettings' etc.
```

**Edge pin naming is REVERSED from intuition**: `PCGEdge.input_pin` is the **upstream** node's output pin; `PCGEdge.output_pin` is the **downstream** node's input pin. A naive `src → dst` dump using these names reads backwards. Iterate a node's `input_pins[*].edges` and take `edge.input_pin.node` to find true upstream nodes.

Subgraph nodes: `settings.subgraph_instance.graph` → the referenced `PCGGraph`. Blueprint nodes: `settings.blueprint_element_type`. Settings-instance nodes (shared settings): `settings.settings` → the original.

Graphs also have implicit `DefaultInputNode`/`DefaultOutputNode` objects that are *not* in the `nodes` list — guard dict lookups when walking edges.

## Node settings observed in Epic's production graphs (starting values)

| Purpose | Node + key settings |
|---|---|
| Dense undergrowth | SurfaceSampler 0.125 pts/m², extents 50×50×500, looseness 1 |
| Trees | SurfaceSampler 0.01 pts/m², extents 150³, looseness 0.2 |
| Rocks/large | SurfaceSampler 0.0005 pts/m², extents 750–800³, looseness 1–4 |
| Category de-overlap | Difference: density_function=Binary, mode=Discrete |
| Path corridor cutout | SplineSampler dimension=OnInterior + BoundsModifier mode=Scale ×8 XY ×100 Z |
| Points along spline lane | SplineSampler dimension=OnSpline, mode=Distance, distance_increment 50–510 |
| Landscape conform | Projection: project_positions=True, project_rotations=True |
| Slope culling | NormalToDensity → DensityFilter |

## Actor-side (host actor, tags, regen)

```python
# Tag an actor + its spline component (the tag contract)
actor.tags.append("PCG_Path")                        # actor tag: unverified snippet, standard API
spline_comp.set_editor_property('component_tags', ["Active_Spline"])   # unverified snippet, standard API

# Regenerate a PCG component and check output
comp.generate(True)     # force regen — verify errors/warnings in LogPCG afterwards
```

`Get Actor Data` settings for the consumer side: `mode=ParseActorComponents`, `actor_selector.actor_selection=BY_TAG`, `actor_selector.actor_selection_tag="PCG_Path"`, `track_actors_only_within_bounds=True` (this is what makes moving the actor auto-regenerate consumers).

Host-actor Blueprint creation (components + variables) is not yet scripted from Python in this project — create the BP via the editor/MCP Blueprint toolsets, or ask the maintainer; don't guess an API.
