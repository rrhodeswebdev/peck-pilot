# Peck Pilot

A demo that turns a CAD part into a machining strategy: it recognizes the machining features on the part, then decides how to cut them, starting with drilled holes.

## Language

**Part**:
A single solid CAD model, received as a STEP file, that is to be machined.
_Avoid_: Model (collides with the ML model), workpiece, component

**Face**:
One bounded surface of a Part's boundary representation; the unit that Feature Recognition labels.
_Avoid_: Surface, facet

**Machining Feature**:
A group of Faces on a Part that is cut as one unit, such as a through hole, blind hole, pocket or slot.
_Avoid_: Feature (alone), geometry

**Feature Recognition**:
Identifying which Machining Feature, if any, each Face of a Part belongs to.
_Avoid_: Segmentation, classification

**Operation**:
One machining step on one Machining Feature with one tool, such as peck drilling a 6 mm hole in 1.5 mm pecks.
_Avoid_: Toolpath, step, cut

**Machining Strategy**:
The ordered set of Operations that machines a whole Part; G-code is generated from it.
_Avoid_: Plan, process plan, toolpath

**Unplanned Feature**:
A Machining Feature, or a hole-like group of Faces, that produced no Operation and is shown for human review.
_Avoid_: Error, skipped feature, unsupported feature

**Stock**:
The raw block a Part is cut from; here, the Part's bounding box.
_Avoid_: Blank, billet, raw material

**Setup**:
One fixturing of the Stock on the machine, from which only Faces reachable along the spindle axis can be cut.
_Avoid_: Fixture, orientation, op (as in "op 10")

**Peck Drilling**:
Drilling a hole in repeated partial plunges, retracting between them to clear chips; the G83 cycle.
_Avoid_: Deep drilling, pecking
