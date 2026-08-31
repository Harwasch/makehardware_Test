# sim/kicad — schematics you can open and simulate

```bash
kicad sim/kicad/dab-sim.kicad_pro     # then Inspect > Simulator > Run
```

KiCad's simulator **is** ngspice, the same engine the hand-written decks in
`sim/link` and `sim/dab` use, so numbers from here and from there are directly
comparable. They agree: this schematic delivers 3016 W in / 2943 W out against
the closed form's 3001 W.

## dab-sim — dual active bridge, 48 V ↔ 400 V

The customer-supplied **56 µH series inductance** on the high-voltage side of
the PCB-coil planar transformer is `L3`, and it is what sets power transfer.
`L1`/`L2` are the transformer at n = 8.33, coupled at 0.9999 so that L3 is the
only leakage. Phase shift is set by the delay on `VG3`/`VG4`: 1.5 µs of a 10 µs
period is 54°, which is the 3 kW point at 100 kHz.

To sweep the operating point, change those two delays. 85 kHz wants 41.9°,
100 kHz wants 54.0°, and above about 119 kHz this transformer cannot reach
3 kW at any phase shift.

**D1–D8 are the body diodes and the model is wrong without them.** With no
freewheel path the 100 ns dead time chops the inductor current and transfer
falls from 3.0 kW to 1.2 kW — measured, not asserted.

## Two traps, both of which cost a debugging cycle

**`Sim.*` properties must be on the symbol instance, not just the library.**
A symbol placed programmatically carries only Reference/Value/Footprint/
Datasheet, so `kicad-cli sch export netlist --format spice` emits `S1 __S1`
with no nodes and no model. Every simulated part here carries `Sim.Device`,
`Sim.Pins` and `Sim.Params` as instance properties for that reason.

**Cosmetic wires can short a control pin.** The SWITCH symbol puts its control
pins at the same heights as its power pins, one grid column to the left, so a
rail drawn straight across a row of switches passes through every `C+` pin and
shorts the supply to the gate net. ngspice reports `singular matrix: check node
vg2#branch` and produces zero data rows. The rails here are drawn ABOVE and
BELOW the switch rows with short stubs down to each pin, which is why the top
rail sits at y = 68.58 rather than on the pin row.

## Reading it

The sheet is wired, not labelled: every power connection is a drawn line, so
the two H-bridges, their body diodes, the transformer and the 56 uH can be
traced by eye. Only the four gate nets `G1`-`G4` are labels, which is normal
practice — drawing them would put eight wires across the sheet for no gain.
The power nets carry labels as well as wires (`VLV_48V`, `LA`, `LB`, `HA`,
`HB`, `VHV_400V`) so the exported netlist reads in those names instead of
`Net-_D1-A_`.

## Reproducing the numbers outside the GUI

```bash
cd sim/kicad
kicad-cli sch export netlist --format spice -o dab-sim.cir dab-sim.kicad_sch
ngspice -b dab-sim.cir
```

`dab-waveforms.png` is the plot of the bridge voltages and the inductor
current, generated from that netlist.
