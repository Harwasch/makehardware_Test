"""Concept A — PCB coil pad. The v1 approach, scaled to the inductance 3 kW needs.

Flat multi-layer PCB spiral over a ferrite tile ring, bonded to an aluminium
cold plate that bolts to the chassis. Everything is one rigid stack, which is
what makes it cheap and repeatable.

Geometry follows from the link budget (sim/link-budget/link_budget.py): 162 uH
at k = 0.5, which the modified Wheeler formula puts at ~27 turns over a
100 mm-350 mm outer / 100 mm inner diameter spiral.
"""
from build123d import *

TITLE = "A — PCB coil pad"
NOTES = (
    "27-turn spiral etched on 4 layers in parallel, 300 mm outer diameter. "
    "Q ~ 29 at 85 kHz, so ~87% coil-to-coil and ~191 W to get out of each pad "
    "through the ferrite and into the cold plate. Cheap, flat and repeatable; "
    "the thermal path is the whole problem."
)
MATERIAL = "graphite"

R_OUT, R_IN = 150.0, 50.0
T_PCB = 3.2          # 4-layer 2 oz stack
T_FERRITE = 5.0      # sintered MnZn tiles
T_PLATE = 8.0        # aluminium cold plate
R_PLATE = 170.0
N_TURNS = 27

# --- coil board, with the spiral shown as concentric rings ------------------
_board = Cylinder(R_OUT, T_PCB) - Cylinder(R_IN, T_PCB)

_pitch = (R_OUT - R_IN) / N_TURNS
_trace_w = _pitch * 0.6
_traces = None
for i in range(N_TURNS):
    r = R_IN + (i + 0.5) * _pitch
    ring = Cylinder(r + _trace_w / 2, 0.7) - Cylinder(r - _trace_w / 2, 0.7)
    _traces = ring if _traces is None else _traces + ring
_traces = Pos(0, 0, T_PCB / 2 + 0.35) * _traces

# --- ferrite tile ring, split into 12 segments so the gaps are visible ------
_ferrite = Cylinder(R_OUT + 5, T_FERRITE) - Cylinder(R_IN - 5, T_FERRITE)
for i in range(12):
    _ferrite -= Rot(0, 0, i * 30) * Pos(0, (R_OUT + R_IN) / 2, 0) * Box(
        2.0, R_OUT - R_IN + 20, T_FERRITE
    )
_ferrite = Pos(0, 0, -(T_PCB + T_FERRITE) / 2) * _ferrite

# --- aluminium cold plate, bolted to chassis at six points ------------------
_plate = Cylinder(R_PLATE, T_PLATE)
for i in range(6):
    _plate -= Rot(0, 0, i * 60) * Pos(0, R_PLATE - 12, 0) * Cylinder(4.2, T_PLATE)
_plate = Pos(0, 0, -(T_PCB / 2 + T_FERRITE + T_PLATE / 2)) * _plate

PART = _board + _traces + _ferrite + _plate
