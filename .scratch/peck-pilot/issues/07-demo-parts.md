# 07 Demo Parts

Status: ready-for-human
Blocked by: none

Spec: Demo Parts.

## What
Model three Parts in Onshape and export them as STEP:
1. a plate with through and blind holes, expected to work
2. a deep hole that triggers G83
3. a Part designed to fail, such as a hole on a side face or overlapping holes

### Modeling guide (Onshape)

In every Part, sketch the base on the **Top** plane and extrude **up** (+Z), so the top face faces +Z. Use millimetres. Make each one a single Part, and export it with right-click Part → Export → STEP. Put the files in `~/Downloads`.

1. **`plate.step`, expected to work.** A 100 × 60 × 15 mm plate.
   - 4 × Ø6.5 through holes, 10 mm in from each corner
   - 2 × Ø8 blind holes, 10 mm deep, at (35, 30) and (65, 30)
   - 1 × Ø4 blind hole, 6 mm deep, at (50, 45)
   - Expect 7 planned holes, the blind-hole warning on 3 of them, and G81 only.
2. **`deep.step`, triggers G83.** A 40 × 40 × 50 mm block.
   - Ø5 through hole at the center, 50 deep, which is more than 3 × D
   - Ø8 blind hole, 30 mm deep, at (10, 10)
   - Expect both holes to use G83, with Q equal to D.
3. **`breaker.step`, designed to fail.** An 80 × 50 × 30 mm block.
   - Ø6 hole drilled from the front face (the −Y side) into the block, 20 mm deep: should give `needs another Setup`
   - Ø6.6 through hole from the top: should give `no drill within tolerance`
   - Ø20 through hole from the top: should give `too large to drill`, unless the model calls it something else
   - Ø6.5 hole with a Ø11 × 6.5 mm counterbore (Onshape Hole feature): MFCAD++ has no counterbore class, so see what the model does

The agent then bundles these Parts, a few held-out MFCAD++ test Parts, and the six upstream test cases.

## Comments

- 2026-11-10: Agent half done. Three held-out MFCAD++ test Parts are bundled in `parts/mfcadpp/` (see its `SOURCE.md`), picked by surveying 400 test Parts with the night-2 model (`runs/pick_demo_parts.log`). The README has a Demo Parts section. Still waiting on the three Onshape Parts; the modeling guide is above.
