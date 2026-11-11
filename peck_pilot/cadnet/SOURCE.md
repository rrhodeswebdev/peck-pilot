# Source

Copied from Hierarchical CADNet (MIT, see `LICENSE`):
https://gitlab.com/qub_femg/machine-learning/hierarchical-cadnet
commit `3f6673009db154043262028649e894a4f164ce13` (2025-02-18), files `src/layers.py`, `src/network_edge.py`, `src/helper.py`.

Only change: `network_edge.py` imports `.layers` relatively instead of `src.layers`.

Paper: Colligan AR, Robinson TR, Nolan DC, Hua Y, Cao W. *Hierarchical CADNet: Learning from B-Reps for Machining Feature Recognition*, Computer-Aided Design.

`step_graph.py` is upstream `test_and_save.py` cut down to the B-rep-to-graph functions (`WorkFace` … `get_graph`, `triangulate_shape`). The TensorFlow/model imports, `read_step_file`, `read_step_with_labels`, `create_hier_graphs`, `write_step_wth_prediction`, `test_step` and `__main__` were removed. No logic was changed, apart from the port from pythonocc to OCP (ADR 0003): imports and static-method calls, `HashCode`/`IsEqual` in place of pythonocc's `__hash__`/`__eq__`, and `Node(i)`/`Triangle(i)` in place of the removed `Nodes()`/`Triangles()` arrays.
