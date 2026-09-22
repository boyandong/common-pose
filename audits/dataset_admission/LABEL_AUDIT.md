# LABEL AUDIT

**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`  **Commit:** COMMIT PENDING

No classifier was trained and no accuracy was consulted. Every decision below follows from label PROVENANCE plus diagnostics that already existed or that this audit computed without a model.

## Matrix

| label | dataset | provenance | frame/trial | pose observable | needs temporal | needs object | boundary | decision |
|---|---|---|---|---|---|---|---|---|
| MyoKi `grasp` (0 rest/transition, 1 cylindrical, 2 s | MyoKi | TASK-METADATA LOOKUP.  The paper: 'grasp: Ta... | TRIAL-WISE.  The relea | PARTIALLY and UNVERIFIED.  A grasp famil... | PLAUSIBLY YES  | NO for the label's D | LOW as a frame-wise target.  L | **RESTRICT** |
| MyoKi `task` (1..74) plus 0 = transition | MyoKi | TASK ID from the official 74-task protocol; ... | TRIAL-WISE for the ide | NO.  Task identity is goal/object define... | YES | YES | the 0 class marks transitions; | **REJECT** |
| KIN-MUS `Phase` (1 reaching, 2 manipulation, 3 relea | KIN-MUS | OPERATOR SEGMENTATION of hand-object CONTACT... | FRAME-WISE.  Every 100 | NOT FROM A SINGLE FRAME.  The frozen obs... | YES | NO - the contact eve | HIGH as a CONTACT label, but t | **ADMIT** |
| KIN-MUS `ADL` (1..26) | KIN-MUS | protocol task identity... | TRIAL-WISE | NO.  The upstream admission audit record... | YES | YES | n/a (trial-level) | **REJECT** |
| KINE-ADL elementary task (178) / record ID (101..199 | KINE-ADL | OPERATOR SEGMENTATION of object release / pl... | TRIAL-WISE continuous  | UNVERIFIED.  The corpus was not download... | YES for the cy | YES for a large subs | operator/object-release define | **INCONCLUSIVE** |
| KINE-ADL candidate contrasts (CAND-1 power vs pinch  | KINE-ADL | PROPOSED by this audit from the guide's task... | trial-wise (CAND-1, CA | UNVERIFIED - no trajectory available... | CAND-3 yes; CA | NO by construction - | UNVERIFIED | **INCONCLUSIVE** |

## Detailed entries

### MyoKi - MyoKi `grasp` (0 rest/transition, 1 cylindrical, 2 spherical, 3 hook, 4 tripod, 

* **annotation_provenance**: TASK-METADATA LOOKUP.  The paper: 'grasp: Task labels translated into grasps ... using the information from Task_categorization.xlsx'. This audit parsed that workbook: 74 of the 75 task rows carry exactly ONE grasp mark, so the mapping is deterministic and total.
* **framewise_or_trialwise**: TRIAL-WISE.  The released vector is constant over a whole task segment; the label is a per-SAMPLE array only because every sample of a task inherits the task's grasp.
* **pose_observable**: PARTIALLY and UNVERIFIED.  A grasp family is a hand-shape family, so it is in principle pose-observable, but no kinematic measurement was possible here (corpus not downloaded).
* **requires_temporal_context**: PLAUSIBLY YES for the transition samples: label 0 covers every inter-task transition, so single-frame pose near a boundary is ambiguous by construction.
* **requires_object_or_context**: NO for the label's DEFINITION (it is a shape category), but the SAME grasp class aggregates many different objects, so a decoder could exploit task order rather than shape.
* **boundary_reliability**: LOW as a frame-wise target.  Label 0 is a catch-all transition class whose extent is acquisition-dependent.
* **subject_coverage**: 35 participants (P01..P35) documented; verified participant metadata lists P01..P35 with 2 documented acquisition anomalies
* **class_balance**: over the 74 tasks: cylindrical 22, complex 20, tripod 7, pinch 7, spherical 6, lumbrical 6, hook 6 - IMBALANCED, and the imbalance is over TASKS, not over frames
* **known_ambiguity**: grasp is a relabelling of task identity; two tasks with the same grasp can differ in force, object mass and wrist action
* **recommended_role**: a coarse task-family stratifier, never a frame-wise target
* **decision**: RESTRICT
* **evidence**: DOC

### MyoKi - MyoKi `task` (1..74) plus 0 = transition

* **annotation_provenance**: TASK ID from the official 74-task protocol; the 0 row is labelled 'Undefined transition/resting phase.'
* **framewise_or_trialwise**: TRIAL-WISE for the identity, frame-wise only in the sense that the transition marker is per sample
* **pose_observable**: NO.  Task identity is goal/object defined ('Take the cup from 2, place it on C.'), exactly like KIN-MUS ADL identity.
* **requires_temporal_context**: YES
* **requires_object_or_context**: YES
* **boundary_reliability**: the 0 class marks transitions; its extent is not a physical event
* **subject_coverage**: 35 participants
* **class_balance**: 74 classes x 6 repetitions x 35 participants if complete; not verified because the corpus was not downloaded
* **known_ambiguity**: 3 of the original 38 participants were excluded for corrupted task labels, which shows the label channel is itself fallible
* **recommended_role**: experimental design variable / stratification; never a target
* **decision**: REJECT
* **evidence**: DOC

### KIN-MUS - KIN-MUS `Phase` (1 reaching, 2 manipulation, 3 releasing)

* **annotation_provenance**: OPERATOR SEGMENTATION of hand-object CONTACT events. The paper: the operator marked 'when any part of the hand came into contact with the object and when the hand released the object, to separate reaching/releasing periods from manipulation', with a documented manual double check of every label.
* **framewise_or_trialwise**: FRAME-WISE.  Every 100 Hz sample carries a phase label; 564 894 frames over 1716 containers.
* **pose_observable**: NOT FROM A SINGLE FRAME.  The frozen observability diagnostic (lane kinmus_task_observability, decision OBS-B) measured single-frame pose at 0.4051 balanced accuracy against 0.3333 chance, 500 ms window 0.6172, causal past-only 0.4955.  Those numbers were computed on the MIS-NAMED ten columns; they are numerically valid for those ten columns and are re-interpreted in ADMISSION_DECISION.md.
* **requires_temporal_context**: YES
* **requires_object_or_context**: NO - the contact event is visible in the hand itself
* **boundary_reliability**: HIGH as a CONTACT label, but the boundary is not a kinematic landmark, so frames within the transition windows are genuinely ambiguous
* **subject_coverage**: 22/22 subjects, every subject contributes all three phases
* **class_balance**: frame shares: reaching 0.2794, manipulation 0.4795, releasing 0.2411 (from the frozen observability lane); majority share 0.4795
* **known_ambiguity**: phase is defined by object contact, so a release can begin before the fingers open; the operator labelled from video
* **recommended_role**: first POC task, provided the interface carries temporal state
* **decision**: ADMIT
* **evidence**: DOC

### KIN-MUS - KIN-MUS `ADL` (1..26)

* **annotation_provenance**: protocol task identity
* **framewise_or_trialwise**: TRIAL-WISE
* **pose_observable**: NO.  The upstream admission audit recorded ADL identity as 'NOT POSE-SUFFICIENT - goal/object/intention defined'.
* **requires_temporal_context**: YES
* **requires_object_or_context**: YES
* **boundary_reliability**: n/a (trial-level)
* **subject_coverage**: 22/22
* **class_balance**: 26 classes, balanced by design
* **known_ambiguity**: several ADLs share the same physical action on different objects
* **recommended_role**: stratification and stress-testing only
* **decision**: REJECT
* **evidence**: DOC

### KINE-ADL - KINE-ADL elementary task (178) / record ID (101..199, 201..279)

* **annotation_provenance**: OPERATOR SEGMENTATION of object release / placement events, reviewed against video. The guide's Appendix II lists, per record, the elementary-task ID, the object IDs and the scenario ID.
* **framewise_or_trialwise**: TRIAL-WISE continuous segments at 100 Hz
* **pose_observable**: UNVERIFIED.  The corpus was not downloaded, so no trajectory was inspected.  Section E of KINEADL_SPECIAL.json classifies the task SEMANTICS only: some are pure hand-shape changes, many are object/context defined, and a group is plainly not pose sufficient (transport tasks).
* **requires_temporal_context**: YES for the cyclic actions
* **requires_object_or_context**: YES for a large subset
* **boundary_reliability**: operator/object-release defined; not a kinematic landmark
* **subject_coverage**: 20 per experiment, 25 unique people, 15 shared
* **class_balance**: 178 elementary tasks over 58 tasks; UNKNOWN at frame level because the corpus is absent
* **known_ambiguity**: Experiment A/B subject overlap makes any cross-experiment grouped split unsafe until SUBJECT_DATA is obtained
* **recommended_role**: candidate contrast source, gated on obtaining the corpus
* **decision**: INCONCLUSIVE
* **evidence**: DOC

### KINE-ADL - KINE-ADL candidate contrasts (CAND-1 power vs pinch grip, CAND-2 bimanual role a

* **annotation_provenance**: PROPOSED by this audit from the guide's task table; not annotated by the dataset
* **framewise_or_trialwise**: trial-wise (CAND-1, CAND-2) / within-trial (CAND-3)
* **pose_observable**: UNVERIFIED - no trajectory available
* **requires_temporal_context**: CAND-3 yes; CAND-1 and CAND-2 plausibly not
* **requires_object_or_context**: NO by construction - each contrast is defined on the hand shape or on the hand's role, not on the object
* **boundary_reliability**: UNVERIFIED
* **subject_coverage**: >=20 per experiment if used as designed
* **class_balance**: UNVERIFIED
* **known_ambiguity**: every candidate currently fails the frozen requirement 'enough trials' as unverified
* **recommended_role**: a candidate list for a later, separately pre-registered session
* **decision**: INCONCLUSIVE
* **evidence**: INFERENCE

## The rule that matters most

**MyoKi `grasp` is a task-metadata lookup, not a frame-wise ground truth.** The released `grasp` vector is constant across each task segment; 74 of the 75 task rows carry exactly one grasp mark, which makes the mapping deterministic and therefore makes it a relabelling of task identity. It carries `LABEL_NOT_FRAMEWISE_GROUND_TRUTH`. `[DOC]` + `[EMPIRICAL]`

Consequently the transition samples (task 0 / grasp 0) cannot be used as a 'rest' class without a separately justified, pre-frozen trimming rule, and no trimming rule may be chosen by classifier accuracy. `[INFERENCE]`

## Boundary definitions, compared

| dataset | what the boundary actually is | kinematic landmark? |
|---|---|---|
| KIN-MUS phase | the operator's mark of first hand-object contact and of release, checked against video | NO |
| KINE-ADL elementary task | the object release / placement event, checked against video | NO |
| MyoKi task | the protocol's task block; 0 marks the transition | NO |

All three segmentation schemes are OPERATOR/CONTACT defined. None of them is a kinematic event, so all three put genuinely ambiguous frames next to their boundaries. Any windowed model must treat the boundary neighbourhood as a separate stratum rather than as clean data. `[INFERENCE]`

