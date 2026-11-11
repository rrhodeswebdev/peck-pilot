# uv and OCP instead of conda and pythonocc

Setup moved from a conda environment to uv, so it's one `uv sync`. pythonocc-core is only published on conda-forge, so the OpenCascade bindings changed to OCP (`cadquery-ocp` on PyPI). We pinned OCP 7.7.2, the closest pip-installable OpenCascade to upstream's 7.5.1, on Python 3.11, the newest Python TensorFlow 2.15.1 supports. This supersedes the pythonocc and Python 3.9 pins in ADR 0002. The TensorFlow 2.15 / Keras 2 pin stands.

## Consequences

- `peck_pilot/occ.py` rebuilds the slice of pythonocc's `TopologyExplorer` this project used, with the same ordering and de-duplication. OCP compares and hashes shapes by Python identity, so the copied CADNet graph code uses `HashCode` and `IsEqual` explicitly where pythonocc's `__hash__` and `__eq__` did that implicitly.
- Checked against the pythonocc build on every bundled Part: 9 of 10 give identical labels, confidences, Machining Features and G-code. On `upstream/5_true.stp`, 2 of 75 Faces mesh differently, and its per-Face accuracy moves from 0.53 to 0.52 (ours) and from 0.44 to 0.47 (published). The test-split figures come from the dataset's pre-built graphs, so they are unaffected.
- OCP 7.8 and later drop `TopoDS_Shape.HashCode`, so upgrading OCP means changing the hashing above.
- `cryptography` is held below 49: newer versions have no Intel-Mac wheel and would need Rust to build.
