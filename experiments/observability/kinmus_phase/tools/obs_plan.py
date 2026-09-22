"""The pre-registered content of KINMUS_TASK_OBSERVABILITY_PLAN.json.

DATA, not analysis.  Imported by ``freeze_plan.py`` (which serialises and hashes
it) and by every driver in this lane, so the frozen choices exist in exactly one
place.

BRANCH CLASSIFICATION
---------------------
DIAGNOSTIC TEST / TASK OBSERVABILITY.  Not Common Pose API validation, not
cross-dataset transfer, not a Gate, not open-set recognition, not architecture
search, not a deep-learning benchmark.
"""
from __future__ import annotations

BRANCH_ID = "S6-KINMUS-TASK-OBSERVABILITY"
PLAN_ARTIFACT = "KINMUS_TASK_OBSERVABILITY_PLAN.json"
LANE_REL = "kinmus_task_observability"

# ===========================================================================
# 1. The one question
# ===========================================================================
SCIENTIFIC_QUESTION = {
    "branch_question": (
        "What information is minimally necessary to infer the KIN-MUS phase label "
        "from hand kinematics alone?"
    ),
    "why_it_exists": (
        "the dataset-admission branch provisionally classified the KIN-MUS phase "
        "label as POSE-SUFFICIENT.  That was a provisional classification, not an "
        "experiment.  There is a concrete conceptual risk: reaching and releasing "
        "may pass through very similar INSTANTANEOUS hand configurations and "
        "differ mainly by motion direction, in which case a single-frame pose "
        "classifier is solving an underdetermined problem"
    ),
    "explicitly_not": [
        "Common Pose API validation",
        "cross-dataset transfer (no emg2pose data of any kind)",
        "Gate optimisation or open-set recognition",
        "Task Compiler",
        "model architecture search",
        "deep-learning benchmark",
        "product-system implementation",
    ],
    "hypotheses": {
        "OBS-A": ("single-frame shared10 pose is sufficient: clearly above null, "
                  "balanced across all three phases, reaching/releasing not "
                  "catastrophically confused, reasonable cross-subject "
                  "consistency, and temporal additions give only modest "
                  "incremental gain.  Interpretation: phase suits the simplest "
                  "first Common Pose API POC."),
        "OBS-B": ("single-frame pose is insufficient, but pose velocity or a short "
                  "local pose trajectory produces a large, reproducible "
                  "improvement AND specifically reduces reaching/releasing "
                  "confusion, exceeding the null and temporal-shuffle controls "
                  "consistently across subjects.  Interpretation: the task is not "
                  "a pure Pose API task; a Hand State API = pose + short local "
                  "temporal dynamics is the appropriate interface.  This does NOT "
                  "invalidate the broader interface hypothesis."),
        "OBS-C": ("even pose + short local dynamics does not generalise across "
                  "subjects.  Interpretation: phase is not a suitable first "
                  "downstream task."),
        "OBS-D": ("data, labels or segmentation quality genuinely prevent a "
                  "reliable distinction.  Not to be used to avoid a negative "
                  "decision."),
    },
}

# ===========================================================================
# 2. Exact source
# ===========================================================================
SOURCE = {
    "dataset": "KIN-MUS UJI",
    "doi": "10.5281/zenodo.3469380",
    "license": "CC-BY-4.0",
    "file": "raw/kin_mus/KIN_MUS_UJI.mat",
    "owned_by_lane": "pose_api_dataset_admission",
    "owning_lane_artifact": "KIN_MUS_SOURCE_AUDIT.json",
    "read_only": True,
    "mat_variable": "EMG_KIN_v4",
    "container_fields": ["Subject", "ADL", "Phase", "time", "Kinematic_data",
                         "EMG_data"],
    "expected": {
        "n_containers": 1716,
        "n_subjects": 22,
        "n_adls": 26,
        "n_phases": 3,
        "n_usable_trials": 1713,
        "n_frames": 564894,
        "n_channels": 18,
        "n_empty_containers": 3,
        "n_duplicated_cells": 2,
    },
    "usable_trial_rule": (
        "a container is usable iff Kinematic_data is 2-D with 18 columns AND its "
        "row count equals time.size.  Empty containers are REPORTED, never "
        "repaired or imputed"
    ),
    "sampling_rate_hz": 100.0,
    "sampling_rate_evidence": (
        "OFFICIAL-DOCUMENTED (MOVMUS guide 'Sampling rate: 100Hz for kinematics', "
        "carried by the admission audit) and re-verified here from the per-trial "
        "time stamps"
    ),
    "provenance_must_be_reverified": (
        "KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json re-reads the .mat and "
        "asserts every expected count above; a mismatch is a hard failure"
    ),
}

# ===========================================================================
# 3. Exact task
# ===========================================================================
TASK = {
    "target": "phase",
    "classes": {"1": "REACHING", "2": "MANIPULATION", "3": "RELEASING"},
    "no_collapsing": "the three phases are never merged in the primary analysis",
    "never_predict": ["ADL identity", "object", "subject", "grasp class"],
    "counts_reported_by": ["frame", "trial", "subject"],
    "imbalance": (
        "checked and reported per split; balanced accuracy and macro F1 are the "
        "primary metrics precisely because class frequency differs"
    ),
}

# ===========================================================================
# 4. Representations
# ===========================================================================
SHARED10 = {
    "name": "shared10_poc_v1",
    "api_order": ["thumb_cmc_flexion", "thumb_mcp_flexion", "index_mcp_flexion",
                  "index_pip_flexion", "middle_mcp_flexion",
                  "middle_pip_flexion", "ring_mcp_flexion", "ring_pip_flexion",
                  "pinky_mcp_flexion", "pinky_pip_flexion"],
    "released_columns": ["CMC1_F", "MCP1_F", "MCP2_F", "PIP2_F", "MCP3_F",
                         "PIP3_F", "MCP4_F", "PIP4_F", "MCP5_F", "PIP5_F"],
    "released_column_indices": [0, 2, 4, 6, 7, 8, 9, 11, 13, 15],
    "unit": "degrees as released",
    "no_additions": ("no additional angles, no DIP reconstruction, no PalmArch, no "
                     "MEDIUM-confidence features, no data-driven feature expansion"),
    "frozen_by": "pose_api_dataset_admission/FIRST_POC_DATASET_DECISION.json",
}

REPRESENTATIONS = {
    "R1_POSE": {
        "definition": "x_t = pose(t), 10 features",
        "role": "PRIMARY",
        "question": "can instantaneous pose alone classify phase?",
    },
    "R2_POSE_VELOCITY": {
        "definition": "x_t = [pose(t), dpose/dt(t)], 20 features",
        "role": "PRIMARY",
        "question": ("does motion direction resolve the reaching vs releasing "
                     "ambiguity?"),
        "velocity_rule": (
            "CENTRAL DIFFERENCE on the frozen 100 Hz grid: v_t = "
            "(pose_{t+1} - pose_{t-1}) / (t_{t+1} - t_{t-1}) using the trial's own "
            "time stamps, in degrees per second.  ONE-SIDED first-order difference "
            "at the first frame and at the last frame ONLY; no other exception.  "
            "Velocity never crosses a trial boundary, because a trial IS one phase "
            "segment.  No smoothing, and no use of any label"
        ),
    },
    "R3_TRAJECTORY": {
        "definition": (
            "at each centre frame t, a 40-feature local summary over the frozen "
            "primary window W frames: [pose(t), mean velocity over the window, "
            "pose(t + h) - pose(t - h) (net local change), per-channel SD of pose "
            "over the window], 10 features each"
        ),
        "role": "PRIMARY",
        "why_not_raw_concatenation": (
            "raw concatenation of ≥21 frames would be 210 features at 500 ms, which "
            "is a large, opaque feature vector; the predeclared summary is the same "
            "information in an interpretable 40-D form and keeps the comparison "
            "against LDA meaningful"
        ),
        "window_rule": (
            "the window is centred and is EXACTLY the intersection of "
            "[t - h, t + h] with the trial's own frame range; frames for which the "
            "full window does not fit inside the trial are EXCLUDED from R3 (they "
            "are reported, not padded).  Because a trial is one phase segment, a "
            "window can never cross a phase boundary"
        ),
        "primary_window_ms": 500,
        "primary_window_frames": 50,
        "sensitivity_windows_ms": [200, 1000],
        "sensitivity_role": (
            "reported for completeness only; they may NOT be used to select the "
            "headline representation"
        ),
    },
    "R4_POSE_PAST_ONLY": {
        "definition": (
            "CAUSAL variant: [pose(t), mean velocity over [t - W, t], "
            "pose(t) - pose(t - W)] using only frames at or before t"
        ),
        "role": "SECONDARY",
        "why": ("a deployable system cannot use future pose unless latency or "
                "offline inference permits it"),
        "must_not_expand_scope": True,
    },
    "R5_FULL18": {
        "definition": "all 18 released KIN-MUS columns, single-frame pose",
        "role": "SECONDARY DIAGNOSTIC ONLY",
        "question": ("does the source dataset contain phase information that the "
                     "Common Pose subset loses?  If full18 works and shared10 does "
                     "not, the problem is INTERFACE INFORMATION LOSS, not phase "
                     "unobservability"),
        "hard_rule": ("full18 may NEVER be used to redefine shared10 after seeing "
                      "results"),
    },
    "R6_FULL18_VELOCITY": {
        "definition": "all 18 columns + velocity",
        "role": "SECONDARY DIAGNOSTIC ONLY",
    },
}

# ===========================================================================
# 5. Validation protocol
# ===========================================================================
VALIDATION = {
    "grouping": "subject",
    "protocol": "grouped 5-fold cross-validation over the 22 subjects",
    "fold_assignment": (
        "folds are assigned by sorting subject ids and dealing round-robin "
        "(subject 1 -> fold 1, ..., subject 5 -> fold 5, subject 6 -> fold 1, ...). "
        "Deterministic, no shuffling, frozen here.  Fold sizes are 5,5,4,4,4"
    ),
    "no_row_wise_split": True,
    "no_trial_split": ("a trial is one phase segment and belongs wholly to one "
                       "subject, so trials can never be split across folds"),
    "no_subject_leakage": (
        "asserted at run time: the intersection of train and test subject sets is "
        "empty in every fold, and the union is all 22 subjects"
    ),
    "normalization": (
        "TRAIN-FOLD ONLY z-scoring: mean and SD are computed on the training "
        "subjects of that fold and applied unchanged to the held-out subject.  A "
        "held-out subject is never normalized using its own statistics"
    ),
    "primary_setting": ("zero-shot new-subject evaluation, no target-subject "
                        "calibration"),
}

# ===========================================================================
# 6. Models
# ===========================================================================
MODELS = {
    "PRIMARY": {
        "A_LDA": ("LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto') on "
                  "the train-fold z-scored features - the project's own frozen "
                  "closed-set baseline configuration"),
        "B_MULTINOMIAL_LR": ("LogisticRegression(multi_class='multinomial', "
                             "solver='lbfgs', max_iter=2000, C=1.0) on the same "
                             "features"),
    },
    "SECONDARY": {
        "C_LINEAR_SVM": "LinearSVC(C=1.0) or SVC(kernel='linear', C=1.0)",
        "D_RBF_SVM": "SVC(kernel='rbf', C=1.0, gamma='scale')",
    },
    "directly_not_used": [
        "neural networks of any kind", "Transformers", "random architecture search",
        "XGBoost", "AutoML", "ensembles", "deep temporal models",
        "any hyperparameter grid",
    ],
    "no_hyperparameter_search": (
        "every model is used at ONE frozen configuration.  The point is task "
        "observability, not classifier innovation.  If simple models cannot read "
        "the signal, the task is not immediately rescued with a large model"
    ),
}

MODEL_SELECTION_RULE = {
    "where": ("entirely within KIN-MUS training subjects; no held-out fold "
              "influences any choice"),
    "primary_goal_is_not": "the highest possible accuracy",
    "primary_goal_is": ("does adding temporal information materially improve "
                        "subject-held-out phase decoding?"),
    "comparison_discipline": (
        "the SAME model family is used when comparing pose vs pose+velocity vs "
        "local trajectory, so the representation comparison is fair.  LDA is the "
        "preferred primary comparison because it is simple and stable; the other "
        "models are controls"
    ),
}

# ===========================================================================
# 7. Metrics
# ===========================================================================
METRICS = {
    "primary": "balanced accuracy (macro-average recall over the three phases)",
    "also": ["macro F1", "overall accuracy", "per-phase recall",
             "per-phase precision", "confusion matrix"],
    "why": ("phase class frequency differs substantially; raw accuracy alone is "
            "not interpretable"),
    "aggregation": [
        "per subject",
        "aggregate across held-out subjects (pooled frames)",
        "mean over subjects with SD",
    ],
    "uncertainty": ("subject-level bootstrap (2000 resamples over the 22 "
                    "subjects, seed 20260101).  Frames are NEVER the resampling "
                    "unit"),
}

# ===========================================================================
# 8. Controls
# ===========================================================================
NULL_CONTROL = {
    "mandatory": True,
    "schemes": {
        "N1_TRIAL_PERMUTATION": (
            "permute the phase label at the TRIAL level within each subject: take "
            "that subject's 78 phase-segment labels and reassign them to its "
            "segments at random.  This destroys only the phase-to-pose "
            "correspondence, preserves the movement repertoire, and keeps every "
            "subject's 'reaching' and 'releasing' segments at their true lengths"
        ),
        "N2_CIRCULAR_SHIFT": (
            "circularly shift the phase label within each subject's segments, "
            "rotating the label sequence while preserving the count structure"
        ),
    },
    "why_not_frame_permutation": (
        "randomly permuting individual frames would destroy the temporal "
        "autocorrelation too and produce an unrealistically EASY null, making the "
        "real result look better than it is"
    ),
    "replicates": 20,
    "seed": 20260101,
    "interpretation": {
        "real_approximately_null": "no reliable phase information",
        "real_much_greater_than_null": "real observable structure exists",
    },
    "evaluation": ("the SAME model, features, folds and normalization as the real "
                   "run; only the labels change"),
}

TEMPORAL_SHUFFLE_CONTROL = {
    "mandatory_if": "R2 or R3 outperforms R1",
    "scheme": (
        "REVERSE the local temporal order within each window: for R3 the window's "
        "frame order is reversed before the summary is computed (so velocities and "
        "the net change flip sign), and for R2 the sign of the velocity is negated. "
        "Pose values are untouched, so the feature SET is identical in size and "
        "marginal distribution; only the local temporal DIRECTION is destroyed"
    ),
    "one_control_only": True,
    "why_one": "do not over-expand controls",
    "question": ("is the improvement truly coming from local dynamics, rather than "
                 "simply having more duplicated pose values?"),
}

BASELINES = {
    "majority_class": "predict the most frequent training-fold phase",
    "prior_only": ("predict the training-fold class prior, evaluated as balanced "
                   "accuracy (which is ~1/3 by construction)"),
    "balanced_random": "uniform random over the three phases -> 1/3 by "
                       "construction",
}

# ===========================================================================
# 9. Boundary / interior
# ===========================================================================
BOUNDARY = {
    "margin_frames": 20,
    "margin_ms": 200,
    "definition": (
        "a frame is INTERIOR iff its index within its trial is >= 20 and < "
        "n_frames - 20.  Everything else is BOUNDARY"
    ),
    "primary_result": "INTERIOR",
    "why": ("labels near a phase boundary may be inherently ambiguous; the "
            "interior result isolates fundamental task ambiguity from "
            "annotation-transition ambiguity"),
    "secondary_result": "BOUNDARY, reported separately",
    "do_not_delete": ("boundary samples are NOT deleted; they are reported as a "
                      "separate stratum with their own counts and metrics"),
}

# ===========================================================================
# 10. Geometry analyses
# ===========================================================================
GEOMETRY = {
    "pose": [
        "per-phase centroid and median in the 10-D shared pose space",
        "per-phase covariance and its leading eigenvalues",
        "pairwise centroid distance (Mahalanobis and Euclidean)",
        "2-D PCA projection of the frozen pose matrix (fit on ALL frames, used for "
        "VISUALISATION only, never as a model input)",
        "nearest-neighbour phase mixing: for each frame, the phase of its nearest "
        "neighbour among a held-out subject's frames",
        "within-subject vs between-subject spread (variance decomposition)",
        "explicitly: are reaching and releasing geometrically overlapping in "
        "instantaneous pose space?",
    ],
    "velocity": [
        "for reaching vs releasing, whether locally similar pose states carry "
        "OPPOSITE velocity directions",
        "method: standardise the 10-D pose; for each reaching frame, find its k "
        "nearest releasing frames (k=50) and compare the sign agreement of the "
        "per-channel velocity between the frame and each neighbour",
        "the same comparison within reaching and within releasing gives the "
        "reference sign-agreement rate",
        "the statistic that matters is whether CROSS-phase sign agreement is "
        "LOWER than WITHIN-phase sign agreement at matched pose locality",
    ],
}

# ===========================================================================
# 11. Decision criteria - FROZEN BEFORE RESULTS
# ===========================================================================
DECISION = {
    "primary_representation_for_the_decision": "shared10_poc_v1",
    "primary_model_for_the_decision": "A_LDA",
    "primary_stratum_for_the_decision": "INTERIOR",
    "null_reference": "N1_TRIAL_PERMUTATION, same pipeline",
    "definition_of_chance": 1.0 / 3.0,
    "thresholds": {
        "ABOVE_NULL": "balanced accuracy above the N1 null's 97.5th percentile",
        "GOOD_ABSOLUTE": "balanced accuracy >= 0.60",
        "STRONG_ABSOLUTE": "balanced accuracy >= 0.75",
        "BALANCED_ACROSS_PHASES": "every per-phase recall >= 0.50",
        "DIRECTIONAL_FAILURE": (
            "the smaller of P(pred=RELEASING | true=REACHING) and "
            "P(pred=REACHING | true=RELEASING) >= 0.25"
        ),
        "MODEST_TEMPORAL_GAIN": "best temporal BA - R1 BA <= 0.05",
        "MATERIAL_TEMPORAL_GAIN": "best temporal BA - R1 BA >= 0.10",
        "SUBJECT_CONSISTENCY": ("at least 16 of 22 subjects (>= 72.7 %) have "
                                "per-subject BA >= 0.50"),
        "SEVERE_SUBJECT_INSTABILITY": ("6 or more of 22 subjects have per-subject "
                                       "BA < 0.45, or the across-subject SD of BA "
                                       ">= 0.15"),
    },
    #: The NUMERIC values of the same thresholds.  The ``thresholds`` block above
    #: is the human-readable statement that was frozen and hashed; this parallel
    #: block is the machine-readable form of exactly the same numbers, so a gate
    #: can be evaluated without parsing prose.  Neither block may be changed.
    "thresholds_numeric": {
        "CHANCE": 1.0 / 3.0,
        "GOOD_ABSOLUTE": 0.60,
        "STRONG_ABSOLUTE": 0.75,
        "MIN_PER_PHASE_RECALL": 0.50,
        "DIRECTIONAL_FAILURE_MIN_ERROR": 0.25,
        "MODEST_TEMPORAL_GAIN": 0.05,
        "MATERIAL_TEMPORAL_GAIN": 0.10,
        "SUBJECT_CONSISTENCY_MIN_SUBJECTS": 16,
        "SUBJECT_CONSISTENCY_MIN_BA": 0.50,
        "SEVERE_INSTABILITY_MIN_SUBJECTS_BELOW": 6,
        "SEVERE_INSTABILITY_MIN_BA_BELOW": 0.45,
        "SEVERE_INSTABILITY_MAX_SD": 0.15,
        "DIRECTIONAL_IMPROVEMENT_MIN": 0.10,
        "PER_SUBJECT_CONSISTENT_MIN": 0.05,
    },
    "OBS_A_requires_all_of": [
        "R1 interior BA >= GOOD_ABSOLUTE",
        "R1 interior BA is ABOVE_NULL",
        "BALANCED_ACROSS_PHASES under R1",
        "NOT DIRECTIONAL_FAILURE under R1",
        "SUBJECT_CONSISTENCY under R1",
        "temporal addition gives only MODEST_TEMPORAL_GAIN",
    ],
    "OBS_B_requires_all_of": [
        "R1 interior BA < GOOD_ABSOLUTE",
        "best temporal interior BA - R1 interior BA >= MATERIAL_TEMPORAL_GAIN",
        "the temporal representation's interior BA is ABOVE_NULL and >= "
        "GOOD_ABSOLUTE",
        "the reaching/releasing directional error under the temporal "
        "representation improves by at least 0.10 absolute over R1",
        "the improvement survives the TEMPORAL_SHUFFLE control (shuffled BA must "
        "be closer to R1 than to the real temporal BA)",
        "the per-subject improvement is consistent: at least 15 of 22 subjects "
        "improve",
    ],
    "OBS_C_if_any_of": [
        "R1 interior BA < 0.45 AND best temporal interior BA < GOOD_ABSOLUTE",
        "best temporal interior BA is not ABOVE_NULL",
        "SEVERE_SUBJECT_INSTABILITY under every representation",
        "DIRECTIONAL_FAILURE persists under every representation",
        "the task only works through activity/object leakage (checked: the models "
        "never see ADL, object or subject identity, so this would show up as "
        "full18 working while shared10 does not AND the geometry showing that the "
        "extra columns are the only separating ones)",
        "shared10 lacks the necessary information and no API-local extension "
        "recovers it",
    ],
    "OBS_D_only_if": ("data, labels, handedness or segmentation genuinely prevent "
                      "a decision; explicitly NOT to be used to avoid a negative "
                      "decision"),
    "reading_order": [
        "1. Is R1 above null at all?  If not, the single-frame hypothesis is dead.",
        "2. Is R1 good in absolute terms and balanced across phases?",
        "3. If R1 is weak, does a predeclared temporal representation give a "
        "material, reproducible, control-surviving gain, specifically on the "
        "reaching/releasing confusion?",
        "4. Is the result stable across subjects?",
        "5. Only then assign A, B, C or D.",
    ],
    "must_also_answer": (
        "Is phase suitable for the FIRST Common Pose API POC?  "
        "YES / NO / ONLY WITH TEMPORAL STATE"
    ),
}

# ===========================================================================
# 12. Hard scope rules and anti-rescue
# ===========================================================================
SCOPE_RULES = {
    "forbidden_inputs": [
        "emg2pose data of any kind", "VEMG2Pose", "KIN-MUS EMG channels",
        "object identity", "activity identity", "environment information",
        "force or contact", "arm kinematics", "task-specific handcrafted "
        "semantic rules", "human annotations outside KIN-MUS", "DB9",
        "subject identity as a feature",
    ],
    "forbidden_activity": [
        "designing a Gate", "comparing UNKNOWN algorithms",
        "tuning a classifier using external data", "training deep learning",
    ],
}

ANTI_RESCUE = {
    "if_shared10_single_frame_is_poor": [
        "do NOT add arbitrary features",
        "do NOT add ADL identity",
        "do NOT add object identity",
        "do NOT add EMG",
        "do NOT use subject ID",
        "do NOT use future task labels",
        "do NOT train a neural network",
        "do NOT switch to a Transformer",
        "do NOT hand-select only easy ADLs",
        "do NOT merge reaching/releasing post-hoc",
        "do NOT tune the temporal window after seeing results indefinitely",
    ],
    "permitted_test": ("only the PREDECLARED velocity / short-trajectory / causal "
                       "variants may test whether local dynamics solve the "
                       "problem"),
    "if_they_fail": "stop",
}

HANDEDNESS = {
    "upstream_issue": ("the released KIN-MUS kinematic block is ONE hand of 18 "
                       "columns and does not label which"),
    "resolution_attempted_before_freezing": True,
    "evidence": "logs/handedness_probe.json, logs/handedness_cluster_inspection.json",
    "policy": (
        "handedness is NOT used to include or exclude any subject and NO mirroring "
        "is applied.  If the block is a single hand, phase observability is a "
        "within-block question and the ambiguity is a recorded limitation only.  If "
        "the block were found to be MIXED hands, the primary analysis would be "
        "restricted to the larger single-hand cluster, frozen BEFORE scoring"
    ),
}

FULL18_POLICY = (
    "full18 is a SECONDARY DIAGNOSTIC only.  It answers whether the source dataset "
    "contains phase information the shared10 subset loses.  It may never redefine "
    "shared10 after results are seen"
)

RUNTIME = {
    "python": r"<EMG2POSE_VENV>\Scripts\python.exe",
    "libraries": "numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2",
    "random_seed": 20260101,
    "git_worktree_clean": False,
    "worktree_state": "project root is not a git repository; COMMIT PENDING",
    "local_training_prohibition": (
        "no deep-learning training is run on this machine; nothing in this branch "
        "trains a deep model.  The two primary classifiers are closed-form or "
        "convex classical fits on at most a few hundred thousand rows"
    ),
    "runtime_estimate": ("minutes; 5 folds x ~10 representation x model "
                         "combinations on 564 894 frames at 10-40 features"),
}

REQUIRED_ARTIFACTS = [
    "KINMUS_TASK_OBSERVABILITY_PLAN.json",
    "KINMUS_TASK_OBSERVABILITY_PLAN.sha256",
    "KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json",
    "KINMUS_PHASE_COUNTS.json",
    "KINMUS_PHASE_POSE_GEOMETRY.json",
    "KINMUS_PHASE_VELOCITY_GEOMETRY.json",
    "KINMUS_SINGLE_FRAME_RESULTS.json",
    "KINMUS_VELOCITY_RESULTS.json",
    "KINMUS_TRAJECTORY_RESULTS.json",
    "KINMUS_FULL18_DIAGNOSTIC.json",
    "KINMUS_OBSERVABILITY_NULL_CONTROL.json",
    "KINMUS_BOUNDARY_ANALYSIS.json",
    "KINMUS_SUBJECT_STABILITY.json",
    "KINMUS_TASK_OBSERVABILITY_DECISION.json",
    "KINMUS_TASK_OBSERVABILITY_REPORT.md",
    "KINMUS_TASK_OBSERVABILITY_HANDOVER.md",
    "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt",
    "ARTIFACT_MANIFEST.json",
    "figures/",
]

PRE_REGISTRATION_STATEMENT = (
    "This plan was written and hashed BEFORE any classifier was fitted and before "
    "any performance number existed.  The representations, the velocity rule, the "
    "window length, the subject-grouped protocol, the model set, the metrics, the "
    "null and shuffle controls, the interior/boundary margin and every decision "
    "threshold are frozen as a unit by the SHA-256 of the raw bytes of this "
    "document.  No threshold, window or representation may be changed after seeing "
    "performance.  The sidecar .sha256 file is a convenience copy; the raw-byte "
    "hash is the authority."
)


def build_plan() -> dict:
    return {
        "artifact": PLAN_ARTIFACT,
        "branch_id": BRANCH_ID,
        "branch_classification": "DIAGNOSTIC TEST / TASK OBSERVABILITY",
        "status": "FROZEN",
        "lane": LANE_REL,
        "scientific_question": SCIENTIFIC_QUESTION,
        "source": SOURCE,
        "task": TASK,
        "shared10": SHARED10,
        "representations": REPRESENTATIONS,
        "validation": VALIDATION,
        "models": MODELS,
        "model_selection_rule": MODEL_SELECTION_RULE,
        "metrics": METRICS,
        "null_control": NULL_CONTROL,
        "temporal_shuffle_control": TEMPORAL_SHUFFLE_CONTROL,
        "baselines": BASELINES,
        "boundary": BOUNDARY,
        "geometry": GEOMETRY,
        "decision": DECISION,
        "scope_rules": SCOPE_RULES,
        "anti_rescue": ANTI_RESCUE,
        "handedness": HANDEDNESS,
        "full18_policy": FULL18_POLICY,
        "runtime": RUNTIME,
        "required_artifacts": REQUIRED_ARTIFACTS,
        "pre_registration_statement": PRE_REGISTRATION_STATEMENT,
    }
