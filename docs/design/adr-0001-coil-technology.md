# ADR-0001 — Coil technology

**Status:** Accepted.
**Date:** 2026-08-29
**Chunk:** M2 · **Gate:** G1 (delegated decision)

## Decision

**Keep the PCB coil.** Specifically: a **fully transposed multi-track PCB
winding** — not a plain parallel-layer stack — with traces near one skin depth,
and **the mounting bracket designed as the heat sink**.

| | |
|---|---|
| Pad | 102 × 203 mm (4 × 8 in), fixed |
| Construction | multi-track, **transposed** layer-to-layer |
| Turns | **24** |
| Trace / space | **0.25 mm / 0.20 mm** — skin depth at 85 kHz is 0.26 mm |
| Copper | **4 oz** (0.14 mm, 0.54 skin depths) |
| Layers | **16** in parallel · 12 is the floor |
| Mutual inductance | 94.6 µH at worst case, against 80.9 µH required |
| **k·Q, worst case** | **75.0** at 16 layers · 61.1 at 12 · requirement **49** |
| Pad dissipation | **39 W** at 16 layers · 48 W at 12 |
| Bracket external area | **≥ 14× the pad footprint** |

Sized against the **binding condition**, which is the 14 mm gap with 5 mm of
offset — the far corner of the `SYS-006` envelope, not the nominal. At the
10 mm nominal it reaches k·Q = 109 and 27 W per pad.

## Context

`MEC-001` allows the coil pair 120 W of 3 kW, which is k·Q ≥ 49. Across the
`SYS-006` envelope the computed coupling is 0.645 at the 10 mm nominal gap, so
the coil must reach **Q ≈ 76**. The customer prefers PCB for manufacturability
and inductance repeatability, and the earlier analysis in this repo claimed a
six-layer plain stack would reach Q = 176. **That claim was wrong**, and the
research commissioned to defend it refuted it instead.

## The defect that produced the wrong answer

`coil_rect.py` computed `r_dc = rho·length/(w·t·layers)` and then multiplied by
the proximity factor. **That divides the proximity loss by N as well**, which is
physically wrong.

Proximity resistance is proportional to conductor volume and to B², and is
**independent of the current the conductor carries** — Nguyen & Fortin
Blanchette, *Electronics* 2020, **9**, 1324, Eq. 2. Parallel layers do not
change total ampere-turns, so B is unchanged: each layer added is another slab
of copper eddy-heating in the same field. Transport loss falls as 1/N;
proximity loss **rises** as N:

> **R_ac(N) = R_dc1 / N + N · R_prox1**, minimum at N_opt = √(R_dc1 / R_prox1)

Measured confirmation of the exact experiment: **Yin et al., *Electronics* 2024,
**13**, 426, Table 12** — a 90 mm PCB spiral (8 turns, 2.8 mm trace, 2 oz) at
100 kHz. One layer: 189 mΩ, Q 17.44. Two identical layers in parallel:
159 mΩ, Q 20.81. **A 15.9% resistance reduction where 1/N predicts 50%** — an
effective exponent of N^−0.25, worse than 1/√N. (The parallel identification is
inferred: self-inductance is unchanged at 5.25→5.27 µH, whereas their series
build measures 20.85 µH, i.e. 4×, as series-aiding coupled coils must. The
paper does not use the word "parallel", so this is a strong inference, not the
authors' own statement.)

With the model corrected, the best **plain parallel** design on our pad reaches
**k·Q = 46.4 against the 49 required** — it fails, by 5%.

## Why transposition rescues it

The penalty is not intrinsic to PCB; it is intrinsic to *stacking layers that
each sit permanently at a different depth in the field*. Transposing the stack,
so every layer spends equal time at every depth, is the published fix.

**Lewis, Onar et al. (ORNL / University of Kentucky), ECCE 2024** built exactly
our case — a multi-layer PCB coil at 85 kHz for an 11 kW wireless charger. With
straightforward sequential layering their 3D FEA found up to **31% difference in
induced voltage and 50% difference in self-inductance between parallel layers**.
Deliberate layer-to-layer transposition cut those to **0.4% and 0.7%**,
validated to under 1% on a fabricated prototype. The same team sized their
85 kHz conductor to **exactly one skin depth: 0.22 mm trace, 0.25 mm space,
1 oz** — which is where our 0.30 mm trace comes from, and why the earlier
0.80 mm choice was wrong in both directions (too wide to stack well, too narrow
for a single-layer optimum).

The consequence of *not* transposing is stated bluntly elsewhere. Li et al.,
*IET Power Electronics* 2018, refuse parallel layers outright: "the current does
not distribute equally between each layer, the current in certain layers may
[be] extremely high with the increasing of the operating frequency." Lloyd
Dixon's Unitrode note **SLUP125** puts it more sharply still for the transformer
case: parallel five strips one skin depth thick and essentially all the
high-frequency current flows in the one nearest the field source.

**The measured anchor.** Narvaez, Carretero, Lope, Acero and colleagues
fabricated and measured a **fully transposed multi-track PCB coil** for wireless
power. At 85 kHz, on a ~380 mm pad, it measured **Q = 153**, against **Q = 260**
for a copper-Litz WPT3 pad of the same footprint from the same lab. Litz wins by
1.7× on Q — **and the transposed PCB coil is still comfortably above what this
design needs.**

At the chosen 24 turns / 0.25 mm / 4 oz / 16 layers, at the worst corner of the
envelope:

| Transposition | k·Q | Per pad | vs 49 |
|---|---|---|---|
| None — plain parallel stack | 45.2 | 66 W | **fails** |
| Half effective | 60.9 | 48 W | passes, 1.24× |
| **Fully transposed** | **75.0** | **39 W** | **passes, 1.53×** |

**The decision survives transposition being only half as effective as intended.**
That is the margin it rests on, and it is why this is a defensible choice rather
than a marginal one — but it also shows how completely it depends on
transposition happening at all.

## The binding constraint is thermal, and it is the bracket's problem

This is the finding that actually shapes the design, and it is not electrical.

A flat plate in still air sheds roughly **150 W/m²** at an acceptable
temperature rise; forced air reaches about 2000 W/m². Our 207 cm² pad therefore
sheds about **3.1 W from its own faces**. We need to remove **36 W** — twelve
times that.

**The pad face is irrelevant. All of the heat leaves through the mounting
structure.** At 36 W/pad the bracket needs roughly **2400 cm² of external
surface — about 12× the pad footprint**. A 400 × 500 mm finned aluminium deck
bracket provides that comfortably, which is precisely why the decision to charge
on deck in a bracket makes this work. Had the pad been hull-mounted with only
its own faces to work with, no coil technology would have saved it.

**This makes the bracket a thermal component, not a fixture**, and it is now
`MEC-009`.

## Consequences

**Good.** The customer keeps PCB, with its inductance repeatability, its absence
of a winding operation, and its tolerance to fabrication scatter — and it is now
backed by a measured comparable rather than by a model. Fine traces near one
skin depth also nearly remove in-plane proximity effect, so the design sits in a
regime where the physics is well understood.

**Bad, and load-bearing.** *Transposition is not optional.* A plain stack misses
the requirement, and a plain stack is what a PCB house will produce unless the
layer interconnect is specified deliberately. This has to be carried explicitly
into the layout rules and checked at fab.

**Bad.** The transposed prediction is **optimistic against the one comparable
measurement**. The model puts our smaller pad at Q = 164; Narvaez measured 153
on a pad 3.7× larger, and Q scales with size, so the real figure is likely well
below 164. The decision survives that de-rating — at Q = 100 the design still
gives k·Q = 65 — but the headline number should not be quoted as a prediction.

**Bad, and the most concrete warning available.** Narvaez's transposed PCB coil,
at 3.3 kW — essentially our power level — measured **93% coil-to-coil, not the
96% we budget**, and in their thermal run the receiver reached **90.3 °C and was
still rising when power was cut at 33 minutes**. A published transposed PCB coil
at our power did not reach thermal equilibrium in half an hour. That is the
risk this ADR accepts, and `MEC-009` is what must retire it.

**Bad, and it cuts against the reason PCB was chosen.** Sixteen layers at 4 oz
is **64 oz of copper in one board**. That is a heavy-copper multilayer at the
far edge of standard capability, not the cheap commodity board the PCB choice
was meant to buy — and the via stitching that makes the transposition work adds
its own resistance and its own fabrication risk. **A fab-capability check is
required before this is committed**, and it is the first thing that could send
the decision back to Litz. Twelve layers is the floor that still passes
(k·Q = 61.1, 48 W/pad) if sixteen proves unbuildable.

The alternative of thinner copper on more layers is worse, not better: 2 oz on
20 layers reaches k·Q = 52.7 and only passes if transposition is nearly perfect,
where 4 oz on 12 passes even at half effectiveness.

## Alternatives considered

* **Litz wire.** Measured Q = 260 against the transposed PCB's 153 on the same
  footprint — genuinely better, by 1.7×. Rejected because the PCB option now
  meets the requirement with margin, and Litz reintroduces a winding operation,
  a wound-part tolerance, and a supplier the customer explicitly wants to avoid.
  **Held as the fallback** if `MEC-009` proves the thermal path cannot be built.
* **Plain parallel layers.** k·Q = 46.4 against 49. Rejected on the arithmetic.
* **Wider traces, fewer layers.** The direction the earlier analysis took. The
  joint sweep over trace width and layer count puts every wide-trace option
  below every narrow-trace one; 0.80 mm with 4 layers reaches k·Q = 35.
* **Solid copper planar coil.** Higher Q than PCB but no longer a PCB process,
  and it forfeits the repeatability that motivated the choice.

## Verification status

Every number attributed to a source above was returned by a research agent and
then **adversarially re-checked by a second agent that went back to the primary
sources**. That check returned `minor-corrections` on the multilayer topic and
`major-corrections` on the Litz comparison — several figures in the first pass
were misread, and one claim labelled "measured" was in fact calculated. The
figures retained here are the post-correction ones.

**One gap:** the verification pass on the ferrite and thermal topic **did not
run** — the account hit its rate limit. So the 150 W/m² natural-convection
figure and the bracket area that follows from it are **researched but
unverified**, and `MEC-009` must not be closed against them without a second
source.
