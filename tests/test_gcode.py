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
