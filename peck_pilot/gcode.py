"""Fanuc-style metric G-code from a Machining Strategy. Work origin (G54): top front-left corner of the Stock."""
import re

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

CLEARANCE = 25.0  # mm above the Stock top: G98 initial plane and tool-change height
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]+")


def stock(solid):
    """Stock is the Part's bounding box. Returns (origin, size): origin is the top front-left corner in Part coordinates."""
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(solid, box, False, False)
    (xmin, ymin, zmin), (xmax, ymax, zmax) = box.CornerMin().Coord(), box.CornerMax().Coord()
    return (xmin, ymin, zmax), (xmax - xmin, ymax - ymin, zmax - zmin)


def clean_name(name):
    """Letters, digits, _ and - only: anything else would let a file name close the (PART ...) comment."""
    return _UNSAFE.sub("_", name).upper() or "UNNAMED"


def generate(ops, origin, size, name="part"):
    ox, oy, oz = origin
    lines = ["%", "O1000 (PECK PILOT)", f"(PART {clean_name(name)})",
             f"(STOCK X{size[0]:.3f} Y{size[1]:.3f} Z{size[2]:.3f}, G54 AT TOP FRONT LEFT)",
             "G21 G17 G40 G49 G80 G90"]
    tool = None
    for op in ops:
        if op.tool != tool:
            if tool:
                lines += ["G80", "M09", "M05", "G91 G28 Z0", "G90"]
            tool = op.tool
            lines += [f"(T{tool.number} {tool.kind.upper()} D{tool.diameter:.3f})", f"T{tool.number} M06",
                      f"S{op.rpm} M03", f"G54 G00 X{op.x - ox:.3f} Y{op.y - oy:.3f}",
                      f"G43 H{tool.number} Z{CLEARANCE:.3f} M08"]
        if op.warning:
            lines.append(f"(WARNING: {op.warning.upper()})")
        q = f" Q{op.peck:.3f}" if op.peck else ""
        lines.append(f"G98 {op.cycle} X{op.x - ox:.3f} Y{op.y - oy:.3f} Z{op.z - oz:.3f} R{op.r_plane - oz:.3f}{q} F{op.feed:.1f}")
    if tool:
        lines += ["G80", "M09", "M05", "G91 G28 Z0", "G90"]
    lines += ["M30", "%"]
    return "\n".join(lines) + "\n"
