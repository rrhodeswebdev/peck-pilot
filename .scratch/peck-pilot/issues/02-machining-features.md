# 02 Machining Features and hole geometry

Status: resolved
Blocked by: 01

Spec: Pipeline steps 3–5 and the Unplanned Feature reasons.

## What
Group touching Faces that share a label into Machining Features. For through holes (1) and blind holes (12), measure from the B-rep:
- cylinder axis
- diameter
- depth
- entry Z

Then apply the Setup filter: the axis must be parallel to Z and the hole must open toward +Z.

## Acceptance
- Each hole group gets one axis and one diameter. Otherwise it becomes an Unplanned Feature with reason `failed geometry check`.
- Holes that aren't top-face holes become `needs another Setup`.
- A hole-like cylindrical Face with a non-hole label becomes `wrong label?`.
- Other feature types are reported as `no strategy yet`.
- pytest uses small STEP Parts built in code with pythonocc: a plate with one through hole, one blind hole, and one side hole.

## Comments

**2026-11-10:** Done. Added `peck_pilot/features.py`; `tests/test_features.py` passes 12 tests.

Deviations from the spec, both found on real MFCAD++ Parts:
- **Hole Faces are grouped by shared axis and radius, not by touching.** A hole cut by another feature is split into several Faces that don't touch. Grouping by touching would have made the Strategy drill the same hole twice. All other feature types still use touching Faces with the same label.
- **Floors and caps are found by geometry, never by label.** A floor is a plane square to the axis, at one end of the bore, lying within its radius.
  - This handles counterbores: the ledge is the wide hole's floor, not the narrow hole's.
  - MFCAD++ 10354 has a "through hole" capped by a disk. The first version would have drilled straight through that material; it now fails the geometry check.
  - A mislabeled floor no longer matters.

Survey of 1,000 MFCAD++ test Parts using their true labels, so it tests the geometry code and not the model:
- 200 holes planned
- 587 need another Setup (axes are spread evenly across X, Y and Z)
- 11 (1.4%) failed the geometry check. These produce no G-code, so they fail safe; not investigated individually.
- No false "wrong label?" flags
- One Part (13975) is stored without a solid and is rejected as `InvalidPart`

Not verified: that every *planned* hole is right. For example, nothing checks for obstructions above the opening; there's a `shortcut:` comment for that.
