# SESSION HANDOVER — S6/COMMON POSE API DATASET ADMISSION

**Recommended successor session name:**
`EMG2POSE-POC1-20260921-KINMUS-PHASE-TRANSFER`

**Lane:** `<PROJECT_ROOT>\pose_api_dataset_admission\` (new; no other lane was modified)
**Date:** 2026-09-21
**Status:** **BRANCH COMPLETE — DECISION `FIRST_POC_DATASET = KIN-MUS UJI`.**
**HUST = REJECT · KINE-ADL BE-UJI = CONDITIONAL · KIN-MUS UJI = ADMIT.**
Use the ASCII junction `<PROJECT_ROOT>` for all tooling.

> **Read this first.** The branch answered its one question: which external
> kinematic dataset deserves to be the first real test of the Common Pose API.
> KIN-MUS UJI won on physical-coordinate trustworthiness. Nothing was trained and
> nothing was scored. Two findings about HUST are decisive and a reader must not
> learn them elsewhere: **its associated publication was retracted by PLOS ONE,
> and its raw data cannot be obtained by any public route.**

---

## 0. Headline

| | |
|---|---|
| Question | Which external kinematic dataset is technically qualified to become the first serious source dataset for the Common Pose API? |
| Answer | **KIN-MUS UJI** (Zenodo `10.5281/zenodo.3469380`, CC-BY-4.0) |
| Frozen plan | `DATASET_ADMISSION_PLAN.json`, SHA-256 **`4d2c8b162e2332a5891a5d89a53166e365b1bbd92c205222492d19957c9683ec`** |
| HUST | **REJECT** — data unobtainable (HTTP 500 / PoW / no archive copy), no channel list, signs/zero/calibration UNKNOWN, licence UNKNOWN, **publication RETRACTED** |
| KINE-ADL BE-UJI | **CONDITIONAL** — Mendeley `10.17632/8mf4y2srgh.4`, CC BY 4.0, 20 subjects, 1160 recordings; corpus not downloaded, pipeline verified |
| KIN-MUS UJI | **ADMIT** — 22 subjects, 26 ADLs, 3 phases, 564 894 frames, 12 shared DOFs (10 HIGH) |
| The representation | **`shared10_poc_v1`** — 10 DOFs, all HIGH confidence, degrees→radians only |
| The decisive evidence | the documented-direction anchor test **passes in 22/22 subjects** for every mapped channel, versus **failing in 100 % of subjects for three channels on DB9** |
| Verification | `tools/dataset_admission_fact_check.py` — **420 assertions, all pass** |

## 1. What this branch did NOT do

No model was trained, no pose was scored, no threshold was fitted, no accuracy was
compared. No classifier, Gate, AutoML run, Gaussian/SIMCA/GMM/OCSVM, kNN gate,
conformal predictor, SelectiveNet, OpenMax, PROSER, energy method or prototype OSR
was constructed or discussed as a choice. No VEMG2Pose inference ran. No human
label was read. No affine transform was fitted to emg2pose. **DB9 was not
rescued, retuned, repaired or rerun** — it appears only as historical context and
as the origin of two criteria. No frozen artifact of any other lane was modified.
No write occurred outside this lane.

## 2. Verified state (executed, not inferred)

| item | evidence |
|---|---|
| Frozen plan | hashed before any comparison; sidecar agrees; no BOM |
| API requirement | canonical16 recovered from `canonical_hand.py` + `canonical16_schema.json` + the contract doc, all pinned by SHA-256; nothing from memory |
| Download attempts | `logs/fetch_results.json`; HUST attempted on **three** independent routes and failed on all three |
| KIN-MUS | 86 661 263 bytes downloaded, SHA-256 recorded, parsed: 1716 containers, 1713 usable, 564 894 frames, (N,18) |
| Angle formulas | read line by line out of the authors' released `obtain_angles_RL_abd_rel.m` and `gains_identification.m` |
| Anchors | manipulation-vs-reaching flexion sum **22/22 subjects positive**, median **+66.44°** |
| Quality | 0 NaNs, 0 constant channels, 0 aliases, no artefactual saturation; 3 empty trials + 2 duplicated cells reported |
| Mapping | 16 API rows + an 18-entry release inventory; 12 HIGH+MEDIUM, 10 HIGH, 4 NONE |
| Fact check | **420 assertions, all pass** |

## 3. THE TWO FINDINGS ABOUT HUST THAT MATTER

**(a) The publication was RETRACTED** by PLOS ONE on 4 March 2016
(`doi:10.1371/journal.pone.0151685`). The notice: the editors "consider that the
work cannot be relied upon". The Dryad record hosting the data carries the
retraction **in its own title**. Consequence: **no HUST claim about units, signs,
zero, calibration or subject structure can rest on the paper.**

**(b) The raw data cannot be obtained.** The published URL
`handcorpus.org/datasets/HUSTdataset.zip` returns **HTTP 500** on every attempt.
The **Wayback Machine holds no capture** of it (the archived handcorpus dataset
files are only HapticEgg.mat, HapticPCMouse.mat, TUBerlin2015June…zip and
UNIPI2014July.c3d). The Dryad download endpoint is behind an **Anubis
proof-of-work interstitial** (HTTP 403 to an automated GET). The page publishes a
**DOF count (16), not a joint list**.

This is why HUST's rows in the mapping matrix are **all `NONE`** and its
sign/zero/calibration fields are **`UNKNOWN`** rather than guessed.

## 4. THE CENTRAL LIMITATION OF THE CANDIDATE POOL

> **All three candidates are strain-gauge GLOVE datasets.** KINE-ADL and KIN-MUS
> share **five of seven** independence dimensions (group, hardware family,
> calibration method, hand model, preprocessing code) and are therefore **NOT
> independent physical evidence**. Across the whole audited set there is exactly
> **one physical pipeline family** and at most two instances of it. **No candidate
> is motion-capture-derived**, whereas emg2pose itself is an inverse-kinematics fit
> over motion capture.

A second *independent* physical source must come from a different sensor family
(motion capture, IMU fusion, or vision-based hand pose) before any claim that the
physical coordinates are *right*, rather than that one glove pipeline is
self-consistent.

**DLR and UNIPI were NOT audited.** The frozen backup rule triggers only if all
three primaries are REJECT, and one is ADMIT. The omission is a rule application,
recorded in `DATASET_INDEPENDENCE_MATRIX.json`, not an oversight.

## 5. INFERENCE / NOT VERIFIED — do not treat as established

* **KINE-ADL's corpus was never measured.** Its quality and anchors are specified
  and unrun. **No KIN-MUS measurement is reported as a KINE-ADL measurement.**
* **HUST's empirical half is impossible**, not merely undone.
* **The released KIN-MUS block is ONE hand and does not label which.** This is a
  hard prerequisite for the next experiment: if it is the left hand, a
  **documented** mirroring step is required — never a fitted one.
* **No within-subject repeatability exists** in KIN-MUS (one trial per
  subject × ADL × phase). The audit **declines** to substitute an across-frame
  statistic; what is reported is within-trial smoothness and across-subject
  agreement on the same ADL.
* **The per-subject calibration gains actually used for KIN-MUS are not
  published.** The code ships the UJI lab's own gains as placeholders and says so
  in a comment.
* **A documentation-versus-data contradiction, unresolved:** the MOVMUS guide
  states the right palmar-arch gauge malfunctioned and that "data of this DoF is
  not reported in the dataset", yet the KIN-MUS release carries a **live 18th
  column** for `PalmArch` (median 28.29°, 331 194 distinct values, max |r| with
  any other column 0.397 — neither constant nor an alias). **Reported, not
  resolved.** It does not affect the POC representation, which excludes PalmArch.
* **The "GLOVE + CALIBRATION TRANSFORM" gap is not closed.** A calibrated
  strain-gauge glove is not an IK-over-motion-capture measurement, and a
  successful transfer later would not close that metrological difference.
* **4 of 16 canonical16 variables have no released column** in the chosen source
  (all four DIPs). `shared10_poc_v1` is smaller than canonical16 **by design**.

## 6. Contaminated / discarded results

**None.** No number in the report comes from a partial run. Three aborted fact-check
runs occurred while the checker itself was being written; each produced only
assertion failures and wrote no artifact.

Nine bugs are listed in the report §25. **Two changed findings, not just tooling:**

1. `uji_row` initially treated `thumb_ip_flexion` as HIGH; reading
   `obtain_angles_RL_abd_rel.m` showed the code computes IP1 with the **PIP gain**
   (`RG_PIP(1)`), so the confidence was **demoted to MEDIUM**.
2. `probe_kinmus.py` crashed on a `(N,)`-shaped trial, which exposed **three empty
   trial containers** in the release (subjects 21/22, ADL 25) plus **two
   duplicated cells** — a real data defect now reported and excluded.

## 7. Worktree state

* Project root is **not** a git repository → **COMMIT PENDING**. Provenance is
  content-hash based; see `ARTIFACT_MANIFEST.json` `freeze_order_hash_chain`.
* `baseline/emg2pose` untouched.
* Nothing outside `<PROJECT_ROOT>\pose_api_dataset_admission\` was written
  (fact-checked).
* **Do not delete** `DATASET_ADMISSION_PLAN.json`,
  `POSE_API_DOF_MAPPING_MATRIX.json`, `FIRST_POC_DATASET_DECISION.json`, or
  `raw/kin_mus/KIN_MUS_UJI.mat`.
* **Do not re-serialise any JSON in this lane** — several artifacts carry their
  own hashes and the manifest will go stale.
* `raw/` holds 112 downloaded third-party files (97.5 MB), hashed in the manifest
  but **never treated as this branch's output**. Their licences are recorded.

## 8. External runtime state — re-verify, do not assume

* **No servers were started and none is needed.** CPU-only: file parsing,
  descriptive statistics, markdown/JSON generation. Total pipeline runtime is
  seconds once the 87 MB download exists.
* **No deep-learning training was run locally or anywhere** — the standing
  prohibition was not approached.
* No background process was left running.
* `<PROJECT_ROOT>` and `<EMG2POSE_VENV>` are junctions; if missing, recreate with
  `cmd /c mklink /J`.
* Use `<EMG2POSE_VENV>\Scripts\python.exe`. `pypdf 6.19.0` was installed into it
  for PDF text extraction — the only environment change this branch made.
* **Network quirk, re-verify before trusting:** this host's resolver answers
  `zenodo.org` with `0.0.0.0`. The audit resolves the name through an explicit
  public resolver (`Resolve-DnsName … -Server 9.9.9.9`) and passes the address to
  `curl --resolve`. A successor reproducing the fetch must do the same or it will
  see spurious DNS/connect failures.
* Other python processes seen on this machine belong to a different project and
  were not touched.

## 9. First concrete actions for the successor session

1. **Do not continue this branch.** It is closed with a decision.
2. Reproduce: `python tools/dataset_admission_fact_check.py` — 420 assertions.
   If it passes, the state is intact.
3. Full re-run order is in `DATASET_ADMISSION_FULL_LOG.txt`.
4. **Next research action** is `NEXT_POC_EXPERIMENT_PLAN.md` — **designed, not
   executed**. Before running it, do the one prerequisite: **confirm the
   handedness of the released KIN-MUS block.** If a left-hand mirror is needed, it
   must be *documented*, never fitted.
5. **Run the next experiment on a server, not locally**, per standing policy — it
   involves fitting two classical models.
6. Do **not** open the Gate question. The next experiment is deliberately limited
   to a frozen LDA and a nearest-centroid rejector.

## 10. PI decision needed

1. **Is the single-pipeline pool acceptable for the first POC?** The audit's
   position is yes for a *first* test (the question is "can a task survive the
   transfer", not "are the coordinates right"), but the independence limitation is
   real and the PI may prefer to search for a motion-capture-derived source first.
2. **Is a 10-DOF representation acceptable as the API's first shape?** This audit
   recommends `shared10_poc_v1` over 12 or 16 on physical-equivalence grounds. That
   is a reduction of the project's historical `canonical16` ambition and is a
   research-scope decision, not an engineering one.
3. **Should KINE-ADL be measured now?** It costs one download plus one unchanged
   re-run of the anchor and quality builders, and would give a second *task*
   ontology over the same physical pipeline.
