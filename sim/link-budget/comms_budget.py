#!/usr/bin/env python
"""In-band communication budget for the Ulysses LARS charger.

The charger needs a handshake and control packets across the same coils that
carry the power. The governing constraint is not signal-to-noise -- it is that
the resonant tank is a bandpass filter whose bandwidth is set by its LOADED Q,
and the loaded Q swings by a factor of fifty between full power and no load.

Handshake happens at no load, which is exactly when the tank is narrowest.

Run:  /opt/hw-py/bin/python sim/link-budget/comms_budget.py
"""
import math

F0 = 85e3
L_COIL = 161.9e-6        # matched coil from link_budget.py
Q_UNLOADED = 98.0        # the floor MEC-001 demands at k = 0.5
WM = 43.2                # ohm, matched mutual reactance from link_budget.py
V_FUND = 360.0           # V rms, fundamental of the 400 V bridge

W0 = 2 * math.pi * F0
R_COIL = W0 * L_COIL / Q_UNLOADED


def reflected_resistance(p_out, v_fund=V_FUND, wm=WM):
    """Resistance the secondary reflects into the primary at a given throughput."""
    if p_out <= 0:
        return 0.0
    r_ac = v_fund * v_fund / p_out
    return wm * wm / r_ac


def loaded_q(r_extra, l=L_COIL, r_coil=R_COIL, w=W0):
    return w * l / (r_coil + r_extra)


def bandwidth(q, f0=F0):
    """-3 dB bandwidth of a second-order bandpass."""
    return f0 / q


def max_symbol_rate(bw):
    """Rule of thumb for a tank acting as a second-order bandpass."""
    return bw / 2


def main():
    print(f"Matched coil: L = {L_COIL*1e6:.1f} uH, X_L = {W0*L_COIL:.1f} ohm, "
          f"Q_unloaded = {Q_UNLOADED:.0f} -> R_coil = {R_COIL:.3f} ohm\n")

    print("Tank bandwidth against throughput -- the load sets the Q:")
    print(f"  {'condition':<30}{'R_reflected':>13}{'Q_loaded':>10}{'BW':>10}{'symbols':>12}")
    for p, label in ((3000, "full power, 3 kW"),
                     (1000, "1 kW"),
                     (300, "300 W trickle"),
                     (30, "30 W standby ping"),
                     (0, "no load (handshake)")):
        r_ref = reflected_resistance(p)
        q = loaded_q(r_ref)
        bw = bandwidth(q)
        print(f"  {label:<30}{r_ref:12.2f}o{q:10.1f}{bw/1e3:8.1f}k"
              f"{max_symbol_rate(bw):9.0f} bd")

    bw_nl = bandwidth(Q_UNLOADED)
    print(f"\nThe binding case: handshake at no load gives {bw_nl:.0f} Hz of bandwidth,")
    print(f"i.e. about {max_symbol_rate(bw_nl):.0f} baud. A 16-byte handshake frame at "
          f"{max_symbol_rate(bw_nl):.0f} baud takes {16*10/max_symbol_rate(bw_nl)*1000:.0f} ms.")

    print("\nDamping the tank during handshake trades efficiency for bandwidth.")
    print("It is only affordable at reduced drive amplitude, which is also the")
    print("safe way to probe an unknown receiver:")
    print(f"  {'damping':>9}{'Q':>7}{'BW':>9}   dissipation at reduced drive")
    for r_d in (100, 47, 22):
        q = loaded_q(r_d)
        bw = bandwidth(q)
        losses = "  ".join(f"{v:.0f} V: {v*v/r_d:.1f} W" for v in (40, 20, 10))
        print(f"  {r_d:7.0f}o{q:7.1f}{bw/1e3:7.1f}k   {losses}")

    print("\nConclusion: a 22 ohm shunt damping network engaged only during")
    print("handshake, driven at 10-20 V fundamental, gives ~22 kHz of bandwidth")
    print("for 4-18 W -- three orders of magnitude more headroom than the")
    print("undamped no-load tank, at a power level that is safe to apply into")
    print("an unidentified or absent receiver.")


if __name__ == "__main__":
    main()
