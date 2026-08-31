# Vision — Ulysses LARS Charger, revision 2

Captured 2026-08-28, decided at [gate 1](reviews/gate-1-vision.md), scope
narrowed 2026-08-31. Source material: the v1 white paper and firmware, reviewed
in [`v1-baseline.md`](v1-baseline.md). Agreed intent lives in
[`requirements/00-vision.sdoc`](../../requirements/00-vision.sdoc) as `VIS-001`
through `VIS-013`.

**Scope: the charger electronics, plus a test packaging.** `VIS-013`. The
converters, the coil pair and their control are ours. Integration — the deck
fixture, the vehicle mounting, the handling — belongs to the mechanical team.
The vehicle is not modelled. What we build in metal is a bench rig that holds
the coil pair at the `SYS-006` envelope so the magnetics can be measured.

**The pads locate on pins.** `VIS-005`, set 2026-08-31. A two-pin hole-and-slot
pattern, in the delivered system and in the test rig alike.

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

## The decision this vision turned on

Coil-to-coil efficiency in an inductive link is governed by the product of
coupling and quality factor, **k·Q** — not by resistance alone:

> η_max = (kQ)² / (1 + √(1 + (kQ)²))²

`MEC-001` allows the coil pair 120 W of 3 kW, which is **k·Q ≥ 49**. Charging on
deck in a pin-located fixture sets the gap by two housing walls rather than a
vehicle hull, which buys a coupling of 0.43–0.57 across the `SYS-006` envelope.

**The coil is an etched PCB**, decided in
[ADR-0001](adr-0001-coil-technology.md) and backed by published measurements:
24 turns of 0.25 mm trace in 4 oz copper, **16 transposed layers**, reaching
k·Q = 75.0 at the worst corner. A plain parallel-layer stack of the same
geometry reaches 45.2 and fails — parallel layers do not reduce resistance as
1/N, and transposition is what makes the difference.

The binding constraint turned out to be **thermal, not electrical**: the pad
sheds about 3 W from its own faces and must lose 39 W, so every watt leaves
through the structure the pad is bolted to. That is `MEC-009`, and it is why the
deck-mount decision is what makes an etched coil viable at all.

Note what the scope change did *not* do. The fixture became the mechanical
team's, but `MEC-009` was **re-aimed, not withdrawn** — it is now an interface
requirement we levy on whoever builds that structure, and one the test packaging
must meet itself. Handing over a coil without handing over its heat-sink
requirement is how a design that closed on paper arrives at a 90 °C pad.

## What we build in metal

One thing, and it is test equipment: a rig that holds the two pads at a known
gap and offset while the magnetics are measured. It is not a prototype of the
deck fixture and is not marine, recoverable or handled.

Three locating-feature concepts were studied at gate 1 — a kinematic
cone-vee-flat mount, tapered rails and a perimeter nest. **All three are
withdrawn**: they were fixture designs, and the fixture is not ours. Pins were
chosen from among them as the interface, because a two-pin hole-and-slot pattern
is the cheapest thing that fixes six degrees of freedom to the tolerance
`SYS-006` needs, is producible under `MEC-006` with no programme tooling, and
leaves the pad faces clear for the thermal path.

The rig is rendered in **[`vision-gallery.md`](vision-gallery.md)**, from the
parametric model in [`concepts/test_packaging.py`](../../concepts/test_packaging.py).
Its envelope is 692 × 410 × 252 mm. The gallery quotes mass at 1.4 g/cm³, which
is the tool's fixed assumption and wrong for this part — in aluminium the solid
model is about 44 kg, and the built rig somewhat less because the electronics
enclosures are drawn as solid blocks. Either way it is a two-person lift, not a
bench-top item.

Each pad conducts into a 340 × 380 mm finned sink giving 8,104 cm² against the
207 cm² pad — 39 times the footprint where `MEC-009` asks for 12. **That margin
should not be read as the thermal case being closed.** `MEC-009`'s 12× is a
flat-plate-equivalent figure at 150 W/m², and a finned surface does not convect
per unit area the way a flat plate does; fin efficiency and channel convection
are still owed by the thermal chunk. The 150 W/m² figure itself is still
single-sourced and unverified.

## What we need from you

1. Is the scope line right — electronics plus a test rig, with integration and
   the fixture going to the mechanical team?
2. Pins: two dowels, hole and slot. Anything about the real fixture that would
   make a different interface better?
3. Is 8–14 mm of gap and 5 mm of offset the envelope the fixture can actually
   hold? It is currently *our assumption about someone else's part*, which is
   the weakest thing in this document.
4. Is anything in the rig's envelope wrong — too big, too small, wrong
   proportions?

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
* The gap and misalignment the mechanical team's fixture can actually hold.
  `SYS-006` states 8–14 mm and 5 mm as what the magnetics tolerate, which is the
  right way round, but it is still an assumption about a part we do not design.
* The 150 W/m² still-air figure behind `MEC-009`'s 12× surface area. Researched,
  single-sourced, never independently confirmed; the verification pass on it did
  not run.
