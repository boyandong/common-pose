# GATE 4A — DEFERRED GATE CANDIDATES (documented, NOT executed)

**Evidence level: SINGLE-USER FEASIBILITY SCREEN ONLY.**
Nothing in this file was run in Gate4A. No resource was consumed for it beyond documentation.

The long-term candidate family for a reliability gate remains:

| id | candidate | status here |
|---|---|---|
| A | Conformalized task-error predictor | scoring core prototyped as CANDIDATE 2; **not** conformalized |
| B | TTA Fisher-consistency gate | prototyped as CANDIDATE 1 |
| C | Deep Ensemble → Fisher uncertainty | **DEFERRED** |
| D | Multivariate conformal uncertainty region → Fisher uncertainty | **DEFERRED** |
| E | LTT / Conformal Risk Control | **RESERVED** for threshold calibration |

---

## C — Deep Ensemble → Fisher uncertainty

**What it is.** Train *N* (≥ 3) independent upstream pose estimators and use the spread of
their Fisher-space predictions as a per-sample uncertainty score, then check whether that
spread ranks the true Fisher displacement `r_t`.

**Why it is not run in Gate4A.**
* It requires training ≥ 3 deep models from scratch or from different seeds. Gate4A is
  forbidden from training any deep network, and Gate4A has no GPU budget for it.
* One participant cannot separate *ensemble spread* from *that participant's* noise floor.
  The quantity of interest ("does ensemble spread transfer across users?") is a
  between-user question and needs ≥ 2–3 users even to be stated.
* Gate4A's TTA candidate already probes the same underlying idea cheaply: instability
  under a label-preserving input perturbation. If the cheap probe shows no ranking
  information, an expensive ensemble is unlikely to be the first thing to try.

**Extra resources required.** A server with enough GPU to train ≥ 3 upstream models
(official `regression_vemg2pose` recipe: 500-epoch budget, early stopping patience 50,
~4 hours per model on a single 4090 class GPU, plus data staging), plus the multi-user
corpus.

**When it becomes the right experiment.** After the multi-user cohort exists *and* after
Gate4A-type cheap probes have been read. It answers "is model-instability information
recoverable with a richer uncertainty estimator?" — a question only worth asking if the
cheap estimator shows at least a weak signal.

**Whether Gate4A results justify investing later.** Decided by the Gate4A decision:
an ensemble is only worth it if at least one deployment-visible score shows consistent
ranking. If every score is `NO_VISIBLE_SIGNAL`, an explicitly uncertainty-aware upstream
model (rather than an ensemble of point estimators) is the more informative next step.

---

## D — Multivariate conformal uncertainty region → Fisher uncertainty

**What it is.** Build per-sample prediction regions from the upstream model, map the region
into the frozen 7-D Fisher space, and use the region's Fisher-space extent as the
reliability score.

**Why it is not run in Gate4A.**
* Conformal validity needs exchangeable units. Gate4A has exactly one participant and one
  session, with strong temporal and within-subject dependence; frames are not exchangeable.
  Any coverage number produced here would be a within-session curve, not a guarantee.
* The upstream estimator exposes no per-sample region: it is a deterministic point
  regressor. Producing a region requires an auxiliary model (heteroscedastic head, quantile
  regression, or residual modelling), which is a new modelling decision, not a measurement.
* A per-sample 20-D pose region mapped through a fixed linear Fisher transform needs a
  defensible region construction *before* any coverage statement is meaningful.

**Extra resources required.** Development / calibration / held-out test users; a
region-producing upstream or auxiliary model; a frozen calibration protocol.

**When it becomes the right experiment.** In the multi-user stage, once a candidate
score family is selected, as the *calibrated* version of a task-error predictor.

---

## E — LTT / Conformal Risk Control

**Status: RESERVED for future threshold calibration — deliberately NOT a Gate4A item.**

* LTT/CRC answer "which threshold on an already-chosen score provably controls risk at a
  chosen level?" They do not generate a score and cannot rescue a score with no ranking
  information.
* Selecting any threshold from the current single participant would be exactly the
  threshold-fitting that Gate4A forbids.
* Ordering for the future: freeze the multi-user cohort design (development users →
  calibration users → held-out test users), select the score family on development users,
  calibrate on calibration users, and only then apply LTT / CRC on held-out users.

---

## Not-deferred (explicitly refused, not merely postponed)

Absolute distance-to-DB9-cloud scoring, OCSVM / GMM / SIMCA novelty gates, hard-class
agreement targets, human gesture labels, and DB9 probability-cloud rescue are **out of
scope for this line of work**, not deferred. Gate4A does not run them and the multi-user
stage is not planned around them.
