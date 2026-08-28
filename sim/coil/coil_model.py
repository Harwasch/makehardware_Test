#!/usr/bin/env python
"""Planar spiral coil model — inductance and coupling from first principles.

No laboratory access, so the coil geometry has to be settled by analysis. This
module does the part that is exactly computable: self-inductance and mutual
inductance of a coaxial pair of planar spirals in AIR, from Maxwell's formula
for circular filaments. AC resistance is a separate, harder problem and lives
in coil_resistance.py.

Two independent methods are implemented for self-inductance and cross-checked
against each other, per the house rule about closed forms:

  1. Filament summation  -- every turn treated as a circular filament, with
     Maxwell's elliptic-integral mutual inductance between every pair and a
     high-frequency self-term for each turn. Rigorous for a coaxial spiral.
  2. Mohan current-sheet -- the standard monomial approximation for planar
     spirals (Mohan, Hershenson, Boyd, Lee, JSSC 34(10), 1999).

They should agree within a few percent. If they do not, one of them is being
used outside its range and the disagreement is the finding.

IMPORTANT LIMITATION: this is an AIR model. A ferrite backing raises both the
self-inductance and the coupling substantially, and no closed form covers it --
that correction needs magnetostatic FEA and is recorded as an open item.

Run:  /opt/hw-py/bin/python sim/coil/coil_model.py
"""
import math

import numpy as np
from scipy.special import ellipk, ellipe

MU0 = 4e-7 * math.pi


# --------------------------------------------------------------------------
# Maxwell's mutual inductance between two coaxial circular filaments
# --------------------------------------------------------------------------
def mutual_filaments(a, b, z):
    """Mutual inductance of two coaxial circular filaments, radii a and b,
    axial separation z. Maxwell's formula:

        M = mu0 * sqrt(a*b) * [ (2/k - k) K(k) - (2/k) E(k) ]
        k^2 = 4ab / ((a+b)^2 + z^2)

    scipy's ellipk/ellipe take the PARAMETER m = k^2, not the modulus k.
    """
    k2 = 4.0 * a * b / ((a + b) ** 2 + z ** 2)
    k = math.sqrt(k2)
    if k2 >= 1.0:                      # coincident filaments — singular
        return float("inf")
    return MU0 * math.sqrt(a * b) * ((2.0 / k - k) * ellipk(k2) - (2.0 / k) * ellipe(k2))


def self_filament(a, r_eq):
    """Self-inductance of a single circular turn, radius a, equivalent
    conductor radius r_eq, at a frequency high enough that current rides the
    surface (internal inductance neglected):

        L = mu0 * a * [ ln(8a/r_eq) - 2 ]

    The -2 is the high-frequency form; -7/4 would include internal inductance
    for a uniform DC current distribution. At 85 kHz with a conductor much
    larger than the 0.22 mm skin depth, the high-frequency form is right.
    """
    return MU0 * a * (math.log(8.0 * a / r_eq) - 2.0)


def rect_equivalent_radius(w, t):
    """Equivalent circular-conductor radius for a rectangular trace, w by t.
    The standard geometric-mean-distance result for a rectangle is
    r_eq = 0.2235 * (w + t), which is what the filament self-term wants.
    """
    return 0.2235 * (w + t)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def spiral_radii(d_out, d_in, n):
    """Mean radius of each of n turns, evenly spaced between the inner and
    outer diameters."""
    r_out, r_in = d_out / 2.0, d_in / 2.0
    if n == 1:
        return np.array([(r_out + r_in) / 2.0])
    return np.linspace(r_in, r_out, n)


def conductor_length(radii):
    return float(np.sum(2.0 * math.pi * radii))


# --------------------------------------------------------------------------
# Method 1 — filament summation
# --------------------------------------------------------------------------
def inductance_filaments(radii, r_eq, z_offset=0.0):
    """Self-inductance of one spiral: sum of turn self-terms plus every
    mutual pair (counted twice, i != j)."""
    n = len(radii)
    total = sum(self_filament(a, r_eq) for a in radii)
    for i in range(n):
        for j in range(n):
            if i != j:
                total += mutual_filaments(radii[i], radii[j], z_offset)
    return total


def mutual_spirals(radii_a, radii_b, gap):
    """Mutual inductance between two coaxial spirals separated by `gap`."""
    return sum(mutual_filaments(a, b, gap) for a in radii_a for b in radii_b)


# --------------------------------------------------------------------------
# Method 2 — Mohan current-sheet approximation
# --------------------------------------------------------------------------
# Mohan et al., "Simple Accurate Expressions for Planar Spiral Inductances",
# IEEE JSSC 34(10) pp. 1419-1424, 1999, Table I.
_MOHAN = {          # c1,   c2,   c3,    c4
    "circular":   (1.00, 2.46, 0.00, 0.20),
    "octagonal":  (1.07, 2.29, 0.00, 0.19),
    "hexagonal":  (1.09, 2.23, 0.00, 0.17),
    "square":     (1.27, 2.07, 0.18, 0.13),
}


def inductance_mohan(d_out, d_in, n, shape="circular"):
    """Current-sheet expression:

        L = mu0 * n^2 * d_avg * c1/2 * [ ln(c2/rho) + c3*rho + c4*rho^2 ]
        d_avg = (d_out + d_in)/2 ,  rho = (d_out - d_in)/(d_out + d_in)

    Documented accuracy is a few percent for rho roughly 0.1 to 0.9; it
    degrades badly for very hollow spirals (rho near 0).
    """
    c1, c2, c3, c4 = _MOHAN[shape]
    d_avg = (d_out + d_in) / 2.0
    rho = (d_out - d_in) / (d_out + d_in)
    return MU0 * n * n * d_avg * c1 / 2.0 * (math.log(c2 / rho) + c3 * rho + c4 * rho * rho)


# --------------------------------------------------------------------------
# Design driver
# --------------------------------------------------------------------------
def turns_for_inductance(l_target, d_out, d_in, r_eq, n_lo=4, n_hi=120):
    """Smallest integer turn count whose filament inductance reaches the
    target. Inductance rises monotonically with n at fixed diameters."""
    best = None
    for n in range(n_lo, n_hi + 1):
        radii = spiral_radii(d_out, d_in, n)
        l = inductance_filaments(radii, r_eq)
        if best is None or abs(l - l_target) < abs(best[1] - l_target):
            best = (n, l, radii)
        if l >= l_target:
            return n, l, radii
    return best


def report(label, d_out, d_in, n, w, t, gaps=(5e-3, 10e-3, 15e-3, 20e-3)):
    r_eq = rect_equivalent_radius(w, t)
    radii = spiral_radii(d_out, d_in, n)
    l_fil = inductance_filaments(radii, r_eq)
    l_moh = inductance_mohan(d_out, d_in, n)
    pitch = (d_out - d_in) / 2.0 / (n - 1) if n > 1 else 0.0

    print(f"\n{label}")
    print(f"  {d_out*1e3:.0f} mm outer / {d_in*1e3:.0f} mm inner, {n} turns, "
          f"conductor {w*1e3:.2f} x {t*1e3:.3f} mm")
    print(f"  radial pitch {pitch*1e3:.2f} mm, clearance "
          f"{(pitch-w)*1e3:.2f} mm, conductor length {conductor_length(radii):.2f} m")
    print(f"  L (filament summation) = {l_fil*1e6:7.1f} uH")
    print(f"  L (Mohan current sheet) = {l_moh*1e6:6.1f} uH   "
          f"[{(l_moh/l_fil-1)*100:+.1f}% vs filament]")
    print(f"  {'gap':>8}{'M':>12}{'k':>9}")
    for g in gaps:
        m = mutual_spirals(radii, radii, g)
        print(f"  {g*1e3:7.0f}mm{m*1e6:11.2f}u{m/l_fil:9.3f}")
    return dict(n=n, L=l_fil, radii=radii, r_eq=r_eq, pitch=pitch,
                length=conductor_length(radii), w=w, t=t)


def main():
    L_TARGET = 161.9e-6
    print("=" * 74)
    print("PLANAR SPIRAL COIL MODEL — inductance and coupling in AIR")
    print("=" * 74)
    print(f"Target from the link budget: L = {L_TARGET*1e6:.1f} uH per side, "
          f"k >= 0.40 at 20 mm")
    print("NOTE: no ferrite in this model. A backing raises both L and k and")
    print("      needs magnetostatic FEA; see the open item at the end.")

    cases = [
        # label,                      d_out,   d_in,    w,      t
        ("A · PCB spiral, 5 mm trace, 4 oz",  0.300, 0.100, 5.0e-3, 0.140e-3),
        ("B · PCB spiral, 3 mm trace, 4 oz",  0.300, 0.100, 3.0e-3, 0.140e-3),
        ("C · Litz bundle, 3.2 mm dia",       0.300, 0.100, 3.2e-3, 3.2e-3),
        ("D · Litz bundle, 3.2 mm, 360 mm OD", 0.360, 0.120, 3.2e-3, 3.2e-3),
    ]
    out = {}
    for label, d_out, d_in, w, t in cases:
        r_eq = rect_equivalent_radius(w, t)
        n, l, _ = turns_for_inductance(L_TARGET, d_out, d_in, r_eq)
        pitch = (d_out - d_in) / 2.0 / (n - 1)
        if pitch < w:
            print(f"\n{label}\n  INFEASIBLE on one layer: {n} turns needs "
                  f"{pitch*1e3:.2f} mm pitch for a {w*1e3:.1f} mm conductor.")
            print(f"  (would need {math.ceil(w/pitch)} layers, or a larger diameter)")
        out[label] = report(label, d_out, d_in, n, w, t)

    print("\n" + "=" * 74)
    print("CROSS-CHECK — the two inductance methods against each other")
    print("=" * 74)
    print("A disagreement beyond a few percent means one method is out of range.")
    print("Mohan's fit degrades for a hollow spiral (rho near 1); the filament")
    print("sum has no such restriction but assumes circular, coaxial turns.")

    print("\n" + "=" * 74)
    print("OPEN — needs magnetostatic FEA, not a closed form")
    print("=" * 74)
    print("  * Ferrite backing raises L (typically 1.3-1.6x) and raises k.")
    print("  * A conductive cold plate behind the ferrite induces eddy currents")
    print("    that lower both, and sets a minimum ferrite thickness.")
    print("  * Seawater in the gap is conductive and lossy at 85 kHz.")
    print("  Until those are modelled the k values above are the AIR-ONLY")
    print("  lower bound for L and an unqualified estimate for k.")


if __name__ == "__main__":
    main()
