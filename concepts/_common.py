"""Shared geometry for the Ulysses docking concepts.

Dimensions that are REAL come from the analysis:
  * coil pad 102 x 203 mm (4 x 8 inch), from the house constraint
  * pad stack 16 mm: 6-layer PCB + ferrite tile + cold plate
  * coil-to-coil gap 20 mm maximum, per SYS-006

Dimensions that are PLACEHOLDER: the Mako hull. Its real form factor is not
yet known and is an open question for the vision review. It is drawn as a
1.4 m capsule so the pad has something to sit on at a believable scale.
"""
from build123d import *

PAD_W, PAD_L, PAD_T = 102.0, 203.0, 16.0     # the 4 x 8 inch coil assembly
GAP = 20.0                                    # coil-to-coil, SYS-006 maximum
HULL_D, HULL_L = 300.0, 1400.0                # PLACEHOLDER vehicle


def coil_pad(w=PAD_W, l=PAD_L, t=PAD_T):
    """The coil assembly: PCB, ferrite tile, cold plate, shown as one stack."""
    pcb = Box(w, l, 2.4)
    ferrite = Pos(0, 0, -(2.4 + 5.0) / 2) * Box(w + 8, l + 8, 5.0)
    plate = Pos(0, 0, -(2.4 / 2 + 5.0 + 8.6 / 2)) * Box(w + 20, l + 20, 8.6)
    plate = fillet(plate.edges().filter_by(Axis.Z), radius=6)
    # spiral shown as concentric rectangles so the coil reads as a coil
    turns = None
    for i in range(10):
        o = i * 4.4
        ring = Box(w - 12 - 2 * o, l - 12 - 2 * o, 0.7) - Box(
            w - 15.2 - 2 * o, l - 15.2 - 2 * o, 0.7)
        turns = ring if turns is None else turns + ring
    turns = Pos(0, 0, 1.55) * turns
    return pcb + ferrite + plate + turns


def hull(d=HULL_D, l=HULL_L):
    """PLACEHOLDER Mako hull — a capsule with a tail fin cluster."""
    body = Cylinder(d / 2, l, rotation=(0, 90, 0))
    nose = Pos(l / 2, 0, 0) * Sphere(d / 2)
    tail = Pos(-l / 2, 0, 0) * Sphere(d / 2)
    v = body + nose + tail
    for ang in (0, 90, 180, 270):
        fin = Rot(ang, 0, 0) * Pos(-l / 2 + 90, 0, d / 2 + 55) * Box(200, 8, 150)
        v += fin
    return v


def enclosure(w, l, h):
    """A sealed electronics enclosure."""
    e = Box(w, l, h)
    e = fillet(e.edges().filter_by(Axis.Z), radius=8)
    lid = Pos(0, 0, h / 2 - 1.5) * Box(w - 16, l - 16, 3)
    return e + lid


def strut(a, b, r=14.0):
    """A round structural strut between two points."""
    import math
    ax, ay, az = a
    bx, by, bz = b
    dx, dy, dz = bx - ax, by - ay, bz - az
    ln = math.sqrt(dx * dx + dy * dy + dz * dz)
    s = Cylinder(r, ln)
    pitch = math.degrees(math.acos(max(-1.0, min(1.0, dz / ln))))
    yaw = math.degrees(math.atan2(dy, dx))
    return Pos((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2) * Rot(0, pitch, yaw) * s
