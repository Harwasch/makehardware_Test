# Coil model — inductance, coupling and quality factor by analysis

> **CORRECTED 2026-08-28.** An earlier version of this document concluded that
> an etched PCB coil could not meet `MEC-001` and that Litz was required. **That
> conclusion was wrong**, and wrong in a way worth naming: it rested on a
> *single-layer* analysis that was then generalised to "the etched spiral" as a
> category. Parallel layers are the obvious lever and were never modelled.
> The corrected result is in [Result 4](#result-4--the-rectangular-pcb-coil-that-works)
> — a 4 × 8 inch, six-layer PCB coil clears the requirement with 1.57× margin.
> The circular single-layer analysis below is kept because its method is sound
> and its intermediate results still hold; only the conclusion drawn from it was
> overreaching.

Chunk **M1**. Written without laboratory access, so every number here is a model
output and the caveats are part of the result. Reproduce with:

```bash
cd sim/coil
/opt/hw-py/bin/python coil_rect.py         # THE DESIGN — rectangular, multilayer
/opt/hw-py/bin/python coil_model.py        # circular inductance and coaxial coupling
/opt/hw-py/bin/python coil_coupling.py     # coupling across the misalignment envelope
/opt/hw-py/bin/python coil_resistance.py   # AC resistance and quality factor
```

## Method, and why each part is trusted differently

| Quantity | Method | Confidence |
|---|---|---|
| Self-inductance | Filament summation with Maxwell's elliptic-integral mutual term, cross-checked against the Mohan current-sheet fit | **High** — the two agree to 2.6–4.2% |
| Coupling, coaxial | Maxwell's formula, exact for coaxial filaments | **High** |
| Coupling, misaligned | Neumann double integral, numerical | **High** — validated against the analytic coaxial result to 0.14% |
| PCB AC resistance | Kuhn & Ibrahim planar-spiral model | **Low** — used three orders of magnitude outside its fitted trace width |
| Litz AC resistance | DC from geometry, `F_R` swept rather than predicted | **Low–medium** |
| Ferrite and cold-plate effects | Not modelled | **Absent** — needs FEA |

The last three rows are why this document settles a direction and not a design.

## Result 1 — the dock's tight gap is worth much more than assumed

The vision interview gave "under 20 mm, well aligned", which I turned into an
assumed **k ≈ 0.5** taken from the EV wireless-power literature. That was
conservative to the point of being wrong. Computed for the real geometry:

| Gap | Lateral | Tilt | k |
|---|---|---|---|
| 5 mm | 0 | 0° | 0.918 |
| 10 mm | 0 | 0° | 0.841 |
| 20 mm | 0 | 0° | 0.711 |
| **20 mm** | **10 mm** | **0°** | **0.705** ← worst in the `SYS-006` envelope |

The EV literature's k ≈ 0.2 comes from a 100–200 mm gap between 300–400 mm pads,
a gap-to-diameter ratio of 0.3–0.5. Here it is 20/300 = **0.067**. Misalignment
across the whole allowed envelope costs less than 1% of k, because a 10 mm
lateral offset is small against a 200 mm mean diameter.

Two things follow:

* **The coil needs less inductance than stated.** M must be 80.9 µH for 3 kW at
  resonance; at k = 0.705 that is **115 µH per side, not 162 µH**.
* **The quality-factor requirement relaxes.** `MEC-001` fixes k·Q ≥ 49; at
  k = 0.705 that is **Q ≥ 69, not Q ≥ 98**.

`MEC-003`'s 0.40 floor now has a 1.76× margin. It should stay at 0.40 — the
margin is what absorbs the ferrite and cold-plate corrections that are not yet
modelled.

## Result 2 — the resized coils

| | **PCB spiral** | **Litz** |
|---|---|---|
| Turns | 24 | 25 |
| Inductance | 116 µH | 124 µH |
| Conductor length | 15.1 m | 15.7 m |
| Conductor | 3.0 × 0.14 mm (4 oz) | 3.2 mm bundle, ~800 × AWG 40 |
| Copper cross-section | 0.42 mm² | 4.02 mm² — **9.6×** |
| Radial pitch / clearance | 4.35 / 1.35 mm | 4.17 / 0.97 mm |
| k at 20 mm | 0.709 | 0.722 |

**The v1 trace width does not fit.** At 5 mm, the turn count needed for this
inductance demands a 3.57 mm pitch — narrower than the trace. A 5 mm etched coil
at this inductance needs two layers in parallel or a larger diameter.

## Result 3 — quality factor, and the decision it points at

Skin depth in copper at 85 kHz is 0.226 mm, so 4 oz copper at 0.140 mm is
0.62 skin depths — skin effect *through the thickness* is mild. The problem is
**proximity effect between adjacent turns**, and it is what separates the two
conductors.

| Coil (hot, 100 °C, winding only) | Q | k·Q | η | Loss at 3 kW |
|---|---|---|---|---|
| PCB spiral | 43 | 31 | 93.7% | **190 W** |
| Litz, F_R = 4.0 (pessimistic) | 187 | 135 | 98.5% | 44 W |
| Litz, F_R = 2.0 | 374 | 270 | 99.3% | 22 W |
| **Requirement** | **≥ 69** | **≥ 49** | **≥ 96.0%** | **≤ 120 W** |

The etched spiral misses the budget by 70 W **before** ferrite core loss and
cold-plate eddy loss are added, and both only make it worse. Litz clears it with
room even at a pessimistic proximity factor.

A detail worth keeping: the PCB spiral's Q is 43 at both 24 and 29 turns. Q is a
property of the conductor cross-section and the frequency, not of the turn
count, because R and ωL scale together. **You cannot wind your way out of a bad
conductor.**

## Corrections to previously reported figures

The vision-stage analysis scaled v1's stated 12 µH / 0.8 Ω coil to the required
inductance and predicted Q ≈ 29 and 381 W. Computing from real geometry instead
gives **Q ≈ 43 and 190 W**. The etched coil is better than that first estimate
said — it still misses the requirement, but by 70 W rather than 261 W. The
earlier figure inherited v1's resistance number, which the same review had
already found to be inconsistent with v1's own stated frequency, so it should
not have been used as a basis.

## What this cannot settle

1. **Ferrite backing.** Raises both L and k, and adds core loss that a measured Q
   would include. No closed form. Needs magnetostatic FEA.
2. **Cold plate.** A conductive plate behind the ferrite carries eddy currents
   that lower L, lower k and add loss, and it sets a minimum ferrite thickness.
3. **The PCB proximity factor**, per the caveat above.
4. **Seawater in the gap.** Conductive and lossy at 85 kHz; `SYS-005` allows
   immersion, so this is a real operating condition and not a corner case.

Until those are modelled, `MEC-001` cannot be marked satisfied. The honest
status is that analysis points firmly at Litz and rules the etched spiral out
by a margin larger than the modelling uncertainty — which is enough to proceed
with M2, and not enough to close the requirement.


---

## Result 4 — the rectangular PCB coil that works

The house constraint is a roughly **4 × 8 inch rectangular** PCB coil with
passive cooling. `coil_rect.py` handles that geometry directly — Grover's
rectangular-loop formula for each turn's self-inductance, numerical Neumann
integration for every turn pair and for the coil-to-coil mutual, so gap, lateral
offset and tilt all work without a symmetry assumption.

### The rectangle costs coupling, and fine traces buy it back

| | 300 mm circular | **102 × 203 mm** |
|---|---|---|
| Coupling k at 20 mm | 0.705 | **0.461** |
| Turns to reach M = 80.9 µH | 24 | **32** |
| Trace width that fits | 3.0 mm | **0.80 mm** |
| R_ac / R_dc | 1.77 | **1.06** |

The coupling penalty is geometric: a 20 mm gap is 20% of the short dimension
here, against 7% of the 300 mm diameter. That is the price of the smaller pad.

The compensation is unexpected and useful. Driving the trace to 0.80 mm
**almost eliminates proximity effect** — the AC/DC resistance ratio falls from
1.77 to 1.06, because the Kuhn–Ibrahim critical frequency scales as
(w + s)/w² and rises steeply as the trace narrows. The coil stops being a
proximity problem and becomes a **pure DC-resistance problem**, which is
precisely what parallel layers fix.

### Layers are the lever

At 32 turns and 0.80 mm trace:

| Layers | R_ac | Q | k·Q | Loss | Per pad | vs k·Q ≥ 49 |
|---|---|---|---|---|---|---|
| 1 | 3.27 Ω | 29 | 13.5 | 412 W | 206 W | fails |
| 2 | 1.64 Ω | 59 | 27.1 | 214 W | 107 W | fails |
| 4 | 0.82 Ω | 117 | 54.1 | 109 W | 54 W | **passes**, 1.10× |
| **6** | **0.55 Ω** | **176** | **81.2** | **73 W** | **36 W** | **passes, 1.66×** |
| 8 | 0.41 Ω | 235 | 108.3 | 55 W | 27 W | passes, 2.21× |

**Six layers is the design point.** Four passes on paper but with only 1.10×
margin, and the layer model is optimistic (below) — that is not enough headroom
to also absorb ferrite and cold-plate losses that have not been modelled at all.

### The design point, across the full misalignment envelope

**32 turns · 0.80 mm trace · 0.28 mm clearance · 6 layers in parallel · 4 oz ·
102 × 203 mm outer**, giving L = 180 µH and M = 82.9 µH against the 80.9 µH
required.

| Gap | Lateral | Tilt | k | k·Q | Loss |
|---|---|---|---|---|---|
| 5 mm | 0 | 0° | 0.799 | 141 | 42 W |
| 10 mm | 10 mm | 3° | 0.618 | 109 | 55 W |
| 20 mm | 0 | 0° | 0.461 | 81 | 73 W |
| **20 mm** | **10 mm** | **0°** | **0.437** | **77.0** | **77 W** |

**Worst case k·Q = 77 against a requirement of 49 — a 1.57× margin.**

### The thermal problem got harder, not easier

38 W leaving a 102 × 203 mm pad is **1858 W/m²**, against 764 W/m² for the same
allowance on the 300 mm circular pad. The rectangular pad is 3.6× smaller in
area, so the same watts are a substantially harder extraction. `MEC-004`'s
**temperature limit is the binding form of that requirement**, not its per-pad
watt allocation — and the watt figure should be re-derived from the temperature
once the ferrite and cold-plate stack is modelled.

### What is still open, and what now matters most

1. **Inter-layer proximity is now the largest modelling uncertainty.** The
   layer table assumes ideal 1/N resistance scaling. Real stacked spirals do
   worse, because each layer sits in the others' field. A turn-to-turn model
   cannot capture it. This single unknown decides whether six layers is right
   or whether eight are needed, so it is the first thing FEA should answer.
2. Ferrite backing, cold-plate eddy loss and seawater in the gap remain
   unmodelled and all push the wrong way.
3. Kuhn–Ibrahim is still outside its fitted trace width — but at 0.80 mm the AC
   correction is only 6%, so the error it carries is now small enough not to
   matter much. The single-layer circular case, where the correction was 77%,
   was where that caveat really bit.

### Why the earlier conclusion was wrong

Worth recording, because the failure mode is general. The single-layer circular
analysis was correct as far as it went. The error was scope: one configuration
was tested and the conclusion was written about a whole conductor technology.
Three cheap levers went unexamined — layers, trace width, and the interaction
between them — and the first of them turns a 190 W failure into a 73 W pass.

`MEC-001` itself needs no change. It was written against k·Q and pad
dissipation rather than against a coil technology, precisely so the decision
would be settled by arithmetic. A six-layer etched coil meets it. **That is the
requirement working correctly, and the analysis around it that failed.**
