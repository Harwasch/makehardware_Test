"""Concept B — Flank dock. The Mako comes alongside a vertical face."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build123d import *
from _common import (coil_pad, hull, enclosure, strut,
                     PAD_W, PAD_L, PAD_T, GAP, HULL_D, HULL_L)

TITLE = "B — Flank dock"
NOTES = (
    "The Mako holds station alongside a vertical dock face and a light clamp "
    "pulls it in. Both pads are vertical, the RX pad let into the flank. The "
    "pads stay clear of silt and are reachable for service without lifting the "
    "vehicle. It needs an active clamp to hold the gap, and the vehicle has to "
    "hold attitude while it docks — the coil sees the most misalignment of the "
    "three."
)
MATERIAL = "cobalt"

_veh = Pos(0, PAD_T + GAP + HULL_D / 2, 0) * hull()
_rx = Rot(90, 0, 0) * Pos(0, 0, -(PAD_T + GAP + 4)) * coil_pad()
_tx = Rot(-90, 0, 0) * Pos(0, 0, -PAD_T) * coil_pad()

# dock face: a plate on legs, with a clamp arm reaching over the hull
_face = Pos(0, -30, 0) * Box(420, 44, 700)
_face = fillet(_face.edges().filter_by(Axis.Y), radius=10)
for sx in (-1, 1):
    _face += Pos(sx * 175, -30, -430) * Box(50, 44, 180)
_face += Pos(0, -30, -520) * Box(460, 320, 40)

_arm = strut((0, -8, 300), (0, 250, 330), r=18)
_pinch = Pos(0, 300, 330) * Rot(0, 90, 0) * Cylinder(46, 190)

_enc = Pos(0, -110, -300) * enclosure(320, 140, 260)

PART = _veh + _rx + _tx + _face + _arm + _pinch + _enc
