# Clone-server paper evidence results

All new feature variants and sensitivity analyses are exploratory on previously examined cohorts. Original heads, scorers, thresholds and cached inputs remain unchanged. No target task accuracy, physical equivalence, strict upstream-unseen generalization or causal online service is established.

New model fits: 60; exact original model instances reused: 36; failed fits preserved: 0.
Independent verification: 1370496 checks; 96 models; weights, thresholds, saved scores, denominators and full-class support verified.

## N80 U-training group additions at 30% offline retention

|Consumer|Added block|Other blocks (bits)|Paired n|Median reduction pp|Pointwise 95% interval|
|---|---|---:|---:|---:|---|
|ceti_age_scoreonly_v3_20261012__C1_primary|pose|0|80|0.824|[0.606, 1.127]|
|ceti_age_scoreonly_v3_20261012__C1_primary|pose|2|80|0.786|[0.315, 1.362]|
|ceti_age_scoreonly_v3_20261012__C1_primary|pose|4|80|0.935|[0.511, 1.228]|
|ceti_age_scoreonly_v3_20261012__C1_primary|pose|6|80|0.763|[0.424, 1.094]|
|ceti_age_scoreonly_v3_20261012__C1_primary|Fisher|0|80|0.173|[-0.210, 0.482]|
|ceti_age_scoreonly_v3_20261012__C1_primary|Fisher|1|80|0.084|[-0.127, 0.379]|
|ceti_age_scoreonly_v3_20261012__C1_primary|Fisher|4|80|-0.010|[-0.323, 0.357]|
|ceti_age_scoreonly_v3_20261012__C1_primary|Fisher|5|80|0.109|[0.004, 0.402]|
|ceti_age_scoreonly_v3_20261012__C1_primary|TTA|0|80|0.206|[0.002, 0.434]|
|ceti_age_scoreonly_v3_20261012__C1_primary|TTA|1|80|0.216|[-0.003, 0.388]|
|ceti_age_scoreonly_v3_20261012__C1_primary|TTA|2|80|0.221|[-0.017, 0.419]|
|ceti_age_scoreonly_v3_20261012__C1_primary|TTA|3|80|0.040|[-0.161, 0.377]|
|ceti_age_scoreonly_v3_20261012__C2_primary|pose|0|80|3.833|[3.120, 4.581]|
|ceti_age_scoreonly_v3_20261012__C2_primary|pose|2|80|3.749|[3.107, 4.378]|
|ceti_age_scoreonly_v3_20261012__C2_primary|pose|4|80|2.452|[1.649, 3.070]|
|ceti_age_scoreonly_v3_20261012__C2_primary|pose|6|80|2.394|[1.655, 3.111]|
|ceti_age_scoreonly_v3_20261012__C2_primary|Fisher|0|80|-0.112|[-0.294, 0.107]|
|ceti_age_scoreonly_v3_20261012__C2_primary|Fisher|1|80|0.034|[-0.153, 0.172]|
|ceti_age_scoreonly_v3_20261012__C2_primary|Fisher|4|80|0.056|[-0.090, 0.180]|
|ceti_age_scoreonly_v3_20261012__C2_primary|Fisher|5|80|0.069|[-0.163, 0.333]|
|ceti_age_scoreonly_v3_20261012__C2_primary|TTA|0|80|1.116|[0.620, 1.665]|
|ceti_age_scoreonly_v3_20261012__C2_primary|TTA|1|80|-0.346|[-0.588, 0.177]|
|ceti_age_scoreonly_v3_20261012__C2_primary|TTA|2|80|1.446|[0.746, 1.963]|
|ceti_age_scoreonly_v3_20261012__C2_primary|TTA|3|80|0.056|[-0.440, 0.262]|
|db9_scoreonly_v3_20261011__C1_primary|pose|0|80|0.353|[0.074, 0.655]|
|db9_scoreonly_v3_20261011__C1_primary|pose|2|80|0.262|[-0.015, 0.406]|
|db9_scoreonly_v3_20261011__C1_primary|pose|4|80|0.083|[-0.394, 0.243]|
|db9_scoreonly_v3_20261011__C1_primary|pose|6|80|0.183|[-0.089, 0.313]|
|db9_scoreonly_v3_20261011__C1_primary|Fisher|0|80|0.241|[-0.019, 0.623]|
|db9_scoreonly_v3_20261011__C1_primary|Fisher|1|80|0.079|[-0.040, 0.328]|
|db9_scoreonly_v3_20261011__C1_primary|Fisher|4|80|0.070|[-0.239, 0.351]|
|db9_scoreonly_v3_20261011__C1_primary|Fisher|5|80|0.369|[0.131, 0.576]|
|db9_scoreonly_v3_20261011__C1_primary|TTA|0|80|0.510|[0.172, 0.868]|
|db9_scoreonly_v3_20261011__C1_primary|TTA|1|80|0.204|[0.045, 0.474]|
|db9_scoreonly_v3_20261011__C1_primary|TTA|2|80|0.246|[-0.001, 0.553]|
|db9_scoreonly_v3_20261011__C1_primary|TTA|3|80|0.226|[0.018, 0.436]|
|db9_scoreonly_v3_20261011__C2_primary|pose|0|80|0.846|[0.529, 1.077]|
|db9_scoreonly_v3_20261011__C2_primary|pose|2|80|0.810|[0.403, 1.096]|
|db9_scoreonly_v3_20261011__C2_primary|pose|4|80|0.565|[0.431, 0.856]|
|db9_scoreonly_v3_20261011__C2_primary|pose|6|80|0.637|[0.486, 0.920]|
|db9_scoreonly_v3_20261011__C2_primary|Fisher|0|80|0.011|[-0.012, 0.047]|
|db9_scoreonly_v3_20261011__C2_primary|Fisher|1|80|-0.014|[-0.049, 0.012]|
|db9_scoreonly_v3_20261011__C2_primary|Fisher|4|80|-0.018|[-0.039, 0.007]|
|db9_scoreonly_v3_20261011__C2_primary|Fisher|5|80|-0.001|[-0.028, 0.041]|
|db9_scoreonly_v3_20261011__C2_primary|TTA|0|80|0.266|[0.010, 0.470]|
|db9_scoreonly_v3_20261011__C2_primary|TTA|1|80|0.120|[0.053, 0.210]|
|db9_scoreonly_v3_20261011__C2_primary|TTA|2|80|0.273|[0.075, 0.452]|
|db9_scoreonly_v3_20261011__C2_primary|TTA|3|80|0.129|[0.048, 0.219]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|pose|0|80|0.046|[-0.055, 0.184]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|pose|2|80|0.051|[-0.107, 0.185]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|pose|4|80|0.065|[-0.056, 0.198]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|pose|6|80|0.040|[-0.049, 0.220]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|Fisher|0|80|-0.023|[-0.043, 0.010]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|Fisher|1|80|-0.041|[-0.086, -0.015]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|Fisher|4|80|0.005|[-0.025, 0.022]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|Fisher|5|80|-0.006|[-0.017, 0.040]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|TTA|0|80|-0.025|[-0.064, 0.029]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|TTA|1|80|0.019|[-0.067, 0.073]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|TTA|2|80|0.004|[-0.045, 0.039]|
|kinmus_uji_scoreonly_v3_20261012__C1_primary|TTA|3|80|0.053|[-0.000, 0.118]|
|show3d_scoreonly_v3_20261012__C1_primary|pose|0|80|1.295|[0.794, 1.875]|
|show3d_scoreonly_v3_20261012__C1_primary|pose|2|80|1.292|[0.729, 1.976]|
|show3d_scoreonly_v3_20261012__C1_primary|pose|4|80|1.057|[0.640, 1.402]|
|show3d_scoreonly_v3_20261012__C1_primary|pose|6|80|1.126|[0.713, 1.326]|
|show3d_scoreonly_v3_20261012__C1_primary|Fisher|0|80|0.038|[0.002, 0.065]|
|show3d_scoreonly_v3_20261012__C1_primary|Fisher|1|80|-0.016|[-0.066, 0.013]|
|show3d_scoreonly_v3_20261012__C1_primary|Fisher|4|80|-0.013|[-0.041, 0.015]|
|show3d_scoreonly_v3_20261012__C1_primary|Fisher|5|80|0.060|[0.016, 0.121]|
|show3d_scoreonly_v3_20261012__C1_primary|TTA|0|80|0.294|[0.066, 0.460]|
|show3d_scoreonly_v3_20261012__C1_primary|TTA|1|80|0.019|[-0.030, 0.151]|
|show3d_scoreonly_v3_20261012__C1_primary|TTA|2|80|0.168|[0.047, 0.300]|
|show3d_scoreonly_v3_20261012__C1_primary|TTA|3|80|0.054|[-0.014, 0.154]|

The same predictions and row sets were used within each training goal; the two goals use different fixed learners and weights. Pose and Fisher fields carry related information. The table does not isolate physical causal effects, does not select a best variant, and does not count comparisons as independent confirmations.

GPU cost status: COMPLETE_OFFLINE_COST_PROFILE. See GPU_OFFLINE_COST.csv for read/view/inference/aggregation timing, peak memory and new-GPU numerical differences; these are offline whole-record times.

Lag and window tables preserve every prespecified setting. There is no selected lag or window. Lag results use a common paired-reference set with original acceptance; aggregation changes units and support. Physical synchronization and absolute-zero calibration remain unverified.

Actual checkpoint training membership needs weight-bound provenance; target semantic accuracy needs independent labels; independent human readers and physical anchors are external requirements. More server compute alone cannot complete these items.
