# What the simulations say

Two decks, both on ngspice-42, both cross-checked against closed form on every
point. Numbers live in the generated tables — [`sim-link.md`](sim-link.md) and
[`sim-dab.md`](sim-dab.md); this is what they mean.

Run them with `./sim/link/run_link.py` and `./sim/dab/run_dab.py`.

## What could be simulated, and what could not

The white paper supports a **faithful** simulation of the resonant link. It
gives measured coil values on page 6 — 12 µH, 0.8 Ω, Q of 12 — a 400 V bus, an
80–120 kHz band with 85 kHz nominal, and 11 µF of rectifier bulk capacitance on
page 5. Only the compensation capacitance is missing, and that follows from
resonance.

It does **not** support a simulation of the DAB. Page 8 names every
semiconductor — IPB60R120, BSC190N, UCC27741, ISO7740, ISO224, UCC1414,
UCC33420, TPSM560 — and none of the three parameters that set a DAB's power
transfer: transformer turns ratio, leakage inductance, switching frequency. A
deck built on assumed values would simulate our assumptions, not the design. So
`sim/dab/dab.cir` runs the inverse instead and solves for the transformer the
converter needs.

## F14 — the v1 coils cannot transfer 3 kW, by a factor of 6.75 in k

This is arithmetic before it is simulation. For series-series compensation
between two 400 V bridges,

    P = V1 * V2 / (omega * M)

so 3.0 kW at 85 kHz from a 400 V square wave (360 V rms fundamental) needs
**M = 80.9 µH**. Mutual inductance cannot exceed self-inductance, and the white
paper's coils are **12 µH**. Reaching 3 kW would need k = 6.75, where k ≤ 1 by
definition. The coils are roughly an order of magnitude too small.

The simulation shows what that looks like in practice. Driven at resonance at
400 V, the v1 tank draws **403 A rms** and puts **4.07 kV** across the
compensation capacitor. The LMG2610 the white paper selects is rated 6.4 A.
Coil dissipation at that current is 403² × 0.8 ≈ **130 kW** in a pad that has
to shed its heat by conduction alone.

The v1 link is therefore not a design that underperforms; it is one that cannot
be operated at its stated bus voltage at resonance at all. Which is consistent
with what the white paper reports from the bench: a resonance tracker that
hunts, and a system characterised at far lower power.

**Held fixed:** 85 kHz drive, 400 V bus, series-series compensation, the coil
as built. **Not varied:** operating frequency far off resonance, a lower bus
voltage, parallel compensation. Any of those makes the v1 hardware *do*
something — none of them makes it deliver 3 kW, because M is the binding limit
and none of them changes M.

## F15 — the white paper's Q of 12 does not hold at the stated frequency

Q = ωL/R with the paper's own L and R gives **8.0 at 85 kHz**, not 12. Q reaches
12 at about 127 kHz, above the top of the 80–120 kHz band the paper specifies.
Nothing downstream depends on this, but a Q quoted without its frequency is how
a coupling budget goes wrong, and `MEC-001` is written as k·Q for that reason.

## F16 — the corrected coil works, and puts 471–622 V on the rectifier

The ADR-0001 design point — 24 turns, 0.25 mm trace, 4 oz, 16 transposed
layers, from `sim/coil/coil_rect.py`, not from memory — gives L = 220 µH,
R_ac = 0.673 Ω and k of 0.433 to 0.572 across the `SYS-006` envelope. Simulated,
it moves 2.1–2.8 kW at **4–8 A** of tank current: three orders of magnitude off
the v1 currents, and inside every device rating.

But the operating point is not where the architecture assumes. With a passive
rectifier, output voltage is set by the load, and delivering 3 kW puts the
rectifier at **471 V at the worst corner, 566 V nominal and 622 V at minimum
gap** — not the 400 V of the `HVDC` rail in `hw/block-diagram.yaml`. Two
consequences, and both are open:

* The rail is misspecified. `HVDC` is 400 V in the block diagram and the real
  figure is roughly 470–620 V, which changes the device voltage class on the
  vehicle DAB's high-voltage bridge.
* It **varies by 32% across the docking envelope** at constant power. The
  downstream DAB has to absorb that, which is a control requirement nobody has
  written yet.

An actively rectified receiver would decouple power from output voltage and
remove both. That is an architecture decision, not a simulation result, and it
belongs to the human.

## F17 — the vehicle DAB's loss budget does not close, and ELE-003's rationale was wrong

Solving for the transformer at 3 kW, 48 V to 400 V:

| φ | L_lk referred to LV | referred to HV | tank rms |
|---:|---:|---:|---:|
| 30° | 0.53 µH | 37 µH | 70.7 A |
| 90° | 0.96 µH | 67 µH | 102.3 A |

at 100 kHz; at 150 kHz the inductances scale by 2/3 and the currents do not
move. Small phase shift is clearly right — same power, 30% less current — and
0.53 µH referred to the low-voltage side is the number the planar transformer
should be specified to.

The conduction loss that follows is the problem. Each switch position conducts
for half the cycle, so a device carries I_rms/(√2·N) with N in parallel, and the
whole low-voltage bridge costs 2·I_rms²·R_ds/N:

* **two devices per branch**, as the white paper specifies — **152 W** at the
  best phase shift
* **four devices per branch**, as `ELE-003` specifies — **76 W**

`ELE-003` budgets **100 W for the entire vehicle-side converter**, rectified DC
to pack terminals. Four per branch spends 76% of that on low-voltage conduction
alone, before the high-voltage bridge, the transformer, or any switching loss.
Two per branch exceeds the whole budget by 52%.

**`ELE-003`'s rationale was wrong and has been corrected.** It claimed 74 W for
two devices and 37 W for four; both were understated about twofold because the
half-cycle factor was dropped. The conclusion it drove — four devices per branch
rather than two — survives and is strengthened. The budget it asserts does not.

`R_ds(on)` here is the 19 mΩ family figure for BSC190N15NS3 scaled 1.6× for
temperature, and it is **not confirmed against a fetched datasheet**. It is
recorded as blocked in `docs/reference/manifest.yaml`. The 100 W budget is the
requirement's, so the gap is real either way, but its size moves with this
number and it should be confirmed before `ELE-003` is re-budgeted.

## What these decks do not cover

Deliberately, and they should not be read as if they did:

* **No switching loss, no ZVS, no dead time.** Both decks use ideal square-wave
  sources. That is the right reduction for a power-transfer question and the
  wrong one for a thermal answer. Chunk `S2` needs real device models, and
  those need datasheets that are not yet fetched.
* **No EMC, no parasitics.** The white paper is explicit that GaN slew rate and
  loop inductance are the hard part of the TX layout; nothing here models that.
* **The rectifier is a generic fast diode.** The paper names MURSDA860 but gives
  no ratings, and a 400 V — let alone 620 V — rectifier is a voltage-class
  question. Recorded as blocked in the manifest.
* **The DAB deck is a power-transfer core**, two square waves across the
  leakage inductance. It says nothing about the magnetising current, the
  transformer's loss, or bridge behaviour at light load.

## F18 — the M = 80.9 µH target assumed an ACTIVE receiver, and the deck used a passive one

Raised by the customer, and they were right to ask. To be clear first: **M is
about the wireless TX-to-RX link, not the DAB.** The DAB has its own series
inductance, and it is a different number in a different place.

The muddle is real, though, and it is mine. Two formulas describe an SS-compensated
link and they are not interchangeable:

* both ends actively switched — `P = V1 * V2 / (omega * M)`. This is what gives
  M = 80.9 uH for 3 kW at 85 kHz between two 400 V bridges, and it is what
  ``MEC-002`` was written from.
* a passive diode rectifier on the receiver — `P = V1^2 * R_ac / (omega * M)^2`,
  where the output voltage is set by the load, not by a bridge.

`sim/link/link.cir` models a **passive** rectifier, because that is what
``U10`` is in the block diagram. So the 80.9 uH figure and the simulation
describe two different receivers, and F16's 471-622 V output is exactly the
symptom of that mismatch.

This sharpens the F16 decision rather than replacing it. **Active rectification
restores M = 80.9 uH as the design target AND regulates the output back to
400 V — it fixes both problems at once.** A passive rectifier means ``MEC-002``
has to be rewritten, because M stops being the governing quantity.

## F19 — the coil is designed for the wrong M, and 24 turns is 20

Following F18 through to the active-rectifier case exposes a second-order error
in ``ADR-0001``. Power transfer is INVERSELY proportional to omega times M, so
too much coupling limits power just as surely as too little:

| turns | L | M | k·Q | P max at 400 V, 85 kHz |
|---:|---:|---:|---:|---:|
| 24 (ADR-0001) | 220 µH | 114.6 µH | 90.9 | **2.12 kW** |
| 22 | 192 µH | 97.9 µH | 84.2 | 2.48 kW |
| **20** | **166 µH** | **82.2 µH** | **77.3** | **2.95 kW** |
| 18 | 140 µH | 67.7 µH | 70.3 | 3.59 kW |

``ADR-0001`` picked 24 turns by maximising k·Q, which is the EFFICIENCY figure,
and never checked M against the POWER requirement. At 24 turns the link tops out
at 2.12 kW — it cannot reach 3 kW at 400 V however well it is driven.

**20 turns gives M = 82.2 µH against the 80.9 µH ``MEC-002`` asks for, reaches
2.95 kW, and still carries k·Q of 77.3 against the 49 ``MEC-001`` requires.**
The efficiency margin was never the binding constraint; it just looked like it
because it was the only thing being optimised.

``ADR-0001`` and ``MEC-002`` both need revising to 20 turns, and that is M2's
work. It does not change the coil technology decision — a transposed
multi-layer etched PCB coil still passes — only the turn count.

## F20 — the 56 µH lands inside the range the DAB deck solved for

The customer supplied it: there is a **56 µH inductor in series with the DAB's
PCB-coil transformer**. `sim/dab/run_dab.py` had solved for 37-67 µH referred to
the high-voltage side, so the real part sits squarely inside the predicted band,
which is a useful check on the deck.

It must be the high-voltage side: referred to the low-voltage side, 56 µH would
cap the converter at 51 W. Referred properly it is 0.806 µH, and it pins the
operating point that was previously open:

| f | phase shift for 3.0 kW |
|---:|---:|
| 85 kHz | 41.9° |
| 100 kHz | 54.0° |
| 150 kHz | cannot reach 3 kW at any phase shift |

**The transformer as built cannot deliver 3 kW above about 119 kHz.** That is a
hard constraint on the switching frequency that nothing in the white paper
states, and it should go into the electrical requirements.
