# Peck Pilot: spec

A local demo for a forward-deployed engineering role at Re:CAM. It takes a Part, recognizes its Machining Features with a model trained in-house, and turns top-face holes into a Machining Strategy and Fanuc-style G-code. It is shown in a live walkthrough or a recorded video and is never hosted.

Vocabulary: `GLOSSARY.md`. Decisions: `docs/adr/0001` to `docs/adr/0003`. Environment: `pyproject.toml` (uv).

## Pipeline

1. **Read the Part.** STEP in, millimetres.
2. **Feature Recognition.** Hierarchical CADNet gives each Face one of 25 labels (24 Machining Feature types plus Stock) and a confidence, which is the softmax maximum.
3. **Group Faces into Machining Features.** Faces that touch and share a label form one group.
4. **Check hole geometry.** Applies to groups labeled through hole (1) or blind hole (12). The group must have exactly one cylinder axis and one diameter. Depth and entry Z come from the B-rep, never from the model.
5. **Filter by Setup.** A hole is planned only if its axis is parallel to Z and it opens toward +Z.
   - shortcut: overhangs above the hole opening are not checked. MFCAD++ parts are prismatic; add the check when real parts arrive.
6. **Build the Machining Strategy.** Apply the drilling rules below.
7. **Generate G-code** from the Machining Strategy.

Any hole that doesn't become an Operation is an **Unplanned Feature**, listed with its reason:
- `wrong label?`: a hole-like cylindrical Face that the model labeled as something other than a hole
- `failed geometry check`
- `needs another Setup`
- `no drill within tolerance`
- `too large to drill`

Other recognized Machining Features are shown as `no strategy yet`. Nothing is dropped silently (ADR 0001).

## Drilling rules

These are fixed constants kept in one module. There is no settings UI.

- **Material:** 6061 aluminum. HSS drills at 75 m/min surface speed. Feed is 0.02 × D mm/rev, clamped to 0.05–0.25. Spindle speed is capped at 10,000 rpm.
- **Drill library:** 1.0–13.0 mm in 0.5 mm steps.
  - Tolerance is ±0.05 mm. Outside it, the hole is `no drill within tolerance`.
  - Above 13 mm, the hole is `too large to drill`.
- **Spot drill:** a 90° spot drill, 6 mm, as T1. Spot depth is min(1.0, D/2) mm, so the spot is never wider than the hole.
- **Cycle choice:** G83 Peck Drilling when depth is more than 3 × D, with peck depth Q = 1 × D. G81 otherwise.
- **Through holes:** the full drill diameter clears the bottom face by 1 mm. The tip allowance is 0.3 × D for a 118° point.
- **Blind holes:** the drill tip stops at the hole floor, so the drill never cuts outside the Part's geometry. The hole gets the warning "flat bottom needs end mill or flat-bottom drill; cone left".
- **Operation order:** spot drill on every hole first, then drills in ascending size. Within one tool, holes are sorted by X, then Y.
  - shortcut: there is no travel optimization; add nearest-neighbor ordering if cycle time matters.
- **Tool numbers:** assigned in order of first use.

## G-code

- Fanuc-style, metric.
- Preamble: `G21 G17 G40 G49 G80 G90`.
- Work offset is `G54`. The origin is the top front-left corner of the Stock, which is the Part's bounding box.
- Each tool: `T# M06`, `S# M03`, `G43 H#`, `M08`.
- Canned cycles use `G98` with the R plane 2 mm above the hole entry, followed by `G80`.
- The program ends with `M09 M05`, `G91 G28 Z0`, `M30`.
- Checked visually in NCViewer for the demo video.

## The model (ADR 0002)

- The needed Hierarchical CADNet files are copied into the repo, with the MIT LICENSE and the source commit recorded. Source: `gitlab.com/qub_femg/machine-learning/hierarchical-cadnet`, commit `3f6673009db154043262028649e894a4f164ce13`.
- The STEP-to-graph code from `test_and_save.py` is changed to return labels and confidences instead of writing a STEP file.
- **Training:** on CPU, local only, with the published checkpoint's configuration (edge variant, 7 layers, 512 units, 25 classes, dropout 0.3).
  - Time one epoch first. Then size a single overnight run (≤ 8 h) by cutting epochs or using a subset of the training split.
  - Evaluate on the full MFCAD++ test split.
  - Record our per-Face accuracy, the epochs and the subset size next to the paper's 97.6%.
- **Fallback:** the published checkpoint, used only if our run fails, and the demo says so whenever it's used.
- Weights are stored outside git. The README says how to obtain or reproduce them.

## App

- **Backend:** FastAPI on Python 3.11, managed by uv (ADR 0003). The model loads once at startup. It is single-user, and synchronous handling is fine.
  - `GET /api/parts`: the bundled demo Parts.
  - `POST /api/analyze`: a bundled Part name or an uploaded STEP file.
    - Returns per-Face triangles, Face ID, label and confidence.
    - Returns the Machining Features with their status, the Operations, and the Unplanned Features with reasons.
    - Returns the G-code text.
- **Upload validation (trust boundary):**
  - The extension must be `.step` or `.stp`, and the file 20 MB or less.
  - `STEPControl_Reader.ReadFile` must return `IFSelect_RetDone` **before** `TransferRoots` is called.
  - The result must be exactly one solid.
  - Every failure returns a clear 4xx error.
  - **Why:** pythonocc 7.5.1 segfaults the whole process when `TransferRoots` runs on a file that isn't valid STEP. This was observed during the environment check.
- **Frontend:** Vite + TypeScript + three.js, no React, one screen.
  - Part dropdown plus file upload.
  - 3D viewer: each Face is colored by its label, with a legend. Clicking a Face shows its label and confidence.
  - Side panel: Machining Features, Operations, Unplanned Features, and the G-code with a download button.
  - Clicking a Face highlights its Operation, and clicking an Operation highlights its Faces.

## Demo Parts

- Held-out MFCAD++ test Parts.
- The six labeled "complex" test cases shipped with the CADNet repo. On these, the published checkpoint scores 43–97% per-Face accuracy, so they double as honest failure cases.
- Three Parts the user models in Onshape:
  - a plate with through and blind holes that should work
  - a deep hole that triggers G83
  - one designed to break it, such as a hole on a side face or overlapping holes

## Tests

- **pytest on the rules:** G81 vs G83 threshold, drill selection and tolerance, peck depth, spot depth, Setup filtering, through-hole vs blind-hole depth.
- **One golden test:** a known Part produces exactly the expected G-code.
- **Upload validation:** a non-STEP file returns 4xx and the server survives.
- No tests on the copied CADNet code.

## Interview framing

"I trained and integrated a published architecture," not "I designed it." Quote our own test accuracy and the gap from the paper. Walk through a failure case and say what would fix it.

## Training measurements (2026-11-09, 2019 Intel i9, CPU only)

- **Dataset:** extracted at `~/datasets/mfcadpp/MFCAD++_dataset/`. The ready-made HDF5 graphs are under `hierarchical_graphs/`, so no graph generation is needed. STEP units are millimetres.
- **Training epoch:** 1,473 batches at about 8.4 s per batch, so about **3.5 h per training epoch**, plus about 15 min of validation.
  - The data loader costs only 0.2 s per batch.
  - The laptop was thermally throttled to 34–42% CPU speed (`pmset -g therm`), and step times climbed from 6 s to 12 s.
- **`tf.function` compilation fails:** the dropout layer can't handle batches of varying size once compiled. Training stays eager, as in the repo.
- **Overnight budget:** one night of 8 h is about 2 epochs. The paper ran 100.
- **Baseline:** the published checkpoint on the full test split (259,128 Faces, `python -m training.evaluate`) scored 96.87% per-Face accuracy, against the paper's 97.6%. Through hole recall was 99.12% and blind hole recall 97.14%.
- **Night 1:** 2 epochs, logged to `runs/night1.log`, with weights at `runs/night1/best.ckpt`.
  - Epoch 1 took 2.9 h and reached 88.5% validation accuracy; epoch 2 took 2.5 h and reached 89.8%.
  - **Test split:** 89.91% per-Face accuracy (published checkpoint 96.87%). Through hole recall 98.26% (published 99.12%), blind hole recall 97.26% (published 97.14%).
  - On the two classes the Machining Strategy uses, it is on par with the published model. The overall gap comes from the other feature types.
  - Continue for a second night with `--init runs/night1/best.ckpt`.
- **Night 2 (2026-11-10):** 2 more epochs from night 1 (4 in total), logged to `runs/night2.log`, with weights at `runs/night2/best.ckpt`. **These are the app's default weights.**
  - Epoch 1 took 2.8 h and reached 92.72% validation accuracy; epoch 2 took 3.7 h (paused twice for a call and for battery) and reached 93.06%.
  - **Test split:** 93.18% per-Face accuracy (published 96.87%). Through hole recall 98.34% (published 99.12%), blind hole recall 96.82% (published 97.14%).
  - **Six upstream complex Parts**, per-Face accuracy night 1 / night 2 / published: 0.79/0.93/0.97, 0.69/0.74/0.83, 0.88/0.85/0.92, 0.44/0.80/0.70, 0.49/0.53/0.44, 0.23/0.33/0.43. Night 2 beats night 1 on 5 of 6 Parts and beats the published model on Parts 4 and 5.
