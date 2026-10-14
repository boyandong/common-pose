# Common Pose

**A research framework for testing whether physical hand pose can decouple biosignal estimation from downstream hand tasks.**

> **Status — active research.**
> A physically audited downstream posture baseline is now frozen on NinaPro DB9.
> Cross-upstream task reuse — the central Common Pose hypothesis — has **not yet been demonstrated**.

---

## Research Question

Most EMG interfaces are trained directly for a specific task:

    EMG → task label

That couples the sensor decoder to the task. Adding a new task can require new task-specific EMG data and retraining.

Common Pose asks a different question:

> **Can a downstream task model be trained only from physical hand pose and task labels, then consume pose produced by an independent biosignal-to-pose estimator without task-specific EMG retraining?**

The proposed decomposition is:

    biosignal
       ↓
    pose estimator
       ↓
    source adapter
       ↓
    Common Pose
       ↓
    pose-only downstream task

The project is not assuming that this decomposition works. It is building the interface and the experiments needed to test whether it does.

---

## Why It Matters

A shared hand-pose representation is only useful if the numbers mean the same physical thing across sources.

In practice, apparently compatible datasets can disagree in:

- joint ordering,
- units,
- sign conventions,
- physical zero,
- calibration procedures,
- handedness,
- invalid-sample encoding,
- sensor fit and channel validity.

This project therefore treats pose interoperability as a **measurement and interface problem**, not only a machine-learning problem.

A joint name matching across two datasets is not sufficient evidence that their numeric coordinates are interchangeable.

---

## Core Idea

A Common Pose frame is intended to make the physical meaning of a pose explicit.

Each pose dimension should eventually carry:

- anatomical degree of freedom,
- value and unit,
- positive direction,
- zero / reference definition,
- handedness convention,
- calibration provenance,
- validity state,
- timestamp,
- optional recent history.

The API itself is still evolving. A dataset-specific vector such as `canonical16` is **not** treated as the final interface.

---

## My Role

I lead the project's:

- problem formulation and system decomposition,
- experimental design and scientific gating,
- cross-dataset coordinate and calibration audits,
- interpretation of negative results and stop / rescope decisions,
- reproducibility and evidence-governance strategy.

A major focus of the project has been separating implementation success from scientific evidence: code that runs, a classifier that scores well, and a physically valid interface are treated as different claims.

---

## Current Evidence

### 1. A physically audited DB9 posture representation

NinaPro DB9 was not used as a black-box kinematic benchmark.

Channel validity was evaluated from physical movement anchors and released sensor/calibration behavior **before downstream classification performance was inspected**.

The frozen representation,

`TRUSTED_DB9_POSE_v1`,

contains eight retained dimensions:

    MCP1
    IP1
    MCP2_f
    PIP2
    MCP3_f
    MCP4_f
    MCP5_f
    PIP5

The subset was subsequently revalidated across **all 77 DB9 participants**. None of the eight retained channels changed status.

Several released channels were excluded or left unresolved. In particular, the released `CMC5` representation was found to derive from the same raw glove column used by `WRIST_F`, despite the published calibration assigning these quantities to different sensors.

Full evidence: [`docs/db9_trusted_subset.md`](docs/db9_trusted_subset.md).

---

### 2. The trusted subset still carries posture information

The downstream utility test uses the official DB9 Exercise-B hand configurations, movement IDs **1–8 only**.

Evaluation:

- 77 participants,
- leave-one-subject-out,
- global subject identity derived from archive identity rather than the source-local `subject` field,
- train-fold-only standardisation,
- one simple LDA per fold,
- fixed per-segment frame cap to prevent source-database recording duration from determining sample weight.

| representation | balanced accuracy | macro-F1 |
|---|---:|---:|
| historical 16-channel representation | 0.8556 | 0.8559 |
| `TRUSTED_DB9_POSE_v1` | **0.7479** | **0.7460** |
| chance | 0.1250 | — |

The trusted subset has no class collapse. Class 4 remains the weakest configuration (`recall = 0.495`) and will be reported separately in future transfer experiments rather than hidden inside an aggregate score.

The goal of this result is not to maximise DB9 classification accuracy. It establishes that a representation selected for physical validity still retains useful downstream posture information.

---

### 3. The upstream pose side has been brought under the same interface assumptions

The official emg2pose model and mini corpus have been used to verify:

- the released joint ordering,
- angle units and flexion conventions,
- the model’s temporal context,
- pose-output timing,
- invalid inverse-kinematics encoding.

These checks establish interface facts, **not** an end-to-end Common Pose result.

The official mini corpus covers a single held-out user, so results derived from it are not presented as a cross-user benchmark.

---

## Corrective and Negative Findings

Several attractive intermediate conclusions did not survive audit.

- An earlier DB9 screen reported that most candidate channels failed. That result was partly caused by segmentation on a pre-relabelling acquisition vector that is misaligned with kinematics in part of the release. The result was superseded by the forensic audit.
- A first DB9 forensic pass covered only 37 participants because the loader selected the protocol by filename exercise code. DB2 stores the same 17-movement protocol under a different exercise number. Selection by data content recovered the full 77-participant cohort.
- A ten-dimensional KIN-MUS representation was initially interpreted as ten intended anatomical DOFs. Four columns had been assigned semantics from a different UJI column order. The numerical experiment remains a feature-space result, but the physical interpretation was withdrawn.
- Simple distributional/open-set transfer from DB9 did not provide a reliable bridge to natural emg2pose poses. Removing physically suspect DB9 channels did not rescue this branch and in some cases increased false acceptance.
- A formal human semantic-validation round was interrupted by model unblinding at an interim checkpoint. Its preregistered primary endpoint is therefore not reported as a completed result.

These failures are retained because they define what the project is currently allowed to claim.

See [`docs/research_status.md`](docs/research_status.md) for the full evidence ledger.

---

## What Is Not Yet Demonstrated

Common Pose has **not** yet established:

- that a frozen downstream task head survives substitution of the upstream pose estimator,
- cross-dataset numerical coordinate equivalence,
- arbitrary or universal downstream task reuse,
- reliable cross-dataset open-set rejection,
- a deployment-grade or frozen Common Pose API,
- multi-user end-to-end EMG → Common Pose → task generalisation.

The current software infrastructure should not be interpreted as evidence for those claims.

---

## Current Scientific Gate

The next experiment tests the central hypothesis directly:

> **Can the frozen DB9 posture head retain meaningful task behavior when the same physical DOFs are supplied by an independently produced pose stream?**

Before evaluating the task output, the upstream source must independently establish the mapping of the required DOFs, including units, signs, physical reference, validity and calibration provenance.

The mapping will not be tuned using downstream task performance.

---

## Repository Structure

    common-pose/
    ├── src/common_pose/          interface, adapters, estimators and task abstractions
    ├── audits/                   frozen dataset, coordinate and channel-validity audits
    │   ├── db9/
    │   ├── dataset_admission/
    │   └── human_semantic_validation/
    ├── experiments/              executed research branches and preserved results
    ├── docs/                     architecture, evidence ledger and technical documentation
    ├── provenance/               curation manifests and source/content hashes
    ├── scripts/                  repository curation and publication checks
    └── tests/                    software and scientific-contract tests

The repository intentionally preserves negative and superseded research artifacts. Their presence does not mean their original conclusions remain current; authoritative status is recorded in [`docs/research_status.md`](docs/research_status.md).

---

## Reproducibility and Data Boundary

Third-party datasets are **not redistributed** in this repository.

The public repository contains:

- analysis and interface code,
- frozen protocols,
- lightweight result artifacts,
- provenance manifests,
- hashes,
- evidence ledgers.

It excludes:

- raw third-party datasets,
- model checkpoints,
- private annotator-level data,
- hidden-label / unblinding material,
- credentials and machine-local configuration.

The curated human-semantic-validation directory is intentionally incomplete because some evaluator-level material should not be public.

---

## Running the Tests

The current test suite checks software and research-contract invariants; passing it does not imply scientific validation of the Common Pose hypothesis.

    python -m pip install -r requirements.txt
    python -m pytest tests/ -q

No raw dataset or GPU is required for the contract tests.

---

## Roadmap

The immediate research sequence is:

1. freeze and document the audited DB9 downstream baseline — **completed**;
2. establish an independent source mapping for the same trusted physical DOFs;
3. test the frozen downstream head under upstream substitution;
4. separate interface/domain-shift failure from pose-estimation failure;
5. only then evaluate whether broader task or dataset interoperability is justified.

---

## Author

**Boyan Dong**
Biomedical Engineering, Southeast University

---

## Citation and License

This project is under active research and does not yet have an associated publication or preprint.

No repository-wide open-source licence has been selected while third-party code lineage is still under review. See [`docs/licensing.md`](docs/licensing.md).
