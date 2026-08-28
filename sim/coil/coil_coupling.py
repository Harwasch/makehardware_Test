#!/usr/bin/env python
"""Coupling between two planar spirals, including MISALIGNMENT.

coil_model.py uses Maxwell's elliptic-integral formula, which is exact but only
valid for COAXIAL filaments. SYS-006 allows 10 mm of lateral and 3 degrees of
angular misalignment, and MEC-003 puts a floor under k across that whole
envelope, so the coaxial number alone cannot close it.

This module integrates Neumann's formula numerically instead:

    M = (mu0 / 4pi) * closed-double-integral of (dl1 . dl2) / |r1 - r2|

which has no symmetry restriction. It is validated against the analytic
coaxial result at zero offset before being trusted off-axis -- if the two
disagree at zero offset the discretisation is too coarse and the off-axis
numbers are worthless.

Run:  /opt/hw-py/bin/python sim/coil/coil_coupling.py
"""
import math

import numpy as np

from coil_model import (MU0, spiral_radii, rect_equivalent_radius,
                        inductance_filaments, mutual_spirals)


def spiral_segments(radii, n_seg, centre=(0.0, 0.0, 0.0), tilt_deg=0.0):
    """Discretise every turn of a spiral into straight segments.

    Returns (midpoints, vectors) each of shape (n_turns * n_seg, 3).
    `tilt_deg` rotates the whole coil about the x axis, which is the angular
    misalignment case.
    """
    theta = np.linspace(0.0, 2.0 * math.pi, n_seg + 1)
    mids, vecs = [], []
    for a in radii:
        x = a * np.cos(theta)
        y = a * np.sin(theta)
        z = np.zeros_like(x)
        p = np.stack([x, y, z], axis=1)
        seg = p[1:] - p[:-1]
        mid = 0.5 * (p[1:] + p[:-1])
        mids.append(mid)
        vecs.append(seg)
    mids = np.concatenate(mids, axis=0)
    vecs = np.concatenate(vecs, axis=0)

    if tilt_deg:
        t = math.radians(tilt_deg)
        rot = np.array([[1.0, 0.0, 0.0],
                        [0.0, math.cos(t), -math.sin(t)],
                        [0.0, math.sin(t), math.cos(t)]])
        mids = mids @ rot.T
        vecs = vecs @ rot.T

    mids = mids + np.asarray(centre, dtype=float)
    return mids, vecs


def mutual_neumann(radii_a, radii_b, gap, lateral=0.0, tilt_deg=0.0, n_seg=90):
    """Neumann double sum between two spirals, with arbitrary offset."""
    ma, va = spiral_segments(radii_a, n_seg)
    mb, vb = spiral_segments(radii_b, n_seg,
                             centre=(lateral, 0.0, gap), tilt_deg=tilt_deg)
    # (dl1 . dl2) for every pair
    dot = va @ vb.T
    # |r1 - r2| for every pair
    diff = ma[:, None, :] - mb[None, :, :]
    dist = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
    return MU0 / (4.0 * math.pi) * float(np.sum(dot / dist))


def main():
    D_OUT, D_IN, N = 0.300, 0.100, 29
    W, T = 3.0e-3, 0.140e-3
    radii = spiral_radii(D_OUT, D_IN, N)
    r_eq = rect_equivalent_radius(W, T)
    L = inductance_filaments(radii, r_eq)

    print("=" * 74)
    print("COUPLING WITH MISALIGNMENT — Neumann numerical integration")
    print("=" * 74)
    print(f"Coil: {D_OUT*1e3:.0f}/{D_IN*1e3:.0f} mm, {N} turns, L = {L*1e6:.1f} uH (air)\n")

    print("VALIDATION — numerical vs analytic, coaxial, before trusting off-axis")
    print(f"  {'gap':>7}{'analytic M':>14}{'numerical M':>14}{'error':>9}")
    ok = True
    for g in (5e-3, 10e-3, 20e-3):
        m_an = mutual_spirals(radii, radii, g)
        m_nu = mutual_neumann(radii, radii, g)
        err = (m_nu / m_an - 1.0) * 100.0
        flag = "" if abs(err) < 1.0 else "   <-- TOO COARSE"
        if abs(err) >= 1.0:
            ok = False
        print(f"  {g*1e3:6.0f}mm{m_an*1e6:13.2f}u{m_nu*1e6:13.2f}u{err:8.2f}%{flag}")
    if not ok:
        print("\n  Discretisation is too coarse. Raise n_seg before reading anything below.")
    print()

    print("COUPLING ACROSS THE SYS-006 ENVELOPE")
    print("  gap 5-20 mm, lateral misalignment to 10 mm, tilt to 3 degrees")
    print(f"  {'gap':>7}{'lateral':>9}{'tilt':>7}{'M':>12}{'k':>9}")
    worst = (None, 1e9)
    for g in (5e-3, 10e-3, 15e-3, 20e-3):
        for lat in (0.0, 5e-3, 10e-3):
            for tilt in (0.0, 3.0):
                m = mutual_neumann(radii, radii, g, lateral=lat, tilt_deg=tilt)
                k = m / L
                if k < worst[1]:
                    worst = ((g, lat, tilt), k)
                print(f"  {g*1e3:6.0f}mm{lat*1e3:8.0f}mm{tilt:6.1f}d{m*1e6:11.2f}u{k:9.3f}")
    (g, lat, tilt), kw = worst
    print(f"\n  WORST CASE in the envelope: gap {g*1e3:.0f} mm, lateral {lat*1e3:.0f} mm, "
          f"tilt {tilt:.0f} deg -> k = {kw:.3f}")
    print(f"  MEC-003 floor is 0.40. Margin: {kw/0.40:.2f}x" if kw >= 0.40
          else f"  MEC-003 floor is 0.40. FAILS by {0.40-kw:.3f}")

    print("\n  Caveat unchanged: AIR ONLY. A ferrite backing raises k, a conductive")
    print("  cold plate behind it lowers k, and neither has a closed form. These are")
    print("  the numbers to beat in FEA, not the final ones.")


if __name__ == "__main__":
    main()
