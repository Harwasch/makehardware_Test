"""Shared geometry for the Ulysses charging-system concepts.

SCOPE: the charger electronics and a test packaging, per VIS-013. The vehicle
is not modelled and is not ours, and neither is the deck fixture — integration
is the mechanical team's. What we deliver is the two coil pads, their converter
electronics, and a bench rig that holds the pads at the SYS-006 envelope so the
magnetics can be verified. Pads locate on dowel pins (VIS-005).

Dimensions that are REAL, from the analysis:
  * coil pad 102 x 203 mm (4 x 8 inch), customer-fixed
  * pad stack 16 mm: 6-layer PCB (2.4) + ferrite tile (5.0) + cold plate (8.6)
  * coil-to-coil gap 10 mm nominal: 4 mm housing wall each side + 2 mm clearance
"""
from build123d import *

PAD_W, PAD_L = 102.0, 203.0
PCB_T, FERRITE_T, PLATE_T = 2.4, 5.0, 8.6
PAD_T = PCB_T + FERRITE_T + PLATE_T          # 16 mm
WALL = 4.0                                    # housing wall over the coil face
GAP = 10.0                                    # coil to coil, nominal


def coil_pad(turns=12):
    """The pad assembly: spiral, PCB, ferrite tile, cold plate."""
    pcb = Box(PAD_W, PAD_L, PCB_T)
    spiral = None
    for i in range(turns):
        o = i * 3.6
        ring = Box(PAD_W - 14 - 2 * o, PAD_L - 14 - 2 * o, 0.6) - \
               Box(PAD_W - 16.4 - 2 * o, PAD_L - 16.4 - 2 * o, 0.6)
        spiral = ring if spiral is None else spiral + ring
    spiral = Pos(0, 0, PCB_T / 2 + 0.3) * spiral
    ferrite = Pos(0, 0, -(PCB_T + FERRITE_T) / 2) * Box(PAD_W + 10, PAD_L + 10, FERRITE_T)
    plate = Pos(0, 0, -(PCB_T / 2 + FERRITE_T + PLATE_T / 2)) * \
            Box(PAD_W + 26, PAD_L + 26, PLATE_T)
    plate = fillet(plate.edges().filter_by(Axis.Z), radius=8)
    return pcb + spiral + ferrite + plate


def housing(extra_h=0.0):
    """Sealed housing around a pad — the wall over the coil face sets the gap."""
    w, l = PAD_W + 46, PAD_L + 46
    h = PAD_T + WALL + 6 + extra_h
    shell = Box(w, l, h)
    shell = fillet(shell.edges().filter_by(Axis.Z), radius=10)
    shell -= Pos(0, 0, -3) * Box(w - 14, l - 14, h - 8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            shell += Pos(sx * (w / 2 + 9), sy * (l / 2 - 26), -h / 2 + 7) * Box(24, 40, 14)
    return shell


def electronics(w=150, l=210, h=78):
    """The converter enclosure that feeds a pad."""
    e = Box(w, l, h)
    e = fillet(e.edges().filter_by(Axis.Z), radius=9)
    e += Pos(0, 0, h / 2 - 2) * Box(w - 22, l - 22, 4)
    for i in range(6):                      # conduction fins into the mount
        e += Pos(-w / 2 - 5, -l / 2 + 24 + i * 32, 0) * Box(10, 22, h - 12)
    return e


def deck_plate(w, l, t=18.0):
    """A flat mounting plate. Used for the rig's base and platen."""
    p = Box(w, l, t)
    p = fillet(p.edges().filter_by(Axis.Z), radius=12)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p -= Pos(sx * (w / 2 - 26), sy * (l / 2 - 26), 0) * Cylinder(7, t)
    return p



def finned_sink(w, l, base_t=12.0, fin_h=38.0, fin_t=4.0, pitch=13.0):
    """The heat sink a pad conducts into.

    MEC-009 wants at least 12x the pad footprint in external area — 2484 cm2
    against the 207 cm2 pad. A bare plate this size gives nowhere near that, so
    the area has to come from fins. `sink_area_cm2` below reports what the
    geometry actually provides rather than asserting it.
    """
    body = Box(w, l, base_t)
    body = fillet(body.edges().filter_by(Axis.Z), radius=10)
    n = int((w - 20) // pitch)
    x0 = -(n - 1) * pitch / 2
    for i in range(n):
        body += Pos(x0 + i * pitch, 0, -(base_t / 2 + fin_h / 2)) * \
                Box(fin_t, l - 16, fin_h)
    return body


def sink_area_cm2(w, l, base_t=12.0, fin_h=38.0, fin_t=4.0, pitch=13.0):
    """External area of finned_sink, in square centimetres.

    Both faces of every fin, the fin tips, and the base top less the fin roots.
    The base underside is not counted: it is the bonded interface to the pad.
    """
    n = int((w - 20) // pitch)
    fl = l - 16.0
    fins = n * (2 * fin_h * fl + fin_t * fl)
    base = w * l - n * fin_t * fl + 2 * base_t * (w + l)
    return (fins + base) / 100.0


def dowel_pin(d=8.0, h=22.0):
    """A locating dowel. Two of these, one in a hole and one in a slot."""
    return Cylinder(d / 2, h) + Pos(0, 0, h / 2) * Cone(d / 2, d / 2 - 1.2, 2.5)
