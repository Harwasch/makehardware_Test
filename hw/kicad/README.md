# KiCad conversion of the EasyEDA boards

Three projects, converted from `hw/easyeda/` on 2026-09-01. Open them with
KiCad 8 or later; the shared symbol library is registered per-project in
`sym-lib-table`.

| Project | Source | Parts | Nets |
|---|---|---|---|
| `dab.kicad_pro` | `hw/easyeda/DAB_Iter1/` | 204 | 88 |
| `tx.kicad_pro` | `hw/easyeda/TX_Iter1/` | 117 | 50 |
| `rx.kicad_pro` | `hw/easyeda/RX_Iter1/` | 70 | 27 |

## How faithful it is, and how you can check

The conversion carries **connectivity and parts**, and that is checked rather
than asserted. `scripts/eda_parse.py` rebuilds the netlist from the EasyEDA
sheet geometry; `scripts/kicad_net_check.py` diffs the KiCad netlist against it,
comparing the *partition of pins into nets* rather than net names:

```bash
/opt/hw-py/bin/python scripts/eda_parse.py hw/easyeda/TX_Iter1/schematic.json \
    --json build/eda/TX.json --netlist build/eda/TX-netlist.txt --bom build/eda/TX-bom.csv
kicad-cli sch export netlist --format kicad -o build/eda/tx-kicad.net hw/kicad/tx.kicad_sch
/opt/hw-py/bin/python scripts/kicad_net_check.py build/eda/tx-kicad.net build/eda/TX.json
```

All three report **MATCH**. The EasyEDA-derived netlists are also committed
alongside each source as `netlist.txt`, so the comparison can be made by eye.

## What it does not carry

* **Layout.** The `.kicad_pcb` files are empty. `hw/easyeda/*/pcb.json` holds
  the original boards; the pad-to-net table in them was used to confirm that
  net `SEC` and the DAB HV loop are the same on the PCB as on the sheet, so the
  findings in `docs/design/as-built-analysis.md` are not schematic-only.
* **Part numbers on the symbols.** Konnect's `batch_edit_schematic_components`
  can only update fields a symbol already has, and there is no batch tool to
  create one, so MPN and LCSC live in `hw/easyeda/*/bom.csv` keyed by reference
  designator rather than in the schematic. Merging them in is a one-line join
  when a batch annotation tool exists.
* **Pin electrical types.** EasyEDA's export records `0` (undefined) for 1480 of
  the 1533 pins, so the symbols in `lib/ulysses.kicad_sym` type every pin
  `passive` except those the source marks no-connect. That keeps ERC quiet about
  artefacts of the conversion; it also means ERC will not catch a real
  power-pin error until the types are filled in.
* **Reference designators are the originals.** The EasyEDA design uses `U` for
  many two-pin passives (`U10` is a 1.5 µF film capacitor on the RX). Renaming
  them would have broken traceability to the boards and to `bom.csv`, so they
  are kept as they are.

## Sheet layout

Each sheet is A0 with the multi-pin devices packed down the left and the
two-pin passives in a grid on the right, connected by net labels. It is a
machine layout, readable per-net rather than per-block. It is meant as a
faithful, diffable carrier of the design — not as a drawing to hand to a
reviewer.
