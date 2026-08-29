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

MULTILAYER CAVEAT, and it is the load-bearing one: parallel layers are modelled
as an ideal 1/N reduction in resistance. Real stacked spirals suffer inter-layer
proximity, which a turn-to-turn model cannot capture, so every multilayer Q here
is optimistic. Design to a layer count with margin, and treat the two-layer
column as indicative only.

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
            lateral=0.0, tilt_deg=0.0, t_c=100.0, n_side=40):
    """Full analysis of a rectangular spiral pair."""
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
    r_dc = rho_cu(t_c) * length / (w * t * layers)
    fr, f_c = kuhn_ibrahim(w, clearance, t, t_c=t_c)
    r_ac = r_dc * fr
    q = W0 * L / r_ac
    k = M / L
    return dict(L=L, M=M, k=k, Q=q, kQ=k * q, eta=eta_max(k, q),
                loss=P_TGT * (1.0 - eta_max(k, q)), length=length, pitch=pitch,
                fr=fr, f_crit=f_c, r_dc=r_dc, r_ac=r_ac, n=n, w=w, t=t,
                layers=layers, inner=turns[-1])


def main():
    M_REQ = V_FUND * V_FUND / (P_TGT * W0)
    A_OUT, B_OUT = 0.102, 0.203        # 4.0 x 8.0 inch
    T_CU = 0.140e-3                    # 4 oz
    KQ_REQ = kq_for_eta(1.0 - 120.0 / P_TGT)

    print("=" * 78)
    print("RECTANGULAR PCB COIL — 4 x 8 inch, passive cooling")
    print("=" * 78)
    print(f"Outer {A_OUT*1e3:.0f} x {B_OUT*1e3:.0f} mm, 4 oz copper, {F_NOM/1e3:.0f} kHz, "
          f"20 mm gap")
    print(f"Mutual inductance needed for {P_TGT/1000:.0f} kW at resonance: "
          f"M = {M_REQ*1e6:.1f} uH")
    print(f"MEC-001 requires k*Q >= {KQ_REQ:.0f} (120 W of {P_TGT/1000:.0f} kW)")
    print(f"Skin depth at {F_NOM/1e3:.0f} kHz, 100 C: {skin_depth(t_c=100.0)*1e3:.3f} mm "
          f"-> 4 oz is {T_CU/skin_depth(t_c=100.0):.2f} skin depths\n")

    print("STEP 1 — turns and trace width needed to reach the mutual inductance")
    print(f"  {'turns':>6}{'trace':>8}{'clear':>8}{'L':>9}{'M':>9}{'k':>7}"
          f"{'R_ac/R_dc':>11}{'Q(1 layer)':>12}")
    cands = []
    for n, w, c in ((24, 1.20e-3, 0.30e-3), (28, 1.00e-3, 0.30e-3),
                    (32, 0.80e-3, 0.28e-3), (36, 0.70e-3, 0.25e-3),
                    (40, 0.60e-3, 0.22e-3)):
        r = analyse(A_OUT, B_OUT, n, w, T_CU, c)
        if r is None:
            print(f"  {n:6d}  spiral closes on itself"); continue
        flag = "  <- meets M" if r["M"] >= M_REQ else ""
        print(f"  {n:6d}{w*1e3:7.2f}m{c*1e3:7.2f}m{r['L']*1e6:8.1f}u{r['M']*1e6:8.2f}u"
              f"{r['k']:7.3f}{r['fr']:11.2f}{r['Q']:12.0f}{flag}")
        if r["M"] >= M_REQ:
            cands.append(r)
    print("\n  Fine traces almost eliminate proximity effect: R_ac/R_dc falls to")
    print("  near unity, so the coil becomes a pure DC-resistance problem --")
    print("  which is exactly what parallel layers fix.\n")

    base = cands[0]
    print(f"STEP 2 — layers in parallel, at {base['n']} turns / "
          f"{base['w']*1e3:.2f} mm trace")
    print(f"  {'layers':>7}{'R_ac':>9}{'Q':>7}{'k*Q':>8}{'eta':>9}{'loss':>8}"
          f"{'per pad':>10}")
    chosen = None
    for lay in (1, 2, 4, 6, 8):
        r = analyse(A_OUT, B_OUT, base["n"], base["w"], T_CU, 0.28e-3, layers=lay)
        ok = "  PASS" if r["kQ"] >= KQ_REQ else "  fails"
        print(f"  {lay:7d}{r['r_ac']:8.3f}o{r['Q']:7.0f}{r['kQ']:8.1f}"
              f"{r['eta']*100:8.2f}%{r['loss']:7.0f} W{r['loss']/2:9.0f} W{ok}")
        if chosen is None and r["kQ"] >= KQ_REQ * 1.4:
            chosen = r
    print()

    print("STEP 3 — the chosen design across the SYS-006 misalignment envelope")
    print(f"  {chosen['n']} turns, {chosen['w']*1e3:.2f} mm trace, "
          f"{chosen['layers']} layers in parallel, 4 oz")
    print(f"  {'gap':>7}{'lateral':>9}{'tilt':>7}{'k':>8}{'k*Q':>8}{'loss':>9}")
    worst = None
    for gap in (5e-3, 10e-3, 20e-3):
        for lat in (0.0, 10e-3):
            for tilt in (0.0, 3.0):
                r = analyse(A_OUT, B_OUT, chosen["n"], chosen["w"], T_CU, 0.28e-3,
                            layers=chosen["layers"], gap=gap, lateral=lat,
                            tilt_deg=tilt)
                if worst is None or r["kQ"] < worst["kQ"]:
                    worst = r
                print(f"  {gap*1e3:6.0f}mm{lat*1e3:8.0f}mm{tilt:6.1f}d"
                      f"{r['k']:8.3f}{r['kQ']:8.1f}{r['loss']:8.0f} W")
    print(f"\n  WORST CASE: k = {worst['k']:.3f}, k*Q = {worst['kQ']:.1f}, "
          f"{worst['loss']:.0f} W ({worst['loss']/2:.0f} W per pad)")
    print(f"  Requirement k*Q >= {KQ_REQ:.0f}: "
          f"{'PASS' if worst['kQ'] >= KQ_REQ else 'FAIL'}, "
          f"margin {worst['kQ']/KQ_REQ:.2f}x")

    area = A_OUT * B_OUT
    print(f"\n  HEAT FLUX: {worst['loss']/2:.0f} W over "
          f"{area*1e6:.0f} mm2 = {worst['loss']/2/area:.0f} W/m2")
    print(f"  For scale, the 300 mm circular pad carried "
          f"{764:.0f} W/m2 at the same allowance.")
    print("  The rectangular pad is 3.6x smaller in area, so the same watts are")
    print("  a much harder extraction problem. MEC-004's temperature limit is")
    print("  the binding form, not the per-pad watt allocation.")

    print("\n" + "=" * 78)
    print("STILL OPEN")
    print("=" * 78)
    print("  * Inter-layer proximity. The 1/N layer scaling above is ideal and")
    print("    real stacked spirals do worse. This is now the single largest")
    print("    modelling uncertainty and it decides the layer count.")
    print("  * Ferrite backing, cold-plate eddy loss, seawater in the gap.")
    print("    None modelled, all push the wrong way. FEA task in M2/M3.")
    print("  * Kuhn and Ibrahim is used outside its fitted trace width, though")
    print("    at these fine traces the AC correction is small enough that the")
    print("    error it carries is small too.")


if __name__ == "__main__":
    main()
