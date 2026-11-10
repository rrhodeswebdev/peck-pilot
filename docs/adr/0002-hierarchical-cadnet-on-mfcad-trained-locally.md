# Hierarchical CADNet on MFCAD++, trained locally on CPU

We use the published Hierarchical CADNet architecture (QUB, MIT license). We copy the needed files with attribution and retrain it ourselves on MFCAD++ (CC BY) on a 2019 Intel MacBook, with no GPU and no cloud. We chose it over AAGNet, BRepNet and UV-Net (about 99% vs 97.6% per-Face accuracy) for three reasons: it uses MFCAD++ exactly as published, it ships a trained MFCAD++ checkpoint as a disclosed fallback, and its license permits reuse. The others either need a re-hosted dataset or a dependency (DGL) that may not run on this Mac, or carry a non-commercial license.

## Consequences

- The environment is pinned to the repo's era: Python 3.9, TensorFlow 2.15 or lower (Keras 3 breaks the code), pythonocc-core 7.5.1 from conda-forge. Don't upgrade these casually.
- Training uses the checkpoint's configuration (edge variant, 7 layers, 512 units), so our run and the published checkpoint are interchangeable.
- CPU-only training is time-boxed to one overnight run. Fewer epochs or a training subset are acceptable; evaluation always uses the full MFCAD++ test split. The accuracy we quote is ours, stated next to the paper's 97.6%.
- MFCAD++ has only two hole types (through hole and blind hole), and no counterbore, countersink or tapped holes.
