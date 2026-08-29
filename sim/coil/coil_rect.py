#!/usr/bin/env python
"""Rectangular planar spiral coil — inductance, coupling, resistance and Q.

The house constraint is a roughly 4 x 8 inch rectangular PCB coil with passive
cooling, so the circular model in coil_model.py does not apply. Geometry is
handled directly rather than approximated:

  * self-inductance of each turn from Grover's rectangular-loop formula
  * mutual inductance between every turn pair, and between the two coils,
    by numerical Neumann integration -- no symmetry assumption, so gap,
    lateral offset and tilt all work
  * AC resistance from Kuhn and Ibrahim, with a layers-in-parallel term

LAYER MODEL: parallel layers do NOT reduce resistance as 1/N. Proximity loss is
independent of the current a conductor carries, so it rises as N while transport
loss falls as 1/N -- see the note in analyse(). Transposing the stack removes
most of that penalty and is what makes this design work; see
docs/design/adr-0001-coil-technology.md.

Run:  /opt/hw-py/bin/python sim/coil/coil_rect.py
"""
import math

import numpy as np

MU0 = 4e-7 * math.pi
RHO_CU_20 = 1.72e-8
ALPHA_CU = 0.00393

F_NOM = 85e3
V_FUND = 360.0          # fundamental rms of the 400 V bridge
P_TGT = 3000.0
W0 = 2.0 * math.pi * F_NOM


def rho_cu(t_c):
    return RHO_CU_20 * (1.0 + ALPHA_CU * (t_c - 20.0))


def skin_depth(f=F_NOM, t_c=20.0):
    return math.sqrt(rho_cu(t_c) / (math.pi * f * MU0))


def rect_self(a, b, r_gmd):
    """Grover: self-inductance of a rectangular loop a x b with conductor
    geometric mean distance r_gmd."""
    d = math.hypot(a, b)
    return (MU0 / math.pi) * (
        -2.0 * (a + b) + 2.0 * d
        - a * math.log((a + d) / b) - b * math.log((b + d) / a)
        + a * math.log(2.0 * a / r_gmd) + b * math.log(2.0 * b / r_gmd)
    )


def gmd_rect(w, t):
    """Geometric mean distance of a rectangular conductor cross-section."""
    return 0.2235 * (w + t)


def rect_segments(a, b, n_side=40, z=0.0, offset=(0.0, 0.0), tilt_deg=0.0):
    """Discretise one rectangular turn into straight segments."""
    xs = np.linspace(-a / 2, a / 2, n_side + 1)
    ys = np.linspace(-b / 2, b / 2, n_side + 1)
    pts = [(x, -b / 2) for x in xs[:-1]]
    pts += [(a / 2, y) for y in ys[:-1]]
    pts += [(x, b / 2) for x in xs[::-1][:-1]]
    pts += [(-a / 2, y) for y in ys[::-1][:-1]]
    pts.append(pts[0])
    p = np.array([[x, y, 0.0] for x, y in pts])
    if tilt_deg:
        t = math.radians(tilt_deg)
        rot = np.array([[1.0, 0.0, 0.0],
                        [0.0, math.cos(t), -math.sin(t)],
                        [0.0, math.sin(t), math.cos(t)]])
        p = p @ rot.T
    p = p + np.array([offset[0], offset[1], z])
    return 0.5 * (p[1:] + p[:-1]), p[1:] - p[:-1]


def neumann(mA, vA, mB, vB):
    """Neumann double sum between two discretised loops."""
    dot = vA @ vB.T
    diff = mA[:, None, :] - mB[None, :, :]
    dist = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
    return MU0 / (4.0 * math.pi) * float(np.sum(dot / dist))


def turn_sizes(a_out, b_out, n, pitch):
    """Concentric rectangles working inwards from the outer turn."""
    return [(a_out - 2.0 * i * pitch, b_out - 2.0 * i * pitch) for i in range(n)]


def kuhn_ibrahim(w, s, t, f=F_NOM, t_c=100.0):
    """Planar-spiral AC/DC resistance ratio. Used outside its fitted trace
    width -- see docs/design/coil-model.md."""
    r_sheet = rho_cu(t_c) / t
    f_crit = 3.1 * (w + s) * r_sheet / (2.0 * math.pi * MU0 * w * w)
    return 1.0 + 0.1 * (f / f_crit) ** 2, f_crit


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


def analyse(a_out, b_out, n, w, t, clearance, layers=1, gap=20e-3,
            lateral=0.0, tilt_deg=0.0, t_c=100.0, n_side=40,
            transposition=0.0):
    """Full analysis of a rectangular spiral pair.

    `transposition` is the fraction of the layer proximity penalty removed by
    transposing the stack, so that every layer spends equal time at every
    depth. 0.0 is a plain parallel stack; 1.0 would remove 75% of the penalty,
    which is the most the published evidence supports (see below). Use 0.0
    unless the construction actually transposes.
    """
    pitch = w + clearance
    turns = turn_sizes(a_out, b_out, n, pitch)
    if min(min(a, b) for a, b in turns) <= 4.0 * pitch:
        return None                       # spiral has closed on itself
    r_gmd = gmd_rect(w, t)

    segs = [rect_segments(a, b, n_side) for a, b in turns]
    L = sum(rect_self(a, b, r_gmd) for a, b in turns)
    for i in range(n):
        for j in range(n):
            if i != j:
                L += neumann(segs[i][0], segs[i][1], segs[j][0], segs[j][1])

    segs2 = [rect_segments(a, b, n_side, z=gap, offset=(lateral, 0.0),
                           tilt_deg=tilt_deg) for a, b in turns]
    M = sum(neumann(segs[i][0], segs[i][1], segs2[j][0], segs2[j][1])
            for i in range(n) for j in range(n))

    length = sum(2.0 * (a + b) for a, b in turns)
    fr, f_c = kuhn_ibrahim(w, clearance, t, t_c=t_c)

    # Layer model. The obvious form -- divide R_dc by N, then apply the
    # proximity factor -- is WRONG, and it was wrong in this file until
    # 2026-08-29. It divides the proximity loss by N as well.
    #
    # Proximity resistance is proportional to conductor volume and to B
    # squared, and is INDEPENDENT of the current that conductor carries
    # (Nguyen and Fortin Blanchette, Electronics 2020, 9, 1324, Eq. 2).
    # Parallel layers do not change total ampere-turns, so B is unchanged:
    # every layer added is another slab of copper eddy-heating in the same
    # field. Transport loss falls as 1/N; proximity loss RISES as N.
    #
    #     R_ac(N) = R_dc1 / N  +  N * R_prox1
    #
    # which has a minimum at N_opt = sqrt(R_dc1 / R_prox1) and gets worse
    # beyond it. Measured confirmation: Yin et al., Electronics 2024, 13, 426,
    # Table 12 -- two identical PCB spiral layers in parallel at 100 kHz cut
    # resistance by 15.9%, not the 50% that 1/N predicts.
    r_dc1 = rho_cu(t_c) * length / (w * t)          # ONE layer
    r_prox1 = r_dc1 * (fr - 1.0)                    # ONE layer's proximity excess
    r_dc = r_dc1 / layers                           # transport term
    r_ac = r_dc + layers * r_prox1 * (1.0 - transposition * 0.75)
    q = W0 * L / r_ac
    k = M / L
    return dict(L=L, M=M, k=k, Q=q, kQ=k * q, eta=eta_max(k, q),
                loss=P_TGT * (1.0 - eta_max(k, q)), length=length, pitch=pitch,
                fr=fr, f_crit=f_c, r_dc=r_dc, r_ac=r_ac, n=n, w=w, t=t,
                layers=layers, inner=turns[-1], r_dc1=r_dc1, r_prox1=r_prox1,
                n_opt=math.sqrt(r_dc1 / r_prox1) if r_prox1 > 0 else float('inf'),
                transposition=transposition)


def main():
    # The ADR-0001 design point.
    A_OUT, B_OUT = 0.102, 0.203        # 4.0 x 8.0 inch
    T_CU = 0.140e-3                    # 4 oz
    N, W, CL = 24, 0.25e-3, 0.20e-3    # one skin depth class, per ORNL/Kentucky
    GAP, LAT = 10e-3, 5e-3             # SYS-006 nominal, worst offset
    M_REQ = V_FUND * V_FUND / (P_TGT * W0)
    KQ_REQ = kq_for_eta(1.0 - 120.0 / P_TGT)

    print("=" * 78)
    print("RECTANGULAR PCB COIL — ADR-0001 design point")
    print("=" * 78)
    print(f"{A_OUT*1e3:.0f} x {B_OUT*1e3:.0f} mm, {N} turns, {W*1e3:.2f} mm trace on "
          f"{CL*1e3:.2f} mm, 4 oz, {F_NOM/1e3:.0f} kHz")
    print(f"Skin depth at 100 C: {skin_depth(t_c=100.0)*1e3:.3f} mm — the trace is "
          f"{W/skin_depth(t_c=100.0):.2f} skin depths")
    print(f"Need M >= {M_REQ*1e6:.1f} uH and k*Q >= {KQ_REQ:.0f}\n")

    print("WHY A PLAIN PARALLEL STACK FAILS")
    print(f"  R_ac(N) = R_dc1/N + N*R_prox1 has a MINIMUM — adding layers past it")
    print(f"  makes the coil worse, because proximity loss rises with N.")
    print(f"  {'N':>3}{'R_dc/N':>9}{'N*R_prox':>10}{'R_ac':>9}{'Q':>7}{'k*Q':>7}")
    for n_lay in (1, 2, 4, 8, 13, 16, 20):
        r = analyse(A_OUT, B_OUT, N, W, T_CU, CL, layers=n_lay, gap=GAP, lateral=LAT)
        print(f"  {n_lay:3d}{r['r_dc']:8.3f}o{n_lay*r['r_prox1']:9.3f}o"
              f"{r['r_ac']:8.3f}o{r['Q']:7.0f}{r['kQ']:7.1f}")
    r1 = analyse(A_OUT, B_OUT, N, W, T_CU, CL, layers=1, gap=GAP, lateral=LAT)
    print(f"  optimum N = sqrt(R_dc1/R_prox1) = {r1['n_opt']:.1f}\n")

    print("WHAT TRANSPOSITION BUYS")
    print(f"  {'transposed':>11}{'layers':>8}{'R_ac':>9}{'Q':>7}{'k*Q':>7}"
          f"{'eta':>9}{'per pad':>9}   vs {KQ_REQ:.0f}")
    for tr in (0.0, 0.25, 0.50, 0.75, 1.0):
        best = None
        for n_lay in range(1, 21):
            r = analyse(A_OUT, B_OUT, N, W, T_CU, CL, layers=n_lay, gap=GAP,
                        lateral=LAT, transposition=tr)
            if best is None or r["kQ"] > best["kQ"]:
                best = r
        ok = "PASS" if best["kQ"] >= KQ_REQ else "fail"
        print(f"  {tr*100:10.0f}%{best['layers']:8d}{best['r_ac']:8.3f}o{best['Q']:7.0f}"
              f"{best['kQ']:7.1f}{best['eta']*100:8.2f}%{best['loss']/2:8.0f} W   {ok}")

    print("\nACROSS THE SYS-006 ENVELOPE, fully transposed, 16 layers  [ADR-0001]")
    print(f"  {'gap':>7}{'lateral':>9}{'k':>8}{'k*Q':>8}{'per pad':>10}")
    worst = None
    for gap in (8e-3, 10e-3, 14e-3):
        for lat in (0.0, 5e-3):
            r = analyse(A_OUT, B_OUT, N, W, T_CU, CL, layers=16, gap=gap,
                        lateral=lat, transposition=1.0)
            if worst is None or r["kQ"] < worst["kQ"]:
                worst = r
            print(f"  {gap*1e3:6.0f}mm{lat*1e3:8.0f}mm{r['k']:8.3f}{r['kQ']:8.1f}"
                  f"{r['loss']/2:9.0f} W")
    print(f"\n  WORST: k*Q = {worst['kQ']:.1f} ({worst['kQ']/KQ_REQ:.2f}x), "
          f"M = {worst['M']*1e6:.1f} uH, {worst['loss']/2:.0f} W per pad")

    area = A_OUT * B_OUT
    print("\n" + "=" * 78)
    print("THE THERMAL CONSTRAINT IS THE BINDING ONE")
    print("=" * 78)
    print(f"  A flat plate in still air sheds about 150 W/m2 at an acceptable rise.")
    print(f"  This pad is {area*1e4:.0f} cm2, so its own faces shed about "
          f"{150*area:.1f} W.")
    print(f"  It must lose {worst['loss']/2:.0f} W — {worst['loss']/2/(150*area):.0f}x that.")
    print(f"  So every watt leaves through the BRACKET, which needs about")
    print(f"  {worst['loss']/2/150*1e4:.0f} cm2 of external surface = "
          f"{worst['loss']/2/150/area:.0f}x the pad footprint. That is MEC-009.")
    print("\n  Caveat: the 150 W/m2 figure is researched but its verification pass")
    print("  did not run. Confirm against a second source before closing MEC-009.")


if __name__ == "__main__":
    main()
