#!/usr/bin/env python
"""Closed-form link budget for the Ulysses LARS wireless charger.

Series-series compensated inductive power transfer. Everything here is closed
form so it can be cross-checked by hand; the SPICE decks under sim/ are the
numerical check against it.

Run:  /opt/hw-py/bin/python sim/link-budget/link_budget.py

Sources for the inputs:
  * 3 kW, 400 V bus, 80-120 kHz band, 12 uH / 0.8 ohm / Q=12 PCB coil
    -> docs/reference/source/mako-charging-white-paper.pdf
  * 48 V, 33 Ah pack, air gap < 20 mm well aligned, conduction cooling
    -> vision interview, 2026-08-28
"""
import math

# ---- inputs ---------------------------------------------------------------
F_NOM = 85e3            # Hz, nominal drive frequency (white paper p.3)
V_BUS = 400.0           # V, TX H-bridge DC bus (white paper p.1)
P_TGT = 3000.0          # W, power transfer target (white paper p.1)
L_V1 = 12e-6            # H, v1 PCB coil inductance (white paper p.6)
R_V1 = 0.8              # ohm, v1 PCB coil series resistance (white paper p.6)
K_NOM = 0.5             # coupling coefficient, < 20 mm well-aligned (interview)
V_PACK = 48.0           # V nominal Mako pack (interview)
AH_PACK = 33.0          # Ah  (interview)

W_NOM = 2 * math.pi * F_NOM


def v_fundamental(vdc):
    """RMS of the fundamental of a full-bridge square wave at +/- vdc."""
    return 2 * math.sqrt(2) / math.pi * vdc


def link_power(v1, v2, w, m):
    """Power transferred by an SS-compensated link with both sides at resonance."""
    return v1 * v2 / (w * m)


def required_mutual(v1, v2, p, w):
    """Mutual inductance that makes an SS link deliver p at resonance."""
    return v1 * v2 / (p * w)


def eta_max(k, q1, q2=None):
    """Maximum coil-to-coil efficiency at the optimal load.

    eta = (k^2 Q1 Q2) / (1 + sqrt(1 + k^2 Q1 Q2))^2
    """
    q2 = q1 if q2 is None else q2
    x = k * k * q1 * q2
    return x / (1 + math.sqrt(1 + x)) ** 2


def q_of(l, r, w=W_NOM):
    return w * l / r


def scale_spiral(l_from, r_from, l_to):
    """Resistance of a spiral rescaled to a new inductance. L ~ N^2, R ~ N."""
    return r_from * math.sqrt(l_to / l_from)


def kq_for_eta(target):
    """Invert eta_max for the k*Q product a given efficiency demands."""
    lo, hi = 1e-3, 1e5
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if eta_max(1.0, mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    v1 = v_fundamental(V_BUS)
    e_pack = V_PACK * AH_PACK / 1000.0

    print(f"Pack today: {V_PACK:.0f} V x {AH_PACK:.0f} Ah = {e_pack:.3f} kWh")
    print(f"  {P_TGT/1000:.1f} kW into it = {P_TGT/(e_pack*1000):.2f}C, "
          f"{e_pack/(P_TGT/1000)*60:.0f} min, {P_TGT/V_PACK:.1f} A on the LV bus")
    print(f"  the white paper's 8 kWh pack would be {8000/V_PACK:.0f} Ah; "
          f"{P_TGT/1000:.1f} kW into that = {P_TGT/8000:.2f}C over {8/(P_TGT/1000):.1f} h")

    print(f"\nTX fundamental at a {V_BUS:.0f} V bus: {v1:.0f} V rms")

    m_v1 = K_NOM * L_V1
    print(f"\nv1 coil, k={K_NOM}: M = {m_v1*1e6:.1f} uH, wM = {W_NOM*m_v1:.2f} ohm")
    print(f"  power this link wants AT RESONANCE with {v1:.0f} V both ends: "
          f"{link_power(v1, v1, W_NOM, m_v1)/1000:.1f} kW")
    print(f"  ... at a tank current of {v1/(W_NOM*m_v1):.0f} A rms. Not operable.")

    m_req = required_mutual(v1, v1, P_TGT, W_NOM)
    i_tank = v1 / (W_NOM * m_req)
    print(f"\nFor {P_TGT/1000:.0f} kW at resonance: M = {m_req*1e6:.1f} uH "
          f"-> tank current {i_tank:.2f} A rms ({i_tank*math.sqrt(2):.2f} A peak)")
    for k in (0.2, 0.35, 0.5, 0.6):
        l_req = m_req / k
        print(f"    k={k:.2f} -> L1=L2 = {l_req*1e6:6.1f} uH "
              f"({l_req/L_V1:5.1f}x the v1 coil)")

    print(f"\nCoil-to-coil efficiency at k={K_NOM} (eta set by k*Q, not by R alone):")
    l_req = m_req / K_NOM
    r_scaled = scale_spiral(L_V1, R_V1, l_req)
    cases = [
        ("v1 PCB coil as documented", L_V1, R_V1),
        (f"PCB coil scaled to {l_req*1e6:.0f} uH", l_req, r_scaled),
        ("Litz at Q=150", l_req, W_NOM * l_req / 150),
        ("Litz at Q=300", l_req, W_NOM * l_req / 300),
    ]
    print(f"  {'coil':<32}{'L':>9}{'R':>8}{'Q':>7}{'k*Q':>7}{'eta':>8}{'loss':>9}")
    for label, l, r in cases:
        q = q_of(l, r)
        e = eta_max(K_NOM, q)
        print(f"  {label:<32}{l*1e6:8.0f}u{r:8.2f}{q:7.1f}{K_NOM*q:7.1f}"
              f"{e*100:7.1f}%{P_TGT*(1-e):8.0f} W")

    print(f"\nWhat the coil has to be, working back from an efficiency target:")
    for target in (0.90, 0.95, 0.97, 0.98):
        kq = kq_for_eta(target)
        print(f"  eta={target*100:.0f}% needs k*Q={kq:6.1f} -> Q={kq/K_NOM:6.0f} at k={K_NOM}"
              f"   (coil loss {P_TGT*(1-target):5.0f} W, {P_TGT*(1-target)/2:5.0f} W per coil)")

    print(f"\nResonant capacitance for the matched coil at {F_NOM/1e3:.0f} kHz: "
          f"{1/(W_NOM**2 * l_req)*1e9:.1f} nF")
    print(f"Capacitor voltage at {i_tank:.2f} A rms: "
          f"{i_tank/(W_NOM*1/(W_NOM**2*l_req)):.0f} V rms "
          f"-- the tank capacitor is a high-voltage part, size it deliberately")


if __name__ == "__main__":
    main()
