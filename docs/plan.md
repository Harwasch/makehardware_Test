# Plan — Ulysses LARS Charger

What work exists, what each piece is, and what has to happen first.
**Statuses are deliberately not in this file** — see the chart in the README for those. This is the scope, and it is what the plan review signs off.

27 chunks · 16 sessions on the critical path · disciplines: electrical, firmware, mechanical, test, documentation

![dependency chart](plan.svg)

## The work

### documentation

#### V1 — Vision, v1 baseline review and link budget  *(critical path)*

Artefacts complete and pushed; the AGREEMENT on them is not. Held at in_progress because review 'vision' is open and unsigned - the stage's own exit condition. The related gate chunk is G1, which is still open — the vision stage's exit condition was never met, so the plan and requirements downstream were built on an unreviewed vision. Established that the v1 magnetics cannot reach 3 kW and that coil-to-coil efficiency is the constraint that decides the architecture.

* **Needs first:** nothing
* **Estimate:** 1 session
* **Produces:** `requirements/00-vision.sdoc`, `docs/design/vision.md`, `docs/design/vision/`, `docs/design/v1-baseline.md`, `sim/link-budget/link_budget.py`, `concepts/`
* **Human review:** `vision` must be signed off before this chunk can be done

#### G1 — Vision review gate — the human agrees the concepts and the numbers

The agreement the workflow requires and never got. Three docking arrangements are in front of the human with the corrected coil analysis; five questions are open. Design chunks depend on this rather than on V1, because designing against an unagreed vision is what produced two bare coil pads when the human wanted to see a product. CLOSED: belly dock, no actuator, charging on deck in a locating bracket, scope limited to the charging system, 4 x 8 inch pad, and PCB kept per ADR-0001. RE-OPENED under the v0.2.0 review mechanism: those decisions were taken in chat and never signed into a ledger, and the locating approach is still open.

* **Needs first:** V1
* **Estimate:** 1 session
* **Produces:** `docs/review/vision.md`, `docs/review/gate-1-vision-record.md`
* **Human review:** `vision` must be signed off before this chunk can be done

#### R1 — System and discipline requirements from the agreed vision  *(critical path)*

Requirements are written against k*Q and pad dissipation, not against a coil technology, so the M2 decision is settled on evidence.

* **Needs first:** V1
* **Estimate:** 1 session
* **Produces:** `requirements/10-system.sdoc`, `requirements/20-electrical.sdoc`, `requirements/20-mechanical.sdoc`, `requirements/20-firmware.sdoc`, `docs/design/requirements-map.svg`
* **Human review:** `requirements` must be signed off before this chunk can be done

#### R2 — Environmental envelope from the marine standards

Design ambient for an open-deck enclosure on a surface vessel operating worldwide, traced to IEC 60945, IACS UR E10 and classification-society rules rather than assumed. Feeds SYS-007 and MEC-004, and blocks the thermal work in M3. Work complete; held at in_progress because it rests on an unsigned vision - if the review moves the application away from an open deck, the +55 C envelope moves with it.

* **Needs first:** V1
* **Estimate:** 1 session
* **Produces:** `docs/design/environment.md`

#### D1 — Design record — ADRs, architecture and interfaces consolidated

* **Needs first:** M2, E1B
* **Estimate:** 1 session
* **Produces:** `docs/design/architecture.md`, `docs/design/interfaces.md`

#### D2 — User documentation and spec sheet

* **Needs first:** T1
* **Estimate:** 1 session
* **Produces:** `docs/user/`

### mechanical

#### M1 — Coil electromagnetic modelling — predict L, R_ac, Q and k by analysis  *(critical path)*

CRITICAL PATH AND EARLIEST RISK, and now an analysis chunk rather than a bench one: no laboratory access, so the quality factor the whole architecture rests on must be predicted from first principles and defended. Self-inductance from Wheeler and Mohan, mutual inductance and coupling from Maxwell's coaxial-filament formula summed over turns, AC resistance from skin and proximity models for both an etched spiral and a Litz bundle. Validated against published MEASURED data for comparable coils, because a model with no measurement behind it anywhere is not evidence. The v1 numbers are internally inconsistent — a stated Q of 12 implies 127 kHz, not the stated 85 kHz — so they cannot serve as the check.
DONE, and CORRECTED. The house coil is a 102 x 203 mm rectangle, not a circle, and the first analysis generalised a single-layer result to a whole conductor technology. Recomputed with coil_rect.py: 32 turns of 0.80 mm trace in 4 oz with SIX LAYERS in parallel reaches k*Q = 77 worst case against the 49 required. Fine traces nearly remove proximity effect (R_ac/R_dc 1.06), so the coil becomes a DC-resistance problem that layers fix. An etched coil MEETS MEC-001. Inter-layer proximity is now the largest modelling uncertainty and is the first FEA task in M2.
Analysis complete and reproducible; held at in_progress because it rests on an unsigned vision and on ADR-0001, whose 4 x 8 inch pad and 16-layer stack are both questions still in front of the human.

* **Needs first:** R1
* **Estimate:** 2 sessions
* **Produces:** `sim/coil/coil_rect.py`, `sim/coil/`, `docs/design/coil-model.md`

#### M2 — Coil technology decision, magnetics design and compensation network  *(critical path)*

Picks PCB or Litz against M1's predictions, then sizes turns, geometry, ferrite and the series tuning capacitor. The tank capacitor is a real part nobody has specified — roughly 22 nF standing off 720 V rms and carrying the full 8.3 A of tank current.

* **Needs first:** M1, G1
* **Estimate:** 2 sessions
* **Produces:** `docs/design/adr-0001-coil-technology.md`, `cad/coil_pad.py`, `docs/design/magnetics.md`

#### M3 — Coil pad thermal design, conduction path and packaging

gmsh + CalculiX. VIS-006 allows no coolant, so this chunk is what proves the M2 choice survives. The dock enclosure sits on OPEN DECK on a surface vessel operating worldwide, so the ambient envelope comes from the marine standards plus solar gain — settled in R2.

* **Needs first:** M2
* **Estimate:** 2 sessions
* **Produces:** `cad/coil_pad.py`, `sim/thermal/`, `docs/design/thermal.md`

### electrical

#### E1 — Power architecture, topology and part selection

TX power stage now settled by ADR-0002 (LMG3526R030, verified against SNOSDF3B). Remaining: the RX rectifier technology, the DAB switches for both sides, the isolation set against the 800 V reinforced requirement, and the resonant capacitor. Bidirectional operation is confirmed required, and the 700 V offline aux stage is no longer needed now that both docks have a 48 V pack.

* **Needs first:** R1, G1
* **Estimate:** 2 sessions
* **Produces:** `docs/design/adr-0002-tx-power-stage.md`, `docs/reference/manifest.yaml`

#### E1B — Block diagram and power budget across all three boards  *(critical path)*

Provisional diagram written and block-diagram --check passes, but the currents are estimates: this chunk cannot close until E1 settles the parts and M2 the magnetics. It already forced two findings — the aux rail cannot be fed from a 60 V-input part on a 400 V bus, and 600 mA is not enough for the TX aux tree.

* **Needs first:** E1, M2
* **Estimate:** 1 session
* **Produces:** `hw/block-diagram.yaml`, `docs/design/block-diagram.svg`
* **Human review:** `architecture` must be signed off before this chunk can be done

#### E2 — TX board schematic capture and ERC  *(critical path)*

GaN H-bridge, aux rails, current sense, STM32H723.

* **Needs first:** E1B
* **Estimate:** 2 sessions
* **Produces:** `hw/tx/tx.kicad_sch`

#### E3 — RX board schematic capture and ERC

Rectifier, bulk, isolated current sense, STM32G431. The v1 bridge is ultrafast silicon described as Schottky; evaluate SiC Schottky and synchronous rectification against the 26 W the diode bridge costs.

* **Needs first:** E1B
* **Estimate:** 1 session
* **Produces:** `hw/rx/rx.kicad_sch`

#### E4 — HVLV dual-active-bridge schematic capture and ERC  *(critical path)*

48 V LV side carries 62.5 A at 3 kW. The v1 two-FETs-per-branch choice dissipates 74 W in conduction alone; more paralleling or a lower-R part.

* **Needs first:** E1B
* **Estimate:** 2 sessions
* **Produces:** `hw/hvlv/hvlv.kicad_sch`

#### E5 — TX PCB layout, DRC and fabrication outputs  *(critical path)*

GaN switching loop and gate loop inductance dominate this layout.

* **Needs first:** E2, S2
* **Estimate:** 2 sessions
* **Produces:** `hw/tx/tx.kicad_pcb`, `build/fab/tx/`

#### E6 — RX PCB layout, DRC and fabrication outputs

* **Needs first:** E3
* **Estimate:** 1 session
* **Produces:** `hw/rx/rx.kicad_pcb`, `build/fab/rx/`

#### E7 — HVLV PCB layout, DRC and fabrication outputs  *(critical path)*

62.5 A of LV copper and a planar transformer in the stackup.

* **Needs first:** E4, S2
* **Estimate:** 2 sessions
* **Produces:** `hw/hvlv/hvlv.kicad_pcb`, `build/fab/hvlv/`

#### E8 — In-band communication link — modulation, demodulation and damping

Data over the power coils. The binding constraint is that the tank is a bandpass filter whose bandwidth swings 50x with load: 43 kHz at 3 kW but only 867 Hz at no load, which is exactly when the handshake happens. Includes the switched damping network that buys that bandwidth back, and its hardware interlock — 22 ohm across the tank at full drive is 5.9 kW.

* **Needs first:** E1, M2
* **Estimate:** 2 sessions
* **Produces:** `docs/design/in-band-comms.md`, `docs/design/adr-0004-comms.md`, `sim/comms/`

#### E9 — Leviathan-side instance — configuration, harness and commissioning

UNBLOCKED. The Leviathan pack is 48 V nominal, the same as the Mako's, so one low-voltage specification covers both ends and the two instances are the same board with different firmware configuration and orientation. What is left here is the dock harness — which carries 48 V for the transmitter's auxiliary rails alongside the 400 V link — the commissioning differences, and the interface document.

* **Needs first:** E4, E7
* **Estimate:** 1 session
* **Produces:** `docs/design/adr-0005-dab-instances.md`, `docs/design/interfaces.md`

### test

#### S1 — Resonant link simulation, cross-checked against the closed form

ngspice model of the compensated link. Must reconcile with sim/link-budget/link_budget.py; a disagreement means one of them is wrong.

* **Needs first:** M2, E1
* **Estimate:** 1 session
* **Produces:** `sim/link/`, `docs/design/link-simulation.md`

#### S2 — Power stage simulation — ZVS, dead time and switching loss

Dead time is safety-critical here and v1 never set it in firmware at all. Sweep corners; a dead time that works at 25 C and shoots through at 85 C is the failure this chunk exists to catch.

* **Needs first:** E1
* **Estimate:** 1 session
* **Produces:** `sim/power-stage/`, `docs/design/switching.md`

#### T1 — Analysis and simulation close-out against the requirements  *(critical path)*

Everything closeable without a laboratory: the Analysis and Simulation requirements, the budget roll-ups, ERC and DRC. req-trace --gate will still exit 1, because every Test requirement stays open until T2. Report the number it prints, gaps first, and do not restate a Test requirement as an Analysis one to make the gate pass.

* **Needs first:** E5, E6, E7, F3, F4, M3, S1
* **Estimate:** 2 sessions
* **Produces:** `docs/design/verification-report.md`

#### T2 — Bench verification — deferred until laboratory access  *(critical path)*

OUT OF SCOPE FOR NOW by instruction: no laboratory work. Held in the plan rather than deleted, because the Test-method requirements are real and the coil quality factor in particular is a prediction until something is measured. This chunk is what closes them.

* **Needs first:** T1
* **Estimate:** 3 sessions
* **Produces:** `docs/design/verification-report.md`

### firmware

#### F1 — TX resonance-tracking firmware rework  *(critical path)*

Keep the validated two-stage architecture; fix the eight findings. The filter is a median where the paper claims RMS, the smoothing branch is dead code, the re-sweep guard can never fire, and dead time is never set.

* **Needs first:** E1B
* **Estimate:** 2 sessions
* **Produces:** `fw/tx/`

#### F2 — HVLV CC/CV control firmware with real constants

Every control constant in v1 is a FILL THIS OUT LATER placeholder, the phase shift is gated behind a condition that can never be true, and the 50 us control ISR does blocking ADC polls with a 1 ms timeout.

* **Needs first:** E1B
* **Estimate:** 2 sessions
* **Produces:** `fw/hvlv/`

#### F3 — Protection, fault handling and safe-state behaviour

Hardware break inputs, over-current and over-voltage trips, coupling-loss detection, and the charge-rate limit the present 1.58 kWh pack needs. v1 has none of this: TIM break is disabled everywhere.

* **Needs first:** F1, F2, S2
* **Estimate:** 1 session
* **Produces:** `fw/common/`, `docs/design/adr-0003-protection.md`

#### F4 — Link protocol, handshake and coexistence with resonance tracking  *(critical path)*

Framing, CRC and the SYS-013 interlock that keeps the dock at handshake power until a receiver identifies itself. The load-shift keying and the resonance hill-climb use the same quantity in opposite directions and will fight unless blanked against each other.

* **Needs first:** E8, F1
* **Estimate:** 2 sessions
* **Produces:** `fw/common/comms/`, `docs/design/protocol.md`

## What we are asking you

1. **Is this all the work?** Test, documentation and manufacturing are the ones that get left out.
2. **Is the order right?** You may know a constraint we do not — a part already on the shelf, a lead time, a review that has to pass.
3. **Is any chunk the wrong size?** One chunk is about one working session; a chunk that is really three should be split now.

---

<sub>Generated by `plan-render` from `plan.yaml`. Edit the plan, not this file.</sub>
