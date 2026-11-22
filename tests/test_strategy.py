import pytest

from peck_pilot.features import Hole, MachiningFeature
from peck_pilot.model import BLIND_HOLE, THROUGH_HOLE
from peck_pilot.strategy import BLIND_WARNING, plan


def hole(x=10, y=10, d=6.0, depth=10.0, through=False, top=20.0):
    return MachiningFeature(THROUGH_HOLE if through else BLIND_HOLE, [0], 0.9,
                            Hole(x, y, top, top - depth, d, through))


def drills(ops):
    return [o for o in ops if o.tool.kind == "drill"]


@pytest.mark.parametrize("depth, cycle", [(18.0, "G81"), (18.01, "G83")])
def test_peck_drilling_only_beyond_three_diameters(depth, cycle):
    [op] = drills(plan([hole(d=6.0, depth=depth)]))
    assert op.cycle == cycle
    assert op.peck == (6.0 if cycle == "G83" else None)


@pytest.mark.parametrize("diameter, size", [(6.05, 6.0), (5.95, 6.0), (6.25, None), (1.0, 1.0), (13.05, 13.0)])
def test_drill_selection_at_tolerance_edges(diameter, size):
    f = hole(d=diameter)
    ops = drills(plan([f]))
    if size is None:
        assert ops == [] and f.reason == "no drill within tolerance"
    else:
        assert ops[0].tool.diameter == size and f.reason is None


def test_holes_over_13mm_are_too_large():
    f = hole(d=14.0)
    assert plan([f]) == [] and f.reason == "too large to drill"


@pytest.mark.parametrize("diameter, spot_depth", [(1.5, 0.75), (2.0, 1.0), (8.0, 1.0)])
def test_spot_depth_never_wider_than_the_hole(diameter, spot_depth):
    spot = plan([hole(d=diameter)])[0]
    assert spot.tool.kind == "spot drill" and spot.cycle == "G81"
    assert spot.z == pytest.approx(20.0 - spot_depth)


def test_through_hole_clears_bottom_with_full_diameter():
    [op] = drills(plan([hole(d=10.0, depth=20.0, through=True)]))
    assert op.z == pytest.approx(0 - 1.0 - 3.0)  # bottom - breakthrough - 0.3 x D
    assert op.warning is None


def test_blind_hole_tip_stops_at_floor_and_warns():
    [op] = drills(plan([hole(d=6.0, depth=10.0)]))
    assert op.z == pytest.approx(10.0) and op.warning == BLIND_WARNING


def test_order_spots_first_then_drills_ascending_and_tools_numbered_by_first_use():
    ops = plan([hole(x=50, d=8.0), hole(x=10, d=8.0), hole(x=30, d=4.0)])
    assert [(o.tool.number, o.tool.diameter, o.x) for o in ops] == [
        (1, 6.0, 10), (1, 6.0, 30), (1, 6.0, 50),
        (2, 4.0, 30),
        (3, 8.0, 10), (3, 8.0, 50),
    ]
    assert all(o.r_plane == 22.0 for o in ops)


def test_features_without_a_hole_or_already_unplanned_are_skipped():
    other = MachiningFeature(14, [1], 0.9, reason="no strategy yet")
    side = MachiningFeature(BLIND_HOLE, [2], 0.9, reason="needs another Setup")
    assert plan([other, side]) == []


def test_speeds_are_capped_and_feeds_clamped():
    [op] = drills(plan([hole(d=1.0)]))
    assert op.rpm == 10_000  # 75 m/min on Ø1 would be 23,873 rpm
    assert op.feed == pytest.approx(10_000 * 0.05)  # 0.02 x 1 = 0.02 mm/rev, clamped up to 0.05


@pytest.mark.parametrize("reason, status", [
    (None, "planned"),
    ("no strategy yet", "no strategy yet"),
    ("wrong label?", "unplanned"),
    ("failed geometry check", "unplanned"),
    ("needs another Setup", "unplanned"),
    ("no drill within tolerance", "unplanned"),
    ("too large to drill", "unplanned"),
])
def test_status_follows_reason(reason, status):
    assert MachiningFeature(14, [0], 0.9, reason=reason).status == status


def test_hole_without_a_drill_is_unplanned_after_planning():
    f = hole(d=6.25)
    assert f.status == "planned"
    plan([f])
    assert f.hole is not None and f.status == "unplanned"
