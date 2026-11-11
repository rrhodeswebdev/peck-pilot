# Peck Pilot

Peck Pilot reads a CAD Part (a STEP file) and recognizes its Machining Features with a graph neural network trained here. It then turns the Part's top-face holes into a Machining Strategy and Fanuc-style G-code. All of this happens in a local web app with a 3D viewer.

The ML only labels Faces (ADR 0001). Grouping, hole measurement, tool choice and G-code all come from B-rep geometry and fixed drilling rules. A wrong label can only stop a hole from being planned. It can never send a drill into the wrong place.

Vocabulary is in [GLOSSARY.md](GLOSSARY.md), decisions in [docs/adr/](docs/adr), and the full spec in [.scratch/peck-pilot/spec.md](.scratch/peck-pilot/spec.md).

## What it does

1. **Read the Part.** A STEP file containing exactly one solid, in millimetres.
2. **Feature Recognition.** [Hierarchical CADNet](https://gitlab.com/qub_femg/machine-learning/hierarchical-cadnet) labels every Face with one of the 25 MFCAD++ classes and a confidence.
3. **Group and measure.** Touching Faces with the same label become one Machining Feature. Each hole's axis, diameter, depth and through or blind status are measured from the geometry, not taken from the model. A blind hole must have a floor and a through hole must not.
4. **Plan.** Holes that open toward +Z get a spot drill, then a drill from a 1.0–13.0 mm library. Holes deeper than 3×D get G83 Peck Drilling; the rest get G81.
5. **G-code.** Fanuc-style, G21 metric, with G54 at the top front-left corner of the Stock.

Anything not planned is listed as an Unplanned Feature with its reason (`needs another Setup`, `failed geometry check`, `wrong label?`, `no drill within tolerance`, `too large to drill`). Other recognized feature types are shown as `no strategy yet`. Nothing is dropped silently.

## Setup

This needs macOS or Linux, [uv](https://docs.astral.sh/uv/) and Node 18 or newer.

```sh
uv sync                                  # Python 3.11, OpenCascade (OCP 7.7.2), TensorFlow 2.15
(cd web && npm install && npm run build) # builds web/dist, which the API serves
```

Prefix the Python commands below with `uv run`, or activate `.venv`. For why this uses OCP rather than pythonocc, see ADR 0003.

### Weights

Weights are kept out of git. The app loads `runs/night2/best.ckpt` by default; set `PECK_PILOT_WEIGHTS=<path to .ckpt>` to load a different file.

- **Published checkpoint, for comparison:** copy `checkpoint/MF_CAD++_residual_lvl_7_edge_MFCAD++_units_512_date_2021-07-27_epochs_100.ckpt.*` from the [Hierarchical CADNet repo](https://gitlab.com/qub_femg/machine-learning/hierarchical-cadnet) into `models/published/`.
- **Our weights:** reproduce them with the steps below.

### Reproduce training

1. Download the MFCAD++ dataset from the [QUB data page](https://pure.qub.ac.uk/en/datasets/mfcad-dataset-dataset-for-paper-hierarchical-cadnet-learning-from/). The site sits behind a browser check, so download it in a browser.
2. Extract it. The ready-made graphs are in `MFCAD++_dataset/hierarchical_graphs/`.
3. Train, then evaluate on the test split:

```sh
G=~/datasets/mfcadpp/MFCAD++_dataset/hierarchical_graphs
uv run python -m training.train $G runs/night1 2                                # about 5.5 h on a 2019 i9 CPU
uv run python -m training.train $G runs/night2 2 --init runs/night1/best.ckpt   # about 6.5 h
uv run python -m training.evaluate runs/night2/best.ckpt $G/test_MFCAD++.h5
```

## Run

```sh
uv run uvicorn peck_pilot.api:app --port 8765
```

Open http://127.0.0.1:8765. Pick a bundled Part or upload a STEP file of 20 MB or less. Click a Face, a Machining Feature or an Operation to highlight the related items.

For frontend development, run `cd web && npm run dev`. Vite proxies `/api` to port 8765.

## Tests

```sh
uv run pytest
```

The tests cover:
- the drilling rules
- Setup filtering and the hole geometry checks, on Parts built in code
- upload validation
- one golden G-code program, `tests/golden/plate.nc`

The copied CADNet code has no tests of its own.

## Accuracy

I trained a published architecture; I did not design it. Training ran on a laptop CPU for 4 epochs over two runs, against the paper's 100. The table gives per-Face accuracy on the full MFCAD++ test split (259,128 Faces):

| | Epochs | Accuracy | Through hole recall | Blind hole recall |
|---|---|---|---|---|
| Paper (Colligan et al.) | 100 | 97.6% | | |
| Published checkpoint, measured here | 100 | 96.87% | 99.12% | 97.14% |
| Ours, run 1 | 2 | 89.91% | 98.26% | 97.26% |
| **Ours, run 2 (default)** | 4 | **93.18%** | 98.34% | 96.82% |

The Machining Strategy only uses the two hole classes, and on those we are close to the published model. Most of the overall gap comes from the other feature types.

On the six harder labeled Parts in `parts/upstream/`, per-Face accuracy is:

| Part | Ours, run 1 | Ours, run 2 | Published |
|---|---|---|---|
| 1 | 0.79 | 0.93 | 0.97 |
| 2 | 0.69 | 0.74 | 0.83 |
| 3 | 0.88 | 0.85 | 0.92 |
| 4 | 0.44 | 0.80 | 0.70 |
| 5 | 0.49 | 0.52 | 0.47 |
| 6 | 0.23 | 0.33 | 0.43 |

These Parts are much more complex than the training set. They are useful as honest failure cases in the demo.

## Demo Parts

The bundled Parts live in `parts/`; both sources are listed in their `SOURCE.md` files.

- **`parts/demo/mounting_plate.step`:** the clean case, and the Part the app opens first. It's a 100 × 60 × 15 mm plate built in code by `make_plate.py`, with nine top-face holes in standard drill sizes. All nine are planned (18 Operations); the two deep Ø3 holes use G83.
- **`parts/mfcadpp/`:** three held-out MFCAD++ test Parts. One shows every outcome (planned with G83, `no drill within tolerance`, `needs another Setup`). One is cleanly planned. In the third, the geometry check catches a model mistake before anything is drilled.
- **`parts/upstream/`:** the six labeled complex Parts from the CADNet repo, which serve as honest failure cases.

## Known limits

- **Only top-face holes are planned.** Holes on other faces are listed as `needs another Setup`.
- **No overhang check:** nothing checks for material overhanging a hole opening. MFCAD++ Parts are prismatic.
- **O-ring walls are exempt from the `wrong label?` check.** An O-ring's outer wall is also a full internal cylinder.
- **No travel optimization:** holes run in X-then-Y order.
- **Fixed rules for one material:** 6061 aluminum with HSS drills.
- **Blind holes leave a cone.** They are flagged "flat bottom needs end mill or flat-bottom drill; cone left".
- **Unlabeled hole types:** MFCAD++ has no counterbore, countersink or tapped-hole classes, so these come out as their component Faces.
- **The G-code has only been checked visually** in a viewer. It has not been proven on a machine.

## Attribution

- **Hierarchical CADNet:** Colligan AR, Robinson TR, Nolan DC, Hua Y, Cao W. *Hierarchical CADNet: Learning from B-Reps for Machining Feature Recognition*, Computer-Aided Design. The code is MIT licensed. The files copied into `peck_pilot/cadnet/` come from commit `3f66730`; see [SOURCE.md](peck_pilot/cadnet/SOURCE.md) and [LICENSE](peck_pilot/cadnet/LICENSE). The test Parts in `parts/upstream/` come from the same repo.
- **MFCAD++ dataset:** Queen's University Belfast, released under a CC BY license; see the [dataset page](https://pure.qub.ac.uk/en/datasets/mfcad-dataset-dataset-for-paper-hierarchical-cadnet-learning-from/). It is used for training and evaluation.
