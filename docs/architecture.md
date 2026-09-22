# Architecture

## 1. The chain

```
   ┌────────────────────────────────────────────────────────────────────────┐
   │  UPSTREAM — replaceable                                                │
   │                                                                        │
   │   biosignal  ──►  pose estimator  ──►  raw pose output                 │
   │   (sEMG, ...)     (learned, or                  (dataset-specific      │
   │                    classical)                    ordering, units,       │
   │                                                  validity encoding)    │
   └────────────────────────────────┬───────────────────────────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   ADAPTER         │  source -> Common Pose
                          │                   │  order, units, signs, zero,
                          │                   │  validity encoding,
                          │                   │  calibration provenance
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  COMMON POSE API  │  DofRegistry · PoseStream
                          │                   │  Validity · Provenance
                          └─────────┬─────────┘
                                    │  time-stamped pose stream
                          ┌─────────▼─────────┐
                          │  DOWNSTREAM TASK  │  consumes pose + label.
                          │       HEAD        │  Never consumes the biosignal.
                          └───────────────────┘
```

The vertical line between estimator and adapter is the research boundary. If a downstream
head needs anything above it, the interface is doing no work and the question
("does a standardized physical pose interface decouple decoding from task definition?") is
untestable by construction.

---

## 2. Module layout

| package | responsibility | must not |
|---|---|---|
| `common_pose.api` | the vocabulary: DOF registry, `PoseStream` / `PoseFrame`, `Validity`, `Provenance`, verdict loading | know about any specific dataset's file layout |
| `common_pose.adapters` | released dataset → pose stream, plus the adapter contract | infer validity from values; repair a released array |
| `common_pose.estimators` | biosignal → pose front end | be a dependency of anything below the API |
| `common_pose.tasks` | downstream task *definitions* and heads | read the biosignal, or a subject id |
| `common_pose.evaluation` | metrics that carry their protocol | return a bare accuracy detached from n / classes / chance |

The dependency direction is strictly downward. `api` imports nothing from `adapters`,
`tasks` or `estimators`.

---

## 3. Why the boundaries are where they are

### 3.1 Nothing below the API depends on which estimator ran

That is the research question made structural. A task head that imports a torch checkpoint,
or reads an EMG array, has quietly answered the question "no" for that task. Keeping the
estimator behind the adapter boundary is not tidiness — it is the experiment.

### 3.2 The adapter is where silent scientific errors are prevented

Almost every wrong result this project found came from an adapter-level mapping being
wrong in a way no metric could detect:

| defect | consequence | where it was caught |
|---|---|---|
| index vector taken from the wrong document | 4 of 10 columns were a different anatomical DOF than they were named | dataset-admission audit |
| segmentation keyed to a misaligned label vector | every movement boundary shifted in 24 of 99 files | channel-forensic audit |
| channel order taken from a secondary document | — | fixed by reading `order_of_angles` from the file itself |
| all-zero IK-failure rows treated as poses | 15.6 % of a corpus silently trained on | baseline bring-up |

So the adapter contract (`PoseAdapter.validate`) is the load-bearing interface in the
repository, not the container.

### 3.3 Validity travels with the value, not beside it

There is no accessor that returns a bare angle. This is an ergonomic cost accepted
deliberately: the alternative is a caller who computes a mean over a column containing 40 %
IK-failure zeros and gets a plausible number.

### 3.4 Provenance is a field, not a comment

Two datasets agreeing on a DOF name, unit and sign can still differ by 2–40° in the medians
because they were produced by different metrological processes. Provenance carries the
distinction between "reproduced", "established-defective" and "not independently closable"
(`True` / `False` / `None`), because collapsing the third case into either of the others
asserts something that was not measured.

---

## 4. Data flow for the DB9 posture task (the worked example)

```
Ninapro DB9 s_<n>_angles.zip
        │
        │ fetch + CRC-verified unpack
        ▼
S<N>_E2_A1.mat        angles (T,22) deg · restimulus · rerepetition · order_of_angles
        │
        │ DB9Adapter: verify order_of_angles against the audited order
        │             segment on restimulus x rerepetition   (NOT `repetition`)
        │             select central fraction of each segment
        │             attach per-channel frozen verdicts -> Validity
        ▼
PoseStream   vocabulary TRUSTED_DB9_POSE_v1 (8) or canonical16 (16)
        │
        │ PostureTaskHead(dimensions=[...])   names, never indices
        │   train-fold-only z-score
        │   one shared LDA per fold
        ▼
predictions + usable mask
        │
        │ classification_report / per_subject_report
        ▼
balanced accuracy, worst-subject BA, per-class recall, chance, class collapse
```

Two things the flow makes explicit that a script would not: the segmentation rule is in the
adapter, not scattered through the analysis, and the split must come from a verified
identity map because the in-file `subject` field collides across source databases.

---

## 5. Where the audits live, and why they are in the repository

`audits/` holds the **evidence**, not just the conclusions: frozen plans with SHA-256,
machine-readable verdicts, captured stdout, and the reasoning in prose. A verdict without
its plan hash is an assertion; with the hash it is a checkable claim, because the plan was
hashed before the run and fixes the rules and thresholds.

`provenance/` holds the curated-copy manifests: for every file copied into this repository
from the historical research workspace, the source path and **both** the source and the
target SHA-256. That is what makes "this code is the code that produced that artifact"
checkable.

The historical workspaces predate version control, so their records say `COMMIT PENDING`
rather than implying coverage that did not exist. This repository starts a clean history;
it does not import a history that contained data and credentials.

---

## 6. Known architectural gaps

Stated because they are real, not because they are small:

1. **The container is not frozen.** `PoseStream` will change as adapters are built out.
2. **No MyoKi / KIN-MUS / KINE-ADL adapters exist.** Those corpora were audited for
   admission but are not redistributable, and not all were obtained.
3. **The subject/hand identity layer is missing.** There is no first-class "who and which
   hand" object, which is exactly where the DB9 collision hazard bites. Subject ids are
   passed as opaque arrays to metrics and the docs say not to use the in-file field.
4. **No timestamp is recovered from DB9.** The released angle bundle carries no time base,
   so the adapter synthesises one at the glove's link rate and labels it as a reconstruction
   rather than a measurement.
5. **Latency is unmeasured.** emg2pose needs 895 ms of history before its first output; the
   true prediction/target lag was never estimated by cross-correlation.
6. **The evaluation layer is offline only.** There is no streaming path, and the emg2pose
   output is causally produced but not streaming.
