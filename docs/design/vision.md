# Vision — Ulysses LARS Charger, revision 2

Captured 2026-08-28. Source material: the v1 white paper and firmware, reviewed
in [`v1-baseline.md`](v1-baseline.md). Agreed intent lives in
[`requirements/00-vision.sdoc`](../../requirements/00-vision.sdoc) as `VIS-001`
through `VIS-010`.

## The thing, in one paragraph

A 3 kW magnetic-resonant wireless charger that moves power from a 400 V bus on
the Leviathan dock to a 48 V pack in the Mako, across a gap that is never
bridged by a connector. The dock holds the vehicle close and square, so the
coils couple well. Nothing is pumped or fanned — every watt the system wastes
has to conduct out through the structure it is bolted to.

## What changed when we asked

The white paper is a complete technical brief, so the vision interview was
short and about the four numbers it never states. All four turned out to matter:

| Question | Answer | What it changed |
|---|---|---|
| Pack voltage and capacity | 48 V, 33 Ah (1.58 kWh), growing in Ah not volts | 3 kW is 1.9C today — the pack, not the charger, is the present limit. 3 kW is for the future pack. |
| Air gap and alignment | < 20 mm, well aligned | k ≈ 0.5 rather than the ≈ 0.2 the EV literature assumes. A real advantage, currently unspent. |
| How firm is 3 kW | Design for it, let physics move it | Licence to report honestly when a number cannot be met. |
| Cooling | Conduction to chassis only | **This is the constraint that decides the magnetics.** |

## The one decision this vision turns on

Everything else follows from a single number: how much heat may be made in a
coil pad that has no coolant.

Coil-to-coil efficiency in an inductive link is governed by the product of
coupling and quality factor, **k·Q** — not by resistance alone:

> η_max = (kQ)² / (1 + √(1 + (kQ)²))²

At the k ≈ 0.5 the dock geometry buys us:

| Coil | Q at 85 kHz | k·Q | η | Loss at 3 kW | Per pad |
|---|---|---|---|---|---|
| v1 PCB coil as documented (12 µH) | 8 | 4 | **61%** | 1170 W | 585 W |
| PCB coil scaled to the right inductance (162 µH) | 29 | 15 | 87% | 381 W | 191 W |
| Litz, conservative (Q = 150) | 150 | 75 | 97.4% | 79 W | 40 W |
| Litz, good (Q = 300) | 300 | 150 | 98.7% | 40 W | 20 W |

Two things follow, and they are the substance of v2:

1. **The v1 coil is 13× too small in inductance** for a 3 kW link at 400 V. At
   resonance with 360 V fundamental on both ends, a 12 µH pair wants to transfer
   40 kW at 112 A. Holding it to 3 kW means running far off resonance — which is
   the exact opposite of what the v1 resonance-tracking firmware is built to do.
   The magnetics and the control are fighting each other.
2. **A PCB coil cannot reach the efficiency that conduction-only cooling
   demands.** Even scaled to the right inductance it lands at 87%, i.e. 191 W
   per pad. Litz reaches 97–99%, i.e. 20–45 W per pad.

The root cause of both is visible in the white paper: p.6 says the coil geometry
came from a paper on an **induction stove**. An induction hob coil is meant to be
low-inductance, high-current and tightly coupled to a steel pan. It is an
excellent coil for that job and the wrong starting point for a 400 V resonant
link — the same category of error as building a 3 kW H-bridge from a part
specified for 75 W flyback converters.

## The two concepts

Rendered from real geometry by `vision-board`; both are 300 mm coils over the
same ferrite ring and the same bolt-down aluminium cold plate, so the only thing
that differs is the conductor.

| | **A — PCB coil pad** | **B — Litz coil pad** |
|---|---|---|
| Conductor | 27-turn spiral, 4 layers in parallel | 27 turns of 2000/40 Litz in a moulded former |
| Envelope | 340 × 340 × **16.9** mm | 340 × 340 × **21.2** mm |
| Mass (approx.) | 1.80 kg | 2.24 kg |
| Q at 85 kHz | ≈ 29 | 150–300 |
| Coil-to-coil η | 87% | 97–99% |
| **Heat per pad at 3 kW** | **191 W** | **20–45 W** |
| Manufacture | ordinary PCB fab, no winding operation | separate winding process with its own tolerance |
| Inductance repeatability | excellent — etched geometry | good, but needs a wound-part tolerance |

`build/vision/` holds the shaded and line views of each.

Concept A is what `VIS-009` wants and it is genuinely the cheaper, more
repeatable part. Concept B is what `VIS-006` and `VIS-007` require. **They
conflict, and B is expected to win**, because 191 W leaving a flat pad through
ferrite into a bolted plate, with no coolant, is not a thermal design — it is a
thermal impossibility, whereas 45 W is an ordinary one.

That decision is deliberately *not* taken here. It is taken in an ADR during the
design sprint, against a measured coil rather than a formula, because the whole
argument rests on a Q that nobody in this programme has yet put on a bench. The
requirements are therefore written against **k·Q and pad dissipation**, not
against a coil technology — so whichever conductor meets the number wins on
evidence.

## What v2 keeps from v1

The two-stage resonance tracking — a static frequency sweep that lands near
resonance, then a hill-climb that converges — is the one thing the white paper
actually demonstrated on a bench, and it should survive intact. The firmware
underneath it needs work (thirteen findings in the baseline, five of which
change behaviour on hardware), but the control architecture is sound.

## What is still open

* Cell charge acceptance for the present 48 V / 33 Ah pack — sets the maximum
  rate that may actually be commanded today, and needs the pack datasheet.
* Whether bidirectional operation is required at all. The DAB is bidirectional;
  nothing in the brief asks the Mako to export power. If it is not needed, the
  HV side simplifies considerably.
* The dock and vehicle ambient temperature, which sets what "conduction to
  chassis" is actually worth in °C/W.
