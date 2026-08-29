"""Concept C — Perimeter nest. The pad drops into a chamfered pocket."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import *
from _common import (coil_pad, housing, electronics, deck_plate,
                     PAD_W, PAD_L, PAD_T, WALL, GAP)

TITLE = "C — Perimeter nest"
NOTES = (
    "The receiver housing drops into a shallow pocket sized to it, with a lead-in "
    "chamfer the whole way round. Nothing protrudes above the deck bracket, so "
    "there is nothing to snag a line or bend in handling, and the full perimeter "
    "carries load and heat. It is the most over-constrained of the three -- the "
    "clearance has to absorb the tolerance stack of the whole pocket, so it "
    "aligns less precisely than either alternative, and it holds silt and water."
)
MATERIAL = "sand"

_base = Pos(0, 0, -9) * deck_plate(PAD_W + 190, PAD_L + 150)
_txh = Pos(0, 0, PAD_T / 2 + 4) * housing()
_tx = Pos(0, 0, PAD_T / 2 + 4) * coil_pad()
_z = PAD_T + WALL * 2 + GAP + 12
_rxh = Pos(0, 0, _z + PAD_T / 2 + 20) * Rot(180, 0, 0) * housing()
_rx = Pos(0, 0, _z + PAD_T / 2 + 20) * Rot(180, 0, 0) * coil_pad()
_iface = Pos(0, 0, _z + PAD_T + 46) * Box(PAD_W + 80, PAD_L + 80, 14)

# the nest: a raised perimeter wall with a chamfered lip
_w, _l = PAD_W + 76, PAD_L + 76
_nest = Box(_w + 40, _l + 40, 96) - Pos(0, 0, 6) * Box(_w, _l, 96)
_nest = fillet(_nest.edges().filter_by(Axis.Z), radius=14)
_nest = Pos(0, 0, 39) * _nest
_lip = Pos(0, 0, 92) * (Box(_w + 40, _l + 40, 22) - Box(_w + 6, _l + 6, 22))
_drain = None
for sx in (-1, 1):
    d = Pos(sx * (_w / 2 + 12), 0, 20) * Rot(0, 90, 0) * Cylinder(9, 44)
    _drain = d if _drain is None else _drain + d
_nest = _nest + _lip - _drain

_elec = Pos(-(_w / 2 + 118), 0, 30) * electronics()
PART = _base + _txh + _tx + _rxh + _rx + _iface + _nest + _elec
