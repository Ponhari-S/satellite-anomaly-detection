## Known Limitations

### Live feature extraction relies on pre-existing segment labels

The backend's `feature_extractor.py` resets its rolling feature-computation
window whenever the incoming reading's `segment` ID changes, so that live
predictions are computed over the same real segment boundaries the model
was trained on (rather than an arbitrary sliding window that could blend
two unrelated segments together).

This works correctly when **replaying historical data** via the simulator,
since every reading in `datasets/dataset.csv` already carries its true
`segment` ID.

It would **not** work out of the box for a genuinely new, live satellite
feed with no pre-existing segment labels — in that case, segment boundaries
would need to be determined in real time, for example via:
- a fixed time/reading-count window, or
- a change-point detection algorithm that flags when the signal's
  statistical behavior shifts enough to start a new segment.

This is a known, deliberate simplification for the current phase of the
project and is flagged here as a candidate area for future work.

### Live prediction accuracy vs. offline accuracy

The offline baseline model scores 0.85 F1 when evaluated on complete,
pre-cut segments (see `ai/evaluate_baseline.py`). When streaming live,
accuracy is measured at roughly 58-61% overall, because live segments
start with an empty buffer and features are necessarily computed on
partial data early in each segment.

This is expected, not a defect: a controlled investigation
(`day19_window_investigation.py`) confirms accuracy rises steadily as
each segment fills in — from ~81% in the first quarter of a segment's
readings to ~98% by the final quarter — consistent with the gap being
explained by partial-data uncertainty rather than a feature or model bug.