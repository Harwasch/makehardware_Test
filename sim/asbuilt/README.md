# `sim/asbuilt` — simulation of the boards as the EasyEDA files draw them

Every component value here is read out of `hw/easyeda/*/schematic.json`. Nothing
is a stand-in for a value the boards do not have, and where a datasheet could
not be fetched it is recorded as blocked in `docs/reference/manifest.yaml`
rather than filled in from memory.

```bash
/opt/hw-py/bin/python sim/asbuilt/topology.py     # the closed-form picture
/opt/hw-py/bin/python sim/asbuilt/make_decks.py   # regenerate the .cir files
/opt/hw-py/bin/python sim/asbuilt/sweep.py 24 300 # frequency sweep, 24 turns, 300 nF
ngspice -b sim/asbuilt/link-24t-85k.cir           # one point
```

## The decks

| Deck | What it is |
|---|---|
| `link-24t-85k.cir` | Designed coil (220 µH) with the 300 nF the boards fit, driven at the 85 kHz the requirements assume. Delivers 44 W. |
| `link-24t-res.cir` | Same hardware at the frequency it actually resonates, 19.6 kHz. |
| `link-5t-85k.cir` | The coil the 300 nF would suit, at 85 kHz. k·Q falls to 20. |
| `link-24t-tuned.cir` | Designed coil correctly compensated (15.9 nF) at 85 kHz — the "as it should be" reference. |
| `dab-hv-loop.cir` | The DAB HV bridge exactly as drawn: output closed on itself through L1. |

## Two things that will bite the next person

**Give every bridge switch a body diode.** The first version of these decks used
bare `SW` elements. The 1 ns gap between the two gate signals leaves the tank
current with nowhere to go, `ROFF=1e9` develops an absurd voltage across the
open switch, and the deck quietly pumps energy in — the DAB loop read 98 A
peak-to-peak instead of 50, with a 25 A DC offset that never decayed. Adding the
body diodes brought it to 50.06 A pk-pk and 14.44 A rms, matching the closed
form `Δi = V·T/(2L)` to 0.1 %. A switching deck that disagrees with hand
integration by exactly 2× is usually this.

**`.meas` in this ngspice cannot take an expression.** `meas tran p avg
"v(a)*i(b)"` fails with *no such vector*. Build the vector first with `let` in
the `.control` block, then measure the named vector.

## Cross-checks

| Quantity | Closed form | ngspice |
|---|---|---|
| DAB loop ripple | 50.06 A pk-pk | 50.00 A pk-pk |
| DAB loop rms | 14.45 A | 14.44 A |
| DAB loop DC | 0 A | 0.12 A |
| Link split frequencies (k = 0.52) | 69.0 / 122.7 kHz | peaks at 72 / 115 kHz |

The split frequencies move inward under load, which is expected; the pair is
predicted, not fitted.
