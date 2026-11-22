"""pythonocc's TopologyExplorer, rebuilt on OCP (cadquery-ocp) for the parts this project uses.

Same order and de-duplication as pythonocc: each sub-shape once regardless of orientation, first-explored instance
kept. faces_from_edge returns the same Python objects that faces() returns, in face order.
"""
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_IndexedMapOfShape

HASH_MAX = 2**31 - 1  # pythonocc's TopoDS_Shape.__hash__ was HashCode(this); OCP hashes by Python identity

_CAST = {TopAbs_SOLID: TopoDS.Solid_s, TopAbs_FACE: TopoDS.Face_s, TopAbs_EDGE: TopoDS.Edge_s,
         TopAbs_VERTEX: TopoDS.Vertex_s}


def _map(shape, kind):
    m = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, m)
    return m


class TopologyExplorer:
    def __init__(self, shape):
        self.shape = shape
        self._faces = None
        self._face_map = None
        self._edge_faces = None

    def _unique(self, kind):
        m = _map(self.shape, kind)
        return [_CAST[kind](m.FindKey(i)) for i in range(1, m.Extent() + 1)]

    def solids(self):
        return self._unique(TopAbs_SOLID)

    def faces(self):
        if self._faces is None:
            self._face_map = _map(self.shape, TopAbs_FACE)
            self._faces = [TopoDS.Face_s(self._face_map.FindKey(i)) for i in range(1, self._face_map.Extent() + 1)]
        return list(self._faces)

    def edges(self):
        return self._unique(TopAbs_EDGE)

    def vertices(self):
        return self._unique(TopAbs_VERTEX)

    def faces_from_edge(self, edge):
        faces = self.faces()
        if self._edge_faces is None:
            self._edge_faces = TopTools_IndexedDataMapOfShapeListOfShape()
            TopExp.MapShapesAndAncestors_s(self.shape, TopAbs_EDGE, TopAbs_FACE, self._edge_faces)
        lst = self._edge_faces.FindFromKey(edge)
        n = lst.Size()
        if 1 <= n <= 2:  # iterating the OCP list from Python is slow; First/Last read it directly
            ids = [self._face_map.FindIndex(lst.First()) - 1]
            if n == 2:
                j = self._face_map.FindIndex(lst.Last()) - 1
                if j != ids[0]:  # a seam edge lists its Face twice
                    ids.append(j)
        else:  # no Face, or non-manifold input where more than two Faces share the edge
            ids = []
            for f in lst:
                i = self._face_map.FindIndex(f) - 1
                if i not in ids:
                    ids.append(i)
        return [faces[i] for i in ids]
