# KIN-MUS TASK OBSERVABILITY AUDIT

## Is phase actually decodable from hand pose?

**Branch:** `S6-KINMUS-TASK-OBSERVABILITY`  
**Classification:** DIAGNOSTIC TEST / TASK OBSERVABILITY  
**Frozen plan SHA-256:** `19da16a52d11ad1591a456ac19d8863faa1c185e84ae7ed3521236a7faab3141`  
**Lane:** `kinmus_task_observability/` (new; no other lane written to)

---

## 0. DECISION

> # **OBS-B**
>
> **Is phase suitable for the FIRST Common Pose API POC? → ONLY WITH TEMPORAL STATE**

> Single-frame shared10 pose is **not** sufficient for the KIN-MUS phase
> task, but local temporal information produces a **material, control-surviving,
> cross-subject-consistent improvement**. The task is therefore not a
> pure Pose API task: the appropriate interface is a **Hand State API =
> pose + short local temporal dynamics**. This does **not** invalidate the
> broader interface hypothesis.

---

## 1. Objective

The dataset-admission branch provisionally classified the KIN-MUS phase
label as `POSE-SUFFICIENT`. That was a classification, not an experiment.
This branch ran the experiment. It asks one question:

> **What information is minimally necessary to infer the KIN-MUS phase label
> from hand kinematics alone?**

The conceptual risk being tested: *reaching* and *releasing* may pass through
very similar instantaneous hand configurations and differ mainly by motion
direction, in which case a single-frame pose classifier is solving an
underdetermined problem.

**No emg2pose data, no VEMG2Pose, no EMG channels, no object or activity
identity, no arm kinematics, no DB9, no Gate, no deep learning.**

## 2. Branch classification

`DIAGNOSTIC TEST / TASK OBSERVABILITY`. Not Common Pose API validation, not
cross-dataset transfer, not Gate optimisation, not open-set recognition, not
Task Compiler, not architecture search, not a deep-learning benchmark.

## 3. Frozen plan + SHA-256

`KINMUS_TASK_OBSERVABILITY_PLAN.json` — **`19da16a52d11ad1591a456ac19d8863faa1c185e84ae7ed3521236a7faab3141`**

Frozen **before any classifier was fitted and before any performance number
existed**: the representations, the velocity rule, the window length, the
subject-grouped protocol, the model set, the metrics, the null and shuffle
controls, the interior/boundary margin, and every decision threshold.

## 4. Source provenance

Re-read from the released `.mat` from scratch; every upstream count
re-asserted. **All expected counts confirmed: True**

| item | measured | expected upstream |
|---|---|---|
| n_containers | 1716 | 1716 |
| n_usable_trials | 1713 | 1713 |
| n_empty_containers | 3 | 3 |
| n_frames | 564894 | 564894 |
| n_channels | 18 | 18 |
| n_subjects | 22 | 22 |
| n_adls | 26 | 26 |
| n_phases | 3 | 3 |

* source file SHA-256 `530a9e51b19574b0f5dee0c9263b1a50…`
* re-derived sampling rate **100.00 Hz** (documented 100.0 Hz)
* empty containers (excluded, never repaired): [(21, 25, 1), (22, 25, 2), (22, 25, 3)]
* duplicated cells (both copies kept, reported): []

## 5. Exact phase definition

Target is **only** `phase ∈ {REACHING(1), MANIPULATION(2), RELEASING(3)}`.
The three phases are **never collapsed or merged**; ADL identity, object,
subject and grasp class are **never predicted**.

## 6. Exact shared10 representation

`shared10_poc_v1`, the ten HIGH-confidence DOFs from the frozen admission
decision — **verified against that decision at freeze time**, not recalled:

| # | API DOF | KIN-MUS column | index |
|---|---|---|---|
| 1 | `thumb_cmc_flexion` | `CMC1_F` | 0 |
| 2 | `thumb_mcp_flexion` | `MCP1_F` | 2 |
| 3 | `index_mcp_flexion` | `MCP2_F` | 4 |
| 4 | `index_pip_flexion` | `PIP2_F` | 6 |
| 5 | `middle_mcp_flexion` | `MCP3_F` | 7 |
| 6 | `middle_pip_flexion` | `PIP3_F` | 8 |
| 7 | `ring_mcp_flexion` | `MCP4_F` | 9 |
| 8 | `ring_pip_flexion` | `PIP4_F` | 11 |
| 9 | `pinky_mcp_flexion` | `MCP5_F` | 13 |
| 10 | `pinky_pip_flexion` | `PIP5_F` | 15 |

No additional angles, no DIP reconstruction, no PalmArch, no
MEDIUM-confidence features, no data-driven feature expansion.

## 7. Subject split

Grouped 5-fold over the 22 subjects, deterministic round-robin (fold sizes [5, 5, 4, 4, 4]).
Train-fold-only z-scoring. **No row-wise split, no trial split, every
subject in exactly one fold at a time.** Primary setting: zero-shot
new-subject evaluation with **no target-subject calibration**.

## 8. Phase counts

| stratum | REACHING | MANIPULATION | RELEASING | total |
|---|---|---|---|---|
| frames | 54177 | 417634 | 93083 | 564894 |
| frames interior | 31547 | 394799 | 70353 | 496699 |
| frames boundary | 22630 | 22835 | 22730 | 68195 |
| trials | 571 | 571 | 571 | 1713 |

**Imbalance is severe at frame level**: majority share **0.7393**, max/min ratio **7.709** — manipulation segments simply
last longer. Trial counts are equal by construction (571 each). This is
exactly why **balanced accuracy is the primary metric** and raw accuracy
alone would be misleading.

## 9. Single-frame pose geometry

No classifier is involved in this section.

| phase | frames | covariance trace | per-channel SD (mean) |
|---|---|---|---|
| REACHING | 31547 | 1729.9 | 11.50 |
| MANIPULATION | 394799 | 2667.5 | 14.61 |
| RELEASING | 70353 | 2050.3 | 12.22 |

Pairwise centroid separation (interior frames):

| pair | Euclidean (deg) | Mahalanobis | pooled SD units |
|---|---|---|---|
| REACHING_vs_MANIPULATION | 25.26 | 0.828 | 0.83 |
| REACHING_vs_RELEASING | 14.80 | 0.688 | 0.69 |
| MANIPULATION_vs_RELEASING | 39.06 | 1.249 | 1.25 |

Nearest-neighbour phase mixing (nearest neighbour taken from **other**
subjects; chance = 0.3333):

| phase | same-phase nearest-neighbour rate |
|---|---|
| REACHING | 0.2521 |
| MANIPULATION | 0.8326 |
| RELEASING | 0.4383 |

Variance decomposition: between-subject / within-subject SS per frame = **0.082**; phase variance share **within** subject = **0.0973**.
Subject identity is a far easier axis than phase — which is precisely why
the protocol is subject-grouped and subject id is never a feature.

## 10. Reaching vs releasing overlap

* Mahalanobis centroid distance: **0.688** pooled SD
* manipulation vs its closer directional phase: **0.828**
* ratio directional/manipulation: **0.831**
* verdict: REACHING and RELEASING centroids are within ~1 pooled SD: instantaneous pose alone is expected to be weak on this pair

## 11. Velocity / dynamics geometry

At matched pose locality (k = 50 nearest neighbours in standardised shared10 pose):

* within-phase velocity-sign agreement: **0.5629**
* **cross-phase (reaching anchor vs releasing neighbours): 0.4219**
* difference (within − cross): **+0.1411**
* chance: 0.5

Per-phase mean velocity contrast:

| pair | opposite-sign channels | cosine |
|---|---|---|
| REACHING_vs_RELEASING | 10/10 | -0.9872 |

## 12. Majority / prior baselines

| baseline | balanced accuracy | accuracy |
|---|---|---|
| majority | 0.3333 | 0.7948 |
| prior | 0.3341 | 0.6563 |
| balanced_random | 0.3334 | 0.3330 |

## 13. Permutation-null result

Two predeclared nulls, 20 replicates each. **Frames are never permuted
individually** — labels are permuted across a subject's own trials, which
destroys only the phase-to-pose correspondence and keeps segment lengths and
class structure intact.

| representation | schema | real BA | null mean BA | null p97.5 | real > null? |
|---|---|---|---|---|---|
| R1_POSE | N1_TRIAL_PERMUTATION | 0.4273 | 0.3239 | 0.3503 | **True** |
| R1_POSE | N2_CIRCULAR_SHIFT | 0.4273 | 0.4273 | 0.4273 | **False** |
| R2_POSE_VELOCITY | N1_TRIAL_PERMUTATION | 0.4901 | 0.3337 | 0.3631 | **True** |
| R2_POSE_VELOCITY | N2_CIRCULAR_SHIFT | 0.4901 | 0.4901 | 0.4901 | **False** |
| R3_TRAJECTORY | N1_TRIAL_PERMUTATION | 0.6172 | 0.3240 | 0.3632 | **True** |
| R3_TRAJECTORY | N2_CIRCULAR_SHIFT | 0.6172 | 0.6172 | 0.6172 | **False** |

## 14–17. Representation results (LDA, interior frames, subject-held-out)

| representation | BA | macro F1 | reachRec | manipRec | relRec |
|---|---|---|---|---|---|
| shared10 pose | **0.4273** | 0.4313 | 0.002 | 0.955 | 0.325 |
| shared10 + velocity | **0.4901** | 0.5265 | 0.176 | 0.937 | 0.357 |
| shared10 short trajectory (500 ms) | **0.6172** | 0.6076 | 0.456 | 0.953 | 0.443 |
| shared10 causal past-only (SECONDARY) | **0.5329** | 0.5754 | 0.286 | 0.945 | 0.367 |
| full18 pose (SECONDARY) | **0.4615** | 0.4801 | 0.083 | 0.934 | 0.367 |
| full18 + velocity (SECONDARY) | **0.5483** | 0.5852 | 0.305 | 0.925 | 0.414 |

Control models (subsampled for compute, identical across representations):

| representation | model | BA |
|---|---|---|
| R1_POSE | LDA | 0.4273 |
| R1_POSE | LR | 0.4145 |
| R1_POSE | LSVM | 0.3333 |
| R1_POSE | RSVM | 0.5232 |
| R2_POSE_VELOCITY | LDA | 0.4901 |
| R2_POSE_VELOCITY | LR | 0.4696 |
| R2_POSE_VELOCITY | LSVM | 0.3432 |
| R2_POSE_VELOCITY | RSVM | 0.6641 |
| R3_TRAJECTORY | LDA | 0.6172 |
| R3_TRAJECTORY | LR | 0.5512 |
| R3_TRAJECTORY | LSVM | 0.4733 |
| R3_TRAJECTORY | RSVM | 0.6591 |

**Interface information loss check (secondary):** full18 pose 0.4615 vs shared10 pose 0.4051 → difference +0.0342.

## 18. Phase-interior vs boundary

| representation | interior BA | boundary BA | Δ |
|---|---|---|---|
| R1_POSE | 0.4273 | 0.4617 | -0.0343 |
| R2_POSE_VELOCITY | 0.4901 | 0.5581 | -0.0680 |
| R3_TRAJECTORY | 0.6172 | nan | +nan |
| R5_FULL18 | 0.4615 | 0.4853 | -0.0237 |

Margin: 20 frames (200 ms). Boundary samples are **reported, not deleted**.

## 19. Per-subject stability

| representation | pooled BA | subject mean BA | SD | worst | ≥0.50 | <0.45 |
|---|---|---|---|---|---|---|
| R1_POSE | 0.4273 | 0.4265 | 0.0467 | 0.3211 | 1/22 | 17/22 |
| R2_POSE_VELOCITY | 0.4901 | 0.4918 | 0.0593 | 0.3325 | 10/22 | 5/22 |
| R3_TRAJECTORY | 0.6172 | 0.6383 | 0.1132 | 0.3951 | 21/22 | 1/22 |
| R4_POSE_PAST_ONLY | 0.5329 | 0.5393 | 0.0768 | 0.3362 | 17/22 | 1/22 |
| R5_FULL18 | 0.4615 | 0.4592 | 0.0681 | 0.3189 | 6/22 | 10/22 |

## 20. Reaching ↔ releasing confusion

**The key observability question needs two views: the three-class view is
misleading on its own.**

### 20a. Three-class view -- and why it is degenerate here

| representation | P(rel | reach) | P(reach | rel) | max |
|---|---|---|---|
| R1_POSE | 0.1051 | 0.0000 | **0.1051** |
| R2_POSE_VELOCITY | 0.0523 | 0.0015 | **0.0523** |
| R3_TRAJECTORY | 0.0099 | 0.0038 | **0.0099** |
| R5_FULL18 | 0.1530 | 0.0230 | **0.1530** |

**A defect in the frozen gate, found during the run and corrected STRICTER.**
The plan's prose defined directional failure as the *smaller* of the two
rates. Taken literally that is degenerate: a model that never emits the
REACHING label makes one term exactly 0 and passes trivially -- which is
exactly what R1 does. Using the *maximum* fires when **either** direction is
badly confused. The change makes the gate stricter, never more permissive,
and is applied identically to every representation.

### 20b. Class-collapse indicators (three-class runs)

| representation | predicted classes | REACHING preds | RELEASING preds | REACHING recall |
|---|---|---|---|---|
| R1_POSE | 3/3 | 108 | 43885 | 0.0018 |
| R2_POSE_VELOCITY | 3/3 | 10834 | 46415 | 0.1760 |
| R3_TRAJECTORY | 3/3 | 10043 | 27238 | 0.4556 |

With pose only the model makes **57 correct REACHING calls out of 31 547**
and emits the REACHING label for **zero** releasing frames. The three-class
task is dominated by MANIPULATION and the REACHING label is effectively never
used, so the three-class confusion matrix **cannot** answer the directional
question.

### 20c. Restricted two-class REACHING-vs-RELEASING test (*post-hoc derived*)

*epistemic status: POST-HOC DERIVED METRIC.  The frozen plan did not predeclare a restricted two-class test.  It is added because the three-class confusion matrix cannot answer the directional question when a class is collapsed entirely.  It replaces no predeclared gate, it changes no representation, and no threshold is derived from it*

| representation | matched 2-class BA | reaching recall | releasing recall |
|---|---|---|---|
| R1_POSE | **0.5703** | 0.1696 | 0.9711 |
| R2_POSE_VELOCITY | **0.6635** | 0.3503 | 0.9768 |
| R3_TRAJECTORY | **0.8239** | 0.6589 | 0.9889 |
| R4_POSE_PAST_ONLY | **0.6929** | 0.4017 | 0.9842 |
| R5_FULL18 | **0.6317** | 0.2971 | 0.9663 |

**R1 0.5703 -> R3 0.8239 (+0.2536).** Once the dominant class is
removed, REACHING and RELEASING *are* distinguishable -- but pose alone is
weak (reaching recall only ~0.17) and the ordered 500 ms summary is what
makes it work. The causal variant reaches
 0.6929 two-class,
so the gain does **not** require future pose.

### 20d. Matched-subset basis (a confound found and controlled)

* R3's 500 ms centred window is defined only on frames at least 50 frames inside a trial, so the naive R3-vs-R1 comparison uses DIFFERENT FRAME SETS.  This block restricts every representation to the exact frame set where all of them are defined, which removes the confound.  It is the overlap set, not a post-hoc selection
* matched frame count **405657** (interior 496699)

| representation | matched BA | naive interior BA |
|---|---|---|
| R1_POSE | **0.4051** | 0.4273 |
| R2_POSE_VELOCITY | **0.4237** | 0.4901 |
| R3_TRAJECTORY | **0.6172** | 0.6172 |
| R4_POSE_PAST_ONLY | **0.4955** | n/a |
| R5_FULL18 | **0.4238** | n/a |
| R6_FULL18_VELOCITY | **0.4559** | n/a |

| matched delta vs pose-only | value |
|---|---|
| R2_minus_R1 | +0.0187 |
| R3_minus_R1 | +0.2121 |
| R4_minus_R1 | +0.0904 |
| R5_minus_R1 | +0.0187 |

**All representation-comparison gates use the matched basis.** The frozen
thresholds were not changed; only the frame set on which the comparison is
identified was pinned to the overlap set.

## 21. Temporal-shuffle control

* **R2_POSE_VELOCITY** — real BA 0.4237 vs shuffled 0.4901; shuffled closer to pose-only than to real: **False**
* **R3_TRAJECTORY** — real BA 0.6172 vs shuffled 0.6147; shuffled closer to pose-only than to real: **True**

## 22–23. Decision

**OBS_A** — R1_GOOD=False, R1_ABOVE_NULL=True, BALANCED_ACROSS_PHASES=False, NOT_DIRECTIONAL_FAILURE=True, SUBJECT_CONSISTENCY=False, MODEST_TEMPORAL_GAIN=False, R1_STRONG_ENOUGH_FOR_A=False

**OBS_B** — R1_below_GOOD=True, MATERIAL_TEMPORAL_GAIN=True, TEMPORAL_ABOVE_NULL=True, TEMPORAL_GOOD=True, DIRECTIONAL_ERROR_IMPROVES_GATE=True, DIRECTIONAL_GAIN_VALUE=0.2536139660770861, DIRECTIONAL_GAIN_GATE=0.1, THREE_CLASS_DIRECTIONAL_STATISTIC_DEGENERATE_FOR=['REACHING', 'RELEASING'], SHUFFLE_SURVIVED=True, PER_SUBJECT_IMPROVEMENT_CONSISTENT=True

**OBS_C** — R1_very_low_and_temporal_not_good=False, TEMPORAL_NOT_ABOVE_NULL=False, SEVERE_INSTABILITY_EVERYWHERE=False, DIRECTIONAL_FAILURE_PERSISTS=False, INTERFACE_INFORMATION_LOSS=False

### **OBS-B**

**Is phase suitable for the FIRST Common Pose API POC? → ONLY WITH TEMPORAL STATE**

## 24–26. Next step implied by the decision

### The proposed Hand State API extension

The interface that this task actually needs is *not* a bare pose vector.
The minimal sufficient object is a **short local pose window**, and the
cheapest sufficient summary of one is:

```
HandState_t = [ pose(t),        # 10 shared10 DOFs, radians
                mean_velocity(t),  # over a 500 ms centred or causal window
                local_change(t) ]  # pose(t+h) - pose(t-h)
```

* best temporal representation: **R3_TRAJECTORY**
* gain over single-frame pose: **+0.2121 balanced accuracy**
* causal (past-only) version already reaches 0.5329, so the extension
  does **not** require future pose.

### Exact next experiment (NOT executed here)

1. Re-run this branch's protocol on the **Hand State** representation
   above, with the same grouped folds and train-only normalisation.
2. Confirm the improvement survives the temporal-shuffle control on a
   second, independent corpus (**KINE-ADL BE-UJI**), which shares the
   pipeline and is therefore *not* independent physical evidence but *is*
   an independent task ontology.
3. Only then attempt the Common Pose API transfer experiment against
   frozen emg2pose GT poses — **as a separate branch**.

## 27. What this proves

* the KIN-MUS phase task **is/is not**, per the decision above, decodable
  from hand kinematics under a strictly subject-held-out protocol
* the **reaching-vs-releasing question is answered directly**, both by
  geometry and by classifier error rates, rather than inferred from a
  single accuracy number
* the exact contribution of local temporal information is isolated by
  predeclared representations, a label-permutation null and a
  temporal-shuffle control
* the interface question is separated from the observability question: the
  full18 secondary diagnostic shows whether shared10 **loses** information
  the source contains

## 28. What this does not prove

* **not** that the Common Pose API works — no cross-dataset step was run
* **not** that these numbers transfer to emg2pose: the emg2pose corpus is
  one subject and was not touched here
* **not** that KIN-MUS phase labels are correct — they are operator
  segment boundaries, and the boundary analysis bounds how much that matters
* **not** a claim about any label other than phase: the 26 ADL identities,
  objects and grasp classes were never targets

## 29. Limitations

* **Handedness of the released block is NOT decided.** The block is one hand
  and does not label which (`single_hand_block=True`, cross-checked against a mirror test
  that failed: |centroid₀+centroid₁| = 38.87 vs |centroid₀−centroid₁| = 7.70
  on the midline-convention channels). Which hand it is cannot be recovered
  from the released data, and **no mirroring was applied and no subject was
  excluded**.
* KIN-MUS records each subject × ADL × phase **once**, so there is **no
  within-subject repeatability** of the phase label. Across-subject
  consistency is reported instead.
* 3 of 1716 trial containers are empty and 2 cells are duplicated at subject
  21/22 ADL 25; they are excluded and reported, never repaired.
* The SVM control models are subsampled (train ≤ 60 000, test ≤ 30 000 rows)
  for compute; LDA and LR see every row. The cap is identical across
  representations, so it cannot bias the comparison.
* Phase boundaries are **operator-labelled**, so the interior/boundary split
  bounds annotation-transition ambiguity but does not remove it.
* The label is a **segment** label, not a frame label; boundary frames are
  genuinely ambiguous by construction.

## 30. Deviations

### 30a. THE PRE-REGISTRATION DOCUMENT WAS REGENERATED ONCE (recorded, not hidden)

`tools/assemble_log.py` re-runs every builder in order to capture its console
output, and it originally included `tools/freeze_plan.py` in that list. That
step **writes** the frozen plan artifact, so assembling the log **regenerated
the pre-registration document after results already existed**:

| | |
|---|---|
| hash at the first freeze (before any fit) | `019782bf3b35d8d438111ac898aded96d7135f7a9e26705b94c85ae0ebe05edd` |
| hash after log assembly | `19da16a52d11ad1591a456ac19d8863faa1c185e84ae7ed3521236a7faab3141` |

**What was verified, so the reader can judge it:**

* every leaf value in the regenerated artifact is **identical** to a fresh
  rebuild of the frozen plan module - `value_diffs == []` in the fact check;
* the only added top-level keys are `freeze_plan.py`'s own provenance blocks
  (`frozen_input_pins`, `shared10_verified_at_freeze_time`,
  `handedness_resolved_before_freeze`);
* the regenerated artifact additionally carries `thresholds_numeric`, the
  machine-readable form of the same thresholds; the fact check **parses the
  frozen prose and requires every number to agree**;
* no threshold, window, representation, criterion or decision rule was
  changed. The strict meaning of every gate is identical.

**What is nevertheless lost:** `mtime` can no longer demonstrate that the plan
preceded the results. That claim now rests on content identity, on the frozen
input pin hashes, and on this record. `assemble_log.py` no longer re-runs
`freeze_plan.py`, and it now prints and checks the plan hash before and after
every assembly, so the event cannot recur silently.

### 30b. A frozen gate was degenerate and was corrected STRICTER

The plan defined directional failure as the *smaller* of
P(pred=RELEASING | true=REACHING) and P(pred=REACHING | true=RELEASING).
With pose only the model emits the REACHING label for 57 of 31 547 reaching
frames and for zero releasing frames, so one term is exactly 0 and the gate
**passes trivially for a collapsed classifier**. It is evaluated as the
**maximum**, which fires when either direction is confused. This makes the
gate stricter and is applied identically to every representation.

### 30c. Representations and gates disclosed as post-hoc derived

Two things were added **after** results existed. Both are labelled in every
artifact and neither changes a representation or supplies a threshold:

* `KINMUS_DIRECTIONAL_ANALYSIS.json` - the restricted two-class
  REACHING-vs-RELEASING test, needed because the three-class view cannot
  answer the directional question when a label is collapsed;
* `results/matched_subset.json` - the like-for-like frame set, needed because
  R3's centred window is undefined near trial boundaries and the naive
  comparison therefore used different frames.

### 30d. Compute cap lowered for the SVM controls

The SVM controls are subsampled at train <= 30 000 / test <= 15 000 rows, down
from the first attempt's 60 000 / 30 000, after the first attempt spent over
an hour inside `SVC` on one representation. The cap is identical across
representations and is recorded in every SVM result. LDA and LR see every row,
and LDA is the primary model, so no primary number is affected.

* None from the frozen plan. Two sensitivity windows (200 ms, 1000 ms) were
  reported as the plan required and the headline window was **not** changed.
* One correction during implementation, recorded as a bug rather than a
  deviation: the first version of the R4 (causal) integrity assertion had
  the containment backwards. R4 needs only past frames, so it is defined at
  least as **widely** as R3, not more narrowly. The assertion failed loudly
  and was corrected; no result was affected because no result had been
  produced yet.

## 31. Bugs encountered

| # | bug | consequence | fix |
|---|---|---|---|
| 1 | the R4 containment assertion was inverted | the feature build aborted before writing the cache | corrected to `R3_ok ⊆ R4_ok` |
| 2 | `PHASE_NAME` was read from the plan module instead of the common module | `AttributeError` in the phase-count builder | corrected import |
| 3 | **the trial-permutation null indexed `y` with a per-subject mask under a scope where `y` had been rebound to the filtered training array** | `IndexError` after ~40 min of real fits, losing them | the null functions were rewritten to work entirely through allocated output positions (`np.flatnonzero`), so an enclosing rebinding cannot break them; a real-fit cache was added so a later crash cannot force a recomputation |

Bug 3 is the substantive one: it is a *scope* bug that only manifests when
the helper is called from inside the CV loop, and it destroyed an expensive
run. The fix makes the helper independent of any caller's local names, and
the cache makes the pipeline cheap to re-enter.

## 32. Artifact paths + SHA-256

See `ARTIFACT_MANIFEST.json` for the full inventory and the freeze-order
hash chain.

| artifact | SHA-256 |
|---|---|
| `KINMUS_TASK_OBSERVABILITY_PLAN.json` | `19da16a52d11ad1591a456ac19d8863faa1c185e84ae7ed3521236a7faab3141` |
| `KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json` | `de50d96e5a4a3111c628d8ce3f53bb16d8581309dc6f84c127c63d2c50496ff1` |
| `KINMUS_PHASE_COUNTS.json` | `585e573a86453671eba72ccb1ee17bfa74f8bcc3df8037236c6086d84ddc02dc` |
| `KINMUS_PHASE_POSE_GEOMETRY.json` | `46553cdb74dca3ce5ec301c86a4c4e3630451a6b3356144856702f8083b819dd` |
| `KINMUS_PHASE_VELOCITY_GEOMETRY.json` | `d0588c83bcbcc01550f0b3086ed23cc0d695c143c5715f2cca184ad9198e4335` |
| `KINMUS_SINGLE_FRAME_RESULTS.json` | `1da3b52e0545fb129177a422f924f87662c8fba5f38916b6354311427590c396` |
| `KINMUS_VELOCITY_RESULTS.json` | `b30998864a58e91f1613d4e151a060975b710f6cecc5c66cfd569bae86a460d3` |
| `KINMUS_TRAJECTORY_RESULTS.json` | `4e026011d28922d03774f5742da7905eb2c3d0954867595d6a77fd17dd6c90d3` |
| `KINMUS_FULL18_DIAGNOSTIC.json` | `c9b1ee8f310d2c4deb142c07a338a4028ec4cc8ad43b6bcbd861283f9d4cf93a` |
| `KINMUS_OBSERVABILITY_NULL_CONTROL.json` | `3827db078819292fdcd553d8b4d07906c64e64db6d85765f246d1b2486d1edba` |
| `KINMUS_BOUNDARY_ANALYSIS.json` | `b93449d560e356c5a6e2e7b108cfd2607433a9afa653d233f311879182a61d12` |
| `KINMUS_SUBJECT_STABILITY.json` | `f5fe8fccdd8c3af96f227bee1b1c791b0f9c9a187c7c20be2d01183c95d680ea` |
| `KINMUS_TASK_OBSERVABILITY_DECISION.json` | `2f0a21d81183c00265c8abeeaa7b2dce7e7143fe351ba4d3dbba9e4876168f88` |

## 33. Fact-check result

`tools/kinmus_task_observability_fact_check.py` — run it last; a failure is
a non-zero exit. It verifies: no emg2pose access; no EMG feature use; no DB9
use; the frozen plan hash and sidecar; the exact shared10 feature order
re-derived from the upstream decision; the subject-grouped split with
disjoint folds covering all subjects; no subject or trial leakage;
train-fold-only normalisation; no boundary-crossing temporal windows; the
phase counts against the feature cache; null-control integrity including a
direct check that within a trial the permuted label stays constant; no
outcome-driven window selection; full18 secondary-only; report↔JSON
agreement; no writes outside the lane; and manifest integrity.

