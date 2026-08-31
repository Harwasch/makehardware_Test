# sim/link, sim/dab

Two ngspice decks. Both are run by a Python driver that sweeps them and
cross-checks every point against closed form, because a simulator that agrees
with arithmetic is evidence and one that does not is a broken deck.

```bash
./sim/link/run_link.py     # resonant link  -> docs/design/sim-link.md
./sim/dab/run_dab.py       # DAB transformer -> docs/design/sim-dab.md
```

Read [`docs/design/sim-findings.md`](../../docs/design/sim-findings.md) for what
the numbers mean. The generated tables are numbers only.

**`link.cir`** is a faithful model of the white paper's resonant link: measured
coil values from page 6, bulk capacitance from page 5, 400 V bus, 85 kHz. Only
the compensation capacitance is computed, because the paper does not give it.

**`dab.cir`** is not a model of the white paper's DAB and cannot be. Page 8
names every semiconductor and none of the three parameters that set DAB power
transfer — turns ratio, leakage inductance, switching frequency. The deck runs
the inverse and solves for the leakage inductance 3 kW needs.

Neither deck carries switching loss, ZVS, dead time or parasitics; both use
ideal square-wave sources. That is chunk `S2`, and it is blocked on datasheets
that are not yet fetched — see `docs/reference/manifest.yaml`.
