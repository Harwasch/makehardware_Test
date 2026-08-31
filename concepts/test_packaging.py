"""The test packaging — a bench rig that holds the coil pair at the SYS-006 envelope.

This is what VIS-013 puts in scope on the mechanical side. It is test equipment,
not a prototype of the deck fixture: it is not marine, not recoverable and not
handled. What it has to do is set a gap and an offset and hold them while the
magnetics are measured, and cool the pads while it does.

Per MEC-010 each pad lands on two dowels in a hole-and-slot pattern, which fixes
six degrees of freedom without fighting the pin spacing. The gap is set by a
shim stack under the upper platen, because a shim stack is measurable with the
same gauge that verifies it.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import *
from _common import (coil_pad, housing, electronics, deck_plate, finned_sink,
                     sink_area_cm2, dowel_pin, PAD_W, PAD_L, PAD_T, WALL, GAP)

TITLE = "Test packaging — pin-located, shim-set gap"
MATERIAL = "steel"          # render colour only; the rig is aluminium

SINK_W, SINK_L = 340.0, 380.0
PIN_DX, PIN_DY = PAD_W / 2 + 34.0, PAD_L / 2 - 18.0
SHIM = 6.0                                    # stack that sets the gap

_area = sink_area_cm2(SINK_W, SINK_L)
_pad_cm2 = PAD_W * PAD_L / 100.0

NOTES = (
    "A bench rig, not a fixture prototype. Each pad sits on two 8 mm dowels in a "
    "hole-and-slot pattern (MEC-010) so it lands in the same place every time "
    "without the pin spacing fighting the holes. The upper platen carries the RX "
    "pad face-down; the coil-to-coil gap is set by the shim stack under the four "
    "columns and read with the same gauge that verifies it, which is what "
    "SYS-017 needs to hold 8-14 mm to 0.5 mm. Lateral offset to 5 mm and tilt to "
    "2 degrees come from shimming one column pair against the other. "
    f"Each pad conducts into a {SINK_W:.0f} x {SINK_L:.0f} mm finned sink giving "
    f"{_area:,.0f} cm2 against the {_pad_cm2:.0f} cm2 pad -- {_area / _pad_cm2:.0f} "
    "times the footprint where MEC-009 asks for 12. That margin is deliberate and "
    "should NOT be read as the thermal case being closed: MEC-009's 12x is a "
    "flat-plate-equivalent figure at 150 W/m2, and a finned surface does not "
    "convect per unit area the way a flat plate does. Fin efficiency and channel "
    "convection are still owed by the thermal chunk. The rig stands on four "
    "feet that lift the lower sink clear of the bench, so its fins see air."
)

# ---- lower half: TX pad on its sink -------------------------------------
_sink_b = Pos(0, 0, -(PAD_T / 2 + 6)) * finned_sink(SINK_W, SINK_L)
_txh = housing()
_tx = coil_pad()
_pins_b = None
for sx in (-1, 1):
    p = Pos(sx * PIN_DX, -PIN_DY if sx < 0 else PIN_DY, PAD_T / 2 + 5) * dowel_pin()
    _pins_b = p if _pins_b is None else _pins_b + p

# ---- feet, so the rig does not stand on its own fins ---------------------
_FIN_DROP = 12.0 + 38.0                       # sink base + fin height
_FOOT_H = 26.0
_feet = None
for sx in (-1, 1):
    for sy in (-1, 1):
        f = Pos(sx * (SINK_W / 2 - 24), sy * (SINK_L / 2 - 24),
                -(PAD_T / 2 + 6 + _FIN_DROP + _FOOT_H / 2)) * Cylinder(17, _FOOT_H)
        _feet = f if _feet is None else _feet + f
_rail = Pos(0, 0, -(PAD_T / 2 + 6 + _FIN_DROP + _FOOT_H - 7)) * \
        Box(SINK_W - 30, SINK_L - 30, 14)
_feet += _rail

# ---- the four columns and the shim stack --------------------------------
_z = PAD_T + WALL * 2 + GAP                   # coil face to coil face
_col_h = _z + 54
_cols = None
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = sx * (SINK_W / 2 - 24), sy * (SINK_L / 2 - 24)
        c = Pos(x, y, _col_h / 2 - PAD_T / 2) * Cylinder(15, _col_h)
        shim = Pos(x, y, _col_h - PAD_T / 2 + SHIM / 2) * Cylinder(19, SHIM)
        _cols = (c + shim) if _cols is None else _cols + c + shim

# ---- upper half: platen, RX pad face-down, its own sink ------------------
_top = _col_h - PAD_T / 2 + SHIM
_platen = Pos(0, 0, _top + 9) * deck_plate(SINK_W + 30, SINK_L + 30)
_sink_t = Pos(0, 0, _top + 18 + PAD_T / 2 + 6) * Rot(180, 0, 0) * \
          finned_sink(SINK_W, SINK_L)
_rx_z = _top + 18 + PAD_T / 2 + 6
_rxh = Pos(0, 0, _rx_z) * Rot(180, 0, 0) * housing()
_rx = Pos(0, 0, _rx_z) * Rot(180, 0, 0) * coil_pad()
_pins_t = None
for sx in (-1, 1):
    p = Pos(sx * PIN_DX, -PIN_DY if sx < 0 else PIN_DY, _rx_z - PAD_T / 2 - 5) * \
        Rot(180, 0, 0) * dowel_pin()
    _pins_t = p if _pins_t is None else _pins_t + p

# ---- the electronics either side ----------------------------------------
_e_tx = Pos(-(SINK_W / 2 + 96), -70, 30) * electronics()
_e_rx = Pos((SINK_W / 2 + 96), 70, _top) * electronics()

PART = (_feet + _sink_b + _txh + _tx + _pins_b + _cols + _platen +
        _sink_t + _rxh + _rx + _pins_t + _e_tx + _e_rx)
