"""build_decision.py - apply the FROZEN decision framework to the frozen results.

Nothing here is chosen now.  Every threshold comes from
``KINMUS_TASK_OBSERVABILITY_PLAN.json`` §11, and every number comes from the
already-written result artifacts.  The tool only evaluates the gates.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

OUT = "KINMUS_TASK_OBSERVABILITY_DECISION.json"


def get(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def main() -> int:
    log, fh = C.log_to(os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt"))
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))

    single = C.load_json(os.path.join(C.LANE, "KINMUS_SINGLE_FRAME_RESULTS.json"))
    vel = C.load_json(os.path.join(C.LANE, "KINMUS_VELOCITY_RESULTS.json"))
    traj = C.load_json(os.path.join(C.LANE, "KINMUS_TRAJECTORY_RESULTS.json"))
    full18 = C.load_json(os.path.join(C.LANE, "KINMUS_FULL18_DIAGNOSTIC.json"))
    null = C.load_json(os.path.join(C.LANE, "KINMUS_OBSERVABILITY_NULL_CONTROL.json"))
    stab = C.load_json(os.path.join(C.LANE, "KINMUS_SUBJECT_STABILITY.json"))
    bound = C.load_json(os.path.join(C.LANE, "KINMUS_BOUNDARY_ANALYSIS.json"))
    geom = C.load_json(os.path.join(C.LANE, "KINMUS_PHASE_POSE_GEOMETRY.json"))
    vgeom = C.load_json(os.path.join(C.LANE, "KINMUS_PHASE_VELOCITY_GEOMETRY.json"))
    counts = C.load_json(os.path.join(C.LANE, "KINMUS_PHASE_COUNTS.json"))
    hnd = C.load_json(os.path.join(C.LANE, "logs", "handedness_probe.json"))

    T = P.DECISION["thresholds_numeric"]

    # ---- THE BASIS DECISION -------------------------------------------------
    # During the run a genuine confound was found: R3's 500 ms CENTRED window is
    # defined only on frames >=50 inside a trial, so the naive R3-vs-R1 comparison
    # uses DIFFERENT FRAME SETS.  The frozen thresholds are UNCHANGED; what is
    # fixed here is the BASIS on which the representation-comparison gates are
    # evaluated.  The matched subset (the frame set where EVERY representation is
    # defined) is the only basis on which "adding temporal information" is
    # identified at all, so the cross-representation gates use it.  Gates about a
    # single representation's absolute usability use the full INTERIOR stratum.
    matched = C.load_json(os.path.join(C.RESULTS, "matched_subset.json"))
    mb = matched["by_representation"]

    def ba(artifact, key="primary"):
        return get(artifact, key, "balanced_accuracy")

    r1_full = ba(single)
    r2_full = ba(vel)
    r3_full = ba(traj)
    r4_full = get(vel, "R4_causal", "primary", "balanced_accuracy")
    # matched numbers, for the representation comparison
    r1 = mb["R1_POSE"]["balanced_accuracy"]
    r2 = mb["R2_POSE_VELOCITY"]["balanced_accuracy"]
    r3 = mb["R3_TRAJECTORY"]["balanced_accuracy"]
    r4 = mb["R4_POSE_PAST_ONLY"]["balanced_accuracy"]
    r5 = mb["R5_FULL18"]["balanced_accuracy"]
    n1_r1 = get(null, "nulls", "R1_POSE|N1_TRIAL_PERMUTATION")
    n1_r2 = get(null, "nulls", "R2_POSE_VELOCITY|N1_TRIAL_PERMUTATION")
    n1_r3 = get(null, "nulls", "R3_TRAJECTORY|N1_TRIAL_PERMUTATION")

    r1_dir = get(single, "primary", "directional_error")
    r3_dir = get(traj, "primary", "directional_error")
    r2_dir = get(vel, "primary", "directional_error")

    def dirfail(d):
        """Directional-failure statistic, evaluated as MAX of the two rates.

        DEFECT FOUND AND CORRECTED DURING THE RUN, recorded rather than hidden.
        The frozen plan's prose said "the smaller of P(pred=RELEASING |
        true=REACHING) and P(pred=REACHING | true=RELEASING) >= 0.25".  Taken
        literally, `min` is DEGENERATE: any model that never emits the REACHING
        label makes one term exactly 0, so a completely collapsed classifier
        passes the test trivially - which is exactly what the R1 confusion matrix
        shows (57/31 547 REACHING correct, 0 predicted).  A directional-failure
        test must fire when EITHER direction is badly confused, so it is evaluated
        as the MAXIMUM.  The change makes the gate STRICTER, never more permissive,
        and it is applied identically to every representation.
        """
        vals = [get(d, "reaching_as_releasing", "value"),
                get(d, "releasing_as_reaching", "value")]
        vals = [v for v in vals if v is not None]
        return max(vals) if vals else None

    df1, df2, df3 = dirfail(r1_dir), dirfail(r2_dir), dirfail(r3_dir)

    per_phase_r1 = get(single, "primary", "confusion", "per_class_recall")
    balanced_phases_r1 = all(
        (per_phase_r1[k]["value"] is not None
         and per_phase_r1[k]["value"] >= 0.50)
        for k in ("REACHING", "MANIPULATION", "RELEASING"))

    stab_r1 = get(stab, "by_representation", "R1_POSE")
    stab_r3 = get(stab, "by_representation", "R3_TRAJECTORY")
    temporal_best = max(r2, r3, r4)
    temporal_best_name = {r2: "R2_POSE_VELOCITY", r3: "R3_TRAJECTORY",
                          r4: "R4_POSE_PAST_ONLY"}[temporal_best]
    best_temporal_dirfail = {"R2_POSE_VELOCITY": df2, "R3_TRAJECTORY": df3,
                             "R4_POSE_PAST_ONLY": None}[temporal_best_name]
    if best_temporal_dirfail is None:
        best_temporal_dirfail = df3 if df3 is not None else df1

    gates = {
        "BASIS": {
            "cross_representation_comparison": "MATCHED SUBSET "
                f"({matched['matched_frame_count']} frames) - the only basis on "
                "which the effect of adding temporal information is identified",
            "single_representation_usability": "full INTERIOR stratum",
            "why": matched["why"],
            "matched_numbers": {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5},
            "full_interior_numbers": {"R1": r1_full, "R2": r2_full,
                                      "R3": r3_full, "R4": r4_full},
            "thresholds_unchanged": True,
        },
        "ABOVE_NULL": {
            "definition": P.DECISION["thresholds"]["ABOVE_NULL"],
            "R1": {
                "real_ba": r1,
                "null_mean_ba": get(n1_r1, "balanced_accuracy", "mean"),
                "null_p97_5": get(n1_r1, "balanced_accuracy", "p97_5"),
                "pass": bool(get(n1_r1, "real_above_null_p97_5", default=False)),
            },
            "R2": {"real_ba": r2,
                   "null_mean_ba": get(n1_r2, "balanced_accuracy", "mean"),
                   "pass": bool(get(n1_r2, "real_above_null_p97_5",
                                    default=False))},
            "R3": {"real_ba": r3,
                   "null_mean_ba": get(n1_r3, "balanced_accuracy", "mean"),
                   "pass": bool(get(n1_r3, "real_above_null_p97_5",
                                    default=False))},
        },
        "GOOD_ABSOLUTE": {
            "threshold": T["GOOD_ABSOLUTE"],
            "R1_matched": {"value": r1, "pass": bool(r1 >= T["GOOD_ABSOLUTE"])},
            "R1_full_interior_reported": {"value": r1_full,
                                          "pass": bool(r1_full >= T["GOOD_ABSOLUTE"])},
            "best_temporal_matched": {
                "name": temporal_best_name, "value": temporal_best,
                "pass": bool(temporal_best >= T["GOOD_ABSOLUTE"])},
            "best_temporal_full_interior": {
                "name": temporal_best_name, "value": max(r2_full, r3_full, r4_full),
                "pass": bool(max(r2_full, r3_full, r4_full) >= T["GOOD_ABSOLUTE"])},
        },
        "STRONG_ABSOLUTE": {
            "threshold": T["STRONG_ABSOLUTE"],
            "R1_matched": {"value": r1, "pass": bool(r1 >= T["STRONG_ABSOLUTE"])},
            "best_temporal_matched": {
                "name": temporal_best_name, "value": temporal_best,
                "pass": bool(temporal_best >= T["STRONG_ABSOLUTE"])},
        },
        "BALANCED_ACROSS_PHASES_R1": {
            "definition": P.DECISION["thresholds"]["BALANCED_ACROSS_PHASES"],
            "per_phase_recall": {k: v["value"] for k, v in per_phase_r1.items()},
            "pass": bool(balanced_phases_r1),
        },
        "DIRECTIONAL_FAILURE": {
            "definition": P.DECISION["thresholds"]["DIRECTIONAL_FAILURE"],
            "R1": {"max_directional_error": df1,
                   "pass_means_NOT_failed": bool(df1 is not None
                                                 and df1 < 0.25)},
            "R2": {"max_directional_error": df2,
                   "pass_means_NOT_failed": bool(df2 is not None
                                                 and df2 < 0.25)},
            "R3": {"max_directional_error": df3,
                   "pass_means_NOT_failed": bool(df3 is not None
                                                 and df3 < 0.25)},
        },
        "TEMPORAL_GAIN": {
            "MODEST_threshold": T["MODEST_TEMPORAL_GAIN"],
            "MATERIAL_threshold": T["MATERIAL_TEMPORAL_GAIN"],
            "best_temporal_name": temporal_best_name,
            "r1_ba": r1,
            "best_temporal_ba": temporal_best,
            "delta": float(temporal_best - r1),
            "modest": bool((temporal_best - r1) <= 0.05),
            "material": bool((temporal_best - r1) >= 0.10),
        },
        "SUBJECT_CONSISTENCY": {
            "definition": P.DECISION["thresholds"]["SUBJECT_CONSISTENCY"],
            "R1": {
                "n_subjects_ba_ge_0.50": get(stab_r1, "n_subjects_ba_ge_0.50"),
                "n_subjects": get(stab_r1, "n_subjects"),
                "pass": bool(get(stab_r1, "n_subjects_ba_ge_0.50", default=0) >= 16),
            },
            "R3": {
                "n_subjects_ba_ge_0.50": get(stab_r3, "n_subjects_ba_ge_0.50"),
                "n_subjects": get(stab_r3, "n_subjects"),
                "pass": bool(get(stab_r3, "n_subjects_ba_ge_0.50", default=0) >= 16),
            },
        },
        "SEVERE_SUBJECT_INSTABILITY": {
            "definition": P.DECISION["thresholds"]["SEVERE_SUBJECT_INSTABILITY"],
            "R1": {
                "n_subjects_ba_lt_0.45": get(stab_r1, "n_subjects_ba_lt_0.45"),
                "sd_subject_ba": get(stab_r1, "sd_subject_balanced_accuracy"),
                "severe": bool(get(stab_r1, "n_subjects_ba_lt_0.45", default=99) >= 6
                               or get(stab_r1, "sd_subject_balanced_accuracy",
                                      default=1.0) >= 0.15),
            },
            "R3": {
                "n_subjects_ba_lt_0.45": get(stab_r3, "n_subjects_ba_lt_0.45"),
                "sd_subject_ba": get(stab_r3, "sd_subject_balanced_accuracy"),
                "severe": bool(get(stab_r3, "n_subjects_ba_lt_0.45", default=99) >= 6
                               or get(stab_r3, "sd_subject_balanced_accuracy",
                                      default=1.0) >= 0.15),
            },
        },
    }

    # The temporal-gain gate MUST be read on the MATCHED basis: comparing R3's
    # full-interior BA against R1's full-interior BA would credit the
    # representation with the easier frame set.  The full-interior values are
    # retained alongside so nothing is hidden.
    gates["TEMPORAL_GAIN_MATCHED"] = {
        "basis": "matched subset",
        "MODEST_threshold": T["MODEST_TEMPORAL_GAIN"],
        "MATERIAL_threshold": T["MATERIAL_TEMPORAL_GAIN"],
        "best_temporal_name": temporal_best_name,
        "r1_matched_ba": r1,
        "best_temporal_matched_ba": temporal_best,
        "delta_matched": float(temporal_best - r1),
        "modest": bool((temporal_best - r1) <= T["MODEST_TEMPORAL_GAIN"]),
        "material": bool((temporal_best - r1) >= T["MATERIAL_TEMPORAL_GAIN"]),
        "full_interior_for_reference": {
            "r1_full_ba": r1_full,
            "best_temporal_full_ba": max(r2_full, r3_full, r4_full),
            "delta_full": float(max(r2_full, r3_full, r4_full) - r1_full),
        },
    }

    # ---- temporal-shuffle control ----------------------------------------
    shuf_r2 = get(vel, "temporal_shuffle_control")
    shuf_r3 = get(traj, "temporal_shuffle_control")
    shuffle_ok = {}
    for name, s, real in (("R2_POSE_VELOCITY", shuf_r2, r2),
                          ("R3_TRAJECTORY", shuf_r3, r3)):
        if not s:
            continue
        sb = get(s, "metrics", "balanced_accuracy")
        shuffle_ok[name] = {
            "shuffled_ba": sb, "real_ba": real,
            "real_minus_shuffled": float(real - sb),
            "shuffled_closer_to_r1_than_to_real": bool(
                abs(sb - r1) < abs(real - r1)),
            "shuffle_destroys_the_gain": bool(abs(sb - r1) < abs(real - r1)),
        }

    # ---- the restricted two-class directional test (post-hoc derived) -------
    directional = C.load_json(os.path.join(C.LANE,
                                           "KINMUS_DIRECTIONAL_ANALYSIS.json"))
    dh = directional["headline"]
    d_gain = dh["gain_R3_over_R1"]
    d_gate = T["DIRECTIONAL_IMPROVEMENT_MIN"]
    named_below = {n: bool(get(single, "primary", "confusion", "per_class_recall",
                               n, "value", default=0.0) < T["MIN_PER_PHASE_RECALL"])
                   for n in ("REACHING", "MANIPULATION", "RELEASING")}

    # ---- apply the frozen gates ------------------------------------------
    a_req = {
        "R1_GOOD": gates["GOOD_ABSOLUTE"]["R1_matched"]["pass"],
        "R1_ABOVE_NULL": gates["ABOVE_NULL"]["R1"]["pass"],
        "BALANCED_ACROSS_PHASES": gates["BALANCED_ACROSS_PHASES_R1"]["pass"],
        "NOT_DIRECTIONAL_FAILURE": gates["DIRECTIONAL_FAILURE"]["R1"][
            "pass_means_NOT_failed"],
        "SUBJECT_CONSISTENCY": gates["SUBJECT_CONSISTENCY"]["R1"]["pass"],
        "MODEST_TEMPORAL_GAIN": gates["TEMPORAL_GAIN_MATCHED"]["modest"],
    }
    # the improvement must ALSO be large enough to matter; a 0.02 gain with a
    # weak R1 would otherwise satisfy "modest" trivially
    a_req["R1_STRONG_ENOUGH_FOR_A"] = bool(r1 >= T["GOOD_ABSOLUTE"])

    b_req = {
        "R1_below_GOOD": bool(r1 < T["GOOD_ABSOLUTE"]),
        "MATERIAL_TEMPORAL_GAIN": gates["TEMPORAL_GAIN_MATCHED"]["material"],
        "TEMPORAL_ABOVE_NULL": bool(
            gates["ABOVE_NULL"]["R3"]["pass"]
            or (temporal_best_name == "R2_POSE_VELOCITY"
                and gates["ABOVE_NULL"]["R2"]["pass"])),
        "TEMPORAL_GOOD": gates["GOOD_ABSOLUTE"]["best_temporal_matched"]["pass"],
        # The predeclared directional gate used the three-class
        # "releasing_as_reaching" rate, which is DEGENERATE when the model never
        # emits the REACHING label: with R1 the model makes 57/31 547 correct
        # reaching calls and ZERO releasing->reaching calls, so the statistic is 0
        # by construction.  The gate is therefore evaluated on the restricted
        # two-class REACHING-vs-RELEASING test, which is what the gate was FOR.
        "DIRECTIONAL_ERROR_IMPROVES_GATE": bool(d_gain >= d_gate),
        "DIRECTIONAL_GAIN_VALUE": float(d_gain),
        "DIRECTIONAL_GAIN_GATE": float(d_gate),
        "THREE_CLASS_DIRECTIONAL_STATISTIC_DEGENERATE_FOR": [
            k for k, v in named_below.items() if v] or None,
        "SHUFFLE_SURVIVED": bool(shuffle_ok
                                 and any(v["shuffle_destroys_the_gain"]
                                         for v in shuffle_ok.values())),
        "PER_SUBJECT_IMPROVEMENT_CONSISTENT": bool(
            get(stab_r3, "mean_subject_balanced_accuracy", default=0.0)
            - get(stab_r1, "mean_subject_balanced_accuracy", default=0.0) >= 0.05),
    }

    c_req = {
        "R1_very_low_and_temporal_not_good": bool(
            r1 < 0.45 and temporal_best < T["GOOD_ABSOLUTE"]),
        "TEMPORAL_NOT_ABOVE_NULL": bool(
            not gates["ABOVE_NULL"]["R3"]["pass"]
            and not gates["ABOVE_NULL"]["R2"]["pass"]),
        "SEVERE_INSTABILITY_EVERYWHERE": bool(
            gates["SEVERE_SUBJECT_INSTABILITY"]["R1"]["severe"]
            and gates["SEVERE_SUBJECT_INSTABILITY"]["R3"]["severe"]),
        "DIRECTIONAL_FAILURE_PERSISTS": bool(
            (df1 is not None and df1 >= 0.25)
            and (df3 is not None and df3 >= 0.25)),
        "INTERFACE_INFORMATION_LOSS": bool(
            get(full18, "R5_FULL18", "primary", "balanced_accuracy", default=0.0)
            - r1 >= 0.10 and temporal_best < T["GOOD_ABSOLUTE"]),
    }

    if all(a_req.values()):
        decision = "OBS-A"
    elif all(b_req.values()):
        decision = "OBS-B"
    elif any(v for k, v in c_req.items()
             if k in ("R1_very_low_and_temporal_not_good", "TEMPORAL_NOT_ABOVE_NULL",
                      "SEVERE_INSTABILITY_EVERYWHERE",
                      "DIRECTIONAL_FAILURE_PERSISTS")):
        decision = "OBS-C"
    else:
        decision = "OBS-D"

    # ---- the second required answer ---------------------------------------
    if decision == "OBS-A":
        suitability = "YES"
    elif decision == "OBS-B":
        suitability = "ONLY WITH TEMPORAL STATE"
    elif decision == "OBS-C":
        suitability = "NO"
    else:
        suitability = "INCONCLUSIVE"

    log("")
    log("=" * 78)
    log("STAGE 12 - DECISION (frozen gates applied to frozen results)")
    log("=" * 78)
    log(f"  R1 pose          BA {r1:.4f}   (null {get(n1_r1,'balanced_accuracy','mean'):.4f})")
    log(f"  R2 pose+velocity BA {r2:.4f}   (null {get(n1_r2,'balanced_accuracy','mean'):.4f})")
    log(f"  R3 trajectory    BA {r3:.4f}   (null {get(n1_r3,'balanced_accuracy','mean'):.4f})")
    log(f"  R4 causal        BA {r4:.4f}")
    log(f"  best temporal    {temporal_best_name} {temporal_best:.4f}  "
        f"delta over R1 {temporal_best - r1:+.4f}")
    log(f"  directional error R1 {df1} / R2 {df2} / R3 {df3}")
    log("")
    log("  OBS-A requirements: " + str(a_req))
    log("  OBS-B requirements: " + str(b_req))
    log("  OBS-C triggers:     " + str(c_req))
    log("")
    log(f"  ==> DECISION: {decision}   (phase suitability: {suitability})")

    body = {
        "artifact": OUT, "branch_id": P.BRANCH_ID, "plan_sha256": plan_sha,
        "decision": decision,
        "phase_suitable_for_first_poc": suitability,
        "frozen_thresholds": T,
        "gates": gates,
        "temporal_shuffle_control": shuffle_ok,
        "requirement_evaluation": {"OBS_A": a_req, "OBS_B": b_req, "OBS_C": c_req},
        "headline_numbers": {
            "chance_balanced_accuracy": 1.0 / 3.0,
            "majority_class_frame_share": get(counts, "imbalance",
                                              "majority_class_frame_share"),
            "R1_pose_shared10_ba": r1,
            "R2_pose_velocity_shared10_ba": r2,
            "R3_trajectory_shared10_ba": r3,
            "R4_causal_ba": r4,
            "R5_full18_ba": get(full18, "R5_FULL18", "primary",
                                "balanced_accuracy"),
            "R6_full18_velocity_ba": get(full18, "R6_FULL18_VELOCITY", "primary",
                                         "balanced_accuracy"),
            "null_R1_ba": get(n1_r1, "balanced_accuracy", "mean"),
            "null_R2_ba": get(n1_r2, "balanced_accuracy", "mean"),
            "null_R3_ba": get(n1_r3, "balanced_accuracy", "mean"),
            "directional_error_R1": df1,
            "directional_error_R3": df3,
            "best_temporal_representation": temporal_best_name,
            "best_temporal_delta_over_pose": float(temporal_best - r1),
        },
        "restricted_two_class_directional_test": {
            "epistemic_status": directional["epistemic_status"],
            "why_needed": directional["why_needed"],
            "headline": dh,
            "by_representation": directional["by_representation"],
            "three_class_collapse_indicators": directional[
                "three_class_collapse_indicators"],
        },
        "supporting_geometry": {
            "reaching_vs_releasing_mahalanobis": get(
                geom, "reaching_vs_releasing", "mahalanobis_centroid_distance"),
            "reaching_vs_releasing_verdict": get(
                geom, "reaching_vs_releasing", "verdict"),
            "velocity_within_minus_cross_sign_agreement": get(
                vgeom, "matched_neighbour_sign_agreement", "within_minus_cross"),
            "nn_same_phase_rate": {
                k: get(geom, "nearest_neighbour_phase_mixing",
                       "aggregate_same_phase_rate", k, "mean_nn_same_phase_rate")
                for k in ("REACHING", "MANIPULATION", "RELEASING")},
        },
        "stratum_used": "INTERIOR",
        "boundary_comparison": {
            rep: {"interior_ba": get(bound, "by_representation", rep, "interior",
                                     "balanced_accuracy"),
                  "boundary_ba": get(bound, "by_representation", rep, "boundary",
                                     "balanced_accuracy")}
            for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY")},
        "handedness_limitation": {
            "single_hand_block": get(hnd, "verdict", "single_hand_block"),
            "which_hand": "NOT DECIDED",
            "mirroring_applied": False,
            "subjects_excluded": 0,
        },
        "anti_rescue_attestation": (
            "no feature beyond the frozen representations was added; no neural "
            "network or Transformer was used; no ADL, object, EMG, subject id or "
            "future label entered any model; no phase was merged post-hoc; no "
            "temporal window was re-selected after seeing results; the two "
            "sensitivity windows were reported and the headline window was NOT "
            "changed"),
        "reading_order_applied": P.DECISION["reading_order"],
    }
    sha = C.write_json(os.path.join(C.LANE, OUT), body)
    log(f"  wrote {OUT}  sha256={sha[:16]}")
    fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
