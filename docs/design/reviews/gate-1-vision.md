# Gate 1 — Vision

**Status:** OPEN. Awaiting decisions.
**Artifact:** https://claude.ai/code/artifact/bf64b8ca-0644-432a-8dc5-34ff2fab3592
**Raised:** 2026-08-28

## Why this gate is being run late

It should have run before the plan, requirements and architecture stages. It did
not: the concepts were built, rendered, examined by the agent and never shown.
The three stages downstream have therefore been proceeding on an unreviewed
vision. This record exists partly to close that gap and partly so the omission
is visible rather than tidied away.

## What was put up for review

**Three docking arrangements**, each rendered from real build123d geometry under
`concepts/`:

| | Arrangement | Argues for | Argues against |
|---|---|---|---|
| **A** | Belly dock — vehicle settles onto a cradle | no actuator, gravity clamps | pads face up, collect silt |
| **B** | Flank dock — vehicle alongside a vertical face | pads shed silt, serviceable in place | needs an active clamp |
| **C** | Saddle dock — hull nests into a 90° vee | self-centring, best alignment | doubles the coil count |

**A correction to the coil analysis.** The earlier conclusion — that an etched
PCB coil could not meet `MEC-001` and Litz was required — was wrong. It rested
on a single-layer analysis generalised to a whole conductor technology. On the
house's 4 × 8 inch rectangle, **32 turns of 0.80 mm trace in 4 oz copper with
six layers in parallel** reaches k·Q = 77 at the worst point of the `SYS-006`
envelope, against the 49 required — a 1.57× margin.

## What is being asked

| Question | Options | Answer |
|---|---|---|
| Docking arrangement | A belly · B flank · C saddle · other | *(open)* |
| Coil technology | Six-layer etched PCB, 102 × 203 mm — confirm | *(open)* |
| Pad aspect ratio | Is 4 × 8 in fixed, or is there room to square it | *(open)* |
| Mako form factor | The hull in every render is a placeholder | *(open)* |
| Charging environment | In water, or recovered to deck first | *(open)* |

## What changed before the review was raised

* `docs/design/coil-model.md` — Result 4 added; the Litz conclusion retracted
  with the reasoning for why it was overreaching.
* `docs/design/v1-baseline.md` — finding F9's scope corrected. It is now about
  the v1 coil specifically, not about etched coils as a class.
* `requirements/20-mechanical.sdoc` — `MEC-001`, `MEC-002` and `MEC-003`
  rationales rewritten against the rectangular multilayer geometry. **No
  requirement statement changed** — `MEC-001` was written against k·Q rather
  than a technology, which is why the correction cost an analysis and not a
  requirements rewrite.
* `concepts/` — the two coil-pad concepts replaced with three system-scope
  docking concepts.

## What changes when it is answered

The docking arrangement sets coil orientation, the alignment the link can count
on, whether pads can be serviced, and whether anything has to actuate. `MEC-003`
in particular is close: the computed worst-case coupling is 0.437 against a 0.40
floor, a margin of 1.09, and the arrangement chosen moves that number.

The charging-environment answer decides whether the two pads share a symmetric
thermal budget. In the water the RX pad has an essentially infinite heat sink
and `MEC-001`'s allocation should be split unevenly; on deck at +55 °C it should
not.
