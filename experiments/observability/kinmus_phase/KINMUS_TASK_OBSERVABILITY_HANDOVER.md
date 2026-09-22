# SESSION HANDOVER — KIN-MUS TASK OBSERVABILITY

**Recommended successor session name:**
`EMG2POSE-POC1B-20260921-HANDSTATE-INTERFACE`

**Lane:** `<PROJECT_ROOT>\kinmus_task_observability\` (new; no other lane modified)
**Date:** 2026-09-21
**Status:** **BRANCH COMPLETE — DECISION `OBS-B`.**
**Is phase suitable for the first Common Pose API POC? → ONLY WITH TEMPORAL STATE.**
Use the ASCII junction `<PROJECT_ROOT>` for all tooling.

> **Read this first.** The previous branch guessed that KIN-MUS phase was
> `POSE-SUFFICIENT`. This branch tested it and the guess was **wrong**. On the
> honest like-for-like frame set, single-frame `shared10` pose reaches **0.4051**
> balanced accuracy — barely above the 0.3333 chance line — and its confusion
> matrix barely uses the REACHING label at all (**57 correct out of 31 547**).
> A predeclared 500 ms window summary reaches **0.6172** on the same frames.
> Phase is a legitimate task **only with a short temporal interface**.

---

## 0. Headline

| | |
|---|---|
| Question | What information is minimally necessary to infer the KIN-MUS phase label from hand kinematics alone? |
| Answer | **OBS-B — local temporal information is required.** Suitability: **ONLY WITH TEMPORAL STATE** |
| Frozen plan | `KINMUS_TASK_OBSERVABILITY_PLAN.json`, SHA-256 **`019782bf3b35d8d438111ac898aded96d7135f7a9e26705b94c85ae0ebe05edd`** |
| Chance BA | 0.3333 (frame majority share is 0.7393) |
| Permutation null (N1) | 0.3239 ± 0.0174 |
| **shared10 pose (matched)** | **0.4051** |
| shared10 + velocity (matched) | 0.4237 |
| **shared10 short trajectory 500 ms (matched)** | **0.6172** |
| shared10 causal past-only (matched) | 0.4955 |
| full18 pose (secondary, matched) | 0.4238 |
| Restricted 2-class REACHING-vs-RELEASING | **0.5703 → 0.8239** |
| Verification | `tools/kinmus_task_observability_fact_check.py` — **248 assertions, all pass** |

## 1. What this branch did NOT do

No emg2pose data, no VEMG2Pose, no EMG channels, no object or activity identity,
no environment information, no force/contact, no arm kinematics, no DB9, no Gate,
no open-set recognition, no deep learning, no neural network, no Transformer, no
AutoML, no architecture search, no cross-dataset transfer, no human annotation.
No post-hoc feature beyond the predeclared representations. No phase merged. No
temporal window re-selected after results. **No frozen artifact of any other lane
was modified** (the upstream admission lane's plan hash is re-verified in the fact
check).

## 2. Verified state (executed, not inferred)

| item | evidence |
|---|---|
| Frozen plan | hashed before any classifier was fitted; sidecar agrees; no BOM |
| Source provenance | re-read from the `.mat`; **all 8 expected upstream counts confirmed** (1716 containers, 1713 usable, 564 894 frames, 22 subjects, 26 ADLs, 3 phases, 18 columns, 3 empty) |
| Sampling rate | re-derived **100.00 Hz** from the trial time stamps |
| shared10 | verified against the upstream `FIRST_POC_DATASET_DECISION.json` at freeze time: order, names and indices [0,2,4,6,7,8,9,11,13,15] |
| Subject split | grouped 5-fold, deterministic round-robin, folds 5/5/4/4/4, disjoint and exhaustive |
| Normalisation | train-fold-only z-scoring; the held-out fold is transformed with train statistics |
| Windows | no R3 window crosses a trial start or end (asserted); a trial carries exactly one phase, so a window can never mix phases |
| Nulls | N1 trial permutation **20 replicates**; verified to keep one label per trial and never permute frames individually |
| Fact check | **248 assertions, all pass** |

## 3. The findings that matter

**(a) The provisional `POSE-SUFFICIENT` classification was WRONG.** On the matched
frame set, single-frame `shared10` pose gives **0.4051** BA against a null of
0.3239 — a real but tiny signal. Per-phase recalls are 0.0018 / 0.9551 / 0.3252:
the model almost never emits REACHING.

**(b) The three-class confusion matrix is a trap and this branch fell into it
first.** With pose only, the model makes **57 correct REACHING calls out of
31 547** and **zero** releasing→reaching calls. The predeclared directional gate
("the smaller of the two rates") therefore reads 0.0 and **passes trivially**.
This is a defect in the frozen gate, corrected to `max` (stricter), and the
restricted two-class test was added because the three-class view cannot answer the
directional question at all.

**(c) REACHING and RELEASING *are* distinguishable when isolated — and local
temporal structure is what makes them so.** Restricted two-class matched BA:
**0.5703 (pose) → 0.8239 (500 ms trajectory)**. Pose alone has reaching recall of
only **0.1696**; the trajectory raises it to **0.6589**.

**(d) A frame-set confound was found and controlled.** R3's 500 ms *centred*
window is undefined on frames within 50 frames of a trial end, so the naive
R3-vs-R1 comparison used **different frame sets**. Restricting every
representation to the overlap set changes R1 from 0.4273 → **0.4051** and the R3
gain from +0.19 → **+0.2121**. Only the matched numbers are used for
representation comparison.

**(e) The temporal gain is NOT motion direction.** Negating every velocity channel
leaves R2's BA **exactly unchanged** (0.4901 → 0.4901), and reversing the R3
window costs only 0.0025 (0.6172 → 0.6147). The gain comes from the window's
*pose-variation content* (net local change and local SD), not from the sign of
dθ/dt. This matters: the interface should be specified as a short pose window,
**not** as pose+velocity.

**(f) Boundary frames are EASIER, not harder.** Interior BA 0.4273 vs boundary
0.4617 for R1; the causal R4 shows 0.5329 interior vs **0.7196** boundary. Phase
extremes at segment ends are more distinctive than the middle of a segment. The
"boundary labels are ambiguous" premise is contradicted by the data.

## 4. INFERENCE / NOT VERIFIED — do not treat as established

* **Handedness of the released block is STILL NOT DECIDED.** The block is one hand
  and does not label which. The mirror test **failed** decisively
  (|c₀+c₁| = 38.87 vs |c₀−c₁| = 7.70 on the midline-convention channels; only 1 of
  5 opposes), so the block is a single hand — but *which* one cannot be recovered
  from the released data. **No mirroring was applied and no subject excluded.**
* **The restricted two-class directional test is POST-HOC DERIVED.** The frozen
  plan did not predeclare it. It replaces no predeclared gate and no threshold
  comes from it; it is labelled as such in every artifact.
* **No within-subject repeatability of the phase label exists** — KIN-MUS records
  each subject × ADL × phase once.
* **Phase labels are operator segment boundaries**, not ground truth. The interior
  /boundary split bounds that, and the unexpected result (boundary easier) means
  the split does not cleanly isolate annotation ambiguity.
* **The SVM control models are subsampled** (train ≤ 30 000, test ≤ 15 000 rows).
  LDA and LR see every row. The cap is identical across representations and is
  recorded in each SVM result. It was lowered from 60 000/30 000 after the first
  attempt spent over an hour inside `SVC` on one representation.
* **R3's 0.6172 is not "good".** It is ~0.13 above a majority-class-only strategy
  (0.7393 raw accuracy is achieved by predicting MANIPULATION throughout), and
  releasing recall is 0.4433. Phase is *partially* observable, not solved.
* **R4 (causal) is the better *deployable* candidate**: 0.7732 two-class from past
  frames only, versus R3's 0.8239 which needs 500 ms of future pose.

## 5. Contaminated / discarded results

**None retained.** Three runs were aborted by bugs and their partial output was
discarded, not used:

1. the first CV run died after ~40 min inside the permutation null (scope bug) and
   its real-fit results were lost — a cache was then added;
2. the second died on an unbound `base` in the cache flush;
3. the boundary analysis died on an empty per-subject reduction, and the geometry
   analysis on a stale dictionary key.

No number in the report comes from any of these. The real fits were re-run to
completion and cached.

## 6. Worktree state

* Project root is **not** a git repository → **COMMIT PENDING**.
* `baseline/emg2pose` untouched.
* Nothing outside `kinmus_task_observability/` was written (fact-checked).
* The upstream `pose_api_dataset_admission/` lane is **read-only** here and its
  frozen hashes re-verified.
* **Do not delete** `KINMUS_TASK_OBSERVABILITY_PLAN.json`,
  `KINMUS_TASK_OBSERVABILITY_DECISION.json`, `KINMUS_DIRECTIONAL_ANALYSIS.json`,
  or `results/features.npz`.
* **Do not re-serialise any JSON in this lane** — several artifacts carry their
  own hashes and the manifest will go stale.

## 7. External runtime state — re-verify, do not assume

* **No servers started, none needed.** CPU-only: classical convex fits on
  564 894 × 10–40 arrays. Total wall time is dominated by the RBF-SVM controls.
* **No deep-learning training ran locally or anywhere.**
* No background process left running.
* `<PROJECT_ROOT>` and `<EMG2POSE_VENV>` are junctions; recreate with
  `cmd /c mklink /J` if missing.
* Use `<EMG2POSE_VENV>\Scripts\python.exe` (numpy 1.26.4, scipy 1.13.1,
  sklearn 1.5.2). No environment change was made by this branch.
* Other python processes on this machine belong to a different project.

## 8. First concrete actions for the successor session

1. **Do not continue this branch.** It is closed with a decision.
2. Reproduce: `python tools/kinmus_task_observability_fact_check.py` — 248
   assertions. If it passes, the state is intact.
3. Full re-run order is in `KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt`.
4. **Next research action** is the Hand State interface experiment (§24 of the
   report). It must:
   * define `HandState_t = [pose(t), mean_velocity over a window, local_change]`
     explicitly, and **prefer the causal (past-only) form**, because R4 already
     achieves 0.7732 two-class without future pose and a deployable system cannot
     wait 500 ms;
   * be tested on a **server**, per standing policy;
   * **not** be a Gate or open-set session.
5. **Do not** reopen the classifier question. If a 40-feature LDA reads 0.62 with
   half a second of pose, a bigger model is a rescue, not an experiment.

## 9. PI decision needed

1. **Is `ONLY WITH TEMPORAL STATE` acceptable for the Common Pose API's first
   shape?** This branch's evidence says the API must carry a short pose window, not
   a bare pose vector. That is a change to the interface the project has been
   assuming, and it is a research-scope decision.
2. **Should phase remain the first POC task at all?** R3's three-class BA of
   0.6172 with releasing recall 0.4433 is workable for *relative* phase
   discrimination and weak for *absolute* phase. The alternative is to pick a
   task the pose reads cleanly, but no such task has been audited.
3. **Should the KINE-ADL corpus now be measured?** It shares the pipeline (not
   independent physical evidence) but is an independent task ontology, and it
   would show whether the Hand State result replicates across a second corpus.
