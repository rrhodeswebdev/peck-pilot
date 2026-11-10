# 04 G-code generation

Status: ready-for-human
Blocked by: 03

Spec: G-code.

## What
Generate Fanuc-style metric G-code from a Machining Strategy. The work origin is the top front-left corner of the Stock.

## Acceptance
- A golden test: a fixed Part produces byte-identical G-code to a checked-in expected file.
- The output loads in NCViewer without errors. This is a manual check, noted in the issue when done.

## Comments

**2026-11-10:** Code done.
- Added `peck_pilot/gcode.py`, plus the golden test `tests/test_gcode.py` with expected output in `tests/golden/plate.nc`. All values were hand-checked:
  - Ø3 through: G83, Q3, Z-21.9
  - Ø8 through: Z-23.4
  - Ø6 blind: Z-10 with the warning
  - spot drills at Z-1
  - side and bottom holes absent
- **Remaining (human):** load `tests/golden/plate.nc` into ncviewer.com and confirm the paths land on the holes. Then set Status to resolved.
