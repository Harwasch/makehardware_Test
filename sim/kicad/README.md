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

**Cosmetic wires can short a control pin.** Drawing a rail across the top of a
switch row put the wire straight through each switch's `C+` pin, shorting VLV
to the gate net; ngspice reported `singular matrix: check node vg2#branch` and
produced zero data rows. The connections here are made with net labels, and
only the four vertical leg wires are drawn.

## Reproducing the numbers outside the GUI

```bash
cd sim/kicad
kicad-cli sch export netlist --format spice -o dab-sim.cir dab-sim.kicad_sch
ngspice -b dab-sim.cir
```

`dab-waveforms.png` is the plot of the bridge voltages and the inductor
current, generated from that netlist.
