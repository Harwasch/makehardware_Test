# ADR-0002 — TX power stage device

**Status:** Accepted for the architecture; the alternate is not yet fully verified.
**Date:** 2026-08-28
**Chunk:** E1

## Context

`ELE-005` requires each transmitter bridge switch to carry 17 A continuous and
24 A repetitive peak; `ELE-006` requires at least 650 V with an 80% derating
ceiling; `ELE-001` allows the whole four-switch bridge 25 W at 3 kW, where each
device sees 5.89 A RMS.

The v1 device, TI **LMG2610**, is disqualified by finding F1: it is a 650 V GaN
half bridge specified for **under 75 W active-clamp flyback**, whose 6.4 A and
4 A drain figures are absolute-maximum *peaks*, and whose 170/248 mΩ asymmetric
on-resistances are deliberately optimised for flyback duty and cannot be
balanced in a 50%-duty bridge.

A further constraint the v1 review surfaced: gate-loop parasitics were named in
the white paper as the reason the LMG2610 was chosen in the first place. Whatever
replaces it should keep the driver inside the package rather than reintroduce
the loop.

## Decision

**TI LMG3526R030**, four devices in a full bridge. Alternate: **Navitas NV6523**.

Verified directly from the datasheet (SNOSDF3B, Nov 2022 rev Jan 2025,
`docs/reference/lmg352xr030-SNOSDF3B.pdf`):

| Parameter | Value | Against the requirement |
|---|---|---|
| V_DS | 650 V (720 V surge, 800 V transient ringing peak) | `ELE-006` met; 400 V is 62% of rating |
| **I_D(RMS)** | **55 A** — an RMS rating, not a peak | `ELE-005` met with 9.3× margin at 5.89 A RMS |
| I_D(pulse) | 125 A, internally limited (intrinsic 120 A, t_p < 10 µs) | 24 A repetitive peak met with 5× margin |
| R_DS(on) | 26 mΩ typ / 35 mΩ max at T_J = 25 °C; **45 mΩ typ at 125 °C** | conduction 4 × 5.89² × 0.045 = **6.24 W** of the 25 W budget |
| R_θJC(top) | 0.28 °C/W | 1.56 W per device is a 0.44 °C junction rise over case |
| Q_RR | **0** | no reverse-recovery loss at any switching speed |
| C_O(er) | 320 pF at 400 V | Q_OSS 190 nC; 2 × 190 nC at ~8 A tank current is a ~48 ns transition |
| Characterisation V_DS | 520 V | our 400 V bus sits inside the characterised range |

The device integrates the driver, gate bias generation, over-current and
short-circuit protection, adjustable 20–150 V/ns slew control, and PWM
temperature reporting behind a logic-level input. The **R030 variant is chosen
over the R050** for conduction loss, and the **3526 over the 3522** because it
adds zero-voltage detection — which in a series-resonant bridge is exactly the
signal the controller wants to confirm ZVS rather than infer it.

Conduction loss is **25% of the bridge budget**, leaving 18.8 W for switching.
Even scaling the guaranteed 25 °C maximum by the typ hot/cold ratio to a
worst-case 60.6 mΩ gives 8.4 W, still 34% of budget.

## Consequences

**Good.** Nine times the current margin the requirement asks for, and the
driver is inside the package so the v1 gate-loop failure mode does not exist
outside it. Zero reverse recovery removes an entire loss term. Top-side cooling
at 0.28 °C/W is the right thermal direction for a conduction-cooled design with
no forced air — heat leaves through the top face into a cold plate rather than
down through the board.

**Bad, and it matters.** *TI publishes no guaranteed maximum R_DS(on) at
125 °C* — only a typical. Every hot-conduction number above is therefore a
typical, and the worst-case figure is an extrapolation. Confirm with TI before
release.

**Bad, and specific to conduction cooling.** The top thermal pad is at SOURCE
potential. On the two high-side devices that is the switching node, slewing
0–400 V at up to 150 V/ns, pressed against a cold plate. The thermal interface
becomes a capacitor injecting displacement current into the chassis, which is
both an EMC problem and a safety one. **The thermal interface material has to be
selected for low capacitance as well as low thermal resistance, and the cold
plate's ground reference has to be a deliberate decision, not an assumption.**
This is now the largest open risk in the power stage and belongs in the EMC
work, not the thermal work.

**Bad.** C_O(er) of 320 pF is the largest in the candidate field. In the
intended ZVS operation that energy is recovered and helps the resonant
transition, but if ZVS is ever lost the C_OSS loss alone is 4 × 25.6 µJ ×
85 kHz = 8.7 W on top of conduction. That makes ZVS a loss-budget dependency,
not just an efficiency nicety — and it is why `S2` sweeps dead time at corners.

## Alternatives considered

* **Navitas NV6523** (GaNSafe, TOLT-16L) — 650 V/800 V transient, top-cooled,
  production datasheet, in stock. 77 mΩ typ at 150 °C gives 10.7 W, 43% of
  budget. Kept as the alternate: it drops into the same cold-plate mechanical
  design, but costs 4.4 W more and still needs an external isolated driver
  sourcing >500 mA into V_DRIVE.
* **Navitas NV6515** (TOLL-4L) — lower loss than its sibling at 8.3 W, but
  **bottom-cooled**, so heat crosses the PCB through a via field before reaching
  the cold plate, which is the wrong direction here. Only a preliminary
  datasheet was available.
* **Infineon IGT65R035D2** (CoolGaN G5) — electrically fine and the widest
  transient margin at 900 V, but a bare transistor with no integrated driver.
  Using it means hand-building the GaN gate loop, which is the exact failure
  v1 chose the LMG2610 to avoid. Infineon's integrated-driver line cannot
  substitute at this voltage.
* **Wolfspeed C3M0060065K** (650 V SiC) — technology hedge only. Highest loss
  at 11.1 W, needs an external isolated driver with a −4 V off-rail, TO-247-4
  with roughly four times the footprint, and its tab is DRAIN so bolting it to
  structure needs an insulating pad worth another 0.5–1 °C/W. Its hard-switched
  E_ON of 70 µJ would consume the entire 25 W budget on switching alone if ZVS
  were lost, where the GaN candidates degrade gracefully.

## Verification status

The LMG352xR030 numbers above were read from the datasheet directly and are
confirmed. **The four alternates were researched by a subagent whose
verification pass did not run** — the workflow hit the account rate limit
before the adversarial check completed. Their figures are recorded here as
researched-but-unverified and must be re-read from primary sources before any
of them is promoted to primary.
