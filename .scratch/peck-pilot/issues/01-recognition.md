# 01 Recognition: STEP file to labeled Faces

Status: resolved
Blocked by: none

Spec: Pipeline steps 1–2, App → Upload validation, The model.

## What
Add `peck_pilot/recognition.py`. It reads a STEP file and returns each Face with its label id and confidence (softmax max), plus the OCC shape and Face objects for later steps.
- Port the STEP-to-graph code from upstream `test_and_save.py` into it. Record the port in `peck_pilot/cadnet/SOURCE.md`.
- Drop the label-reading and STEP-writing parts.
- Load the weights once. Default to `runs/night1/best.ckpt`, with a path parameter so the published checkpoint can be swapped in.

## Acceptance
- A file that isn't valid STEP raises a clear error. The process doesn't segfault: check `ReadFile` returns `IFSelect_RetDone` before `TransferRoots`.
- A STEP file that isn't exactly one solid raises a clear error.
- On upstream test case `1_true.stp`, accuracy against its stored labels matches the spike (about 0.97 with the published checkpoint).
- pytest covers the non-STEP file and the test-case smoke run.

## Comments

**2026-11-10:** Done.
- Added `peck_pilot/recognition.py`. The graph code is ported verbatim as `peck_pilot/cadnet/step_graph.py`.
- `tests/test_recognition.py` passes 5 of 5:
  - junk, empty and truncated files raise `InvalidPart`, with no segfault
  - files with more than one solid are rejected
  - the published checkpoint scores ≥ 0.95 on `1_true.stp`
- Our night-1 weights vs the published checkpoint on the six upstream complex parts, per-Face accuracy:

  | Part | Ours | Published |
  |---|---|---|
  | 1 | 0.79 | 0.97 |
  | 2 | 0.69 | 0.83 |
  | 3 | 0.88 | 0.92 |
  | 4 | 0.44 | 0.70 |
  | 5 | 0.49 | 0.44 |
  | 6 | 0.23 | 0.43 |

  The gap on hard Parts is larger than on the MFCAD++ test split.
