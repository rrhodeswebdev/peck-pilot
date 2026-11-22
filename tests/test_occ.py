import pytest
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_IndexedMapOfShape

from peck_pilot.api import PARTS_DIR, bundled_parts
from peck_pilot.occ import TopologyExplorer


def check_faces_from_edge(part):
    """Compare faces_from_edge on every edge of a bundled Part with the old method, iterating the OCP Face list.

    Returns the number of seam edges seen: a list of two entries that names one Face twice.
    """
    reader = STEPControl_Reader()
    reader.ReadFile(str(PARTS_DIR / part))
    reader.TransferRoots()
    solid = TopologyExplorer(reader.OneShape()).solids()[0]
    topo = TopologyExplorer(solid)
    faces = topo.faces()
    face_map = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(solid, TopAbs_FACE, face_map)
    edge_faces = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid, TopAbs_EDGE, TopAbs_FACE, edge_faces)
    seams = 0
    for edge in topo.edges():
        lst = edge_faces.FindFromKey(edge)
        ids = []
        for f in lst:
            i = face_map.FindIndex(f) - 1
            if i not in ids:
                ids.append(i)
        want = [faces[i] for i in ids]
        got = topo.faces_from_edge(edge)
        assert len(got) == len(want)
        assert all(a is b for a, b in zip(got, want))
        if lst.Size() == 2 and len(got) == 1:
            seams += 1
    return seams


@pytest.mark.parametrize("part", bundled_parts())
def test_faces_from_edge_matches_iterating_the_list(part):
    check_faces_from_edge(part)


def test_seam_edges_list_their_face_once():
    assert sum(check_faces_from_edge(p) for p in bundled_parts()) > 0
