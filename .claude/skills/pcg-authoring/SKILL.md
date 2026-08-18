---
name: pcg-authoring
description: Author UE 5.8 PCG systems the way Epic's Electric Dreams sample does — multi-category scatter without overlap, dynamic spline-driven paths/rivers that regenerate when a spline moves, authored-cluster assemblies, and host-actor tunables — including the verified Python/MCP recipes for building PCG graphs programmatically. Use this whenever the task involves creating or editing a PCG graph, set-dressing/scatter along a corridor or region, cutting a dynamic path or river through PCG content, de-overlapping asset categories, PCG assemblies, or making PCG react to a moved actor/spline. Use it even if the request just says "scatter some rocks/trees" or "make the path dynamic" without naming PCG. For raw node/class API lookups also see ue-procedural-generation; this skill owns the composition patterns and the programmatic authoring workflow.
---

# PCG Authoring (Electric-Dreams-style)

Patterns extracted from a live MCP dissection of Epic's Electric Dreams sample (UE 5.8) — `PCGDemo_Forest` (410 nodes), `PCGDemo_Ditch` (411 nodes), their host Blueprints and subgraphs — plus API recipes verified by executing them in a live 5.8 editor.

To re-inspect the source material yourself: install Electric Dreams from the Epic Games Launcher, or keep an archive of just its PCG content (all graphs, custom nodes, host BPs, assembly data assets, breakdown levels — ~224 MB of uassets; art meshes are not needed) and copy that into any UE 5.8 project with the PCG plugin enabled. Spawner mesh refs will show as missing; the graph structure loads fine. If you keep such an archive, record its path in `LOCAL.md` under a key like `ElectricDreamsArchive` so this skill can reference it without hardcoding a machine path.

**Rule of thumb: if your design uses "Self Pruning" for de-overlap *between* categories, stop.** Epic's production graphs (and their shipped Biome Core plugin) de-overlap with priority-layered `Difference`, not merge-and-prune. Self Pruning's legitimate use is cleanup *within* one category/lane (the ditch graph uses exactly one, AllEqual, on a single lane; Biome Core exposes it per-asset).

## The five load-bearing patterns

### 1. Priority layering with Difference (multi-category de-overlap)

Place categories in priority order (biggest/rarest first). Each category:

```
SurfaceSampler (on landscape/region)          ← extents ≈ asset footprint
  → Difference(Source=samples,
               Differences=[cutouts, all earlier categories' points])
  → AttributeNoise on density → DensityFilter  ← patchiness
  → TransformPoints (jitter / random yaw / scale range)
  → Projection (onto landscape, project rotations too)
  → StaticMeshSpawner
```

- Publish each category's *placed* points through `BoundsModifier` (inflate to the asset's real footprint) on a **named reroute**; later categories subtract them.
- `Difference` settings: `density_function=Binary`, `mode=Discrete` (points) — `Inferred` when subtracting spatial data.
- Within one category, spacing is free: `SurfaceSampler` never overlaps its own `PointExtents`. No pruning pass needed anywhere.
- Never merge categories, self-prune, and re-split by attribute — that was our failed first design and Epic's graphs do not do it. (Epic's shipped Biome Core plugin de-overlaps the same way: priority-sorted sequential binary Difference.)
- 5.8 notes: `Density Filter` is officially superseded by `Attribute Filter` (prefer it in new graphs); a native `Discard Points on Irregular Surface` node now covers the keep-big-assets-off-rough-ground job.
- **Slope & gradient shaping** (the sample uses these heavily): `NormalToDensity` → filter culls vegetation off steep ground (9 uses in the forest graph). `Distance` / `Distance To Density` turn proximity into density for soft falloffs — soft band edges near water, sparser scatter near neighbors. The neighbor-distance trick (Electric Dreams `DistanceToNeighbors`, 3 nodes): `PointExtentsModifier(SearchDistance)` → self-`Projection` → `Distance(Source=In, Target=projected self, MaximumDistance=SearchDistance)` — writes distance-to-nearest-neighbor for scale/density modulation.

### 2. The tag contract (cross-graph communication + auto-regen)

- A host actor publishes itself with an **actor tag** (e.g. `PCG_Path`); its spline carries a **component tag** (e.g. `Active_Spline`) so one actor can publish several splines and consumers pick lanes.
- Consumers: `Get Actor Data` (mode `ParseActorComponents`, select **by tag**, `track_actors_only_within_bounds=True`) → `Filter Data By Tag` (keep the component tag).
- **Tracking is the dynamism**: a `Get Actor Data` node registers tag tracking; when the tracked actor moves or changes inside the consumer's bounds, the consumer's PCG component dirties and regenerates automatically. No event wiring, no Blueprint glue. Drag the spline → everything downstream re-carves.
- A graph reads its *own* actor's spline with `Get Spline Data`, `actor_filter=Self` — keeps the host actor self-contained and duplicable.
- One graph can also consume another PCG component's **generated output**: `Get Actor Data` with `mode=GetDataFromPCGComponent` (Electric Dreams: LargeAssembly composes on SmallAssembly results).

### 3. Carving a path/river through scatter

Consumer side (the scatter graph): tracked path spline → `SplineSampler` (`dimension=OnInterior`) → `BoundsModifier` (`mode=Scale`, e.g. ×8 XY / ×100 Z — this scale IS the corridor width) → merge into a `Cutouts` named reroute → feed every category's `Difference`. Closed-spline exclusion zones use the identical recipe.

Caveat: official docs state Interior sampling requires a **closed** spline (Electric Dreams feeds its ditch spline into `OnInterior` — whether that spline is closed was not verified). For an open path spline, the robust band recipe is `dimension=OnSpline` at a dense `distance_increment` (≤ half the band radius, so bends don't scallop) + `BoundsModifier` inflating each sample to the band width with a huge Z so terrain height can't escape the cutout.

Producer side (the path graph itself): several `SplineSampler`s over the same spline at different `distance_increment`s create independent lanes (walls at 510 uu, scatter at 115 uu, decals at 50 uu…), plus one `OnInterior` sampler for the floor. Each lane gets its own mini-pipeline and spawner.

(Epic's Biome Core plugin packages the same idea: an **open** spline with component tag `BiomePath` carves a path whose width comes from spline control-point scale — worth copying the control-point-scale-as-width trick for variable-width paths/rivers.)

### 4. Host-actor architecture

One plain Actor Blueprint per system: region component (Box or Spline), a `PCGComponent` bound to the graph, and **plain double/int variables as tunables** (`TreeDensity`, `RockSeed`, …) that the graph reads with `Get Actor Property` nodes. All tuning happens in the Details panel — designers never open the graph. Electric Dreams also adds CallInEditor buttons (clean regen, seed ±1).

Graph hygiene at scale: **named reroutes** for anything used twice (`Landscape Data`, `Cutouts`, per-category point data); **subgraphs** for any repeated per-category pipeline, instantiated with per-instance overrides.

### 5. Assemblies (authored clusters, e.g. a fallen tree with mushrooms on it)

Author the cluster once, capture it as saved point data, stamp it with `CopyPoints` (`Source` = cluster points, `Target` = sampled locations). Verified shape of Electric Dreams' assembly assets (`/Game/PCG/Assets/PCGAssemblies/` in the archive): each `ASM_*_PCG` asset holds saved `PCGPointData` published on **two pins — `Root` (hierarchy root) and `Points` (children)**; a `PCGAsset` BP element carries a `PCGDataCollection` referencing them, and `SG_CopyPointsWithHierarchy` (CopyPoints + index-offset fixup + `ApplyHierarchy`) stamps them preserving parent-child transforms. In 5.8 prefer the native equivalent: `PCGDataAsset` + the Load PCG Data Asset node. Epic's ditch assemblies are named things like `ASM_RiverEmbankment_00..04`, `ASM_HornBeamJungle_*`, `ASM_LargeBoulder_01A` — river embankments and tree clusters stamped along spline lanes, directly the model for river/path dressing moments.

## Programmatic authoring via MCP (verified recipes)

Read `references/python-authoring.md` **before writing any graph-building Python** — it contains the exact API shapes verified live (`add_node_of_type` returns a `(node, settings)` tuple; edge pin labels; the weighted-mesh-entry trap where `descriptor.static_mesh` needs a loaded object, not a SoftObjectPath; the reversed `PCGEdge` pin naming that makes naive graph dumps read backwards).

## Verifying PCG work

- After building/regenerating: check `LogPCG` for errors and warnings — a graph that produces zero points usually logs why.
- Regenerate via the component (`PCGComponent.generate(True)` from Python) rather than trusting stale output.
- A dressing graph's success criterion is visual: screenshot the region (this project's orientation-bug rule applies — property reads alone pass broken-looking output).
- Test the dynamic contract by actually moving the tracked spline actor and confirming downstream regeneration.

## Official-docs context

Read `references/pcg-docs-digest.md` for the distilled official 5.8 documentation: data types and conversions, runtime generation modes and constraints, shape grammar, GPU nodes, PCG Biome Core (Epic's ready-made layered-biome plugin — check its suitability verdict there before hand-rolling a large multi-biome system), and debugging tools.
