# Official UE 5.8 PCG documentation — distilled digest

Compiled 2026-08-17 from the full official PCG doc tree (18 pages; URL list at bottom). Identifiers are exact as documented. Caveat: pages were digested via targeted summarization; per-node sub-pages weren't individually crawled, so nodes may have settings beyond those listed.

Contents: [Core model](#core-model--data-types) · [Tracking & regen](#dynamic-tracking--regeneration) · [Shape grammar](#shape-grammar--authoring) · [Assemblies](#assemblies--pcg-data-assets) · [Biome Core](#pcg-biome-core) · [GPU](#gpu-processing) · [Debugging](#debugging) · [Version caveats](#version-caveats)

## Core model & data types

- Plugins: `Procedural Content Generation Framework` (core), `...Geometry Script Interop` (needed for mesh-surface sampling + `Primitive Cross-Section`), `PCG Biome Core`/`PCG Biome Sample` (Experimental), `Procedural Vegetation Editor` (Experimental).
- Core classes: `UPCGComponent`, `APCGVolume`, `UPCGGraph`, level-wide `PCGWorldActor` (owns `Partition Grid Size`).
- Points carry transform, `BoundsMin/Max`, color, `Density` 0–1, `Steepness`, `Seed`, user attributes. Static attributes prefix `$` (`$Position`, `$Transform`, `$Scale`, swizzles like `$Position.ZYX`, `$Transform.Location`); `@Last` = previous node's output attribute; metadata domains `@Data` / `@Points` / `@Elements`. Spline control points expose `$ArriveTangent`, `$LeaveTangent`, `$InterpType`, `@Data.$SplineTransform`, `@Data.$IsClosed`.
- Spatial data types: **Volumes** (3D, `Volume Sampler`), **Surfaces** (2.5D e.g. landscape, `Surface Sampler`), **Lines** (splines + Landscape Splines, `Get Spline Data` → `Spline Sampler`), **Points**, **Polygon 2D** (`Create Polygon 2D`, `Polygon Operation` union/intersect/difference, `Clip Paths`, `Offset Polygon`, `Create Surface From Polygon 2D`). Union/intersection/difference produce lazy **composite data** that collapses to points on demand (`To Point`, `Make Concrete`, or implicitly). **Attribute Sets** = non-spatial tables.
- Graph parameters are Material-style and overridable per component; graph instances via "Save Instance"; C++ `PCG_Overridable` properties become override pins. Editor keys: **D** debug, **E** enable/disable, **A** inspect.

## Dynamic tracking & regeneration

**Manual gap, flagged:** no 5.8 manual page documents tag-based actor tracking / dirty-on-move semantics ("track actors only within bounds" etc.) — that machinery appears only in API refs (`UPCGComponent::DirtyGenerated`, `PCGDataFromActor`) and forums. **The authority for the tracking pattern is the live Electric Dreams evidence this skill was built from** (re-verifiable against the sample per SKILL.md): `Get Actor Data` by tag registers tracking; tracked-actor changes inside the consumer's bounds auto-dirty and regenerate. The docs do demonstrate editor-time reactive regen (Fence guide: spline edits "update dynamically"; Overview: real-time viewport updates).

- `Get Actor Data` family (`Get Spline/Landscape/Primitive/Volume/PCG Component Data`): **Actor Filter** = `Self`/`Parent`/`Root`/`All World Actors`/`Original`; `Include Children`; **Mode** = `Parse Actor Components` / `Get Single Point` / `Get Data from PCG Component` / `Get Data from PCG component or Parse Actor components`; `Expected Pins`, `Get Data On All Grids`, `Allowed Grids`, `Components Must Overlap Self`.
- Manual triggers: `Generate`/`Cleanup` buttons on the component; `Force Regen` (ctrl-click defeats node cache).
- **Runtime generation** (`Generation Trigger = Generate at Runtime`): content generates/cleans up around **Generation Sources** — editor viewport (needs `Treat Editor Viewport as Generation Source` on PCGWorldActor), player controller, WP streaming sources, `PCG Generation Source Component`. Config: Graph Settings → Runtime Generation → `Generation Radii` per grid size (+ `Generation Radius` for Unbounded, `Cleanup Radius Multiplier`; per-component `Override Generation Radii`); per-component scheduling policy (distance + `Direction Weight`); frustum culling (`Use Frustum Culling`, `Generate/Cleanup Bounds Modifier`); pooling `pcg.RuntimeGeneration.EnablePooling` / `.BasePoolSize` (100). Budgets: `pcg.FrameTime` 16.667 ms, `pcg.EditorFrameTime` 50 ms. `pcg.RuntimeGeneration.Refresh` force-regens all cells. Runtime regen follows source movement automatically.
- Generation modes: *Partitioned* (`Is Partitioned` + PCGWorldActor `Partition Grid Size` → `PCGPartitionActor` grid); *Hierarchical* (`Use Hierarchical Generation` + `HiGen Default Grid Size`; `Grid Size` node overrides downstream; data flows large→small grid only; `Unbounded` executes once — pair with `Cull Points Outside Actor Bounds`); *Runtime* as above.

## Shape grammar & authoring

Grammar strings drive segment/spline subdivision: `A` once, `A, B` sequence, `A*` fill, `A+` at-least-once, `[A, B]2` repetition, `{[A,P]:2,[BL,P]:1}*` weighted random, `<A, B, C>` first-that-fits. Nodes: `Spline to Segment`, `Subdivide Segment`, `Subdivide Spline`, `Duplicate Cross-Section`, `Clean Spline` (fuse colocated/remove collinear points), `Spline Direction`, `Select Grammar`, `Print Grammar`, `Primitive Cross-Section` (experimental).

**Fence-guide pipeline** (canonical spline→meshes, useful for fences/walls/railings along any spline): `Get Spline Data` (Actor Filter `Self`) → `Add Attribute` (grammar string from a graph parameter) → `Subdivide Spline` (Module Info = array of `PCG Subdivision Submodule` {Symbol, Scalable}) → `Match and Set Attributes` against an attribute-set table (per mesh: `Bounds From Mesh`, size/pivot attrs, `Point to Attribute Set`) → pivot-correction math → `Static Mesh Spawner` with selector `PCGMeshSelectorByAttribute` (Attribute `Mesh`). The **attribute-table + Match And Set** pattern generalizes to any data-driven per-category configuration.

Notable nodes beyond the obvious: `World Ray Hit Query` (physics raycast, returns physical material + hit actor, `Apply Metadata From Landscape`, `Ignore PCG Hits`), `Point Neighborhood`, `Spatial Noise`, `Spline Intersection`, `Split Splines`, `Create Surface From Spline`, `Distance to Density`, `Attribute Filter` (**supersedes `Density Filter`**), `Discard Points on Irregular Surface` (native version of Electric Dreams' hand-built bumpy-area filter), `Match And Set Attributes` (match by value/nearest/weighted), `Loop` subgraph node, `Sanity Check Point Data`, `Mutate Seed`. Static Mesh Spawner selectors: `PCGMeshSelectorWeighted`, `PCGMeshSelectorByAttribute`, `PCGMeshSelectorWeightedByCategory`; per-instance property overrides by attribute. `Spawn Actor` attach modes + `Collapse Actors`/`Merge PCG only`/`No Merging`.

**PCG Editor Mode** (Experimental, Modes dropdown → PCG): in-viewport tools `SplineTool` (draw spline), `SplineSurfaceTool` (closed areas), `PaintTool`, `VolumeTool`; graphs advertise compatibility via Tool Data (Compatible Tool Tags etc.). Useful for hand-placing spline/volume hosts fast.

## Assemblies / PCG data assets

`Load PCG Data Asset` node loads a PCG Data Asset (sync or async). Assembly (Biome glossary): "PCG point data created and exported from all static meshes and ISMs found in a level" — author a cluster in a level, export to a data asset, stamp via Copy Points-style instancing. The exact export UI flow isn't in the manual (editor context menu); Electric Dreams' `PCGAsset`/`ApplyHierarchy` BP elements are the 5.2-era equivalent.

## PCG Biome Core

Experimental plugin pair (`PCG Biome Core` + `PCG Biome Sample`). Ready-made landscape-scale biome system: host `BP_PCGBiomeCore` (global graph + volume), biome actors `BP_PCGBiomeVolume`/`BP_PCGBiomeSpline`/`BP_PCGBiomeTexture` (landscape-layer weights), data assets `BiomeDefinition` {BiomeName, BiomeColor, **BiomePriority — lower = higher**}, `BiomeGenerator` {GeneratorType, GeneratorPriority, GeneratorAllowOverlap, GeneratorGraph from template `TPL_BiomeCore_Generator`}, `BiomeAsset` {Weight, Generator, TransformGraph, Mesh, Assembly, Actor, ChildAssets + Asset/Mesh/Assembly/Filter/Runtime options incl. `SelfPrune`, `ExtentsMultiplier`, cull distances, water-distance filters}.

**Exclusion mechanic (directly relevant to us):** exclusion actors use actor tag `PCG_BiomeExclusion`; component tag `BiomeExclusion` (volumes/closed splines) = binary removal; component tag **`BiomePath` on an OPEN spline carves a path whose width comes from spline control-point scale** — Epic's packaged version of the dynamic-path pattern.

**De-overlap (confirms our pattern):** the global graph sorts all biome output by priority and applies "binary difference … sequentially between the incoming data of the current iteration and the remaining points from previous loop iterations" using per-asset bounds (`ExtentsMultiplier`), skippable per generator via `GeneratorAllowOverlap`. I.e. Epic's shipped system de-overlaps exactly like Electric Dreams: priority-ordered sequential binary Difference.

**Verdict for this project's corridor dressing:** overkill — built for multi-biome open worlds, Experimental, two extra plugins, opaque fixed pipeline. Steal instead: priority-ordered sequential Difference; attribute-table-keyed per-category config; per-category `SelfPrune` option; tag-based exclusion splines. Reach for Biome Core only if we later need many spatially-assigned biomes or camera-proximity runtime scatter (its runtime tier: GPU HLSL scatter around camera, requires `Generate at Runtime` + partitioned + HiGen Unbounded).

## GPU processing

Beta. GPU-capable: `Custom HLSL` (Point Processor/Generator, Attribute Processor, Custom kernels), `Static Mesh Spawner` (`Execute on GPU`), `Copy Points`, `Attribute Partition` (String/SoftObjectPath/SoftClassPath only), `Cull Points Outside Actor Bounds`, `Data Count`, `Normal to Density`, `Transform Points`. GPU-spawned instances are runtime-only GPU memory: **no collision, no navmesh, no ray tracing, no distance fields, no static lighting, no HLOD** — unusable for gameplay-relevant obstacles. Group GPU nodes contiguously (readback costs).

## Debugging

Per-node: **D** debug / **E** disable / **A** inspect; `Print Grammar`, `Sanity Check Point Data`, `Print String`; Profiling pane (per-node CPU); Unreal Insights (`UPCGSubystem::Tick`). Runtime: `pcg.RuntimeGeneration.EnableDebugOverlay 1`; `pcg.GraphExecution.DebugDrawGeneratedCells 1` (yellow boxes = generating cells; red sphere = source); `pcg.RuntimeGeneration.Refresh`; cache CVars `pcg.Cache.Editor.Enabled` (on) / `pcg.Cache.Runtime.Enabled` (off). `Break In Debugger` per node (attached debugger; ctrl-click `Force Regen` beats the cache).

## Version caveats

- Experimental: PCG Editor Mode, Biome Core/Sample, PVE (off by default; **PVE 5.7 assets incompatible with 5.8**). Beta: GPU processing.
- `Density Filter` fully superseded by `Attribute Filter` (Electric Dreams still uses Density Filter — works, but prefer Attribute Filter in new graphs).
- Biome Core 5.6+: definitions/assets can live inline on biome actors; `Biome Setup` actor deprecated.
- Native `Discard Points on Irregular Surface` exists in 5.8 — use it instead of hand-building Electric Dreams' `DiscardPointsInBumpyAreas` subgraph.

## Source pages

Landing: dev.epicgames.com/documentation/en-us/unreal-engine/procedural-content-generation-framework-in-unreal-engine — plus Overview, PCG Editor Mode, Shape Grammar, GPU Processing, Development Guides, Fence Generator, Generation Modes, Data Types Reference, Node Reference, World Partition, Biome landing/Core Overview/Quick Start/Reference/Glossary, PVE, Runtime Generation Debugging (all `…-in-unreal-engine` slugs under the same base).
