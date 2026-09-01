# The boards as they stand — conversion, simulation and analysis

Three EasyEDA designs were supplied on 2026-09-01 and are now in the repo:

| Board | EasyEDA document | KiCad project | Parts | Nets |
|---|---|---|---|---|
| HV/LV DAB | `hw/easyeda/DAB_Iter1/` | `hw/kicad/dab.kicad_pro` | 204 | 88 |
| Transmitter | `hw/easyeda/TX_Iter1/` | `hw/kicad/tx.kicad_pro` | 117 | 50 |
| Receiver | `hw/easyeda/RX_Iter1/` | `hw/kicad/rx.kicad_pro` | 70 | 27 |

Everything below is derived from those files. `scripts/eda_parse.py` rebuilds the
netlist geometrically from the sheet; `scripts/kicad_net_check.py` diffs the
KiCad netlist against it. All three boards come back **MATCH** — same partition
of pins into nets, pin for pin — so the KiCad projects are the same circuit, not
an approximation of it.

```
DAB   88 nets, 645 connected pins   MATCH
TX    50 nets, 376 connected pins   MATCH
RX    27 nets, 182 connected pins   MATCH
```

Reproduce with:

```bash
/opt/hw-py/bin/python scripts/eda_parse.py hw/easyeda/DAB_Iter1/schematic.json \
    --bom build/eda/DAB-bom.csv --netlist build/eda/DAB-netlist.txt --json build/eda/DAB.json
/opt/hw-py/bin/python scripts/kicad_net_check.py build/eda/dab-kicad.net build/eda/DAB.json
/opt/hw-py/bin/python sim/asbuilt/topology.py          # the numbers in this document
/opt/hw-py/bin/python sim/asbuilt/make_decks.py        # regenerate the ngspice decks
/opt/hw-py/bin/python sim/asbuilt/sweep.py 24 300      # frequency sweep
```

---

## What the boards actually are

**TX** — a full bridge made from two TI **LMG2640** 650 V GaN half-bridge power
stages (U11, U26) across a bus (`VCC`) whose bulk is 500 V-class film and X7R.
Leg A's switch node `SW` goes through **three 100 nF X2 film capacitors in
parallel (300 nF)** to the `PORT_OUT+` pad; leg B's switch node `SW2` goes
straight to its own pad. Current sense is the LMG2640's own emulated CS output
into an OPA2328 per leg. Control is an STM32H723ZGT6.

**RX** — a full-bridge rectifier of **twelve MURSD860A**, three per arm, feeding
`VCC`/`GND2` through five 1.5 µF TDK film capacitors to an XT60PB connector.
`PORT+` reaches the bridge through **another three 100 nF in parallel (300 nF)**;
`PORT-` goes through a TMCS1133 current sensor. An STM32G431RBT6 supervises.

**DAB** — an HV full bridge of four **IPB60R120P7** (600 V) across `HV_BUS`, and
an LV bridge of eight **BSC190N15NS3G** (150 V, 19 mΩ, two per switch) across
`LV_BUS`. Gate drive is four UCC27714 with two UCC14141 isolated bias supplies.
An STM32H723ZGT6 drives four complementary pairs A/A#, B/B#, C/C#, D/D#.

So the intended chain is: 400 V bus → TX bridge → 300 nF → coil → coil →
300 nF → RX rectifier → 400 V → DAB HV bridge → transformer → DAB LV bridge →
48 V battery.

---

## Findings

### F21 — the series compensation is 19× too large for 85 kHz *(blocking)*

Both boards fit 300 nF. Series-series compensation resonates at
`f = 1/(2π√(LC))`, so 300 nF implies the coil inductance in the middle column:

| f (kHz) | L implied by 300 nF (µH) |
|---|---|
| 20 | 211 |
| 40 | 52.8 |
| **85** | **11.7** |
| 100 | 8.4 |

The coil this programme designed (ADR-0001, 102 × 203 mm, 24 turns, 16
transposed layers) is **220 µH** by `sim/coil/coil_rect.py`. With 300 nF that
resonates at **19.6 kHz**, not 85 kHz. Reaching 85 kHz on that coil needs
**15.9 nF** — a nineteenth of what is fitted.

Simulated, driving the designed coil at 85 kHz through the fitted 300 nF
(`sim/asbuilt/link-24t-85k.cir`):

```
P_in 51 W    P_out 44 W    I_tank 2.15 A rms    V_out 48.6 V
```

**44 W against a 3 kW requirement.** The tank is far above resonance, so its
reactance — not the load — sets the current.

Either the capacitor bank or the coil has to move. They cannot both be right.

### F22 — the TX GaN stage cannot reach 3 kW, at any tuning *(blocking)*

From the LMG2640 datasheet (SNOSDH5, November 2024, now in
`docs/reference/`):

* recommended continuous drain current **±8.2 A**, both FETs
* cycle-by-cycle over-current threshold **8.2 A min / 9.1 A typ / 10 A max** —
  the device gates itself off above this
* R<sub>DS(on)</sub> 105 mΩ at 25 °C, **200 mΩ at 125 °C**

A 400 V bridge's fundamental is 360 V rms. At unity power factor:

| OCP trip (A peak) | I₁ (A rms) | Deliverable power (W) |
|---|---|---|
| 8.2 (min) | 5.80 | **2088** |
| 9.1 (typ) | 6.43 | 2317 |
| 10.0 (max) | 7.07 | 2546 |

3 kW needs 8.3 A rms — **11.8 A peak**, above even the best-case trip point. The
part protects itself before the design reaches its rating. This is a device
limit, not a tuning problem: no capacitor value fixes it.

Three ways out, all of which are decisions for you rather than for me: raise the
bus (3 kW at 5.8 A rms needs ~574 V, which erases the margin on both the 650 V
GaN and the 500 V capacitors), parallel or interleave more stages, or lower the
system power target.

The same shape of finding retired the LMG2610 in ADR-0002. The LMG2640 is a real
improvement — 8.2 A against 6.4 A peak — but it is still short of 3 kW.

### F23 — the DAB's HV bridge output is closed on itself *(blocking)*

Tracing the DAB sheet from the HV bridge:

```
AH.S / AL.D  ->  net D1_1  ->  L1.1
L1.2         ->  net S$194154  ->  U94.IN+     (TMCS1133 current sensor)
U94.IN-      ->  net BH_3      ->  BH.S / BL.D
```

That is the entire loop. **There is no transformer and no port** between the two
legs — the bridge output returns to itself through the 47 µH inductor and the
sense element. The same is true on the PCB: `D1_1` has 7 pads, `S$194154` has 2,
`BH_3` has 7, and there is no free pad or connector on any of them.

Simulated as drawn at 400 V, 85 kHz (`sim/asbuilt/dab-hv-loop.cir`):

```
i_pk +25.00 A    i_min -25.00 A    i_rms 14.44 A    i_bus 0.12 A
```

which matches the closed form `Δi = V·T/(2L) = 50.1 A` peak-to-peak and
`i_rms = 14.45 A` to 0.1 %. No power is transferred; the current is pure
circulating ripple.

L1 is an `IHLP6767GZER470M11`, rated **8.6 A saturation / 8.7 A rms** (Vishay
via DigiKey/TME parametric — see the manifest note). The loop asks it for 25 A
peak. In reality the core saturates around a third of that, the inductance
collapses and the current runs away further.

The user has described "a 56 µH inductor in series with the PCB-coil transformer
of the DAB". The board has 47 µH and no transformer. Both need reconciling.

### F24 — the DAB's two LV bridge legs share one switch node *(blocking)*

Net `SEC` carries all of:

```
CH1.S CH2.S DH1.S DH2.S   (four high-side sources)
CL1.D CL2.D DL1.D DL2.D   (four low-side drains)
AGD3.HS AGD4.HS  CBA3.1 CBA4.1  A_H_PD3.1 A_H_PD4.1  D3.A D11.A
```

Leg C and leg D therefore have the *same* switch node — 24 pads on the PCB, so
this is the layout as well as the schematic. But the gates are separate: AGD4
drives C/C# and AGD3 drives D/D#, from independent MCU outputs.

The moment firmware phases C against D — which is what a full bridge does — a
high-side FET of one leg and a low-side FET of the other are on together across
`LV_BUS` with nothing in between. At 48 V into 8 × 19 mΩ that is a bolted fault.

Either the two legs should be one paralleled leg driven by one signal (in which
case the transformer needs somewhere else to connect), or the node has to be
split. As drawn it is not a working full bridge.

### F25 — LV_BUS bulk capacitors are 25 V parts *(blocking)*

`LV_BUS` carries `C6`, `C7`, `C8` = **XT470UF25V90RV0111**. The part number
spells the rating: **470 µF, 25 V**. `LV_BUS` is the vehicle-battery side, 48 V
nominal and up to ~58.8 V for a 14S pack.

The other four capacitors on the same net (`U64`, `U65`, `U106`, `U107`,
NCC `HHXC630ARA220MF80G`) read 63 V / 22 µF from the NCC code, and the 6.3 mm
can in the footprint corroborates 63 V rather than 630 V. Those are correctly
classed; the three 470 µF parts are not.

### F26 — the DAB's LV output connector is at twice its current rating

Amass XT connectors are named for current, not voltage: XT60 is 30 A continuous
/ 500 V DC, XT30 is 15 A / 500 V (TME/Amass listings).

| Net | Connector | Current at 3 kW | Rating |
|---|---|---|---|
| DAB `HV_BUS` | U82 XT60-M | 7.5 A | 30 A |
| **DAB `LV_BUS`** | **U83 XT60-M** | **62.5 A** | **30 A** |
| DAB 48 V aux | CN1 XT30UW | ~1 A | 15 A |
| RX `VCC` | CN3 XT60PB | 7.5 A | 30 A |

Voltage is comfortable everywhere. The LV output is at 2.1× its current rating.

### F27 — strong coupling splits the resonance; 85 kHz is the dip

This one is physics, not a mistake, and it changes how the link should be
driven. At k = 0.52 the two tuned tanks are strongly coupled, so the link has
**two** resonances at roughly `f₀/√(1±k)`, not one at `f₀`.

Sweeping the correctly tuned case (24-turn coil, 15.9 nF, so f₀ = 85 kHz):

| f (kHz) | P_out (W) | η | I_tank (A rms) |
|---|---|---|---|
| 68.9 | 679 | 0.944 | 4.8 |
| **72.3** | **732** | 0.950 | 4.5 |
| 76.5 | 553 | 0.956 | 3.2 |
| **85.0** | **375** | 0.957 | 2.2 |
| 93.5 | 383 | 0.955 | 2.3 |
| **114.8** | **734** | 0.945 | 4.4 |
| 131.8 | 423 | 0.932 | 3.8 |

Predicted split: 69.0 kHz and 122.7 kHz; simulated peaks at 72 and 115 kHz, the
load pulling them inward. Driving at the coil's own resonance delivers **half**
what driving at either split peak does.

The requirements assume a single 85 kHz resonance. For a belly-dock pad at
k ≈ 0.5 that assumption does not hold, and the firmware's resonance tracker will
find one of the split peaks, not 85 kHz. This wants to be settled in the
requirements before the coil is committed.

### F28 — eight unvalued capacitors on the TX 400 V bus

`TX VCC` carries `C1 C3 C4 C6 C8 C29 C30 C31`, all with part `C1206` /
LCSC `C9900018280` — a generic placeholder, no capacitance and no voltage
rating. They sit directly across the 400 V bus. Whatever they are meant to be
has to be specified before this can be quoted or built.

### F29 — MURSD860A cannot be sourced from a datasheet *(blocked)*

The RX rectifier is twelve MURSD860A. The EasyEDA file records no manufacturer,
and the part could not be resolved to a datasheet: onsemi's `MUR860` is 600 V /
8 A in TO-220, this is a TO-252 part with a different suffix, and the LCSC page
for `C2852589` was not reachable from here.

The reverse voltage rating decides whether the RX bridge is right or badly
wrong, since the surrounding parts imply a ~400 V link. **Recorded as blocked in
`docs/reference/manifest.yaml` — please supply the datasheet or the intended
rating.**

---

## What still holds from before

The coil work is unaffected: `sim/coil/` and ADR-0001 are geometry and materials
analysis, and nothing in these boards contradicts them. The 24-turn design point
gives L = 220 µH, k = 0.52, Q = 174, k·Q = 91 at 85 kHz — comfortably past the
k·Q ≥ 49 the efficiency target needs.

What the boards do contradict is the *electrical* design point around that coil:
the compensation, the drive frequency, and the power the TX stage can pass.

## What I removed

`sim/link/`, `sim/dab/`, `sim/kicad/` and `docs/design/sim-{link,dab,findings}.md`
modelled an assumed topology — a 48 V↔400 V DAB with a transformer, and an
active-both-ends link. Neither matches these files, so their numbers no longer
describe anything real. They are gone; `sim/asbuilt/` replaces them and derives
every component value from the EasyEDA export.

## Decisions I need from you

1. **F21** — move the compensation, or move the coil? These are different
   programmes: 15.9 nF on the designed coil, or a ~6-turn coil to suit 300 nF
   (which drops k·Q from 91 to ~24 and puts the efficiency target out of reach).
2. **F22** — 3 kW needs a different TX power stage, a higher bus, or a lower
   target. Which?
3. **F23/F24** — is the DAB board an intentional bench fixture (bridge into an
   inductor, LV legs paralleled), or are the transformer and the second switch
   node missing?
4. **F29** — the MURSD860A rating.
5. **F27** — should the requirements move off a fixed 85 kHz?
