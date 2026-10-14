# Gate4D continuous layer selection — frozen before Gate4D outcomes

Frozen consumer: DB9 trusted-8 `LinearDiscriminantAnalysis(solver='svd')`, 8 standardized inputs, 8 classes, 7 Fisher coordinates; `transform` and `decision_function` are available. The path is canonical trusted-8 pose → frozen DB9 mean/SD → `head.transform` (7-D) → 8 class scores → 8 probabilities → argmax class.

**Primary layer:** `z = head.transform((pose8 - mu) / sd)`, 7-D `float64` Fisher coordinates. For paired GT and prediction, compare `delta_F = z_pred - z_gt` at matching Gate4C block indices. The frozen DB9 training-corpus component standard deviations in `gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json` are the diagonal reference scale. Primary error is `sqrt(sum_j (delta_F[j]/sigma_DB9[j])^2)`. This is diagonal scale normalization, not a claim of full covariance whitening. No held-out user enters the scale.

No fallback is needed because the exact `head.transform` exists. Probabilities and hard classes are secondary because their normalization and argmax add final decision effects. A shared additive offset through the same linear transform cancels in the paired difference; scale and user-specific calibration errors can remain.
