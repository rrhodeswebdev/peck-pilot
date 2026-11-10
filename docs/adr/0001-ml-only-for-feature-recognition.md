# ML only for Feature Recognition

The trained model does one thing: label each Face of a Part with a Machining Feature type. Everything after that is deterministic geometry and fixed rules. That covers grouping Faces into Machining Features, measuring hole diameter, depth and axis, choosing drills and G81 vs G83, and generating G-code. Recognizing features from raw B-rep geometry is the step that's genuinely hard to hand-code. Measurements and machining rules must be exact and explainable, and there's no labeled data to learn them from without first writing those same rules.

## Consequences

- When the model is wrong, the result must be visible, never a silently missing Operation. Faces carry their prediction confidence. Hole-like Faces that produce no Operation are listed as Unplanned Features.
- A hole group that fails geometric checks, such as no single cylinder axis or diameter, becomes an Unplanned Feature instead of being guessed at.
