#!/usr/bin/env python
"""AC resistance and quality factor of the candidate coils.

This is the highest-uncertainty number in the whole design and the one the
architecture decision rests on, so the caveats here matter as much as the
numbers. With no laboratory, every figure below is a model output.

WHAT IS SOLID
  * DC resistance from geometry. Exact.
  * Skin depth. Exact.
  * The fact that Litz has roughly an order of magnitude more copper
    cross-section than an etched spiral of the same footprint. Exact.

WHAT IS NOT
  * The PCB proximity model. Kuhn and Ibrahim (IEEE T-MTT 49(1), 2001) derived
    their expression for silicon RFIC spirals with trace widths of tens of
    microns. Our trace is 3 mm -- three orders of magnitude outside the range
    it was fitted over. It is used here because it is the standard closed form
    for a planar spiral and nothing better exists in closed form, but the
    result is an ESTIMATE and is flagged as such everywhere it appears.
  * The Litz factor. A well-made bundle with strand diameter well under a skin
    depth has a low intrinsic factor, but external proximity from adjacent
    turns in a tight spiral is not captured by the strand-level model.
  * NEITHER MODEL INCLUDES FERRITE CORE LOSS OR COLD-PLATE EDDY LOSS. A
    measured coil Q includes both. So every Q below is a winding-only CEILING,
    not a prediction of what a finished pad would measure.

Run:  /opt/hw-py/bin/python sim/coil/coil_resistance.py
"""
import math

RHO_CU_20 = 1.72e-8          # ohm.m
ALPHA_CU = 0.00393           # per K
MU0 = 4e-7 * math.pi
F = 85e3
W0 = 2.0 * math.pi * F


def rho_cu(t_c):
    return RHO_CU_20 * (1.0 + ALPHA_CU * (t_c - 20.0))


def skin_depth(f=F, t_c=20.0):
    return math.sqrt(rho_cu(t_c) / (math.pi * f * MU0))


def r_dc(length_m, area_m2, t_c=20.0):
    return rho_cu(t_c) * length_m / area_m2


def kuhn_ibrahim(w, s, t, f=F, t_c=20.0):
    """Planar-spiral AC/DC resistance ratio, Kuhn and Ibrahim.

        f_crit = 3.1 * (w + s) * R_sheet / (2 * pi * mu0 * w^2)
        R_ac / R_dc = 1 + (1/10) * (f / f_crit)^2

    R_sheet = rho / t. USED OUTSIDE ITS FITTED RANGE -- see module docstring.
    """
    r_sheet = rho_cu(t_c) / t
    f_crit = 3.1 * (w + s) * r_sheet / (2.0 * math.pi * MU0 * w * w)
    return 1.0 + 0.1 * (f / f_crit) ** 2, f_crit


def litz_strands(bundle_dia, strand_dia, packing=0.50):
    """Strand count that fits a bundle at a given copper packing factor."""
    a_bundle = math.pi * (bundle_dia / 2.0) ** 2
    a_strand = math.pi * (strand_dia / 2.0) ** 2
    return int(packing * a_bundle / a_strand), packing * a_bundle


def q_of(l_h, r_ohm, f=F):
    return 2.0 * math.pi * f * l_h / r_ohm


def eta_max(k, q):
    x = (k * q) ** 2
    return x / (1.0 + math.sqrt(1.0 + x)) ** 2


def kq_for_eta(target):
    lo, hi = 1e-3, 1e5
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if eta_max(1.0, mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    # Geometry from coil_model.py: 300/100 mm, 29 turns.
    LENGTH = 18.22          # m of conductor
    L_COIL = 169.3e-6       # H, air, no ferrite
    K_WORST = 0.705         # worst case across the SYS-006 envelope, air
    P_TGT, LOSS_BUDGET = 3000.0, 120.0

    print("=" * 76)
    print("COIL AC RESISTANCE AND QUALITY FACTOR")
    print("=" * 76)
    print(f"Geometry: 300/100 mm, 29 turns, {LENGTH:.2f} m of conductor, "
          f"L = {L_COIL*1e6:.1f} uH (air)")
    print(f"Reactance at {F/1e3:.0f} kHz: X_L = {W0*L_COIL:.1f} ohm")
    for t_c in (20.0, 100.0):
        print(f"Skin depth in copper at {F/1e3:.0f} kHz, {t_c:.0f} C: "
              f"{skin_depth(t_c=t_c)*1e3:.3f} mm")

    print("\n" + "-" * 76)
    print("A · ETCHED PCB SPIRAL — 3 mm trace, 0.57 mm gap, 4 oz (0.140 mm)")
    print("-" * 76)
    W, S, T = 3.0e-3, 0.57e-3, 0.140e-3
    area = W * T
    print(f"  copper cross-section {area*1e6:.3f} mm2   "
          f"(trace thickness / skin depth = {T/skin_depth():.2f})")
    for t_c in (20.0, 100.0):
        rdc = r_dc(LENGTH, area, t_c)
        fr, fcrit = kuhn_ibrahim(W, S, T, t_c=t_c)
        rac = rdc * fr
        print(f"  {t_c:5.0f} C:  R_dc = {rdc:6.3f} ohm   f_crit = {fcrit/1e3:5.1f} kHz   "
              f"R_ac/R_dc = {fr:5.2f}   R_ac = {rac:6.3f} ohm")
        print(f"           Q_dc = {q_of(L_COIL, rdc):6.1f}   "
              f"Q_ac = {q_of(L_COIL, rac):6.1f}  (winding only, ESTIMATE)")

    print("\n" + "-" * 76)
    print("B · LITZ BUNDLE — 3.2 mm outside diameter")
    print("-" * 76)
    D_BUNDLE, D_STRAND = 3.2e-3, 0.0799e-3       # AWG 40
    n_str, a_cu = litz_strands(D_BUNDLE, D_STRAND)
    print(f"  AWG 40 strand diameter {D_STRAND*1e3:.4f} mm = "
          f"{D_STRAND/skin_depth():.3f} skin depths  (well under 1 — the point of Litz)")
    print(f"  {n_str} strands fit at 50% copper packing -> "
          f"{a_cu*1e6:.3f} mm2 of copper")
    print(f"  That is {a_cu/area:.1f}x the etched spiral's copper in the same footprint.")
    for t_c in (20.0, 100.0):
        rdc = r_dc(LENGTH, a_cu, t_c)
        print(f"  {t_c:5.0f} C:  R_dc = {rdc:6.4f} ohm   Q_dc = {q_of(L_COIL, rdc):7.0f}")
        for fr in (1.2, 2.0, 4.0):
            rac = rdc * fr
            print(f"           F_R = {fr:4.1f} -> R_ac = {rac:6.4f} ohm, "
                  f"Q = {q_of(L_COIL, rac):7.0f}")

    print("\n" + "=" * 76)
    print("AGAINST THE REQUIREMENT")
    print("=" * 76)
    kq_req = kq_for_eta(1.0 - LOSS_BUDGET / P_TGT)
    q_req = kq_req / K_WORST
    print(f"  MEC-001 allows {LOSS_BUDGET:.0f} W of {P_TGT/1000:.0f} kW, "
          f"i.e. eta >= {(1-LOSS_BUDGET/P_TGT)*100:.1f}% -> k*Q >= {kq_req:.1f}")
    print(f"  Worst-case k across the SYS-006 envelope is {K_WORST:.3f} (air, computed),")
    print(f"  so the coil must reach Q >= {q_req:.0f}.")
    print()
    print(f"  {'coil':<44}{'Q':>8}{'k*Q':>8}{'eta':>8}{'loss':>9}")
    fr_pcb, _ = kuhn_ibrahim(W, S, T, t_c=100.0)
    q_pcb = q_of(L_COIL, r_dc(LENGTH, area, 100.0) * fr_pcb)
    rows = [("PCB spiral, hot, winding only (ESTIMATE)", q_pcb)]
    rdc_litz = r_dc(LENGTH, a_cu, 100.0)
    for fr in (2.0, 4.0):
        rows.append((f"Litz, hot, F_R = {fr:.1f}, winding only", q_of(L_COIL, rdc_litz * fr)))
    rows.append(("Litz, published measured range for WPT pads", 300.0))
    for label, q in rows:
        e = eta_max(K_WORST, q)
        print(f"  {label:<44}{q:8.0f}{K_WORST*q:8.1f}{e*100:7.1f}%{P_TGT*(1-e):8.0f} W")

    print("\n" + "=" * 76)
    print("READ THIS BEFORE USING ANY NUMBER ABOVE")
    print("=" * 76)
    print("  1. Every Q here is WINDING ONLY. Ferrite core loss and eddy loss in")
    print("     the cold plate are not modelled and both reduce it. A measured")
    print("     coil Q includes them, which is why published Litz WPT pads")
    print("     measure 200-400 rather than the four figures the winding alone")
    print("     suggests. Treat these as ceilings.")
    print("  2. The PCB proximity factor uses Kuhn and Ibrahim three orders of")
    print("     magnitude outside its fitted trace width. It is the best closed")
    print("     form available and it is still an estimate.")
    print("  3. The Litz F_R is swept rather than predicted, because external")
    print("     proximity between adjacent turns of a tight spiral is not")
    print("     captured by a strand-level model.")
    print("  4. k is computed in AIR. Ferrite raises it, a cold plate lowers it.")
    print()
    print("  The decision these support is directional, not final: the etched")
    print("  spiral lands short of the requirement even before ferrite and plate")
    print("  loss are added, and Litz clears it with room even at a pessimistic")
    print("  F_R. Closing MEC-001 properly still needs FEA or a measurement.")


if __name__ == "__main__":
    main()
