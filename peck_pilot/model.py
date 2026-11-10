"""Hierarchical CADNet configuration shared by training, evaluation and the app (ADR 0002)."""
from peck_pilot.cadnet.network_edge import HierarchicalGCNN

NUM_CLASSES = 25  # 24 Machining Feature types + Stock, MFCAD++ label ids
THROUGH_HOLE, BLIND_HOLE = 1, 12
LABEL_NAMES = [  # MFCAD++ feature_labels.txt, indexed by label id
    "Chamfer", "Through hole", "Triangular passage", "Rectangular passage", "6-sided passage",
    "Triangular through slot", "Rectangular through slot", "Circular through slot", "Rectangular through step",
    "2-sided through step", "Slanted through step", "O-ring", "Blind hole", "Triangular pocket",
    "Rectangular pocket", "6-sided pocket", "Circular end pocket", "Rectangular blind slot",
    "Vertical circular end blind slot", "Horizontal circular end blind slot", "Triangular blind step",
    "Circular blind step", "Rectangular blind step", "Round", "Stock",
]

# Matches the published MFCAD++ checkpoint so the two are interchangeable.
PUBLISHED_CHECKPOINT = "MF_CAD++_residual_lvl_7_edge_MFCAD++_units_512_date_2021-07-27_epochs_100.ckpt"


def build_model():
    return HierarchicalGCNN(units=512, rate=0.3, num_classes=NUM_CLASSES, num_layers=7)
