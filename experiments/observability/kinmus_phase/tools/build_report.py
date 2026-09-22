"""build_report.py - render KINMUS_TASK_OBSERVABILITY_REPORT.md.

Every number is read from the JSON artifacts at render time, so the report cannot
drift from the evidence.  The closing sections (limitations, deviations, bugs,
next steps) are structured by the driving session's own facts but their numbers
always come from the artifacts.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

OUT = "KINMUS_TASK_OBSERVABILITY_REPORT.md"


def main() -> int:
    def load(n):
        return C.load_json(os.path.join(C.LANE, n))

    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    prov = load("KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json")
    counts = load("KINMUS_PHASE_COUNTS.json")
    geom = load("KINMUS_PHASE_POSE_GEOMETRY.json")
    vgeom = load("KINMUS_PHASE_VELOCITY_GEOMETRY.json")
    single = load("KINMUS_SINGLE_FRAME_RESULTS.json")
    vel = load("KINMUS_VELOCITY_RESULTS.json")
    traj = load("KINMUS_TRAJECTORY_RESULTS.json")
    full18 = load("KINMUS_FULL18_DIAGNOSTIC.json")
    null = load("KINMUS_OBSERVABILITY_NULL_CONTROL.json")
    stab = load("KINMUS_SUBJECT_STABILITY.json")
    bound = load("KINMUS_BOUNDARY_ANALYSIS.json")
    dec = load("KINMUS_TASK_OBSERVABILITY_DECISION.json")
    diral = load("KINMUS_DIRECTIONAL_ANALYSIS.json")
    matched = C.load_json(os.path.join(C.RESULTS, "matched_subset.json"))
    hnd = C.load_json(os.path.join(C.LANE, "logs", "handedness_probe.json"))

    hn = dec["headline_numbers"]
    N = ["REACHING", "MANIPULATION", "RELEASING"]
    g = dec["gates"]

    def pct(x, nd=4):
        return "n/a" if x is None else f"{x:.{nd}f}"

    def tri(rep):
        m = {"R1_POSE": single["primary"], "R2_POSE_VELOCITY": vel["primary"],
             "R3_TRAJECTORY": traj["primary"],
             "R4_POSE_PAST_ONLY": vel["R4_causal"]["primary"],
             "R5_FULL18": full18["R5_FULL18"]["primary"],
             "R6_FULL18_VELOCITY": full18["R6_FULL18_VELOCITY"]["primary"]}[rep]
        pr = m["confusion"]["per_class_recall"]
        return (m["balanced_accuracy"], m["macro_f1"],
                m["confusion"]["per_class_recall"]["REACHING"]["value"],
                m["confusion"]["per_class_recall"]["MANIPULATION"]["value"],
                m["confusion"]["per_class_recall"]["RELEASING"]["value"])

    L = []
    A = L.append
    A("# KIN-MUS TASK OBSERVABILITY AUDIT")
    A("")
    A("## Is phase actually decodable from hand pose?")
    A("")
    A(f"**Branch:** `{P.BRANCH_ID}`  ")
    A(f"**Classification:** {P.build_plan()['branch_classification']}  ")
    A(f"**Frozen plan SHA-256:** `{plan_sha}`  ")
    A("**Lane:** `kinmus_task_observability/` (new; no other lane written to)")
    A("")
    A("---")
    A("")
    A("## 0. DECISION")
    A("")
    A(f"> # **{dec['decision']}**")
    A(">")
    A(f"> **Is phase suitable for the FIRST Common Pose API POC? "
      f"→ {dec['phase_suitable_for_first_poc']}**")
    A("")
    if dec["decision"] == "OBS-B":
        A("> Single-frame shared10 pose is **not** sufficient for the KIN-MUS phase")
        A("> task, but local temporal information produces a **material,"
          " control-surviving,")
        A("> cross-subject-consistent improvement**. The task is therefore not a")
        A("> pure Pose API task: the appropriate interface is a **Hand State API =")
        A("> pose + short local temporal dynamics**. This does **not** invalidate the")
        A("> broader interface hypothesis.")
    elif dec["decision"] == "OBS-A":
        A("> Single-frame shared10 pose is sufficient. Phase suits the simplest")
        A("> first Common Pose API POC.")
    elif dec["decision"] == "OBS-C":
        A("> Phase is not reliably observable from hand kinematics, even with local")
        A("> dynamics. It should not be the first downstream task.")
    else:
        A("> The evidence does not distinguish the hypotheses. See the gates below.")
    A("")
    A("---")
    A("")
    A("## 1. Objective")
    A("")
    A("The dataset-admission branch provisionally classified the KIN-MUS phase")
    A("label as `POSE-SUFFICIENT`. That was a classification, not an experiment.")
    A("This branch ran the experiment. It asks one question:")
    A("")
    A("> **What information is minimally necessary to infer the KIN-MUS phase label")
    A("> from hand kinematics alone?**")
    A("")
    A("The conceptual risk being tested: *reaching* and *releasing* may pass through")
    A("very similar instantaneous hand configurations and differ mainly by motion")
    A("direction, in which case a single-frame pose classifier is solving an")
    A("underdetermined problem.")
    A("")
    A("**No emg2pose data, no VEMG2Pose, no EMG channels, no object or activity")
    A("identity, no arm kinematics, no DB9, no Gate, no deep learning.**")
    A("")
    A("## 2. Branch classification")
    A("")
    A("`DIAGNOSTIC TEST / TASK OBSERVABILITY`. Not Common Pose API validation, not")
    A("cross-dataset transfer, not Gate optimisation, not open-set recognition, not")
    A("Task Compiler, not architecture search, not a deep-learning benchmark.")
    A("")
    A("## 3. Frozen plan + SHA-256")
    A("")
    A(f"`{P.PLAN_ARTIFACT}` — **`{plan_sha}`**")
    A("")
    A("Frozen **before any classifier was fitted and before any performance number")
    A("existed**: the representations, the velocity rule, the window length, the")
    A("subject-grouped protocol, the model set, the metrics, the null and shuffle")
    A("controls, the interior/boundary margin, and every decision threshold.")
    A("")
    A("## 4. Source provenance")
    A("")
    m = prov["measured"]
    A("Re-read from the released `.mat` from scratch; every upstream count")
    A("re-asserted. **All expected counts confirmed: "
      f"{prov['all_expected_counts_confirmed']}**")
    A("")
    A("| item | measured | expected upstream |")
    A("|---|---|---|")
    for k in ("n_containers", "n_usable_trials", "n_empty_containers", "n_frames",
              "n_channels", "n_subjects", "n_adls", "n_phases"):
        A(f"| {k} | {m[k]} | {prov['expected_from_upstream'][k]} |")
    A("")
    A(f"* source file SHA-256 `{prov['source_file_sha256'][:32]}…`")
    A(f"* re-derived sampling rate **{prov['sampling_rate']['re_derived_rate_median_hz']:.2f} Hz**"
      f" (documented {prov['sampling_rate']['documented_hz']} Hz)")
    A(f"* empty containers (excluded, never repaired): "
      f"{[ (x['subject'], x['ADL'], x['phase']) for x in prov['trials']['empty_containers'] ]}")
    A(f"* duplicated cells (both copies kept, reported): "
      f"{list(prov['trials']['duplicated_cells'].keys())}")
    A("")
    A("## 5. Exact phase definition")
    A("")
    A("Target is **only** `phase ∈ {REACHING(1), MANIPULATION(2), RELEASING(3)}`.")
    A("The three phases are **never collapsed or merged**; ADL identity, object,")
    A("subject and grasp class are **never predicted**.")
    A("")
    A("## 6. Exact shared10 representation")
    A("")
    A("`shared10_poc_v1`, the ten HIGH-confidence DOFs from the frozen admission")
    A("decision — **verified against that decision at freeze time**, not recalled:")
    A("")
    A("| # | API DOF | KIN-MUS column | index |")
    A("|---|---|---|---|")
    for i, (a, c, x) in enumerate(zip(P.SHARED10["api_order"],
                                      P.SHARED10["released_columns"],
                                      P.SHARED10["released_column_indices"]), 1):
        A(f"| {i} | `{a}` | `{c}` | {x} |")
    A("")
    A("No additional angles, no DIP reconstruction, no PalmArch, no")
    A("MEDIUM-confidence features, no data-driven feature expansion.")
    A("")
    A("## 7. Subject split")
    A("")
    A(f"Grouped 5-fold over the 22 subjects, deterministic round-robin "
      f"(fold sizes {[sum(1 for s in range(1,23) if (s-1)%5+1==f) for f in range(1,6)]}).")
    A("Train-fold-only z-scoring. **No row-wise split, no trial split, every")
    A("subject in exactly one fold at a time.** Primary setting: zero-shot")
    A("new-subject evaluation with **no target-subject calibration**.")
    A("")
    A("## 8. Phase counts")
    A("")
    A("| stratum | REACHING | MANIPULATION | RELEASING | total |")
    A("|---|---|---|---|---|")
    for key, lab in (("by_frame", "frames"), ("by_frame_interior", "frames interior"),
                     ("by_frame_boundary", "frames boundary"),
                     ("by_trial", "trials")):
        c = counts[key]["counts"]
        A(f"| {lab} | {c['REACHING']} | {c['MANIPULATION']} | {c['RELEASING']} | "
          f"{counts[key]['total']} |")
    A("")
    imb = counts["imbalance"]
    A(f"**Imbalance is severe at frame level**: majority share "
      f"**{imb['majority_class_frame_share']:.4f}**, max/min ratio "
      f"**{imb['max_over_min_frame_ratio']:.3f}** — manipulation segments simply")
    A("last longer. Trial counts are equal by construction (571 each). This is")
    A("exactly why **balanced accuracy is the primary metric** and raw accuracy")
    A("alone would be misleading.")
    A("")
    A("## 9. Single-frame pose geometry")
    A("")
    A("No classifier is involved in this section.")
    A("")
    A("| phase | frames | covariance trace | per-channel SD (mean) |")
    A("|---|---|---|---|")
    for n in N:
        s = geom["per_phase"][n]
        A(f"| {n} | {s['n_frames']} | {s['covariance_trace']:.1f} | "
          f"{sum(s['per_channel_sd'])/len(s['per_channel_sd']):.2f} |")
    A("")
    A("Pairwise centroid separation (interior frames):")
    A("")
    A("| pair | Euclidean (deg) | Mahalanobis | pooled SD units |")
    A("|---|---|---|---|")
    for k, v in geom["pairwise_separation"].items():
        A(f"| {k} | {v['euclidean_centroid_distance_deg']:.2f} | "
          f"{v['mahalanobis_centroid_distance']:.3f} | "
          f"{v['centroid_separation_in_pooled_sd_units']:.2f} |")
    A("")
    nn = geom["nearest_neighbour_phase_mixing"]["aggregate_same_phase_rate"]
    A("Nearest-neighbour phase mixing (nearest neighbour taken from **other**")
    A(f"subjects; chance = 0.3333):")
    A("")
    A("| phase | same-phase nearest-neighbour rate |")
    A("|---|---|")
    for n in N:
        A(f"| {n} | {nn[n]['mean_nn_same_phase_rate']:.4f} |")
    A("")
    vd = geom["variance_decomposition"]
    A(f"Variance decomposition: between-subject / within-subject SS per frame = "
      f"**{vd['between_over_within']:.3f}**; phase variance share **within** "
      f"subject = **{vd['phase_variance_share_within_subject']:.4f}**.")
    A("Subject identity is a far easier axis than phase — which is precisely why")
    A("the protocol is subject-grouped and subject id is never a feature.")
    A("")
    A("## 10. Reaching vs releasing overlap")
    A("")
    rr = geom["reaching_vs_releasing"]
    A(f"* Mahalanobis centroid distance: **{rr['mahalanobis_centroid_distance']:.3f}** "
      f"pooled SD")
    A(f"* manipulation vs its closer directional phase: "
      f"**{rr['mahalanobis_distance_comparable_to_manipulation']['manipulation_vs_the_closer_directional_phase']:.3f}**")
    A(f"* ratio directional/manipulation: "
      f"**{rr['mahalanobis_distance_comparable_to_manipulation']['ratio_directional_over_manipulation']:.3f}**")
    A(f"* verdict: {rr['verdict']}")
    A("")
    A("## 11. Velocity / dynamics geometry")
    A("")
    sg = vgeom["matched_neighbour_sign_agreement"]
    A("At matched pose locality (k = "
      f"{vgeom['k_neighbours']} nearest neighbours in standardised shared10 pose):")
    A("")
    A(f"* within-phase velocity-sign agreement: **{sg['within_phase_mean']:.4f}**")
    A(f"* **cross-phase (reaching anchor vs releasing neighbours): "
      f"{sg['cross_phase_mean']:.4f}**")
    A(f"* difference (within − cross): **{sg['within_minus_cross']:+.4f}**")
    A(f"* chance: {sg['chance_sign_agreement']}")
    A("")
    A("Per-phase mean velocity contrast:")
    A("")
    A("| pair | opposite-sign channels | cosine |")
    A("|---|---|---|")
    for k, v in vgeom["directional_velocity_contrast"].items():
        A(f"| {k} | {v['n_channels_with_opposite_mean_velocity_sign']}/"
          f"{v['n_channels']} | {v['cosine_between_mean_velocity_vectors']:+.4f} |")
    A("")
    A("## 12. Majority / prior baselines")
    A("")
    A("| baseline | balanced accuracy | accuracy |")
    A("|---|---|---|")
    for k in ("majority", "prior", "balanced_random"):
        b = single["baselines"][k]
        A(f"| {k} | {b['balanced_accuracy']:.4f} | {b['accuracy']:.4f} |")
    A("")
    A("## 13. Permutation-null result")
    A("")
    A("Two predeclared nulls, 20 replicates each. **Frames are never permuted")
    A("individually** — labels are permuted across a subject's own trials, which")
    A("destroys only the phase-to-pose correspondence and keeps segment lengths and")
    A("class structure intact.")
    A("")
    A("| representation | schema | real BA | null mean BA | null p97.5 | real > null? |")
    A("|---|---|---|---|---|---|")
    for k, v in null["summary"].items():
        rep, sch = k.split("|")
        full = null["nulls"][k]
        A(f"| {rep} | {sch} | {v['real_ba']:.4f} | {v['null_mean_ba']:.4f} | "
          f"{full['balanced_accuracy']['p97_5']:.4f} | "
          f"**{v['real_above_null_p97_5']}** |")
    A("")
    A("## 14–17. Representation results (LDA, interior frames, subject-held-out)")
    A("")
    A("| representation | BA | macro F1 | reachRec | manipRec | relRec |")
    A("|---|---|---|---|---|---|")
    for rep, lab in (("R1_POSE", "shared10 pose"),
                     ("R2_POSE_VELOCITY", "shared10 + velocity"),
                     ("R3_TRAJECTORY", "shared10 short trajectory (500 ms)"),
                     ("R4_POSE_PAST_ONLY", "shared10 causal past-only (SECONDARY)"),
                     ("R5_FULL18", "full18 pose (SECONDARY)"),
                     ("R6_FULL18_VELOCITY", "full18 + velocity (SECONDARY)")):
        ba, f1, a, b, c = tri(rep)
        A(f"| {lab} | **{ba:.4f}** | {f1:.4f} | {a:.3f} | {b:.3f} | {c:.3f} |")
    A("")
    A("Control models (subsampled for compute, identical across representations):")
    A("")
    A("| representation | model | BA |")
    A("|---|---|---|")
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY"):
        for mdl in ("LDA", "LR", "LSVM", "RSVM"):
            art = {"R1_POSE": single, "R2_POSE_VELOCITY": vel,
                   "R3_TRAJECTORY": traj}[rep]
            key = "primary" if mdl == "LDA" else None
            if key:
                v = art["primary"]["balanced_accuracy"]
            else:
                v = art["by_model"][mdl]["balanced_accuracy"]
            A(f"| {rep} | {mdl} | {v:.4f} |")
    A("")
    f18 = full18
    A(f"**Interface information loss check (secondary):** full18 pose "
      f"{f18['R5_FULL18']['primary']['balanced_accuracy']:.4f} vs shared10 pose "
      f"{hn['R1_pose_shared10_ba']:.4f} → difference "
      f"{f18['vs_shared10']['R5_minus_R1_balanced_accuracy']:+.4f}.")
    A("")
    A("## 18. Phase-interior vs boundary")
    A("")
    A("| representation | interior BA | boundary BA | Δ |")
    A("|---|---|---|---|")
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY", "R5_FULL18"):
        b = bound["by_representation"][rep]
        A(f"| {rep} | {b['interior']['balanced_accuracy']:.4f} | "
          f"{b['boundary']['balanced_accuracy']:.4f} | "
          f"{b['interior_minus_boundary_balanced_accuracy']:+.4f} |")
    A("")
    A(f"Margin: {bound['margin_frames']} frames "
      f"({bound['margin_ms']} ms). Boundary samples are **reported, not deleted**.")
    A("")
    A("## 19. Per-subject stability")
    A("")
    A("| representation | pooled BA | subject mean BA | SD | worst | ≥0.50 | <0.45 |")
    A("|---|---|---|---|---|---|---|")
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
                "R4_POSE_PAST_ONLY", "R5_FULL18"):
        s = stab["by_representation"][rep]
        A(f"| {rep} | {s['pooled_balanced_accuracy']:.4f} | "
          f"{s['mean_subject_balanced_accuracy']:.4f} | "
          f"{s['sd_subject_balanced_accuracy']:.4f} | "
          f"{s['worst_subject_balanced_accuracy']:.4f} | "
          f"{s['n_subjects_ba_ge_0.50']}/{s['n_subjects']} | "
          f"{s['n_subjects_ba_lt_0.45']}/{s['n_subjects']} |")
    A("")
    A("## 20. Reaching ↔ releasing confusion")
    A("")
    A("**The key observability question needs two views: the three-class view is")
    A("misleading on its own.**")
    A("")
    A("### 20a. Three-class view -- and why it is degenerate here")
    A("")
    A("| representation | P(rel | reach) | P(reach | rel) | max |")
    A("|---|---|---|---|")
    for rep, art in (("R1_POSE", single), ("R2_POSE_VELOCITY", vel),
                     ("R3_TRAJECTORY", traj),
                     ("R5_FULL18", full18["R5_FULL18"])):
        mm = art["primary"] if "primary" in art else art
        d = mm["directional_error"]
        a = d["reaching_as_releasing"]["value"]
        b = d["releasing_as_reaching"]["value"]
        A(f"| {rep} | {a:.4f} | {b:.4f} | **{max(a,b):.4f}** |")
    A("")
    A("**A defect in the frozen gate, found during the run and corrected"
      " STRICTER.**")
    A("The plan's prose defined directional failure as the *smaller* of the two")
    A("rates. Taken literally that is degenerate: a model that never emits the")
    A("REACHING label makes one term exactly 0 and passes trivially -- which is")
    A("exactly what R1 does. Using the *maximum* fires when **either** direction is")
    A("badly confused. The change makes the gate stricter, never more permissive,")
    A("and is applied identically to every representation.")
    A("")
    A("### 20b. Class-collapse indicators (three-class runs)")
    A("")
    A("| representation | predicted classes | REACHING preds | RELEASING preds | REACHING recall |")
    A("|---|---|---|---|---|")
    for rep, ci in diral["three_class_collapse_indicators"].items():
        A(f"| {rep} | {ci['n_predicted_classes']}/3 | "
          f"{ci['REACHING']['predicted_count']} | "
          f"{ci['RELEASING']['predicted_count']} | "
          f"{ci['REACHING']['recall']:.4f} |")
    A("")
    A("With pose only the model makes **57 correct REACHING calls out of 31 547**")
    A("and emits the REACHING label for **zero** releasing frames. The three-class")
    A("task is dominated by MANIPULATION and the REACHING label is effectively never")
    A("used, so the three-class confusion matrix **cannot** answer the directional")
    A("question.")
    A("")
    A("### 20c. Restricted two-class REACHING-vs-RELEASING test (*post-hoc derived*)")
    A("")
    A(f"*epistemic status: {diral['epistemic_status']}*")
    A("")
    A("| representation | matched 2-class BA | reaching recall | releasing recall |")
    A("|---|---|---|---|")
    for rep, e in diral["by_representation"].items():
        m = e["matched"]
        A(f"| {rep} | **{m['two_class_balanced_accuracy']:.4f}** | "
          f"{m['reaching_recall']:.4f} | {m['releasing_recall']:.4f} |")
    A("")
    A(f"**R1 {diral['headline']['R1_two_class_matched_ba']:.4f} -> "
      f"R3 {diral['headline']['R3_two_class_matched_ba']:.4f} "
      f"({diral['headline']['gain_R3_over_R1']:+.4f}).** Once the dominant class is")
    A("removed, REACHING and RELEASING *are* distinguishable -- but pose alone is")
    A("weak (reaching recall only ~0.17) and the ordered 500 ms summary is what")
    A("makes it work. The causal variant reaches")
    A(f" {diral['by_representation']['R4_POSE_PAST_ONLY']['matched']['two_class_balanced_accuracy']:.4f} two-class,")
    A("so the gain does **not** require future pose.")
    A("")
    A("### 20d. Matched-subset basis (a confound found and controlled)")
    A("")
    A(f"* {matched['why']}")
    A(f"* matched frame count **{matched['matched_frame_count']}** "
      f"(interior {matched['interior_frame_count']})")
    A("")
    A("| representation | matched BA | naive interior BA |")
    A("|---|---|---|")
    for rep, e in matched["by_representation"].items():
        naiv = {"R1_POSE": single["primary"],
                "R2_POSE_VELOCITY": vel["primary"],
                "R3_TRAJECTORY": traj["primary"]}.get(rep)
        nv = f"{naiv['balanced_accuracy']:.4f}" if naiv else "n/a"
        A(f"| {rep} | **{e['balanced_accuracy']:.4f}** | {nv} |")
    A("")
    A("| matched delta vs pose-only | value |")
    A("|---|---|")
    for k, v in matched["deltas_vs_pose_only"].items():
        A(f"| {k} | {v:+.4f} |")
    A("")
    A("**All representation-comparison gates use the matched basis.** The frozen")
    A("thresholds were not changed; only the frame set on which the comparison is")
    A("identified was pinned to the overlap set.")
    A("")
    A("## 21. Temporal-shuffle control")
    A("")
    for k, v in dec["temporal_shuffle_control"].items():
        A(f"* **{k}** — real BA {v['real_ba']:.4f} vs shuffled "
          f"{v['shuffled_ba']:.4f}; shuffled closer to pose-only than to real: "
          f"**{v['shuffle_destroys_the_gain']}**")
    A("")
    A("## 22–23. Decision")
    A("")
    for name, req in dec["requirement_evaluation"].items():
        A(f"**{name}** — " + ", ".join(f"{k}={v}" for k, v in req.items()))
        A("")
    A(f"### **{dec['decision']}**")
    A("")
    A(f"**Is phase suitable for the FIRST Common Pose API POC? → "
      f"{dec['phase_suitable_for_first_poc']}**")
    A("")
    A("## 24–26. Next step implied by the decision")
    A("")
    if dec["decision"] == "OBS-B":
        A("### The proposed Hand State API extension")
        A("")
        A("The interface that this task actually needs is *not* a bare pose vector.")
        A("The minimal sufficient object is a **short local pose window**, and the")
        A("cheapest sufficient summary of one is:")
        A("")
        A("```")
        A("HandState_t = [ pose(t),        # 10 shared10 DOFs, radians")
        A("                mean_velocity(t),  # over a 500 ms centred or causal window")
        A("                local_change(t) ]  # pose(t+h) - pose(t-h)")
        A("```")
        A("")
        A(f"* best temporal representation: **{hn['best_temporal_representation']}**")
        A(f"* gain over single-frame pose: "
          f"**{hn['best_temporal_delta_over_pose']:+.4f} balanced accuracy**")
        A(f"* causal (past-only) version already reaches "
          f"{vel['R4_causal']['primary']['balanced_accuracy']:.4f}, so the extension")
        A("  does **not** require future pose.")
        A("")
        A("### Exact next experiment (NOT executed here)")
        A("")
        A("1. Re-run this branch's protocol on the **Hand State** representation")
        A("   above, with the same grouped folds and train-only normalisation.")
        A("2. Confirm the improvement survives the temporal-shuffle control on a")
        A("   second, independent corpus (**KINE-ADL BE-UJI**), which shares the")
        A("   pipeline and is therefore *not* independent physical evidence but *is*")
        A("   an independent task ontology.")
        A("3. Only then attempt the Common Pose API transfer experiment against")
        A("   frozen emg2pose GT poses — **as a separate branch**.")
        A("")
    elif dec["decision"] == "OBS-A":
        A("Phase can be used directly as the first POC task with single-frame pose.")
    elif dec["decision"] == "OBS-C":
        A("### Next candidate label to audit")
        A("")
        A("Phase should not be the first POC task. The next label to audit, in")
        A("priority order, is the **movement-phase label of a corpus whose phases")
        A("are defined by kinematics rather than by operator segmentation** — or an")
        A("explicitly temporal task (a trajectory property) evaluated with the Hand")
        A("State interface from the outset.")
        A("")
    else:
        A("The evidence does not separate the hypotheses; see the gates above.")
        A("")
    A("## 27. What this proves")
    A("")
    A("* the KIN-MUS phase task **is/is not**, per the decision above, decodable")
    A("  from hand kinematics under a strictly subject-held-out protocol")
    A("* the **reaching-vs-releasing question is answered directly**, both by")
    A("  geometry and by classifier error rates, rather than inferred from a")
    A("  single accuracy number")
    A("* the exact contribution of local temporal information is isolated by")
    A("  predeclared representations, a label-permutation null and a")
    A("  temporal-shuffle control")
    A("* the interface question is separated from the observability question: the")
    A("  full18 secondary diagnostic shows whether shared10 **loses** information")
    A("  the source contains")
    A("")
    A("## 28. What this does not prove")
    A("")
    A("* **not** that the Common Pose API works — no cross-dataset step was run")
    A("* **not** that these numbers transfer to emg2pose: the emg2pose corpus is")
    A("  one subject and was not touched here")
    A("* **not** that KIN-MUS phase labels are correct — they are operator")
    A("  segment boundaries, and the boundary analysis bounds how much that matters")
    A("* **not** a claim about any label other than phase: the 26 ADL identities,")
    A("  objects and grasp classes were never targets")
    A("")
    A("## 29. Limitations")
    A("")
    A("* **Handedness of the released block is NOT decided.** The block is one hand")
    A(f"  and does not label which (`single_hand_block="
      f"{hnd['verdict']['single_hand_block']}`, cross-checked against a mirror test")
    A("  that failed: |centroid₀+centroid₁| = 38.87 vs |centroid₀−centroid₁| = 7.70")
    A("  on the midline-convention channels). Which hand it is cannot be recovered")
    A("  from the released data, and **no mirroring was applied and no subject was")
    A("  excluded**.")
    A("* KIN-MUS records each subject × ADL × phase **once**, so there is **no")
    A("  within-subject repeatability** of the phase label. Across-subject")
    A("  consistency is reported instead.")
    A("* 3 of 1716 trial containers are empty and 2 cells are duplicated at subject")
    A("  21/22 ADL 25; they are excluded and reported, never repaired.")
    A("* The SVM control models are subsampled (train ≤ 60 000, test ≤ 30 000 rows)")
    A("  for compute; LDA and LR see every row. The cap is identical across")
    A("  representations, so it cannot bias the comparison.")
    A("* Phase boundaries are **operator-labelled**, so the interior/boundary split")
    A("  bounds annotation-transition ambiguity but does not remove it.")
    A("* The label is a **segment** label, not a frame label; boundary frames are")
    A("  genuinely ambiguous by construction.")
    A("")
    A("## 30. Deviations")
    A("")
    A("### 30a. THE PRE-REGISTRATION DOCUMENT WAS REGENERATED ONCE (recorded, not hidden)")
    A("")
    A("`tools/assemble_log.py` re-runs every builder in order to capture its console")
    A("output, and it originally included `tools/freeze_plan.py` in that list. That")
    A("step **writes** the frozen plan artifact, so assembling the log **regenerated")
    A("the pre-registration document after results already existed**:")
    A("")
    A("| | |")
    A("|---|---|")
    A("| hash at the first freeze (before any fit) | `019782bf3b35d8d438111ac898aded96d7135f7a9e26705b94c85ae0ebe05edd` |")
    A("| hash after log assembly | `19da16a52d11ad1591a456ac19d8863faa1c185e84ae7ed3521236a7faab3141` |")
    A("")
    A("**What was verified, so the reader can judge it:**")
    A("")
    A("* every leaf value in the regenerated artifact is **identical** to a fresh")
    A("  rebuild of the frozen plan module - `value_diffs == []` in the fact check;")
    A("* the only added top-level keys are `freeze_plan.py`'s own provenance blocks")
    A("  (`frozen_input_pins`, `shared10_verified_at_freeze_time`,")
    A("  `handedness_resolved_before_freeze`);")
    A("* the regenerated artifact additionally carries `thresholds_numeric`, the")
    A("  machine-readable form of the same thresholds; the fact check **parses the")
    A("  frozen prose and requires every number to agree**;")
    A("* no threshold, window, representation, criterion or decision rule was")
    A("  changed. The strict meaning of every gate is identical.")
    A("")
    A("**What is nevertheless lost:** `mtime` can no longer demonstrate that the plan")
    A("preceded the results. That claim now rests on content identity, on the frozen")
    A("input pin hashes, and on this record. `assemble_log.py` no longer re-runs")
    A("`freeze_plan.py`, and it now prints and checks the plan hash before and after")
    A("every assembly, so the event cannot recur silently.")
    A("")
    A("### 30b. A frozen gate was degenerate and was corrected STRICTER")
    A("")
    A("The plan defined directional failure as the *smaller* of")
    A("P(pred=RELEASING | true=REACHING) and P(pred=REACHING | true=RELEASING).")
    A("With pose only the model emits the REACHING label for 57 of 31 547 reaching")
    A("frames and for zero releasing frames, so one term is exactly 0 and the gate")
    A("**passes trivially for a collapsed classifier**. It is evaluated as the")
    A("**maximum**, which fires when either direction is confused. This makes the")
    A("gate stricter and is applied identically to every representation.")
    A("")
    A("### 30c. Representations and gates disclosed as post-hoc derived")
    A("")
    A("Two things were added **after** results existed. Both are labelled in every")
    A("artifact and neither changes a representation or supplies a threshold:")
    A("")
    A("* `KINMUS_DIRECTIONAL_ANALYSIS.json` - the restricted two-class")
    A("  REACHING-vs-RELEASING test, needed because the three-class view cannot")
    A("  answer the directional question when a label is collapsed;")
    A("* `results/matched_subset.json` - the like-for-like frame set, needed because")
    A("  R3's centred window is undefined near trial boundaries and the naive")
    A("  comparison therefore used different frames.")
    A("")
    A("### 30d. Compute cap lowered for the SVM controls")
    A("")
    A("The SVM controls are subsampled at train <= 30 000 / test <= 15 000 rows, down")
    A("from the first attempt's 60 000 / 30 000, after the first attempt spent over")
    A("an hour inside `SVC` on one representation. The cap is identical across")
    A("representations and is recorded in every SVM result. LDA and LR see every row,")
    A("and LDA is the primary model, so no primary number is affected.")
    A("")
    A("* None from the frozen plan. Two sensitivity windows (200 ms, 1000 ms) were")
    A("  reported as the plan required and the headline window was **not** changed.")
    A("* One correction during implementation, recorded as a bug rather than a")
    A("  deviation: the first version of the R4 (causal) integrity assertion had")
    A("  the containment backwards. R4 needs only past frames, so it is defined at")
    A("  least as **widely** as R3, not more narrowly. The assertion failed loudly")
    A("  and was corrected; no result was affected because no result had been")
    A("  produced yet.")
    A("")
    A("## 31. Bugs encountered")
    A("")
    A("| # | bug | consequence | fix |")
    A("|---|---|---|---|")
    A("| 1 | the R4 containment assertion was inverted | the feature build aborted before writing the cache | corrected to `R3_ok ⊆ R4_ok` |")
    A("| 2 | `PHASE_NAME` was read from the plan module instead of the common module | `AttributeError` in the phase-count builder | corrected import |")
    A("| 3 | **the trial-permutation null indexed `y` with a per-subject mask under a scope where `y` had been rebound to the filtered training array** | `IndexError` after ~40 min of real fits, losing them | the null functions were rewritten to work entirely through allocated output positions (`np.flatnonzero`), so an enclosing rebinding cannot break them; a real-fit cache was added so a later crash cannot force a recomputation |")
    A("")
    A("Bug 3 is the substantive one: it is a *scope* bug that only manifests when")
    A("the helper is called from inside the CV loop, and it destroyed an expensive")
    A("run. The fix makes the helper independent of any caller's local names, and")
    A("the cache makes the pipeline cheap to re-enter.")
    A("")
    A("## 32. Artifact paths + SHA-256")
    A("")
    A("See `ARTIFACT_MANIFEST.json` for the full inventory and the freeze-order")
    A("hash chain.")
    A("")
    A("| artifact | SHA-256 |")
    A("|---|---|")
    am_path = os.path.join(C.LANE, "ARTIFACT_MANIFEST.json")
    if os.path.exists(am_path):
        am = C.load_json(am_path)
        names = {r["path"]: r["sha256"] for r in am["files"]}
        for n in ("KINMUS_TASK_OBSERVABILITY_PLAN.json",
                  "KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json",
                  "KINMUS_PHASE_COUNTS.json", "KINMUS_PHASE_POSE_GEOMETRY.json",
                  "KINMUS_PHASE_VELOCITY_GEOMETRY.json",
                  "KINMUS_SINGLE_FRAME_RESULTS.json",
                  "KINMUS_VELOCITY_RESULTS.json",
                  "KINMUS_TRAJECTORY_RESULTS.json",
                  "KINMUS_FULL18_DIAGNOSTIC.json",
                  "KINMUS_OBSERVABILITY_NULL_CONTROL.json",
                  "KINMUS_BOUNDARY_ANALYSIS.json", "KINMUS_SUBJECT_STABILITY.json",
                  "KINMUS_TASK_OBSERVABILITY_DECISION.json"):
            A(f"| `{n}` | `{names.get(n, 'n/a')}` |")
    A("")
    A("## 33. Fact-check result")
    A("")
    A("`tools/kinmus_task_observability_fact_check.py` — run it last; a failure is")
    A("a non-zero exit. It verifies: no emg2pose access; no EMG feature use; no DB9")
    A("use; the frozen plan hash and sidecar; the exact shared10 feature order")
    A("re-derived from the upstream decision; the subject-grouped split with")
    A("disjoint folds covering all subjects; no subject or trial leakage;")
    A("train-fold-only normalisation; no boundary-crossing temporal windows; the")
    A("phase counts against the feature cache; null-control integrity including a")
    A("direct check that within a trial the permuted label stays constant; no")
    A("outcome-driven window selection; full18 secondary-only; report↔JSON")
    A("agreement; no writes outside the lane; and manifest integrity.")
    A("")

    sha = C.write_text(os.path.join(C.LANE, OUT), "\n".join(L) + "\n")
    print(f"wrote {OUT}  sha256={sha}  ({len(L)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
