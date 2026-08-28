"""Concept B — Litz coil pad. Same footprint, wound conductor instead of etched.

A 27-turn Litz spiral laid into a moulded former, over the same ferrite ring and
the same cold plate. Roughly an order of magnitude more Q than the etched
spiral, which is what moves coil-to-coil efficiency from 87% to 97-99%.

The cost is that the winding is a separate manufacturing operation with its own
tolerance, and the pad is thicker.
"""
from build123d import *

TITLE = "B — Litz coil pad"
NOTES = (
    "27 turns of 2000/40 Litz in a moulded former, 300 mm outer diameter. "
    "Q ~ 150-300 at 85 kHz, so 97-99% coil-to-coil and only ~45 W per pad to "
    "remove. Thicker, and the winding is its own process with its own "
    "tolerance -- which is exactly what the v1 white paper chose PCB to avoid."
)
MATERIAL = "cobalt"

R_OUT, R_IN = 150.0, 50.0
D_LITZ = 3.2          # Litz bundle outside diameter
T_FORMER = 6.0        # moulded glass-filled former
T_FERRITE = 5.0
T_PLATE = 8.0
R_PLATE = 170.0
N_TURNS = 27

# --- former with a spiral groove --------------------------------------------
_former = Cylinder(R_OUT + 6, T_FORMER) - Cylinder(R_IN - 6, T_FORMER)

# --- the winding itself: 27 turns of round bundle ----------------------------
_pitch = (R_OUT - R_IN) / N_TURNS
_wind = None
for i in range(N_TURNS):
    r = R_IN + (i + 0.5) * _pitch
    turn = Cylinder(r + D_LITZ / 2, D_LITZ) - Cylinder(r - D_LITZ / 2, D_LITZ)
    _wind = turn if _wind is None else _wind + turn
_wind = Pos(0, 0, (T_FORMER + D_LITZ) / 2 - 1.0) * _wind

# --- ferrite ring, same as concept A -----------------------------------------
_ferrite = Cylinder(R_OUT + 5, T_FERRITE) - Cylinder(R_IN - 5, T_FERRITE)
for i in range(12):
    _ferrite -= Rot(0, 0, i * 30) * Pos(0, (R_OUT + R_IN) / 2, 0) * Box(
        2.0, R_OUT - R_IN + 20, T_FERRITE
    )
_ferrite = Pos(0, 0, -(T_FORMER + T_FERRITE) / 2) * _ferrite

# --- same cold plate ----------------------------------------------------------
_plate = Cylinder(R_PLATE, T_PLATE)
for i in range(6):
    _plate -= Rot(0, 0, i * 60) * Pos(0, R_PLATE - 12, 0) * Cylinder(4.2, T_PLATE)
_plate = Pos(0, 0, -(T_FORMER / 2 + T_FERRITE + T_PLATE / 2)) * _plate

PART = _former + _wind + _ferrite + _plate
