"""Concept A — Cone, vee and flat. Kinematic, deterministic, repeatable."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import *
from _common import (coil_pad, housing, electronics, deck_plate,
                     PAD_W, PAD_L, PAD_T, WALL, GAP)

TITLE = "A — Cone, vee and flat"
NOTES = (
    "Three hardened pins on the bracket: one lands in a cone, one in a vee, one "
    "on a flat. That constrains exactly six degrees of freedom with no "
    "over-constraint, so the pad lands in the same place every time and thermal "
    "growth does not fight it. Standard metrology practice. Repeatability is the "
    "best of the three and the contact is three small points, which is also the "
    "drawback -- point contacts carry no heat and take the whole landing load."
)
MATERIAL = "steel"

_base = Pos(0, 0, -9) * deck_plate(PAD_W + 150, PAD_L + 120)
_txh = Pos(0, 0, PAD_T / 2 + 4) * housing()
_tx = Pos(0, 0, PAD_T / 2 + 4) * coil_pad()
_z = PAD_T + WALL * 2 + GAP + 12
_rxh = Pos(0, 0, _z + PAD_T / 2 + 20) * Rot(180, 0, 0) * housing()
_rx = Pos(0, 0, _z + PAD_T / 2 + 20) * Rot(180, 0, 0) * coil_pad()
_iface = Pos(0, 0, _z + PAD_T + 46) * Box(PAD_W + 90, PAD_L + 70, 14)

# the three kinematic features
_feat = None
_pts = [(-(PAD_W / 2 + 52), -(PAD_L / 2 - 10)), ((PAD_W / 2 + 52), -(PAD_L / 2 - 10)),
        (0, (PAD_L / 2 + 40))]
for i, (x, y) in enumerate(_pts):
    post = Pos(x, y, 14) * Cylinder(16, 46)
    ball = Pos(x, y, 40) * Sphere(15)
    seat = Pos(x, y, _z + PAD_T + 30) * Cone(22, 6, 20)
    f = post + ball + seat
    _feat = f if _feat is None else _feat + f

_elec = Pos(-(PAD_W / 2 + 128), 0, 30) * electronics()
PART = _base + _txh + _tx + _rxh + _rx + _iface + _feat + _elec
