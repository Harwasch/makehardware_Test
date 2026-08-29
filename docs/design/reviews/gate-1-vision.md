# Gate 1 — Vision

**Status:** DECIDED, one item delegated.
**Artifact:** https://claude.ai/code/artifact/bf64b8ca-0644-432a-8dc5-34ff2fab3592
**Raised:** 2026-08-28 · **Answered:** 2026-08-28

## Why this gate ran late

It should have run before the plan, requirements and architecture stages. It did
not: the concepts were built, rendered, examined by the agent and never shown.
Three stages downstream were built on an unreviewed vision. Recorded here rather
than tidied away, because the mechanism that now prevents it —
[`hw-review`](../../../.claude/skills/hw-review/SKILL.md) — exists only because
this happened.

## Decisions

| Question | Decision |
|---|---|
| **Docking arrangement** | **Belly dock, no actuator.** Concept A. |
| **Charging environment** | **Recovered to deck**, into a mounting bracket with locating features. Not in the water. |
| **Scope** | **The wireless charging system only.** The vehicle is not ours and is not to be modelled. |
| **Pad geometry** | **Rectangular, 4 × 8 inch, fixed for now.** |
| **Coil technology** | **Delegated** — my call, to be backed by published sources. See below. |

## What each decision changed

**Scope — the vehicle is out.** The three system concepts were rebuilt to show
the charging system alone: deck bracket, both pads in housings, the gap, and the
converter enclosure. The vehicle appears only as the interface plate its pad
bolts to. The concepts now differ on the remaining real mechanical decision —
how the two pads locate to each other:

| | Locating approach | Argues for | Argues against |
|---|---|---|---|
| **A** | Cone, vee and flat — kinematic | best repeatability, no over-constraint | three point contacts carry no heat and take the whole landing load |
| **B** | Tapered rails | wide capture, line contact carries heat and load | over-constrained; the fit must be loose for thermal growth, and looseness is alignment error |
| **C** | Perimeter nest | nothing protrudes, full perimeter carries load | most over-constrained, aligns least precisely, traps silt and water |

**Deck charging tightened the envelope, and it is worth a lot.** With both pads
in rigid housings on a common bracket, the gap is two housing walls and a
clearance — not a vehicle hull. `SYS-006` tightens from 5–20 mm gap and 10 mm
offset to **8–14 mm and 5 mm**.

| | Old free-docking envelope | **Deck bracket** |
|---|---|---|
| Worst-case coupling | 0.437 | **0.558** at 14 mm, **0.645** at 10 mm |
| 4 layers, k·Q | 53 (1.09×) | **66–76 (1.34–1.55×)** |
| 6 layers, k·Q | 80 (1.64×) | **98–114 (2.01–2.32×)** |
| `MEC-003` margin | 1.09× | **1.40×** |

That is what moves an etched PCB coil from marginal to comfortable.

**Deck charging also settles the thermal case, unfavourably.** Both pads sit on
an open deck at the `SYS-016` ambient of +55 °C. There is no seawater heat sink
on either side, so `MEC-001`'s loss allowance stays symmetric — recorded in
`VIS-005` so it is not quietly revisited later.

## The delegated decision

Coil technology is mine to make and to defend with sources. It is **not recorded
here as decided**, because the evidence is still being gathered: published
*measured* quality factors for multilayer PCB coils at 80–120 kHz, and how badly
the ideal 1/N resistance scaling for parallel layers breaks down in practice.
That single unknown decides whether four layers, six layers or neither is right.

It will be recorded in `docs/design/adr-0001-coil-technology.md` with its
citations. **Until that ADR exists this gate is not fully closed**, and `G1`
stays `in_progress` in the plan.

## Requirements changed

* `VIS-005` — restated: recovered to deck into a locating bracket, not docked
  in the water. Rationale carries the coupling figures and the symmetric
  thermal consequence.
* `SYS-006` — envelope tightened to 8–14 mm gap, 5 mm lateral, 2° tilt, with
  the derivation of each number.
* `MEC-003` — rationale updated; the 0.40 floor stays, now with 1.40× margin.

No requirement *statement* was weakened to accommodate a decision.
