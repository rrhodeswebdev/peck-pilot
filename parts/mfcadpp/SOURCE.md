Held-out Parts from the MFCAD++ **test** split, which training never saw (Queen's University Belfast, CC BY; see the README). Each Face's STEP name is its true MFCAD++ label id.

They were picked by running the night-2 model and the full pipeline over the first 400 test Parts (`runs/pick_demo_parts.log`):

- `10469.step`: one through hole planned with G83, one `no drill within tolerance` (Ø2.25), one `needs another Setup`. Shows all three outcomes on one Part.
- `11455.step`: two Ø2 through holes planned with G83, one Ø2.34 hole `no drill within tolerance`. All labels are correct.
- `11694.step`: **a model mistake caught by geometry.** The model labels a Stock Face as through hole, which merges it with a real hole. The group fails the geometry check, so nothing is drilled. One other hole is planned.

Across those 400 Parts, the night-2 model averaged 90.3% per-Face accuracy. Planned holes are rare (38 Parts) because MFCAD++ hole diameters are random: 31 holes miss the 0.5 mm drill library and are reported as `no drill within tolerance`.
