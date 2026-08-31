# concepts/

build123d models for the vision stage. Every dimension here is one the model
actually holds — these are geometry renders, not artistic impressions, so a
concept cannot show something unbuildable.

```bash
vision-md            # renders concepts/*.py and writes docs/design/vision-gallery.md
```

Run `vision-md`, not `vision-board` directly: it points the generated gallery at
`vision-gallery.md` so it stops overwriting the hand-written `vision.md`, and it
flattens the raw `<details>` blocks `vision-board` emits, which `review-artifact`
escapes into visible tags on the published review page.

| File | Concept |
|---|---|
| `_common.py` | shared geometry — coil pad, housing, enclosure, finned sink, dowel |
| `test_packaging.py` | the bench rig: pads on pins, gap set by shims |

**Scope is the electronics plus this one rig** (`VIS-013`). Integration — the
deck fixture, the vehicle mounting, the handling — is the mechanical team's, so
the rig is test equipment and not a fixture prototype. It is not marine, not
recoverable and not handled.

Two earlier generations of concept are withdrawn and deleted rather than kept as
dead files, because a stale concept is read as a live proposal:

* `dock_belly.py`, `dock_flank.py`, `dock_saddle.py` — docking arrangements.
  Settled at gate 1: belly dock, no actuator, charge on deck.
* `locate_cone_vee.py`, `locate_tapered_rails.py`, `locate_nest.py` — locating
  schemes. Withdrawn 2026-08-31 with the fixture; pins were taken from among
  them as the interface (`VIS-005`).

The coil pad is real — 102 × 203 mm at a 16 mm stack, from
`sim/coil/coil_rect.py`. The finned sink is sized against `MEC-009` and reports
its own area rather than asserting it; `sink_area_cm2()` is the number quoted.

Mass figures in the gallery are quoted at 1.4 g/cm³, which is `vision-board`'s
fixed assumption and wrong for an aluminium rig — `MATERIAL` sets the render
colour only. Multiply by 1.93 for aluminium, and remember the enclosures are
drawn as solid blocks.

No image backend is configured in this environment (`imagegen --list` reports no
keys), so styled or contextual imagery is not available. If the vision board
should look like a product rather than shaded CAD, that needs `FAL_KEY`,
`BFL_API_KEY` or `OPENAI_API_KEY` set in the environment.
