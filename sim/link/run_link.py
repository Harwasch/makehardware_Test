#!/opt/hw-py/bin/python
"""Sweep the resonant-link deck and cross-check every point against closed form.

Two designs, one deck:

  v1  the white paper's measured coils - 12 uH, 0.8 ohm (page 6)
  v2  the ADR-0001 design point, from sim/coil/coil_rect.py, not from memory

The closed form for a series-series compensated link driven at resonance into a
diode rectifier is

    R_ac = (8/pi^2) * R_load          the rectifier's equivalent AC resistance
    Z_r  = (w*M)^2 / R_ac             impedance the secondary reflects
    I1   = V1_fund / (R_p + Z_r)      primary current, reactances cancelled
    P    = I1^2 * Z_r

and every simulated point is compared against it. Where they disagree by more
than a few percent the deck is wrong, not the arithmetic.

    ./sim/link/run_link.py            # run the sweep, write the results table
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "link.cir")
OUT = "docs/design/sim-link.md"

PI = math.pi
VBUS = 400.0
V_FUND = 2 * math.sqrt(2) * VBUS / PI          # 360 V rms fundamental
FS = 85e3
W = 2 * PI * FS

# White paper page 6, measured. The compensation capacitance is not in the
# paper and is computed for resonance at FS.
V1 = {"name": "v1 white paper", "L": 12e-6, "R": 0.8}
# sim/coil/coil_rect.py at the ADR-0001 design point, 10 mm gap, 100 degC.
V2 = {"name": "v2 ADR-0001", "L": 220.3e-6, "R": 0.673}
# k across the SYS-006 envelope, from coil_rect.analyse() at 100 degC:
#   8 mm aligned 0.572 | 10 mm aligned 0.520 | 14 mm, 5 mm offset, 2 deg 0.433
K_NOM, K_WORST, K_BEST = 0.520, 0.433, 0.572


def closed_form(L, R, k, rload, f=FS):
    w = 2 * PI * f
    M = k * L
    r_ac = 8 / PI**2 * rload
    z_r = (w * M) ** 2 / r_ac
    i1 = V_FUND / (R + z_r)
    p = i1**2 * z_r
    return {"M": M, "wM": w * M, "R_ac": r_ac, "Z_r": z_r,
            "I1": i1, "P": p, "Vout": math.sqrt(max(p, 0) * rload)}


def run(L, R, k, rload, f=FS, cs=None):
    """One ngspice run. `cs` lets a case stay compensated for FS while the
    drive moves off it, which is how a real tracker limits current."""
    with open(DECK) as fh:
        deck = fh.read()
    cs = cs if cs is not None else 1 / ((2 * PI * f) ** 2 * L)
    for key, val in (("FS", f), ("LC", L), ("RC", R), ("KC", k),
                     ("RLOAD", rload)):
        deck = re.sub(rf"^\.param {key}=.*$", f".param {key}={val:.10g}",
                      deck, flags=re.M)
    deck = re.sub(r"^\.param CS=.*$", f".param CS={cs:.10g}", deck, flags=re.M)
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as fh:
        fh.write(deck)
        path = fh.name
    try:
        r = subprocess.run(["ngspice", "-b", path], capture_output=True,
                           text=True, timeout=600)
    finally:
        os.unlink(path)
    out = r.stdout + r.stderr
    vals = {}
    for m in re.finditer(r"^(\w+)\s*=\s*([-\d.e+]+)\s*$", out, re.M):
        vals[m.group(1)] = float(m.group(2))
    # ngspice prints a warning and then plausible numbers; carry them along
    obs = [l.strip() for l in out.splitlines()
           if re.search(r"singular|Warning|doesn't converge|Error", l, re.I)
           and "No compatibility" not in l]
    return vals, obs


def main() -> int:
    rows = []
    print(f"{'case':16} {'k':>5} {'Rload':>7} "
          f"{'I_tx sim':>9} {'I_tx cf':>9} {'Vout sim':>9} {'P sim':>9} "
          f"{'P cf':>9} {'err':>6}")
    # v1 at the load that would put 3 kW on a 400 V rail, over plausible k.
    # v2 at that same load, and at the load that actually yields 3 kW on each
    # corner of the SYS-006 envelope.
    grid = ([(V1, k, 53.3) for k in (0.20, 0.30, 0.52, 0.70)]
            + [(V2, K_NOM, 53.3), (V2, K_NOM, 106.8),
               (V2, K_WORST, 53.3), (V2, K_WORST, 73.9),
               (V2, K_BEST, 129.0)])
    bad = 0
    for design, k, rload in grid:
        vals, obs = run(design["L"], design["R"], k, rload)
        cf = closed_form(design["L"], design["R"], k, rload)
        vout = vals.get("vout_avg", float("nan"))
        p_sim = vout * vout / rload
        err = abs(p_sim - cf["P"]) / cf["P"] * 100 if cf["P"] else float("nan")
        if err > 12 or obs:
            bad += 1
        print(f"{design['name']:16} {k:5.2f} {rload:7.1f} "
              f"{vals.get('itx_rms', float('nan')):9.1f} {cf['I1']:9.1f} "
              f"{vout:9.1f} {p_sim:9.1f} {cf['P']:9.1f} {err:5.1f}%")
        if obs:
            for o in obs[:3]:
                print(f"    observation: {o}")
        rows.append({"design": design["name"], "k": k, "rload": rload,
                     "itx": vals.get("itx_rms"), "irx": vals.get("irx_rms"),
                     "vout": vout, "vtank": vals.get("vtank_pk"),
                     "vpp": vals.get("vout_pp"),
                     "p_sim": p_sim, "p_cf": cf["P"], "i_cf": cf["I1"],
                     "wM": cf["wM"], "err": err, "obs": obs})
    write_report(rows)
    return 1 if bad else 0


def write_report(rows) -> None:
    o = ["# Resonant link simulation", "",
         "Generated by `sim/link/run_link.py` from `sim/link/link.cir` on "
         "ngspice-42. Do not edit by hand.", "",
         f"Drive {VBUS:.0f} V square wave at {FS/1e3:.0f} kHz, fundamental "
         f"{V_FUND:.0f} V rms. Series-series compensation, each side tuned to "
         "resonance at the drive frequency. Full-bridge rectifier into a "
         "bulk capacitor and a resistive load.", "",
         "| Design | k | R_load Ω | ωM Ω | I_tx sim A | I_tx closed form A | "
         "V_out V | P sim W | P closed form W | error |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        o.append(f"| {r['design']} | {r['k']:.2f} | {r['rload']:.1f} | "
                 f"{r['wM']:.1f} | {r['itx']:.1f} | {r['i_cf']:.1f} | "
                 f"{r['vout']:.0f} | {r['p_sim']:.0f} | {r['p_cf']:.0f} | "
                 f"{r['err']:.1f}% |")
    o += ["", "Peak voltage on the compensation capacitor, which is what the "
          "part has to be rated for:", "",
          "| Design | k | V_tank peak V | Output ripple V pp |",
          "|---|---:|---:|---:|"]
    for r in rows:
        o.append(f"| {r['design']} | {r['k']:.2f} | "
                 f"{(r['vtank'] or 0):.0f} | {(r['vpp'] or 0):.2f} |")
    obs = [(r["design"], r["k"], x) for r in rows for x in r["obs"]]
    o += ["", "## Simulator observations", ""]
    o += ([f"* {d} k={k:.2f}: `{x}`" for d, k, x in obs] if obs
          else ["None. No singular-matrix or convergence warnings on any run."])
    with open(OUT, "w") as fh:
        fh.write("\n".join(o) + "\n")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
