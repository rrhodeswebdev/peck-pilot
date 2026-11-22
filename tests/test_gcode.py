import re
from pathlib import Path

from test_features import BLIND_BOTTOM, BLIND_SIDE, BLIND_TOP, DEEP, THROUGH, plate

from peck_pilot import gcode
from peck_pilot.features import find_features
from peck_pilot.strategy import plan

GOLDEN = Path(__file__).parent / "golden" / "plate.nc"


def plate_program():
    rec = plate(THROUGH, BLIND_TOP, BLIND_SIDE, BLIND_BOTTOM, DEEP)
    origin, size = gcode.stock(rec.solid)
    return gcode.generate(plan(find_features(rec)), origin, size, "plate")


def test_plate_matches_golden_program():
    # To accept an intended change: python -c "from tests.test_gcode import *; GOLDEN.write_text(plate_program())"
    assert plate_program() == GOLDEN.read_text()


def test_part_comment_neutralises_hostile_names():
    line = gcode.generate([], (0, 0, 0), (1, 1, 1), name="x) G00 Z-50 (\n%;\u00e9").splitlines()[2]
    assert line == "(PART X_G00_Z-50_)"
    assert re.fullmatch(r"\(PART [A-Z0-9_-]+\)", line)


def test_part_comment_has_a_name_when_nothing_is_left():
    assert gcode.generate([], (0, 0, 0), (1, 1, 1), name="").splitlines()[2] == "(PART UNNAMED)"
    assert gcode.generate([], (0, 0, 0), (1, 1, 1)).splitlines()[2] == "(PART PART)"
