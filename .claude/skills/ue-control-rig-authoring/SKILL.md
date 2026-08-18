---
name: ue-control-rig-authoring
description: "Use this skill when BUILDING or scripting Control Rigs in Unreal Engine — creating a Control Rig asset, adding controls/bones/nulls, Construction Event, Forwards/Backwards Solve, Full Body IK inside Control Rig, spline rigging, pose caching, Modular Control Rigs (modules, connectors, sockets), control shapes, rig function libraries, Python scripting of rigs (RigVMController, HierarchyController), Control Rig debugging, and animating with rigs (Animation Mode, Bake to Control Rig, FK Control Rig, constraints, space switching). Trigger on: 'rig this character/prop', 'add controls to', 'build a control rig', 'procedural rig', 'bake animation to rig', 'foot roll / IK controls', or Sequencer keying on rig controls. For merely RUNNING an existing rig in an AnimBP (Control Rig node, post-process ABP) see ue-character-rigging-retargeting; for retargeting see the same."
metadata:
  version: 1.0.0
---

# UE Control Rig Authoring

You are an expert in authoring Control Rigs in UE 5.x — building the rig graph, the hierarchy, and the animator-facing controls, plus scripting all of it with Python.

**Verification honesty:** the rig-graph half of this skill (hierarchy, solves, FBIK, Python) is cross-checked against the UE 5.8 docs and rig assets on disk (Epic's Game Animation Sample ships `CR_Biped_FootPlacement`, `CR_UEFN_Mannequin_FullBodyIK`, and a procedural `CR_Walker`; marketplace packs ship face/feet rigs). The **animator-workflow half** (Animation Mode, space switching, constraints in Sequencer) is doc-derived without a verified local example — treat those sections as a map, verify in-editor before writing specs against them.

## Context Check

This workspace runs a spec-driven workflow: read the feature's architect spec (`docs/architect/`) and the active slice doc (`docs/slices/`) before starting. CLAUDE.md and LOCAL.md are auto-loaded. Skills advise, specs decide.

---

## Asset creation and the three events

Create: right-click a Skeletal Mesh → `Create → Control Rig` (asset gets `_CtrlRig` postfix), or Content Browser → Animation → Control Rig (then `Import Hierarchy` in Rig Hierarchy to bind the mesh).

The rig graph runs up to three events — viewport border color tells you which is active:

| Event | Runs | Border | For |
|---|---|---|---|
| **Construction Event** | once, post-init | red | spawn/configure elements procedurally (`Spawn Bone/Null/Control/Animation Channel`; default cap 128 spawned elements via Procedural Element Limit), set control offsets/initial transforms, enable rig sharing across meshes |
| **Forwards Solve** | every frame (viewport, AnimBP) | — | controls → bones; the actual rig |
| **Backwards Solve** | on demand | yellow | bones → controls; powers **Bake to Control Rig** (turn an existing animation into keyable rig controls; options: Export Transforms/Curves, Record in World Space, Reduce Keys) |

`Backwards and Forwards` runs both sequentially (blue border) — a baking dry-run for debugging.

## Hierarchy: controls, bones, nulls

- **Bones**: imported from the mesh (or spawned — procedural bones are legal).
- **Controls**: animator-facing manipulators; shape + color from the Control Shape Library; transform channels can be limited/locked per axis; animation channels add custom keyable scalars (foot roll, blink).
- **Nulls**: transform groups for structure/pivots (the classic offset-above-control pattern: null holds placement, control stays zeroed).
- Naming and structure ARE the product — an animator sees the hierarchy panel; group per limb, suffix `_ctrl`, mirror left/right names so Python and pose mirroring can pattern-match.

## Full Body IK (inside the rig)

`Hierarchy → Full Body IK` node on the Forwards Solve chain. Root = pelvis/hips; add effectors (+) per end bone, feed each a transform (usually from a control's `Get Transform`).

- **Bone Settings**: rotation/position stiffness 0–1; `Use Preferred Angles` + per-axis values (stops knees bending backwards); per-axis limits Free/Limited/Locked.
- **Exclude bones** you never want solved — Epic recommends exclusion over maxed stiffness.
- Root behavior: `Pre Pull` (root follows average effector motion), `Pin to Input` (partial-body rigs), `Free`.
- Knobs: Iterations (convergence vs CPU), Mass Multiplier (~0–5 global stiffness), Allow Stretch, `Start Solve from Input Pose` (reset per tick vs iterate on previous — the latter converges faster, drifts under teleports).
- Debug: `Draw Debug` + `Draw Scale`.

The sample's `CR_UEFN_Mannequin_FullBodyIK` (run from a post-process ABP) is the on-disk worked example.

## Modular Control Rigs (Experimental)

Assemble a rig from prebuilt **Modules** (arm/leg/spine) in the viewport: create a `ModularRig` asset, drag modules onto **sockets**; **connectors** must resolve to a rig element (auto-resolves to a socket; manual resolver dropdowns in the Module Hierarchy panel). Authoring your own module = Control Rig asset → `Switch to Rig Module` → define primary connector (one) + secondary connectors + resolution rules (Type/Tag/Child-of-Primary/And/Or) + optional connector events.

Caveats (Epic's): **Experimental**; currently costlier than an inlined rig (single-threaded, modules execute sequentially root→leaf, execution stack not visible in UI). Fine for iteration speed; inline the final rig if profiling says so. Python: `rig_blueprint.modular_rig_model` / `get_modular_rig_controller()`.

## Python scripting (the automation path)

The killer feature: **Control Rig Python Log** (Window → Message Log → Control Rig Python Log) records every editor action as replayable Python — do it once by hand, harvest the script. Docs-verified API surface:

```python
unreal.load_module('ControlRigDeveloper')
rig = unreal.load_object(name='/Game/Rigs/CR_MyRig', outer=None)
# graph edits go through the controller:
controller = rig.get_controller()
unit = unreal.RigUnit_MathFloatAdd.static_struct()
node = controller.add_unit_node(script_struct=unit, method_name="Execute",
                                position=unreal.Vector2D(0, 0))
# hierarchy edits through the hierarchy controller:
hc = rig.get_hierarchy_controller()
key = hc.add_bone(name="MyBone", parent=unreal.RigElementKey(),
                  transform=unreal.Transform())
rig.add_member_variable("MyVariable", "Transform", is_public=True, is_read_only=False)
rig.recompile_vm()          # or recompile_vm_if_required()
```

Elements are addressed by `RigElementKey` (type + name). Engine ships example utilities (`add_controls_for_selected`, `add_null_above_selected`) in `Engine/Plugins/Animation/ControlRig/Content/Python` — read them before writing your own. With the MCP editor connection, run such scripts through `execute_python_code`.

## Debugging the rig

- Event border colors (above) tell you what's executing; `Control Rig Debugging` tools break on graph nodes and watch values.
- Bake-direction bugs are usually a Backwards Solve that doesn't mirror the Forwards Solve — keep them structurally symmetric.
- Perf: profile before inlining modular rigs; trim per-frame `Get Transform` calls (cache in Construction where static); pose caching nodes store poses for reuse across the graph.

## Animating with the rig ⚠ *doc-derived — verify in-editor*

- **Animation Mode**: select the rig in Sequencer → animator workspace (control selection, keying, snapper, tweeners, pose library).
- **Bake to Control Rig**: converts a skeletal animation into rig-control keys via Backwards Solve — the entry point for editing imported/mocap animation in-engine.
- **FK Control Rig**: instant per-bone FK controls with zero rig authoring — quick animation fixes without building anything.
- **Space switching**: re-parent controls dynamically while animating (hand follows weapon vs world); **constraints** (position/rotation/scale to another object) cover prop attachment.
- Keys land on the Sequencer track; the rig evaluates in Sequencer AND can evaluate in an ABP (Control Rig node) — same asset, two consumers.

## Common mistakes

| Anti-pattern | Fix |
|---|---|
| Rigging in Forwards Solve what belongs in Construction | One-time setup (offsets, spawned elements) → Construction Event |
| FBIK knees bend backwards | Preferred angles + per-axis limits on knee bones |
| Everything max-stiffness instead of excluded | Exclude bones from the solve (Epic's recommendation) |
| Backwards Solve missing → Bake to Control Rig silently useless | Author it alongside Forwards Solve, keep symmetric |
| Hand-editing 40 controls one by one | Python Log → harvest → script the rest |
| Modular rig shipped without profiling | Experimental + single-threaded — inline if it shows up in traces |
| Control limits skipped | Animators WILL pull the arm through the torso; limit/lock channels |

## Related Skills

- `ue-character-rigging-retargeting` — running rigs at runtime (Control Rig AnimBP node, post-process ABPs), IK Rig (the *retargeting* IK system — separate from Control Rig).
- `ue-animation-system` — the AnimGraph the rig plugs into.
- `ue-sequencer-cinematics` — Sequencer, where rig animation is keyed and baked.
- `ue-physics-animation` — physics-driven secondary motion instead of hand-keyed.

## Reference Files

- `../../docs/game-animation-sample-analysis.md` (repo docs) — where the sample's rigs sit (post-process FBIK, foot placement CR).
