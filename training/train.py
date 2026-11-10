"""Train Hierarchical CADNet (edge) on MFCAD++, CPU only. Saves the best-validation weights after every epoch,
so an interrupted run loses at most one epoch. Adapted from the upstream train_edge.py (see peck_pilot/cadnet/SOURCE.md).

Usage: python -m training.train <hierarchical_graphs_dir> <out_dir> <epochs> [--init <weights.ckpt>]
"""
import os
import sys
import time

import tensorflow as tf

from peck_pilot.cadnet.helper import dataloader_edge
from peck_pilot.model import NUM_CLASSES, build_model


def main(data_dir, out_dir, epochs, init=None):
    os.makedirs(out_dir, exist_ok=True)
    train_path = os.path.join(data_dir, "training_MFCAD++.h5")
    val_path = os.path.join(data_dir, "val_MFCAD++.h5")

    model = build_model()
    if init:
        model.load_weights(init).expect_partial()
    loss_fn = tf.keras.losses.CategoricalCrossentropy()
    optimizer = tf.keras.optimizers.Adam(learning_rate=1e-2)  # upstream default
    train_loss, train_acc = tf.keras.metrics.Mean(), tf.keras.metrics.CategoricalAccuracy()
    val_loss, val_acc = tf.keras.metrics.Mean(), tf.keras.metrics.CategoricalAccuracy()
    best_val_acc = 0.0

    for epoch in range(1, epochs + 1):
        start = time.time()
        for step, (x, y) in enumerate(dataloader_edge(train_path)):
            y = tf.one_hot(y, depth=NUM_CLASSES)
            with tf.GradientTape() as tape:
                logits = model(x, training=True)
                loss = loss_fn(y, logits)
            grads = [tf.clip_by_norm(g, 1.0) for g in tape.gradient(loss, model.trainable_variables)]
            optimizer.apply_gradients(zip(grads, model.trainable_variables))
            train_loss.update_state(loss)
            train_acc.update_state(y, logits)
            if step % 50 == 0:
                print(f"epoch {epoch} step {step} loss={float(train_loss.result()):.4f} "
                      f"acc={float(train_acc.result()):.4f} elapsed={(time.time() - start) / 60:.0f}m", flush=True)

        for x, y in dataloader_edge(val_path):
            y = tf.one_hot(y, depth=NUM_CLASSES)
            logits = model(x, training=False)
            val_loss.update_state(loss_fn(y, logits))
            val_acc.update_state(y, logits)

        acc = float(val_acc.result())
        print(f"epoch {epoch} done in {(time.time() - start) / 3600:.2f}h "
              f"train_acc={float(train_acc.result()):.4f} val_loss={float(val_loss.result()):.4f} val_acc={acc:.4f}",
              flush=True)
        if acc > best_val_acc:
            best_val_acc = acc
            model.save_weights(os.path.join(out_dir, "best.ckpt"))
            print(f"saved best.ckpt (val_acc={acc:.4f})", flush=True)
        for m in (train_loss, train_acc, val_loss, val_acc):
            m.reset_states()


if __name__ == "__main__":
    args = sys.argv[1:]
    init = args[args.index("--init") + 1] if "--init" in args else None
    main(args[0], args[1], int(args[2]), init)
