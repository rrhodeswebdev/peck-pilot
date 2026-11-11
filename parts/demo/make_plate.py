"""Build parts/demo/mounting_plate.step: a plate whose holes all use standard drill sizes and open from the top,
so every hole should be planned. Usage: uv run parts/demo/make_plate.py"""
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

L, W, T = 100, 60, 15  # mm; top face at z = T
HOLES = [  # (x, y, diameter, depth or None for through)
    *[(x, y, 6.5, None) for x in (10, 90) for y in (10, 50)],  # 4 x Ø6.5 through: mounting bolts
    (35, 30, 8.0, 10), (65, 30, 8.0, 10),  # 2 x Ø8 blind, 10 deep: dowel pins
    (50, 45, 4.0, 6),  # Ø4 blind, 6 deep
    (50, 15, 3.0, None), (25, 45, 3.0, None),  # 2 x Ø3 through: 5 x D deep, so G83
]

shape = BRepPrimAPI_MakeBox(L, W, T).Shape()
for x, y, d, depth in HOLES:
    z0, h = (-1, T + 2) if depth is None else (T - depth, depth + 1)
    tool = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1)), d / 2, h).Shape()
    shape = BRepAlgoAPI_Cut(shape, tool).Shape()

writer = STEPControl_Writer()
writer.Transfer(shape, STEPControl_AsIs)
writer.Write(str(Path(__file__).with_name("mounting_plate.step")))
