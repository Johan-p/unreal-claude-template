# Asset Naming Conventions

Source: [Epic's Recommended Asset Naming Conventions](https://dev.epicgames.com/documentation/unreal-engine/recommended-asset-naming-conventions-in-unreal-engine-projects) (Unreal Engine documentation).

**These conventions are mandatory for all assets created in this project** — by Claude Code (including via MCP asset creation) and by hand. Epic frames them as a recommendation; we adopt them as a hard rule so the Content Browser stays searchable and tooling can rely on prefixes.

## Naming format

```
[AssetTypePrefix]_[AssetName]_[Descriptor]_[OptionalVariantLetterOrNumber]
```

- **AssetTypePrefix** — identifies the asset type (table below).
- **AssetName** — the asset's name, PascalCase.
- **Descriptor** — context for how the asset is used (e.g. what surface, which character).
- **OptionalVariantLetterOrNumber** — differentiates multiple versions/variants (`_A`, `_B`, `_01`, `_02`).

Examples following the format: `SM_Door_Wooden_01`, `M_Water_Ocean`, `T_Arena_Floor_01`, `WBP_HUD_Score`.

## Asset type prefixes

### Rendering / geometry

| Asset Type | Prefix |
|---|---|
| Static Mesh | `SM_` |
| Skeletal Mesh | `SK_` |
| Material | `M_` |
| Material Instance | `MI_` |
| Post Process Material | `PPM_` |
| Texture | `T_` |
| HDRI | `HDR_` |
| Physics Asset | `PHYS_` |
| Physics Material | `PM_` |
| OCIO Profile | `OCIO_` |

### Blueprints / gameplay

| Asset Type | Prefix |
|---|---|
| Blueprint | `BP_` |
| Blueprint Interface | `BI_` |
| Actor Component | `AC_` |
| Widget Blueprint | `WBP_` |
| Enum | `E_` |
| Structure | `F_` |
| Data Table | `DT_` |
| Curve Table | `CT_` |
| Data Asset | `DA_` |

### Animation

| Asset Type | Prefix |
|---|---|
| Animation Blueprint | `ABP_` |
| Animation Sequence | `AS_` |
| Animation Montage | `AM_` |
| Blend Space | `BS_` |
| Skeleton | `SKEL_` |
| Rig | `Rig_` |

### VFX (Niagara)

| Asset Type | Prefix |
|---|---|
| Niagara System | `FXS_` |
| Niagara Emitter | `FXE_` |
| Niagara Function | `FXF_` |

### Cinematics / media

| Asset Type | Prefix |
|---|---|
| Level Sequence | `LS_` |
| Sequencer Edits | `EDIT_` |
| Media Source | `MS_` |
| Media Output | `MO_` |
| Media Player | `MP_` |
| Media Profile | `MPR_` |

### Levels / input / audio (added by this project — not in Epic's table)

| Asset Type | Prefix |
|---|---|
| Level / Map | `L_` |
| Input Action | `IA_` |
| Input Mapping Context | `IMC_` |
| MetaSound Source | `MSS_` |
| Sound Wave (imported audio: music, stings) | `SW_` |
| PCG Graph | `PCG_` |

`PCG_` is not in Epic's table (which predates the PCG framework); the plugin's own samples use this prefix. Landscapes are level-embedded actors, not content-browser assets — no prefix; their materials/grass types use the normal `M_`/`MI_` rows.

`MSS_` deliberately avoids `MS_`, which Epic's table already assigns to Media Source. `SW_` (Epic's table has no Sound Wave row and states the list is not exhaustive) covers imported waves, distinct from `MSS_` (authored MetaSounds) and `MS_` (Media Source).

### Misc / virtual production

| Asset Type | Prefix |
|---|---|
| Level Snapshots | `SNAP_` |
| Remote Control Preset | `RCP_` |
| NDisplay Configuration | `NDC_` |

## Project rules on top of Epic's list

- If an asset type isn't in the table, pick a sensible short prefix, use it consistently, and **add it to this file in the same change**.
- Never rename an existing asset outside the editor/MCP rename tools — raw file renames break redirectors and references.
- C++ classes follow Unreal's native prefixes (`A` actors, `U` objects/components, `F` structs, `E` enums, `I` interfaces), not this asset table.
- **A self-contained area may use a short code in place of its full name**, in both class names and asset name-bodies, when the full name makes identifiers unwieldy — the containing folder (`<UnrealProjectDir>\Source\<YourProject>\<Area>\`, `/Game/<Area>/`) already supplies the context. Prefer the full name; reach for a code only when it genuinely helps readability.
  **The level is the exception** — it keeps the full name (`L_<Area>`, not `L_<Code>`), because it is the one asset a human picks out of a flat list.
  Pick the code once per area and record it here when you do. Codes in use: *(none yet — add rows as they are chosen)*.
- **Texture naming format:** `T_<AreaCode>_<Subject>`.
- **Static mesh naming format:** `SM_<AreaCode>_<Subject>[_<Variant>]`; tiling material textures follow `T_<AreaCode>_<Material>`. If the project runs a dedicated art pipeline (e.g. an external DCC → import path), record its naming format here alongside a link to the pipeline spec.
- **Vendor-pack exception:** assets inside a marketplace pack's own root keep the vendor's names and prefixes exactly as imported — typos included. This table's rules apply to assets *we* create, which never live inside a vendor root (see [`FolderStructure.md`](FolderStructure.md)).
