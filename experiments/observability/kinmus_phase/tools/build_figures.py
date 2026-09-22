"""build_figures.py - the 11 required figures.

Reads artifacts and the frozen feature cache only.  Fits nothing that any result
depends on.  Every figure is regenerable.
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

CACHE = os.path.join(C.RESULTS, "features.npz")
COL = {"REACHING": "#1565c0", "MANIPULATION": "#2e7d32", "RELEASING": "#c62828"}
SEED = 20260101


def load(n):
    return C.load_json(os.path.join(C.LANE, n))


def save(fig, name):
    os.makedirs(C.FIGDIR, exist_ok=True)
    p = os.path.join(C.FIGDIR, name)
    fig.tight_layout()
    fig.savefig(p, dpi=130)
    plt.close(fig)
    print(f"    {name}")


def main() -> int:
    log, fh = C.log_to(os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt"))
    log("")
    log("=" * 78)
    log("STAGE 13 - FIGURES")
    log("=" * 78)

    z = np.load(CACHE, allow_pickle=False)
    y, subj = z["phase"], z["subject"]
    interior = z["boundary_interior"]
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
    names = ["REACHING", "MANIPULATION", "RELEASING"]
    phases = [1, 2, 3]

    # ---- 1 class distribution -------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, (key, title) in zip(axes, (("by_frame", "by FRAME"),
                                       ("by_trial", "by TRIAL"),
                                       ("by_subject", "by SUBJECT (trials)"))):
        if key == "by_subject":
            vals = [sum(counts["by_subject"][s]["frames_by_phase"][n]
                        for s in counts["by_subject"]) for n in names]
        else:
            vals = [counts[key]["counts"][n] for n in names]
        ax.bar(names, vals, color=[COL[n] for n in names])
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v}", ha="center", va="bottom", fontsize=8)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=20)
    fig.suptitle("1. Phase class distribution (KIN-MUS, 1713 usable trials, "
                 "564 894 frames)")
    save(fig, "01_phase_class_distribution.png")

    # ---- 2 single-frame PCA projection by phase --------------------------
    X = z["R1_POSE"][interior]
    yint = y[interior]
    mu = X.mean(axis=0)
    Xz = X - mu
    U, S, Vt = np.linalg.svd(Xz, full_matrices=False)
    evr = (S ** 2) / (S ** 2).sum()
    rng = np.random.default_rng(SEED)
    sub = rng.choice(Xz.shape[0], min(30000, Xz.shape[0]), replace=False)
    proj = Xz[sub] @ Vt[:2].T
    ys = yint[sub]
    fig, ax = plt.subplots(figsize=(8, 6.4))
    for c, n in zip(phases, names):
        s = ys == c
        ax.scatter(proj[s, 0], proj[s, 1], s=3, alpha=0.25, color=COL[n], label=n)
    ax.scatter(proj[:, 0], proj[:, 1], s=0, alpha=0)
    ax.set_xlabel(f"PC1 ({evr[0]*100:.1f} % var)")
    ax.set_ylabel(f"PC2 ({evr[1]*100:.1f} % var)")
    ax.legend(markerscale=4, fontsize=8)
    ax.set_title("2. shared10 instantaneous pose, PCA projection by phase\n"
                 "(PCA is for visualisation only and is never a model input)")
    save(fig, "02_pca_projection_by_phase.png")

    # ---- 3 reaching vs releasing pose overlap ----------------------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    ax = axes[0]
    for c, n in zip(phases, names):
        s = ys == c
        ax.scatter(proj[s, 0], proj[s, 1], s=4, alpha=0.35, color=COL[n], label=n)
    ax.set_title("3a. all three phases in PC1-PC2")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend(markerscale=3, fontsize=8)
    ax = axes[1]
    for c, n in [(1, "REACHING"), (3, "RELEASING")]:
        s = ys == c
        ax.scatter(proj[s, 0], proj[s, 1], s=4, alpha=0.35, color=COL[n], label=n)
    rr = geom["reaching_vs_releasing"]
    ax.set_title(f"3b. REACHING vs RELEASING only\nMahalanobis centroid distance "
                 f"{rr['mahalanobis_centroid_distance']:.2f} pooled SD")
    ax.set_xlabel("PC1")
    ax.legend(markerscale=3, fontsize=8)
    fig.suptitle("3. REACHING vs RELEASING pose overlap")
    save(fig, "03_reaching_vs_releasing_overlap.png")

    # ---- 4 reaching vs releasing velocity separation ---------------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    mvel = {n: np.array(vgeom["per_phase_mean_velocity"][n]
                        ["mean_velocity_deg_per_s"]) for n in names}
    idx = np.arange(10)
    w = 0.38
    ax = axes[0]
    ax.bar(idx - w / 2, mvel["REACHING"], w, label="REACHING", color=COL["REACHING"])
    ax.bar(idx + w / 2, mvel["RELEASING"], w, label="RELEASING", color=COL["RELEASING"])
    ax.axhline(0, color="k", lw=1)
    ax.set_xticks(idx)
    ax.set_xticklabels([n.replace("_flexion", "").replace("_", " ")
                        for n in P.SHARED10["api_order"]], rotation=45, ha="right",
                       fontsize=7)
    ax.set_ylabel("mean velocity (deg/s)")
    ax.set_title("4a. mean velocity per channel")
    ax.legend(fontsize=8)
    ax = axes[1]
    mag = vgeom["matched_neighbour_sign_agreement"]
    vals = [mag["within_phase_mean"], mag["cross_phase_mean"], 0.5]
    ax.bar(["WITHIN\nphase", "CROSS\n(Reach vs Release)", "chance"],
           vals, color=["#2e7d32", "#c62828", "#9e9e9e"])
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("velocity-sign agreement at matched pose locality")
    ax.set_title("4b. does similar pose carry opposite motion?")
    fig.suptitle("4. REACHING vs RELEASING velocity separation")
    save(fig, "04_reaching_vs_releasing_velocity.png")

    # ---- 5/6/7 confusion matrices ---------------------------------------
    def cm_fig(ax, m, title):
        cm = np.array(m["confusion"]["matrix_true_x_pred"], dtype=float)
        rows = cm.sum(axis=1, keepdims=True)
        norm = np.divide(cm, rows, out=np.zeros_like(cm), where=rows > 0)
        im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{norm[i,j]:.2f}\n({int(cm[i,j])})", ha="center",
                        va="center", fontsize=8,
                        color="white" if norm[i, j] > 0.55 else "black")
        ax.set_xticks(range(3))
        ax.set_xticklabels(names, rotation=20, fontsize=8)
        ax.set_yticks(range(3))
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("predicted")
        ax.set_ylabel("true")
        ax.set_title(f"{title}\nBA {m['balanced_accuracy']:.3f}")
        return im
    for fname, key, title in (
            ("05_confusion_pose_only.png", single["primary"],
             "5. Confusion - shared10 POSE only"),
            ("06_confusion_pose_velocity.png", vel["primary"],
             "6. Confusion - shared10 POSE + VELOCITY"),
            ("07_confusion_best_temporal.png", traj["primary"],
             "7. Confusion - shared10 SHORT TRAJECTORY (500 ms)")):
        fig, ax = plt.subplots(figsize=(5.4, 5))
        cm_fig(ax, key, title)
        save(fig, fname)

    # ---- 8 per-subject balanced accuracy ---------------------------------
    fig, ax = plt.subplots(figsize=(13, 5.2))
    subs = sorted(int(s) for s in np.unique(subj))
    series = [("R1_POSE", "shared10 pose", "#1565c0"),
              ("R2_POSE_VELOCITY", "pose+velocity", "#f9a825"),
              ("R3_TRAJECTORY", "trajectory 500 ms", "#2e7d32"),
              ("R5_FULL18", "full18 (secondary)", "#6a1b9a")]
    w = 0.2
    for k, (rep, lab, col) in enumerate(series):
        vals = [stab["by_representation"][rep]["per_subject"][str(s)]
                ["balanced_accuracy"] for s in subs]
        ax.bar(np.arange(len(subs)) + (k - 1.5) * w, vals, w, label=lab, color=col)
    ax.axhline(1 / 3, color="k", ls="--", lw=1)
    ax.text(-0.6, 0.34, "chance", fontsize=8)
    ax.axhline(0.5, color="k", ls=":", lw=1)
    ax.text(-0.6, 0.51, "0.50 gate", fontsize=8)
    ax.set_xticks(np.arange(len(subs)))
    ax.set_xticklabels([f"S{s}" for s in subs], fontsize=7)
    ax.set_ylim(0, 1)
    ax.set_ylabel("per-subject balanced accuracy")
    ax.set_title("8. Per-subject balanced accuracy (subject-held-out, interior "
                 "frames)")
    ax.legend(fontsize=8, ncol=4)
    save(fig, "08_per_subject_balanced_accuracy.png")

    # ---- 9 real vs permutation null --------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.4))
    labels, reals, nullmeans, nullp = [], [], [], []
    for rep, lab in (("R1_POSE", "pose"), ("R2_POSE_VELOCITY", "pose+vel"),
                     ("R3_TRAJECTORY", "traj 500 ms")):
        for scheme, sl in (("N1_TRIAL_PERMUTATION", "N1 trial perm"),
                           ("N2_CIRCULAR_SHIFT", "N2 circular")):
            k = f"{rep}|{scheme}"
            v = null["nulls"][k]
            labels.append(f"{lab}\n{sl}")
            reals.append(v["real_balanced_accuracy"])
            nullmeans.append(v["balanced_accuracy"]["mean"])
            nullp.append(v["balanced_accuracy"]["p97_5"])
    x = np.arange(len(labels))
    lo = np.clip(np.array(nullmeans) - (np.array(nullmeans) - 0.0), 0, None)
    up = np.clip(np.array(nullp) - np.array(nullmeans), 0, None)
    ax.bar(x - 0.2, reals, 0.4, label="real", color="#1565c0")
    ax.bar(x + 0.2, nullmeans, 0.4, label="permutation null (mean)", color="#9e9e9e")
    ax.errorbar(x + 0.2, nullmeans, yerr=[np.zeros(len(up)), up],
                fmt="none", ecolor="k", capsize=3, label="null 97.5th pct")
    # flag the degenerate null honesty: where the null spread is exactly zero the
    # scheme is uninformative and the plot must say so rather than look precise
    for i, (lab, nm, npc) in enumerate(zip(labels, nullmeans, nullp)):
        if abs(npc - nm) < 1e-9:
            ax.text(i, 0.02, "degenerate\nnull", ha="center", fontsize=6,
                    color="#c62828", rotation=90)
    ax.axhline(1 / 3, color="k", ls="--", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(0, 1)
    ax.set_ylabel("balanced accuracy")
    ax.set_title("9. Real vs permutation-null performance (LDA, interior, "
                 "subject-held-out)")
    ax.legend(fontsize=8)
    save(fig, "09_real_vs_null.png")

    # ---- 10 boundary vs interior -----------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.2))
    reps = ["R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY", "R5_FULL18"]
    xi = np.arange(len(reps))
    iv = [bound["by_representation"][r]["interior"]["balanced_accuracy"] for r in reps]
    bv = [bound["by_representation"][r]["boundary"]["balanced_accuracy"] for r in reps]
    ax.bar(xi - 0.2, iv, 0.4, label="INTERIOR (primary)", color="#2e7d32")
    ax.bar(xi + 0.2, bv, 0.4, label="BOUNDARY (secondary)", color="#f9a825")
    for i, (a, b) in enumerate(zip(iv, bv)):
        ax.text(i - 0.2, a, f"{a:.3f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + 0.2, b, f"{b:.3f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(1 / 3, color="k", ls="--", lw=1)
    ax.set_xticks(xi)
    ax.set_xticklabels([r.replace("_", "\n") for r in reps], fontsize=7)
    ax.set_ylim(0, 1)
    ax.set_ylabel("balanced accuracy")
    ax.set_title("10. Boundary vs interior performance "
                 f"(margin {bound['margin_frames']} frames)")
    ax.legend(fontsize=8)
    save(fig, "10_boundary_vs_interior.png")

    # ---- 11 shared10 vs full18 -------------------------------------------
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    rows = [("shared10 pose", single["primary"]["balanced_accuracy"], "#1565c0"),
            ("full18 pose (2nd)", full18["R5_FULL18"]["primary"]
             ["balanced_accuracy"], "#6a1b9a"),
            ("shared10 + vel", vel["primary"]["balanced_accuracy"], "#1565c0"),
            ("full18 + vel (2nd)", full18["R6_FULL18_VELOCITY"]["primary"]
             ["balanced_accuracy"], "#6a1b9a"),
            ("shared10 traj", traj["primary"]["balanced_accuracy"], "#1565c0")]
    ypos = np.arange(len(rows))
    ax.barh(ypos, [r[1] for r in rows], color=[r[2] for r in rows])
    for i, r in enumerate(rows):
        ax.text(r[1], i, f" {r[1]:.3f}", va="center", fontsize=9)
    ax.set_yticks(ypos)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8)
    ax.axvline(1 / 3, color="k", ls="--", lw=1)
    ax.set_xlim(0, 1)
    ax.invert_yaxis()
    ax.set_xlabel("balanced accuracy (interior, subject-held-out)")
    ax.set_title("11. shared10 vs full18: does the Common Pose subset lose "
                 "phase information?\n(full18 is a SECONDARY diagnostic only)")
    save(fig, "11_shared10_vs_full18.png")

    log(f"  {len(os.listdir(C.FIGDIR))} figures written")
    log(f"  decision for reference: {dec['decision']} / "
        f"{dec['phase_suitable_for_first_poc']}")
    fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
