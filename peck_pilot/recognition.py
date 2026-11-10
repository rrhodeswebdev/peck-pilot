"""Feature Recognition: read a Part from STEP and label each Face (ADR 0001)."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Extend.TopologyUtils import TopologyExplorer

from peck_pilot.cadnet import step_graph
from peck_pilot.model import build_model

DEFAULT_WEIGHTS = Path(__file__).resolve().parents[1] / "runs" / "night2" / "best.ckpt"


class InvalidPart(ValueError):
    """The file can't be used as a Part; the message is safe to show the user."""


@dataclass
class Recognition:
    solid: object  # TopoDS_Solid
    faces: list  # TopoDS_Face, in the same order as labels and confidences
    labels: np.ndarray  # MFCAD++ label id per Face
    confidences: np.ndarray  # softmax max per Face


def load_model(weights=DEFAULT_WEIGHTS):
    model = build_model()
    model.load_weights(str(weights)).expect_partial()
    return model


def read_part(path):
    reader = STEPControl_Reader()
    # pythonocc 7.5.1 segfaults the whole process if TransferRoots runs after a failed read.
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise InvalidPart("not a readable STEP file")
    if reader.TransferRoots() == 0 or reader.OneShape().IsNull():
        raise InvalidPart("STEP file contains no geometry")
    solids = list(TopologyExplorer(reader.OneShape()).solids())
    if len(solids) != 1:
        raise InvalidPart(f"expected exactly one solid, found {len(solids)}")
    return solids[0]


def recognize(path, model):
    solid = read_part(path)
    step_graph.triangulate_shape(solid)
    work_faces, work_edges, faces = step_graph.get_brep_information(solid)
    # Upstream keys Faces by hash(); a collision would silently misalign labels and Faces.
    if len(work_faces) != len(faces):
        raise RuntimeError("Face hash collision while building the graph")
    facets, facet_edges, _, _ = step_graph.get_mesh_information(solid)
    graph = step_graph.get_graph(work_faces, facets, work_edges, facet_edges)
    probs = model(graph, training=False).numpy()
    return Recognition(solid, faces, probs.argmax(1), probs.max(1))
