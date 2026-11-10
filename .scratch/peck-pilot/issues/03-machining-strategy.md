# 03 Machining Strategy: drilling rules

Status: resolved
Blocked by: 02

Spec: Drilling rules (all constants live in one module).

## What
Turn the planned holes into ordered Operations:
- spot drill first, then drill
- G81 or G83, with peck depth Q
- spindle speed and feed
- tool numbers in order of first use

Holes that can't be drilled are Unplanned Features: `no drill within tolerance` or `too large to drill`.

## Acceptance
pytest covers:
- the 3×D threshold for G81 vs G83
- drill selection at the ±0.05 mm tolerance edges
- holes over 13 mm
- spot depth min(1.0, D/2)
- through-hole depth vs blind-hole depth, plus the blind-hole warning
- Operation order

## Comments

**2026-11-10:** Done. Added `peck_pilot/strategy.py`, which holds every rule constant. `tests/test_strategy.py` passes 16 tests.
- Holes the Strategy can't drill get `reason` set on their Machining Feature.
- With unclamped feeds, every drill runs at about 477 mm/min. Feed = rpm × 0.02·D, and D cancels out of rpm × D. This is expected, not a bug.
