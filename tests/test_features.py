import numpy as np
import pytest
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.GProp import GProp_GProps
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from peck_pilot.features import find_features
from peck_pilot.model import BLIND_HOLE, STOCK, THROUGH_HOLE
from peck_pilot.occ import TopologyExplorer
from peck_pilot.recognition import Recognition

THROUGH = ((20, 20, -1), (0, 0, 1), 4.0, 22)  # Ø8 through, top face
BLIND_TOP = ((50, 30, 10), (0, 0, 1), 3.0, 11)  # Ø6 x 10 deep from the top
BLIND_SIDE = ((-1, 30, 10), (1, 0, 0), 2.5, 16)  # Ø5 x 15 deep from the x=0 side
BLIND_BOTTOM = ((80, 30, -1), (0, 0, 1), 3.0, 6)  # Ø6 x 5 deep from the bottom
DEEP = ((80, 45, -1), (0, 0, 1), 1.5, 22)  # Ø3 through a 20 mm plate: 6.7 x D, so G83
THROUGH_RADII = (4.0, 1.5)  # the "perfect labels" helper calls these cylinders through holes, the rest blind


def plate(*holes, slot=False):
    """100 x 60 x 20 mm plate, top face at z=20, with cylinders cut out. Returns perfectly labeled Recognition.
    slot: a side slot (x<30, 15<y<25, 8<z<12) that cuts across the THROUGH hole's wall."""
    shape = BRepPrimAPI_MakeBox(100, 60, 20).Shape()
    if slot:
        shape = BRepAlgoAPI_Cut(shape, BRepPrimAPI_MakeBox(gp_Pnt(-1, 15, 8), 31, 10, 4).Shape()).Shape()
    for (x, y, z), d, r, h in holes:
        shape = BRepAlgoAPI_Cut(shape, BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z), gp_Dir(*d)), r, h).Shape()).Shape()
    solid = next(iter(TopologyExplorer(shape).solids()))
    faces = list(TopologyExplorer(solid).faces())
    labels = []
    for f in faces:
        s = BRepAdaptor_Surface(f, True)
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(f, props)
        if s.GetType() == GeomAbs_Cylinder:
            labels.append(THROUGH_HOLE if round(s.Cylinder().Radius(), 6) in THROUGH_RADII else BLIND_HOLE)
        else:
            labels.append(BLIND_HOLE if props.Mass() < 30 else STOCK)  # floors are ≤ 28.3 mm²; the slot's end wall is 40
    return Recognition(solid, faces, np.array(labels), np.full(len(faces), 0.9))


def by_label(features, label):
    return [f for f in features if f.label == label]


def test_top_through_hole_is_measured():
    [f] = find_features(plate(THROUGH))
    assert f.label == THROUGH_HOLE and f.reason is None
    assert f.hole.through
    assert (f.hole.x, f.hole.y, f.hole.diameter) == pytest.approx((20, 20, 8))
    assert (f.hole.top_z, f.hole.bottom_z) == pytest.approx((20, 0))


def test_top_blind_hole_includes_floor_and_depth():
    [f] = find_features(plate(BLIND_TOP))
    assert f.reason is None and not f.hole.through
    assert len(f.faces) == 2  # wall + floor
    assert (f.hole.x, f.hole.y, f.hole.diameter) == pytest.approx((50, 30, 6))
    assert (f.hole.top_z, f.hole.bottom_z, f.hole.depth) == pytest.approx((20, 10, 10))


@pytest.mark.parametrize("hole", [BLIND_SIDE, BLIND_BOTTOM])
def test_holes_not_reachable_from_top_need_another_setup(hole):
    [f] = find_features(plate(hole))
    assert f.hole is None and f.reason == "needs another Setup"


def test_blind_hole_floor_is_found_by_geometry_even_if_mislabeled():
    rec = plate(BLIND_TOP)
    rec.labels[[i for i, l in enumerate(rec.labels) if l == BLIND_HOLE and not _is_cyl(rec.faces[i])]] = STOCK
    [f] = find_features(rec)
    assert f.reason is None and f.hole.depth == pytest.approx(10) and len(f.faces) == 2


def test_blind_label_on_an_open_bore_fails_geometry_check():
    rec = plate(THROUGH)
    rec.labels[rec.labels == THROUGH_HOLE] = BLIND_HOLE
    [f] = find_features(rec)
    assert f.reason == "failed geometry check"


def test_counterbore_ledge_is_the_floor_of_the_wide_hole_only():
    rec = plate(((20, 20, -1), (0, 0, 1), 2.0, 22), ((20, 20, 15), (0, 0, 1), 3.0, 6))  # Ø4 through, Ø6 x 5 deep
    rec.labels[[i for i, f in enumerate(rec.faces) if _is_cyl(f) and BRepAdaptor_Surface(f, True).Cylinder().Radius() < 2.5]] = THROUGH_HOLE
    holes = sorted((f for f in find_features(rec) if f.label in (THROUGH_HOLE, BLIND_HOLE)), key=lambda f: f.hole.diameter)
    assert [(h.hole.diameter, h.hole.through, h.hole.bottom_z) for h in holes] == pytest.approx([(4, True, 0), (6, False, 15)])


def test_through_hole_with_a_floor_is_not_drilled_through():
    rec = plate(BLIND_TOP)
    rec.labels[rec.labels == BLIND_HOLE] = THROUGH_HOLE  # MFCAD++ 10354 has a capped "through hole" like this
    [f] = find_features(rec)
    assert f.hole is None and f.reason == "failed geometry check" and len(f.faces) == 2


def test_bore_with_wrong_label_is_flagged_for_review():
    rec = plate(THROUGH)
    rec.labels[rec.labels == THROUGH_HOLE] = 14  # rectangular pocket
    [f] = find_features(rec)
    assert f.label == 14 and f.reason == "wrong label?"


def test_hole_split_by_a_slot_is_one_feature():
    rec = plate(THROUGH, slot=True)
    [hole] = by_label(find_features(rec), THROUGH_HOLE)
    assert len(hole.faces) == 2  # wall pieces above and below the slot don't touch
    assert hole.reason is None and (hole.hole.top_z, hole.hole.bottom_z) == pytest.approx((20, 0))


def test_split_hole_with_conflicting_labels_fails_geometry_check():
    rec = plate(THROUGH, slot=True)
    rec.labels[np.flatnonzero(rec.labels == THROUGH_HOLE)[0]] = BLIND_HOLE
    [f] = [f for f in find_features(rec) if f.label in (THROUGH_HOLE, BLIND_HOLE)]
    assert f.reason == "failed geometry check" and len(f.faces) == 2


def test_mixed_plate_reports_every_feature_once():
    features = find_features(plate(THROUGH, BLIND_TOP, BLIND_SIDE, BLIND_BOTTOM))
    planned = [f for f in features if f.reason is None]
    assert sorted((f.hole.x, f.hole.y) for f in planned) == [(20, 20), (50, 30)]
    assert len(by_label(features, BLIND_HOLE)) == 3
    face_ids = [i for f in features for i in f.faces]
    assert len(face_ids) == len(set(face_ids))


def _is_cyl(face):
    return BRepAdaptor_Surface(face, True).GetType() == GeomAbs_Cylinder
