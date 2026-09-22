# Common Pose

A research prototype for a **common physical hand-pose interface** connecting
biosignal-based pose estimation with reusable downstream task models.

> **Status: research prototype.** The interface is being established, not shipped. Nothing
> here demonstrates universal task transfer, cross-dataset numerical equivalence, or an
> SDK. [`docs/research_status.md`](docs/research_status.md) is the evidence ledger and is
> the honest answer to "what do you actually know?".

---

## Motivation

Most biosignal interfaces are built as a single-purpose pipeline:

```
EMG ──────────────────────────────► task label
```

The decoder and the task definition are entangled. Adding a downstream task tends to mean
collecting a new task-specific EMG dataset, because the model was never asked to produce
anything reusable — it was asked to produce that one label.

Common Pose explores a different decomposition:

```
EMG ──► physical hand state ──► reusable task model
```

If the middle term is a *standardized physical* description of the hand — the same joints,
units, signs and zero across sources — then sensor decoding and task definition become
separable: a task head could in principle be trained on `pose + label` alone and then
attached to a different upstream estimator. That is the hypothesis being tested. It is
currently unproven, and a large part of this repository is the audit work needed to make
it testable at all.

---

## Concept

```
                 ┌──────────────────┐
   biosignal ───►│  pose estimator  │  replaceable front end
   (sEMG, ...)   └────────┬─────────┘
                          │  physical hand joint state
                          ▼
                 ┌──────────────────┐
                 │ Common Pose API  │  semantics, validity, provenance
                 └────────┬─────────┘
                          │  time-stamped pose stream
                          ▼
                 ┌──────────────────┐
                 │ downstream task  │  trained on pose + label,
                 │      head        │  never on task-specific EMG
                 └──────────────────┘
```

A task head consumes pose and labels. If it needed the raw biosignal, the interface would
be doing no work and the research question would be untestable by construction.

---

## Common Pose API

The idea is a standardized, time-stamped stream of physical hand joint states, carrying
validity and provenance, with optional access to recent history. Every dimension should
eventually answer all of:

| field | question |
|---|---|
| anatomical DOF | which joint, which axis |
| unit | degrees or radians, stated, never implied |
| positive direction | what a positive value means (flexion? abduction?) |
| zero / reference definition | what 0 is, and how it was physically established |
| handedness convention | left / right, and whether it is mirrored |
| calibration provenance | where the scale came from, and whether it is independently closable |
| validity / confidence | may *this sample* of *this dimension* be interpreted as the named quantity |

**A dataset-specific 16-dimensional vector is not the API.** The container is deliberately
provisional precisely because the project is still establishing what it must carry. What is
already frozen is a *result*: the physically audited DB9 channel subset, described below.

Two design consequences that are enforced in code rather than documented as intentions:

* **A value never travels without its interpretability.** There is no accessor anywhere in
  this package that returns a bare joint angle. Validity is three-valued
  (`VALID` / `INVALID` / `NOT_ESTABLISHED`) because a boolean flag forces "not yet
  established" to collapse into one of the other two, and both collapse directions have
  already produced wrong results in this project's history.
* **An invalid sample is not a zero.** The emg2pose release encodes inverse-kinematics
  failures as all-zero joint-angle rows rather than NaN — 15.6 % of the official mini
  corpus. Zero is a legitimate angle (the extended hand). Masking is explicit, and the
  measured effect on one held-out session is 16.09° MAE unmasked versus 12.48° masked.

Semantic anatomical correspondence is **not** numerical coordinate equivalence; see
[`docs/common_pose_api.md`](docs/common_pose_api.md).

---

## Current research status

### Validated / established

* **Dataset provenance and coordinate audits** across the released pose corpora considered
  for admission, with sources, hashes and access dates recorded per artifact.
* **DB9 channel-level forensic validation.** A frozen, physically motivated audit whose
  verdicts are `KEEP` / `DROP` / `INCONCLUSIVE` — established with no reference whatsoever
  to classification performance.
* **Identification of physically unreliable released DB9 channels.** Not just "noisy":
  directionally wrong. On an unambiguous fist the raw DIP3 gauge and the released angle
  move *opposite* to the published flexion-positive criterion in 35 of 37 subjects, while
  every MCP and PIP channel in the very same segments moves the documented way in 37/37.
* **A reduced trusted DB9 pose subset** — `TRUSTED_DB9_POSE_v1`, 8 channels, frozen before
  any classifier ran.
* **Subject-held-out posture utility on the trusted dimensions**, reported against the
  historical 16-channel arm (see below).

### In progress

* Final validation of the trusted DB9 subset. **The subset is PROVISIONAL**: the utility
  arm covers 37 Exercise-B subjects, not the final full-corpus validation.
* Common Pose cross-dataset adapters.
* Connection to EMG-based pose estimation.

### Not yet demonstrated

* Universal task transfer.
* Universal cross-dataset numerical coordinate equivalence.
* A deployment-grade API. The current container is a research prototype and is expected to
  change.
* Arbitrary downstream task support.
* That any downstream task head trained here would survive an upstream estimator
  substitution. This is the central open question.

---

## DB9 physical audit

**DB9 was not treated as a black-box benchmark.** Its channel layer was audited against
physical anchors derived from the protocol itself, and some released calibrated channels
cannot safely be interpreted as physical anatomical angles.

Representative findings, all with evidence in
[`audits/db9/channel_forensic/`](audits/db9/channel_forensic/):

| finding | evidence |
|---|---|
| `DIP3`, `DIP5` are **inverted** relative to the published sign criterion | raw gauge and released angle fall together in 35/37 and 32/37 subjects on an unambiguous fist, while MCP/PIP rise in 37/37 |
| `CMC5` is not the palmar arch | the released column is an exact linear function (slope 0.28511 = the published 0.285) of the **same raw sensor** that feeds `WRIST_F` |
| an earlier "many channels fail" verdict was **partly wrong** | it segmented on the pre-relabelling `repetition` vector, which is length-misaligned with the kinematics in 24 of 99 released files |
| the in-file `subject` field is **not a valid identity key** | it is source-database-local; `S68_E2_A1.mat` reports `subject == 1`, colliding with `S1_E2_A1.mat` |

**The trusted subset comes from physical validity rules, not from classification
performance.** That ordering is the point: a subset chosen for accuracy cannot then be used
to argue that the surviving channels are physically sound.

### What the trusted subset costs

Both arms are always reported together. Omitting the loss would hide the price of the
audit; omitting the second number would hide that the surviving subset is genuinely usable.

| | arm A — historical 16-channel | arm B — trusted subset (8) |
|---|---|---|
| balanced accuracy | 0.8538 | 0.7254 |
| accuracy | 0.8555 | 0.7286 |
| chance (9 classes) | 0.1111 | 0.1111 |
| worst subject BA | 0.5648 | 0.4794 |
| class collapse | no | no |

Task: DB9 Exercise-B **hand-shape** movements (official ids 1–8, 17), subject-held-out, one
shared LDA per fold, train-fold-only standardisation, central 60 % of every segment,
544 556 frames over 37 subjects.

> **The task definition matters and is stated rather than implied.** Exercise B mixes nine
> hand shapes with eight wrist movements. `TRUSTED_DB9_POSE_v1` contains no wrist channel
> by construction, so the mixed 17-class task penalises it for a target it was never
> designed to carry — on that task it reaches BA 0.4853. Both numbers are real; they answer
> different questions.

### Trusted subset — PROVISIONAL

8 channels, frozen before any classifier ran, subset SHA-256
`e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`:

`MCP1`, `IP1`, `MCP2_f`, `PIP2`, `MCP3_f`, `MCP4_f`, `MCP5_f`, `PIP5`

* `DROP` (6): `MCP2_a` (vendor-excluded, all-NaN), `CMC5`, `MCP5_a`, `DIP3`, `DIP5`, `WRIST_A`
* `INCONCLUSIVE` (8): `CMC1_f`, `CMC1_a`, `PIP3`, `MCP4_a`, `PIP4`, `DIP2`, `DIP4`, `WRIST_F`

`DROP` means established not to be the named physical quantity. `INCONCLUSIVE` means the
evidence does not settle it — that is a different statement and is not interchangeable
with `DROP`. Details and the full forensic chain:
[`docs/db9_trusted_subset.md`](docs/db9_trusted_subset.md).

---

## Repository structure

```
common-pose/
├── src/common_pose/          the interface
│   ├── api/                  DOF registry, pose container, validity, provenance
│   ├── adapters/             released dataset -> Common Pose stream
│   ├── estimators/           biosignal -> pose front end
│   ├── tasks/                downstream task definitions and heads
│   └── evaluation/           metrics that carry their protocol
├── audits/
│   ├── db9/
│   │   ├── channel_forensic/ frozen physical-validity audit (plan, ledgers, verdicts)
│   │   ├── coordinate_audit/ cross-dataset coordinate and calibration audit
│   │   └── trusted_pose/     TRUSTED_DB9_POSE_v1 — the frozen artifact
│   ├── dataset_admission/    third-party pose corpora: admissibility and blockers
│   └── human_semantic_validation/  annotation ontology and protocol (partly withheld)
├── experiments/
│   ├── db9_posture/          frozen posture-task results
│   ├── bridge/               emg2pose pose vs DB9 pose
│   └── observability/        KIN-MUS task-phase observability
├── docs/                     architecture, API philosophy, status, reproducibility, licensing
├── provenance/               curation manifest: per-file source and target hashes
├── scripts/                  build, verification and pre-publication scan entry points
└── tests/                    contract tests, runnable without any dataset
```

`src/common_pose/adapters/_db9_pipeline/` holds the DB9 task pipeline (loader, canonical
mapping, labels, quality checks, fetch and unpack tools) carried over from the research
workspace. It is source material for the adapter rather than part of the interface, which
is why it is underscore-prefixed and why it is not a sibling package of
`adapters/db9.py` — those two would collide in the import namespace.

Not every directory contains finished work. Where a lane is provisional, downgraded or
withheld, the directory's own README says so. `PUBLICATION_AUDIT.md` records what was
verified before publication and what was not.

---

## Reproducibility

**Third-party datasets are not redistributed.** Every dataset used here is obtainable from
its official source; this repository ships the code, the analysis protocols, the frozen
manifests and the content hashes, but never the data itself.

| dataset | role | official source |
|---|---|---|
| **Ninapro DB9** | calibrated CyberGlove-II kinematics; the physical-audit and posture-task corpus | [ninapro.hevs.ch](https://ninapro.hevs.ch/instructions/DB9.html) |
| **emg2pose** | sEMG → hand pose front end and UmeTrack hand model | [github.com/facebookresearch/emg2pose](https://github.com/facebookresearch/emg2pose) |
| **KIN-MUS UJI** | external pose source with a task-phase label | [doi:10.5281/zenodo.3469380](https://doi.org/10.5281/zenodo.3469380) |
| **KINE-ADL BE-UJI** | external ADL kinematics | [doi:10.17632/8mf4y2srgh.4](https://doi.org/10.17632/8mf4y2srgh.4) |
| **MyoKi** | external pose + sEMG + IMU corpus | DLR Myography & Kinematics record |

What this repository does provide for reproducibility:

* **frozen plans with hashes** — each audit lane pins a plan SHA-256 before it runs, so the
  rules cannot be adjusted after seeing the outcome;
* **frozen evidence artifacts** with their own hashes, under `audits/`;
* **content hashes of the source files** curated here, in `provenance/`;
* **protocol definitions in code** — the task, the split policy, the normalisation rule and
  the metrics are executable objects, not prose;
* **contract tests** that run with no dataset at all: `python -m pytest tests/ -q`.

Where a commit hash is unavailable the provenance records say `COMMIT PENDING` rather than
implying version control coverage that did not exist at the time.

### Running the tests

```bash
python -m pip install -r requirements.txt
python -m pytest tests/ -q          # 58 tests, no dataset, no GPU, no training
```

These are contract tests, not smoke tests. Each pins a property whose violation has already
produced a wrong scientific result somewhere in this project.

---

## Roadmap

1. Freeze the trusted physical pose representation (currently **provisional**).
2. Validate the pose-only downstream task.
3. Integrate the EMG → pose front end.
4. Test the frozen downstream task under upstream estimator substitution.
5. Study cross-dataset interoperability.

---

## Author

**Boyan Dong** — Biomedical Engineering, Southeast University

---

## Citation

This project is currently under active research. A formal citation will be added when an
associated publication or preprint is available.

---

## License

License information will be added after third-party code provenance is reviewed. See
[`docs/licensing.md`](docs/licensing.md) — several dependencies carry
non-commercial or share-alike terms and their lineage constrains what this repository can
claim.
