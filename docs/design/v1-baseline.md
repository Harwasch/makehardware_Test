# v1 baseline — the Mako 2.0 wireless charger as documented

Source: `docs/reference/source/mako-charging-white-paper.pdf`, plus the two
firmware repositories archived under `docs/reference/source/fw-v1/`.

This document is the **as-documented** record of v1 and a review of it. It is
not a design for v2. Its job is to establish what exists, which numbers are
trustworthy, and which of them will not survive contact with the 3 kW target —
so that the v2 requirements are written against reality rather than against the
white paper's claims.

Everything in *Findings* was derived from the primary sources: the vendor
datasheets in `docs/reference/manifest.yaml` and the firmware source itself.

## 1. Top-level intent

| Parameter | Value | Source |
|---|---|---|
| Max power transfer | 3 kW | white paper p.1 |
| Input bus | 400 VDC | white paper p.1 |
| Vehicle battery | 8 kWh | white paper p.1 |
| Target charge time | 2.6 h | white paper p.1 |
| Coupling | magnetic resonant, air gap | white paper p.1 |
| Drive frequency band | 80–120 kHz, 85 kHz nominal | white paper p.3 |

The 2.6 h figure is consistent: 8 kWh ÷ 3 kW = 2.67 h at 100% efficiency, so it
is a *floor*, and it assumes the charger holds full power for the whole charge.
A real CC/CV profile tapers, so 2.6 h is not achievable end-to-end. **v2 should
state charge time against a defined SoC window and efficiency, not as 8/3.**

## 2. Architecture as built

Three boards, two of them on one PCB (`RXTX`):

```
Leviathan 400 V ─► HVLV (dual active bridge) ─► TX H-bridge ─► TX coil
                                                                 ) )  air gap
                       Mako battery ◄─ RX rectifier ◄─ RX coil ◄─
```

* **HVLV** — bi-directional dual active bridge, planar transformer, phase-shift
  controlled by an STM32H723ZGT6 using TIM1/TIM8.
  HV bridge `IPB60R120` CoolMOS; LV bridge `BSC190N` OptiMOS, two paralleled per
  branch. Isolation set: `UCC1414` (gate-drive power), `ISO7740` (PWM),
  `ISO224` (analog), `UCC33420` (digital power). Gate drive `UCC27741`.
  Aux rails from `TPSM560`.
* **TX** — high-voltage GaN H-bridge, `LMG2610`, 80–120 kHz square wave into a
  series-resonant tank. Current-sense emulation → `OPA2328` → STM32H723ZGT6 ADC.
  Aux rails from `TPSM540`. The LMG2610 is also the star ground point between
  power and analog ground.
* **RX** — 12 × `MURSDA860` in a bridge rectifier (3 paralleled per leg), 11 µF
  bulk, `TMCS1133` isolated Hall current sense, STM32G431 compute.
* **Coils** — PCB-etched spirals, 5 mm trace width, 12 µH, 0.8 Ω series, Q = 12,
  ferrite backing with a cooling path underneath.

## 3. Findings

### F1 — The TX power stage is specified ~40× below the power target *(blocking)*

The white paper states the LMG2610 is "rated for a 600V bus and drain current of
6.4A". The datasheet (SNOSDE2A, `docs/reference/lmg2610-SNOSDE2A.pdf`) says:

* 650 V, not 600 V.
* **6.4 A is the low-side absolute-maximum *peak* drain current. The high-side
  abs-max peak is 4 A.** Neither is a continuous rating; both are abs-max, i.e.
  the value beyond which damage is permitted, not a design point.
* The device is "intended for **< 75-W** active-clamp flyback converters".
* The 170 mΩ low-side / 248 mΩ high-side asymmetry is *deliberate* — "optimized
  for ACF operating conditions". A 50%-duty resonant H-bridge cannot use it.

Against the 3 kW target, using first-harmonic approximation for a square-wave
driven series-resonant tank at resonance:

| Quantity | Value |
|---|---|
| DC input current, 3 kW / 400 V | 7.50 A |
| Fundamental RMS of the 400 V square wave, `2√2·V/π` | 360 V |
| Tank current, 3000 W / 360 V | **8.33 A RMS** |
| Tank current peak | **11.8 A peak** |
| Per-FET RMS (≈50% conduction) | 5.89 A |

So the high-side FET would see 11.8 A peak against a 4 A absolute maximum —
**2.9× over abs-max** — and the low-side 11.8 A against 6.4 A, **1.8× over**.

Thermally it is worse. Conduction loss alone, ignoring all switching loss:

| | RDS(on) | I²R at 5.89 A RMS |
|---|---|---|
| Low-side | 170 mΩ | 5.90 W |
| High-side | 248 mΩ | 8.61 W |
| **Per package** | | **14.5 W** |

With RθJA = 25.3 °C/W that is a 367 °C rise, against TJ(max) = 150 °C. Even
bonded to a perfect heatsink through RθJC(bot) = 1.22 °C/W, 14.5 W in a 9×7 mm
QFN is not a package you can cool — and the current-sense emulation function
requires the low-side thermal pad to be tied to power ground, which constrains
the heatsinking further.

**This is not a margin problem. The part cannot reach the target and would fail
on the first attempt at full power.** It is consistent with the white paper's
own evidence: p.7 reports bench results for resonance *tracking* only, and
never reports a power figure.

Replacement class: a 650 V GaN FET around 30 mΩ with an integrated driver —
e.g. TI `LMG3522R030`/`LMG3526R030` (650 V, 30 mΩ, top-cooled 12×12 VQFN, TI's
own evaluation board runs 3.6 kW). At 30 mΩ the same 5.89 A RMS gives 1.04 W per
FET instead of 5.9–8.6 W. Confirm in sourcing; this is a class, not yet a choice.

### F2 — Several part numbers do not resolve to orderable parts

| White paper | Resolves to | Note |
|---|---|---|
| `TPSM540` and `TPSM560` (both used) | `TPSM560R6` (600 mA) or `TPSM5601R5` (1.5 A) | Neither paper name is a real part. 600 mA vs 1.5 A changes the aux-rail budget. |
| `UCC1414` | `UCC14240-Q1` (2.0 W isolated gate-drive bias) | |
| `UCC27741`, "rating of 650V" | `UCC27714`, rated **600 V** | Digits transposed *and* the voltage is wrong. Direct margin impact on a 400 V bus. |
| `MURSDA860`, described as "schottky" | closest real family `MUR860` / `MURS` — **ultrafast recovery, not Schottky** | See F3. |
| `IPB60R120` | `IPB60R120C7` (600 V, 120 mΩ, 19 A) | 600 V on a 400 V bus is 1.5× — thin for a bridge with leakage ringing. |
| `BSC190N` | `BSC190N15NS3-G` (150 V, 19 mΩ, 50 A) | 150 V bounds the LV bus. See F5. |

`LMG2610`, `OPA2328`, `TMCS1133`, `ISO7740`, `ISO224`, `UCC33420`,
`STM32H723ZGT6` and `STM32G431` all resolve correctly.

### F3 — The RX rectifier is not a Schottky bridge

`MUR` is an ultrafast *PN* recovery family, not Schottky, and silicon Schottky
does not exist at 600 V — above roughly 200 V, "Schottky" means SiC. So the v1
bridge has both a ~1.7 V forward drop *and* reverse-recovery charge, at
85–120 kHz, which is exactly what the paper says it wanted to avoid.

At the paper's own 6 A load, two diodes in series conducting: 2 × 1.7 V × 6 A =
**20.4 W** in the bridge. This is the thermal problem p.5 gestures at, quantified.

A 650 V SiC Schottky (e.g. Wolfspeed C3D/C6D, onsemi FFSH) has essentially zero
reverse recovery, which removes the switching-loss term entirely. Forward drop
is comparable, so the win is in recovery and in EMI, not in conduction. **v2
should either move to SiC Schottky or, better, evaluate synchronous rectification** —
at 3 kW the diode bridge is the largest single loss term outside the coils.

### F4 — The coil numbers are internally inconsistent, and the coils dominate loss

12 µH with 0.8 Ω series resistance gives:

| f | X_L | Q = X_L/R | C for resonance |
|---|---|---|---|
| 85 kHz | 6.41 Ω | **8.0** | 292 nF |
| 100 kHz | 7.54 Ω | 9.4 | 211 nF |
| 120 kHz | 9.05 Ω | 11.3 | 147 nF |

The stated Q of 12 corresponds to ≈127 kHz, not to the stated 85 kHz nominal.
Either Q was measured at the top of the band, or R is lower than 0.8 Ω, or the
numbers come from different builds. **One of these three numbers is wrong and
v2 must measure all three on one physical coil before anything is designed
around them.**

The loss is the bigger issue. At the 8.33 A RMS that 3 kW demands:

* I²R per coil = 8.33² × 0.8 = **55.5 W**
* Both coils = **111 W**, i.e. ~3.7% of 3 kW *in the coils alone*

55 W spread over a PCB spiral, cooled only through the ferrite backing, is the
hardest thermal problem in the system — considerably harder than the white paper
implies when it calls PCB-coil thermals a "drawback". Note also that 0.8 Ω is
presumably a DC measurement; at 85 kHz, skin and proximity effect in a 5 mm
copper trace will make the AC resistance higher, so 55 W is a floor.

**This is the finding most likely to force an architecture change** — wider or
thicker copper, more layers in parallel, a lower tank current via a higher bus
voltage, or a return to Litz.

### F5 — The LV bus voltage is undefined, and the firmware contradicts the FETs

The white paper never states the Mako battery voltage. The HVLV firmware sets
`v_ref = 250.0f` — but the LV bridge uses 150 V-rated `BSC190N15NS3`. If the LV
bus really were 250 V the LV FETs would be destroyed at rest.

Most likely `v_ref` is one of the `FILL THIS OUT LATER` placeholders (it is
declared among them) rather than a real setpoint. But the LV bus voltage sets
the LV bridge current, the transformer turns ratio, and the entire LV thermal
design. **This is the single biggest open question in the v1 record and it
blocks the DAB architecture.** It must be answered by the human before any HVLV
work starts.

### F6 — Firmware: the described algorithm and the implemented algorithm differ

Reviewing `txrx-TX_V1.c` against the white paper's p.7 description:

1. **The filter is a median, not an RMS.** The paper says the firmware "generates
   an aggregate rms current reading" and "eliminates the highest few elements
   that stand out as outliers". `filter()` sorts and returns `sorted[len/2]` —
   a plain median. No RMS is computed anywhere. Since the sensed waveform is a
   sine with a positive offset, its median is close to its *mean*, which is not
   proportional to power. The hill-climb is therefore maximising the wrong
   quantity — it still peaks near resonance, but the peak is shallower and more
   noise-sensitive than an RMS metric would be.
2. **The smoothing filter is dead code.** `smoothed_initialized` is a
   non-static local declared inside the sample-complete block, so it is 0 on
   every entry and the EMA branch never runs — `smoothed_read = current_read`
   always. The intended 1/4-weight IIR does nothing.
3. **`memset(adc_fft, 0, fft_size)` clears bytes, not elements.** The array is
   `uint32_t[2000]` = 8000 bytes; the memset clears 2000, i.e. the first 500
   entries. Stale samples from the previous frequency point survive into the next
   measurement. (Harmless only because the buffer is fully rewritten before
   being read — but it is a latent trap for anyone who changes the fill logic.)
4. **The re-sweep guard never fires.** `threshold = 0` and `smoothed_read` is
   unsigned, so `smoothed_read < threshold` is never true. If coupling is lost
   the system never falls back to a static sweep.
5. **Dead time is never set.** `Set_PWM_DeadTime()` is defined and never called;
   the comment says "DO NOT CHANGE DEAD TIME VALUE" but nothing in the program
   sets one — it relies entirely on the CubeMX initialisation. On a 400 V GaN
   bridge, dead time is the difference between working and a shoot-through
   failure. It must be explicit, verified, and covered by a requirement.
6. **An ADC timeout injects a zero.** `HAL_ADC_PollForConversion(&hadc1, 1)`
   has a 1 ms timeout; on timeout `raw_volt` stays 0 and *is still pushed into
   the sample array*. A median is robust to a few of these, which is probably
   why it was not noticed.
7. **Three different frequency bands appear in one file.** The code sweeps
   40–110 kHz, the comment above it says 40–160 kHz, and the paper says 80–120 kHz.
8. **8 kB VLAs on the stack**, twice (`adc_fft`, and `sorted` inside `filter()`),
   plus a full 2000-element qsort per control cycle.

And `hvlv-Master.c`:

9. **The phase shift is never applied.** `i_threshold = 0` and the write is
   `if (i_batt < i_threshold) TIM1->CCR3 = phaseShiftPulse;`. With the threshold
   at zero the condition is never true, so the DAB never leaves zero phase shift.
   The sense of the test also looks inverted — a current *limit* should stop the
   phase shift increasing, not gate it entirely.
10. **Every control constant is a placeholder.** `CURRENT_SENSOR_MV_PER_A`,
    `VOLTAGE_SENSE_RATIO`, `ARR_PHASE_MAX`, `CONTROL_TS`, both PI gain pairs,
    `v_ref`, `i_ref_cc` and `i_threshold` are all marked `FILL THIS OUT LATER`.
    The loop is structurally complete and numerically empty.
11. **Blocking ADC polls inside a 50 µs ISR.** `ControlLoop_Update()` runs from
    the TIM6 interrupt at `CONTROL_TS = 50 µs` and calls
    `HAL_ADC_PollForConversion(..., 1)` twice — a 1 ms timeout inside a 50 µs
    period. Any slow conversion overruns the loop. This needs DMA or
    injected-conversion-complete, not polling.
12. **No path back from CV to CC**, and no hysteresis on the handoff.
13. **Break inputs disabled.** In `hvlv-pspwm-ex.c`, `DeadTime = 0` and
    `BreakState = TIM_BREAK_DISABLE`. As a bench sketch that is fine; as the
    phase-shift reference it is dangerous, and no hardware over-current trip
    into TIM BRK appears anywhere in the v1 firmware.

Findings 1, 2, 5, 9 and 11 are the ones that change behaviour on hardware.

## 4. What v1 actually demonstrated

The white paper's only reported bench result (p.7) is that static resonance
tracking lands near resonance and dynamic tracking converges the rest of the way.
That is a real and useful result, and it validates the two-stage control
architecture — which v2 should keep.

No power, efficiency, thermal, coupling or air-gap measurement is reported
anywhere in the document. **v2 should treat 3 kW as an unproven target, not as a
demonstrated capability.**

## 5. Open questions for the human

1. **What is the Mako battery voltage and chemistry?** (F5 — blocks the DAB.)
2. **What is the design air gap and the expected coil misalignment envelope?**
   Coupling k is a function of both, and no k is given anywhere. Without k there
   is no tank design.
3. **Is 3 kW a hard requirement, or the best achievable?** F1 and F4 both bite
   hardest at 3 kW; at 1.5 kW much of the difficulty goes away.
4. **Is the 400 V Leviathan bus fixed?** Raising it reduces tank current
   quadratically in loss terms and is the cheapest fix for F4.
5. **Is bidirectional operation actually required?** The DAB is bidirectional;
   nothing in the brief asks the Mako to export power. If it is not needed, the
   HV side simplifies considerably.
6. **What is the ambient?** The Leviathan dock is presumably marine. Coolant
   availability changes the coil answer in F4 completely.
