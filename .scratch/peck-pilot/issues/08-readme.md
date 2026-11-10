# 08 README and attribution

Status: resolved
Blocked by: 06

## What
The README covers:
- what the demo does
- setup with `environment.yml`
- how to get the dataset and weights, or reproduce them with `training/`
- the accuracy table: ours vs published
- attribution for MFCAD++ (CC BY) and Hierarchical CADNet (MIT)
- known limits, taken from the `shortcut:` comments

## Comments

- 2026-11-10: `README.md` written. It covers what the demo does, setup, weights and how to reproduce them, run and test commands, the accuracy table (night 1, night 2 and published, on the test split and the six upstream Parts), known limits from the `shortcut:` comments plus a few others, and attribution. The default weights are now `runs/night2/best.ckpt` (93.18% on the test split). The demo Parts section waits on issue 07.
