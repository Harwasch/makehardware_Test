#!/usr/bin/env python3
"""Sweep drive frequency across a link case and report delivered power.

A series-series link at high coupling does not have one resonance: it splits
into two.  This sweep is how you see where the power actually goes.

    /opt/hw-py/bin/python sim/asbuilt/sweep.py [n_turns] [C_nF]
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_decks import link_deck                              # noqa: E402

MEAS = re.compile(r"^(p_in|p_out|i_tank|i_pk|v_out|v_ctx) = ([-\d.e+]+)", re.M)


def run(n, f, c):
    deck, info = link_deck(n, f, c_tank=c)
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as fh:
        fh.write(deck)
        path = fh.name
    try:
        out = subprocess.run(["ngspice", "-b", path], capture_output=True,
                             text=True, timeout=300).stdout
    finally:
        os.unlink(path)
    return {k: float(v) for k, v in MEAS.findall(out)}, info


def main(argv):
    n = int(argv[1]) if len(argv) > 1 else 24
    c = float(argv[2]) * 1e-9 if len(argv) > 2 else 15.9e-9
    _, info = link_deck(n, 85e3, c_tank=c)
    print(f"coil {n} turns: L = {info['L']*1e6:.1f} uH, k = {info['k']:.3f}, "
          f"C = {c*1e9:.1f} nF, f0 = {info['f0']/1e3:.1f} kHz")
    f0 = info["f0"]
    k = info["k"]
    print(f"split frequencies f0/sqrt(1+/-k) = {f0/(1+k)**0.5/1e3:.1f} kHz"
          f" and {f0/(1-k)**0.5/1e3:.1f} kHz\n")
    print(f"  {'f (kHz)':>8} {'P_in (W)':>9} {'P_out (W)':>10} "
          f"{'eta':>6} {'I_tank (A)':>11} {'V_out (V)':>10}")
    freqs = [f0 * x for x in (0.55, 0.65, 0.75, 0.81, 0.85, 0.9, 1.0,
                              1.1, 1.2, 1.35, 1.44, 1.55, 1.7)]
    for f in freqs:
        m, _ = run(n, f, c)
        if "p_out" not in m:
            print(f"  {f/1e3:8.1f}   (no result)")
            continue
        eta = m["p_out"] / m["p_in"] if m.get("p_in") else 0.0
        print(f"  {f/1e3:8.1f} {m['p_in']:9.0f} {m['p_out']:10.0f} "
              f"{eta:6.3f} {m['i_tank']:11.1f} {m['v_out']:10.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
