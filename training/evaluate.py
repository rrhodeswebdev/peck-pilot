"""Per-Face accuracy of a checkpoint on an MFCAD++ HDF5 split.

Usage: python -m training.evaluate <weights.ckpt> <split.h5>
"""
import sys

import numpy as np

from peck_pilot.cadnet.helper import dataloader_edge
from peck_pilot.model import BLIND_HOLE, NUM_CLASSES, THROUGH_HOLE, build_model


def evaluate(weights, h5_path):
    model = build_model()
    model.load_weights(weights).expect_partial()
    correct = np.zeros(NUM_CLASSES)
    total = np.zeros(NUM_CLASSES)
    for x, y in dataloader_edge(h5_path):
        pred = model(x, training=False).numpy().argmax(1)
        np.add.at(total, y, 1)
        np.add.at(correct, y[pred == y], 1)
    return correct, total


if __name__ == "__main__":
    correct, total = evaluate(sys.argv[1], sys.argv[2])
    print(f"faces={int(total.sum())} accuracy={correct.sum() / total.sum():.4f}")
    for label, name in ((THROUGH_HOLE, "through hole"), (BLIND_HOLE, "blind hole")):
        print(f"{name}: faces={int(total[label])} recall={correct[label] / total[label]:.4f}")
