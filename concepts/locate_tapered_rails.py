"""Concept B — Tapered rails. Wide capture, self-centring as it lands."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import *
from _common import (coil_pad, housing, electronics, deck_plate,
                     PAD_W, PAD_L, PAD_T, WALL, GAP)

TITLE = "B — Tapered rails"
NOTES = (
    "Two long tapered rails either side of the pad. The lead-in is wide at the "
    "top and closes to the running fit at the bottom, so a sloppy approach still "
    "lands centred. Capture range is much larger than a kinematic mount and the "
    "contact is a line rather than three points, which carries heat and load far "
    "better. The cost is that a line contact over-constrains: the fit has to be "
    "loose enough for thermal growth, and that looseness is alignment error."
)
MATERIAL = "cobalt"

_base = Pos(0, 0, -9) * deck_plate(PAD_W + 170, PAD_L + 110)
_txh = Pos(0, 0, PAD_T / 2 + 4) * housing()
_tx = Pos(0, 0, PAD_T / 2 + 4) * coil_pad()
_z = PAD_T + WALL * 2 + GAP + 12
_rxh = Pos(0, 0, _z + PAD_T / 2 + 20) * Rot(180, 0, 0) * housing()
_rx = Pos(0, 0, _z + PAD_T / 2 + 20) * Rot(180, 0, 0) * coil_pad()
_iface = Pos(0, 0, _z + PAD_T + 46) * Box(PAD_W + 110, PAD_L + 60, 14)

# tapered rails: a straight lower section with a splayed lead-in above
_rails = None
for sx in (-1, 1):
    lower = Pos(sx * (PAD_W / 2 + 46), 0, 34) * Box(26, PAD_L + 40, 86)
    lead = Pos(sx * (PAD_W / 2 + 62), 0, 106) * Rot(0, sx * -13, 0) * \
           Box(26, PAD_L + 40, 84)
    r = lower + lead
    _rails = r if _rails is None else _rails + r
# end stops set the along-length position
for sy in (-1, 1):
    _rails += Pos(0, sy * (PAD_L / 2 + 34), 40) * Box(PAD_W + 40, 22, 74)

_elec = Pos(-(PAD_W / 2 + 148), 0, 30) * electronics()
PART = _base + _txh + _tx + _rxh + _rx + _iface + _rails + _elec
