"""Group labeled Faces into Machining Features and measure holes from the B-rep (ADR 0001: no geometry from the model)."""
import math
from dataclasses import dataclass

import numpy as np
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepTools import breptools_UVBounds
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.TopAbs import TopAbs_REVERSED
from OCC.Core.TopTools import TopTools_IndexedMapOfShape
from OCC.Core.gp import gp_Pnt, gp_Vec
from OCC.Extend.TopologyUtils import TopologyExplorer

from peck_pilot.model import BLIND_HOLE, THROUGH_HOLE

STOCK = 24
O_RING = 11
HOLE_LABELS = (THROUGH_HOLE, BLIND_HOLE)
TOL = 1e-3  # mm: coaxial distance, radius match, floor position


@dataclass
class Hole:
    x: float
    y: float
    top_z: float
    bottom_z: float
    diameter: float
    through: bool

    @property
    def depth(self):
        return self.top_z - self.bottom_z


@dataclass
class MachiningFeature:
    label: int
    faces: list  # Face indices into Recognition.faces
    confidence: float  # lowest Face confidence in the group
    hole: Hole = None  # set only for a top-face hole ready for a Machining Strategy
    reason: str = None  # why no Strategy: "no strategy yet" or an Unplanned Feature reason


def _cylinder(face):
    s = BRepAdaptor_Surface(face, True)
    return s.Cylinder() if s.GetType() == GeomAbs_Cylinder else None


def _is_plane(face):
    return BRepAdaptor_Surface(face, True).GetType() == GeomAbs_Plane


def _vertices(face):
    return np.array([BRep_Tool.Pnt(v).Coord() for v in TopologyExplorer(face).vertices()])


def _axis(cyl):
    ax = cyl.Axis()
    return np.array(ax.Location().Coord()), np.array(ax.Direction().Coord()), cyl.Radius()


def _coaxial(a, b):
    (pa, da, ra), (pb, db, rb) = a, b
    if abs(abs(da @ db) - 1) > 1e-6 or abs(ra - rb) > TOL:
        return False
    off = pb - pa
    return np.linalg.norm(off - (off @ da) * da) < TOL


def _is_full_internal_cylinder(face, cyl):
    """A whole bore: 360° of cylinder with material outside it. What a hole looks like whatever its label."""
    umin, umax, vmin, vmax = breptools_UVBounds(face)
    if umax - umin < 2 * math.pi - 1e-6:
        return False
    s = BRepAdaptor_Surface(face, True)
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    s.D1(umin, (vmin + vmax) / 2, p, du, dv)
    normal = np.array(du.Crossed(dv).Coord()) * (-1 if face.Orientation() == TopAbs_REVERSED else 1)
    loc, d, _ = _axis(cyl)
    off = np.array(p.Coord()) - loc
    radial = off - (off @ d) * d
    return normal @ radial < 0


def _adjacency(rec):
    index = TopTools_IndexedMapOfShape()
    for f in rec.faces:
        index.Add(f)
    topo = TopologyExplorer(rec.solid)
    pairs = set()
    for edge in topo.edges():
        ids = sorted({index.FindIndex(f) - 1 for f in topo.faces_from_edge(edge)})
        pairs.update((a, b) for i, a in enumerate(ids) for b in ids[i + 1:])
    neighbours = {i: set() for i in range(len(rec.faces))}
    for a, b in pairs:
        neighbours[a].add(b)
        neighbours[b].add(a)
    return neighbours


def _end_caps(rec, neighbours, cyl_ids, loc, d, r, tmin, tmax):
    """Faces closing either end of the bore, judged by geometry alone so a mislabeled cap still stops a drill-through.
    A cap is planar, square to the axis, at tmin or tmax, and inside the bore's radius: that rules out the face the
    hole opens from (it surrounds the bore) and a counterbore ledge seen from the narrower hole."""
    low, high = [], []
    for n in {n for i in cyl_ids for n in neighbours[i]} - set(cyl_ids):
        face = rec.faces[n]
        if not _is_plane(face):
            continue
        normal = np.array(BRepAdaptor_Surface(face, True).Plane().Axis().Direction().Coord())
        v = _vertices(face) - loc
        tp = v @ d
        if abs(abs(normal @ d) - 1) > 1e-6 or np.any(np.linalg.norm(v - np.outer(tp, d), axis=1) > r + TOL):
            continue
        if np.all(abs(tp - tmin) < TOL):
            low.append(n)
        elif np.all(abs(tp - tmax) < TOL):
            high.append(n)
    return low, high


def _measure(label, loc, d, r, tmin, tmax, low, high):
    """Hole geometry, or the Unplanned Feature reason it can't be planned."""
    if label == BLIND_HOLE and bool(low) != bool(high):
        opens = 1 if low else -1  # floor at the low end: opens toward +d
    elif label == THROUGH_HOLE and not (low or high):
        opens = 0  # through: opens both ways
    else:
        return None, "failed geometry check"  # blind without one floor, or "through" but capped
    if abs(abs(d[2]) - 1) > 1e-6 or (opens and opens * d[2] < 0):
        return None, "needs another Setup"
    # shortcut: no check for material overhanging the hole opening; MFCAD++ Parts are prismatic.
    ends = sorted([(loc + tmin * d)[2], (loc + tmax * d)[2]])
    return Hole(x=loc[0], y=loc[1], top_z=ends[1], bottom_z=ends[0], diameter=2 * r,
                through=label == THROUGH_HOLE), None


def find_features(rec):
    neighbours = _adjacency(rec)
    labels = [int(l) for l in rec.labels]
    cyls = [_cylinder(f) for f in rec.faces]
    features, used = [], set()

    def add(label, ids, hole=None, reason=None):
        used.update(ids)
        features.append(MachiningFeature(label, sorted(ids), float(min(rec.confidences[i] for i in ids)), hole, reason))

    # Holes: cluster hole-labeled cylinders by axis and radius, since one hole cut by another feature
    # can be several partial Faces that don't touch.
    clusters = []
    for i, c in enumerate(cyls):
        if c is None or labels[i] not in HOLE_LABELS:
            continue
        for cl in clusters:
            if _coaxial(_axis(cyls[cl[0]]), _axis(c)):
                cl.append(i)
                break
        else:
            clusters.append([i])
    for cl in clusters:
        cl_labels = {labels[i] for i in cl}
        loc, d, r = _axis(cyls[cl[0]])
        t = (np.concatenate([_vertices(rec.faces[i]) for i in cl]) - loc) @ d
        low, high = _end_caps(rec, neighbours, cl, loc, d, r, t.min(), t.max())
        ids = cl + sorted(set(low + high) - used)
        if len(cl_labels) > 1:
            add(min(cl_labels), ids, reason="failed geometry check")
            continue
        label = cl_labels.pop()
        hole, reason = _measure(label, loc, d, r, t.min(), t.max(), low, high)
        add(label, ids, hole, reason)

    # A whole bore the model labeled as something else.
    # shortcut: O-ring outer walls are also full internal cylinders, so they're exempt; revisit for real Parts.
    for i, c in enumerate(cyls):
        if i not in used and c is not None and labels[i] not in HOLE_LABELS + (O_RING, STOCK) \
                and _is_full_internal_cylinder(rec.faces[i], c):
            add(labels[i], [i], reason="wrong label?")

    # Everything else: touching Faces with the same label.
    for start in range(len(rec.faces)):
        if start in used or labels[start] == STOCK:
            continue
        group, stack = set(), [start]
        while stack:
            i = stack.pop()
            if i in group or i in used:
                continue
            group.add(i)
            stack.extend(n for n in neighbours[i] if labels[n] == labels[start])
        label = labels[start]
        add(label, group, reason="failed geometry check" if label in HOLE_LABELS else "no strategy yet")

    return features
