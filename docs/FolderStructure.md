# Content Folder Structure — By Feature

**Decision:** the `Content/` folder in the Unreal project (`<UnrealProjectDir>`) is organized **by feature**, the way Epic Games recommends for most projects. Everything a feature needs lives in that feature's folder — meshes, textures, materials, blueprints, animations, sounds, all together.

> **Template note:** the rule and the reasoning below are project-agnostic — keep them. The tree under *Current layout* is an **illustrative placeholder**: replace it with this project's real folders and keep it current as folders are added or removed.

## The rule

When creating or importing any asset, place it in `Content/<Feature>/` — the folder of the feature it belongs to. Do not create top-level type folders (`Content/Meshes/`, `Content/Textures/`, `Content/Blueprints/`, `Content/Levels/`) — type is already encoded in the asset name prefix (see [`NamingConventions.md`](NamingConventions.md)); the folder encodes the feature.

If the project is large enough to have several self-contained top-level areas (separate game modes, separate shipped experiences, distinct worlds), make each one a top-level folder and apply the by-feature rule *inside* it: `Content/<Area>/<Feature>/`.

## Why by-feature

**Pros:**
- All assets for a feature are in one place.
- A feature (or a whole area) can be moved or deleted by moving or deleting one folder.
- Teams (or agents) can own a folder without stepping on each other.
- Fewer cross-feature references.

**Cons to actively manage:**
- Shared assets (master materials, common functions) need their own folder — that's what `Core/` and `Shared/` are for; don't let them get dumped into whichever feature used them first.
- The structure tempts people to **duplicate assets instead of sharing them** — before duplicating an asset into a second feature, promote it to `Shared/` instead.
- Generic one-offs (a loading spinner, a debug material) have no obvious home — they go in `Shared/`, not in a random feature folder.

## Current layout

Illustrative shape — replace with the project's real tree and keep this list current as folders are added or removed:

```
Content/
  Core/              # framework plumbing used everywhere:
                     #   game mode / player controller Blueprints,
                     #   Input/ (IMC + IA assets), core levels
  <Feature>/         # one folder per feature — everything that feature owns
    L_<Feature>      #   the feature's level, if it has one
    UI/              #   WBP_ widgets belonging to this feature
    ...              #   meshes, materials, textures, sounds for this feature
  <AnotherFeature>/
  Shared/            # genuinely cross-feature assets only
                     #   (master materials, shared meshes, common widgets)
  <VendorPack>/      # VENDOR ROOT — marketplace pack, see exception below
```

## Project rules on top

- **A feature's folder holds everything that feature owns, including its level.** There is no top-level `Levels/` folder — a level lives in the folder of the feature it belongs to.
- **`Core/`** holds framework assets: game mode, player controller, input assets, and similar always-loaded plumbing. If the project has multiple self-contained areas, each area may have its own `Core/` — that is correct, and they never mix.
- **`Shared/`** is for assets used by **two or more features**, and nothing else. An asset earns a place there when a second feature actually uses it — not in anticipation. Promoting an asset there is done with the editor/MCP **move** tool (which fixes up referencers), never a raw file move.
- **Give generic asset names a feature descriptor.** `WBP_<Feature>Menu`, not `WBP_MainMenu` — folders keep them unique, but the Content Browser's search does not.
- Stock template/starter content stays quarantined in its own folder (wherever the template put it) and is not mixed into feature folders.
- **Marketplace vendor-root exception:** a purchased pack keeps its own top-level folder, is *not* by-feature, and **must not be moved or renamed** — moving a pack breaks its internal references, and redirector-chasing a several-hundred-asset pack is not work worth doing. Author **nothing** inside a vendor root: anything derived from a pack asset (a material instance, a Blueprint wrapper) lives in the consuming feature's folder and references the pack from there. If vendor packs are gitignored, note that here so a fresh clone knows to re-fetch them before building.
