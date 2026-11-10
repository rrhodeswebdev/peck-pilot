# 05 API

Status: resolved
Blocked by: 04

Spec: App → Backend, Upload validation.

## What
FastAPI app with `GET /api/parts` and `POST /api/analyze`. The response contains:
- per-Face triangles, Face ID, label and confidence
- Machining Features with their status
- Operations
- Unplanned Features with reasons
- the G-code

The model loads once at startup.

## Acceptance
- An upload that's the wrong extension, over 20 MB or not valid STEP gets a 4xx, and the server keeps serving.
- A bundled Part round-trips through the endpoint.
- pytest uses FastAPI's TestClient.

## Comments

**2026-11-10:** Done.
- Added `peck_pilot/api.py`; run it with `uvicorn peck_pilot.api:app`. `tests/test_api.py` passes 10 tests:
  - path traversal and unlisted parts return 404
  - wrong extension returns 415
  - files over 20 MB return 413
  - junk STEP returns 422, and the server keeps serving
  - a valid upload is planned
- Weights default to `runs/night1/best.ckpt` and can be overridden with `PECK_PILOT_WEIGHTS`. Tests use the published checkpoint.
- The response gives each Face's mesh as flat `vertices` and `indices` arrays. Winding is flipped on reversed Faces. Meshing uses the recognition triangulation: 0.9 mm linear, 0.5 rad angular.
  - This may look faceted on small holes. Re-mesh finer after recognition if it does; recognition doesn't depend on it.
- End to end with night-1 weights on the synthetic 5-hole plate: all 5 holes recognized at ≥ 0.99 confidence, 3 planned, and the side and bottom holes flagged as needing another Setup.
