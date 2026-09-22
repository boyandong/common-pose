"""build_geometry.py - direct geometry of the phase pose distribution.

No classifier is fitted here.  The point is to ask BEFORE interpreting any
classifier score whether the three phases are even separable in instantaneous
pose space, and especially whether REACHING and RELEASING geometrically overlap.

Writes:
  KINMUS_PHASE_POSE_GEOMETRY.json
  KINMUS_PHASE_VELOCITY_GEOMETRY.json
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

CACHE = os.path.join(C.RESULTS, "features.npz")
POSE_OUT = "KINMUS_PHASE_POSE_GEOMETRY.json"
VEL_OUT = "KINMUS_PHASE_VELOCITY_GEOMETRY.json"
SEED = 20260101
NN_ANCHORS = 20000
NN_REF = 40000
KNN_K = 50


def subsample(idx: np.ndarray, n: int, rng) -> np.ndarray:
    if idx.size <= n:
        return idx
    return np.sort(rng.choice(idx, n, replace=False))


def main() -> int:
    t0 = time.time()
    log, fh = C.log_to(os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt"))
    log("")
    log("=" * 78)
    log("STAGE 6 - PHASE POSE AND VELOCITY GEOMETRY (no classifier)")
    log("=" * 78)
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    log(f"frozen plan sha256 = {plan_sha}")

    z = np.load(CACHE, allow_pickle=False)
    X = z["R1_POSE"]
    y = z["phase"]
    subj = z["subject"]
    interior = z["boundary_interior"]
    rng = np.random.default_rng(SEED)

    stats = {}
    for c in C.PHASES:
        sel = (y == c) & interior
        A = X[sel]
        mu = A.mean(axis=0)
        med = np.median(A, axis=0)
        cov = np.cov(A, rowvar=False)
        ev = np.linalg.eigvalsh(cov)
        stats[C.PHASE_NAME[c]] = {
            "n_frames": int(sel.sum()),
            "centroid_deg": [float(v) for v in mu],
            "median_deg": [float(v) for v in med],
            "feature_names": P.SHARED10["api_order"],
            "covariance_trace": float(np.trace(cov)),
            "covariance_eigenvalues_desc": [float(v) for v in ev[::-1]],
            "covariance_condition_number": float(ev.max() / max(ev.min(), 1e-12)),
            "per_channel_sd": [float(v) for v in A.std(axis=0, ddof=1)],
            "centroid_zscored_within_phase": None,   # filled below
        }

    # ---- pairwise separation ------------------------------------------------
    names = [C.PHASE_NAME[c] for c in C.PHASES]
    pooled = np.cov(X[interior], rowvar=False)
    pooled_inv = np.linalg.pinv(pooled)
    pairs = {}
    for i, a in enumerate(names):
        for jj in range(i + 1, len(names)):
            b = names[jj]
            da = X[(y == C.PHASES[i]) & interior]
            db = X[(y == C.PHASES[jj]) & interior]
            ma, mb = da.mean(axis=0), db.mean(axis=0)
            d = ma - mb
            pairs[f"{a}_vs_{b}"] = {
                "euclidean_centroid_distance_deg": float(np.linalg.norm(d)),
                "mahalanobis_centroid_distance": float(
                    np.sqrt(max(0.0, d @ pooled_inv @ d))),
                "pooled_sd_along_the_separating_direction_deg": float(
                    np.sqrt(max(0.0, d @ pooled @ d)) / max(1e-12,
                                                           np.linalg.norm(d))),
                "centroid_separation_in_pooled_sd_units": float(
                    np.sqrt(max(0.0, d @ pooled_inv @ d))),
                "per_channel_centroid_difference_deg": {
                    n: float(v) for n, v in zip(P.SHARED10["api_order"], d)},
            }
    log("")
    log("  pairwise centroid separation (interior frames)")
    for k, v in pairs.items():
        log(f"    {k:<28} euclid {v['euclidean_centroid_distance_deg']:>7.2f} deg  "
            f"mahal {v['mahalanobis_centroid_distance']:>6.3f}  "
            f"= {v['centroid_separation_in_pooled_sd_units']:>5.2f} SD")

    # ---- PCA for VISUALISATION only ----------------------------------------
    Xc = X[interior]
    mu = Xc.mean(axis=0)
    Xz = Xc - mu
    U, S, Vt = np.linalg.svd(Xz, full_matrices=False)
    evr = (S ** 2) / (S ** 2).sum()
    proj = Xz @ Vt[:2].T
    log("")
    log(f"  PCA (visualisation only): PC1 {evr[0]:.3f}, PC2 {evr[1]:.3f} of "
        f"variance; first 4 = {np.round(evr[:4], 4).tolist()}")
    pc_phase = {}
    yint = y[interior]
    sint = subj[interior]
    for c in C.PHASES:
        sel = yint == c
        pc_phase[C.PHASE_NAME[c]] = {
            "n": int(sel.sum()),
            "pc1_mean": float(proj[sel, 0].mean()),
            "pc2_mean": float(proj[sel, 1].mean()),
            "pc1_p5_p95": [float(np.percentile(proj[sel, 0], 5)),
                           float(np.percentile(proj[sel, 0], 95))],
            "pc2_p5_p95": [float(np.percentile(proj[sel, 1], 5)),
                           float(np.percentile(proj[sel, 1], 95))],
        }
    # nearest-centroid agreement in the 2-D projection, as a visualisation aid
    cen2 = np.vstack([np.array([pc_phase[n]["pc1_mean"], pc_phase[n]["pc2_mean"]])
                      for n in names])
    d2 = ((proj[:, None, :] - cen2[None, :, :]) ** 2).sum(axis=2)
    vis_pred = np.array(C.PHASES)[d2.argmin(axis=1)]
    vis_ba = C.balanced_accuracy(yint, vis_pred)
    log(f"  PCA-2D nearest-centroid balanced accuracy (visual aid only): "
        f"{vis_ba:.4f}")

    # ---- nearest-neighbour phase mixing ------------------------------------
    log("")
    log("  nearest-neighbour phase mixing (subsampled, deterministic)")
    mix = {}
    idx_int = np.flatnonzero(interior)
    for held_out in sorted(set(int(s) for s in np.unique(sint))):
        anchor = np.flatnonzero(interior & (subj == held_out))
        pool = np.flatnonzero(interior & (subj != held_out))
        if anchor.size == 0 or pool.size < 100:
            continue
        a_idx = subsample(anchor, NN_ANCHORS // 4, rng)
        r_idx = subsample(pool, NN_REF // 4, rng)
        A, R = X[a_idx], X[r_idx]
        # chunked nearest neighbour
        preds = np.empty(A.shape[0], dtype=np.int64)
        dmin = np.empty(A.shape[0], dtype=np.float64)
        step = 2000
        for s0 in range(0, A.shape[0], step):
            d = ((A[s0:s0 + step, None, :] - R[None, :, :]) ** 2).sum(axis=2)
            j = d.argmin(axis=1)
            preds[s0:s0 + step] = y[r_idx][j]
            dmin[s0:s0 + step] = np.sqrt(d[np.arange(j.size), j])
        ya = y[a_idx]
        cnt = {}
        for c in C.PHASES:
            sel = ya == c
            if sel.sum() == 0:
                continue
            got = {}
            for c2 in C.PHASES:
                got[C.PHASE_NAME[c2]] = C.rate(int((preds[sel] == c2).sum()),
                                               int(sel.sum()))
            cnt[C.PHASE_NAME[c]] = {
                "n": int(sel.sum()),
                "nn_phase_distribution": got,
                "nn_same_phase_rate": float((preds[sel] == c).mean()),
                "median_nn_distance_deg": float(np.median(dmin[sel])),
            }
        mix[str(held_out)] = cnt
    agg = {}
    for c in C.PHASES:
        v = [mix[s][C.PHASE_NAME[c]]["nn_same_phase_rate"] for s in mix
             if C.PHASE_NAME[c] in mix[s]]
        agg[C.PHASE_NAME[c]] = {
            "mean_nn_same_phase_rate": float(np.mean(v)) if v else None,
            "sd": float(np.std(v, ddof=1)) if len(v) > 1 else None,
            "n_subjects": len(v),
        }
    for c in names:
        log(f"    {c:<14} nearest neighbour from another subject has the SAME "
            f"phase in {agg[c]['mean_nn_same_phase_rate']:.4f} of frames")

    # ---- within- vs between-subject variance decomposition -----------------
    log("")
    log("  variance decomposition (interior frames)")
    grand = X[interior].mean(axis=0)
    subj_means = {}
    for s in np.unique(sint):
        subj_means[int(s)] = X[interior & (subj == s)].mean(axis=0)
    SM = np.vstack([subj_means[int(s)] for s in np.unique(sint)])
    between = float(((SM - grand) ** 2).sum(axis=1).mean())
    within = float(np.mean([
        ((X[interior & (subj == s)] - subj_means[int(s)]) ** 2).sum(axis=1).mean()
        for s in np.unique(sint)]))
    # and the same decomposition for the phase effect, within subject
    phase_ss, resid_ss = [], []
    for s in np.unique(sint):
        sel_s = interior & (subj == s)
        gm = X[sel_s].mean(axis=0)
        for c in C.PHASES:
            sel = sel_s & (y == c)
            if sel.sum() < 2:
                continue
            pm = X[sel].mean(axis=0)
            phase_ss.append(float(((pm - gm) ** 2).sum()) * int(sel.sum()))
            resid_ss.append(float(((X[sel] - pm) ** 2).sum(axis=1).sum()))
    phase_ss_t = float(np.sum(phase_ss))
    resid_ss_t = float(np.sum(resid_ss))
    decomp = {
        "between_subject_ss_per_frame": between,
        "within_subject_ss_per_frame": within,
        "between_over_within": between / max(within, 1e-12),
        "phase_ss_within_subject": phase_ss_t,
        "residual_ss_within_subject": resid_ss_t,
        "phase_variance_share_within_subject": phase_ss_t
        / max(phase_ss_t + resid_ss_t, 1e-12),
        "interpretation": ("the phase signal is the WITHIN-subject part.  A large "
                           "between/within ratio means subject identity is an "
                           "easier axis than phase, which is exactly why the "
                           "protocol is subject-grouped and why subject id is "
                           "never a feature"),
    }
    log(f"    between-subject / within-subject SS per frame = "
        f"{decomp['between_over_within']:.3f}")
    log(f"    phase variance share within subject = "
        f"{decomp['phase_variance_share_within_subject']:.4f}")

    # ---- the explicit reaching-vs-releasing question -----------------------
    ra = X[(y == 1) & interior]
    rl = X[(y == 3) & interior]
    rr = {
        "n_reaching": int(ra.shape[0]), "n_releasing": int(rl.shape[0]),
        "centroid_distance_deg": pairs["REACHING_vs_RELEASING"][
            "euclidean_centroid_distance_deg"],
        "mahalanobis_centroid_distance": pairs["REACHING_vs_RELEASING"][
            "mahalanobis_centroid_distance"],
        "separation_in_pooled_sd_units": pairs["REACHING_vs_RELEASING"][
            "centroid_separation_in_pooled_sd_units"],
        "reaching_sd_per_channel_deg": [float(v) for v in ra.std(axis=0, ddof=1)],
        "releasing_sd_per_channel_deg": [float(v) for v in rl.std(axis=0, ddof=1)],
        "mahalanobis_distance_comparable_to_manipulation": None,
        "verdict": None,
    }
    # how separated are reaching and releasing relative to a within-phase spread?
    sep_rl = rr["mahalanobis_centroid_distance"]
    sep_manip_min = min(
        pairs["REACHING_vs_MANIPULATION"]["mahalanobis_centroid_distance"],
        pairs["MANIPULATION_vs_RELEASING"]["mahalanobis_centroid_distance"])
    rr["mahalanobis_distance_comparable_to_manipulation"] = {
        "reaching_vs_releasing": sep_rl,
        "manipulation_vs_the_closer_directional_phase": sep_manip_min,
        "ratio_directional_over_manipulation": sep_rl / max(sep_manip_min, 1e-12),
    }
    rr["verdict"] = (
        "REACHING and RELEASING are far apart in centroid terms"
        if sep_rl >= 1.0 else
        "REACHING and RELEASING centroids are within ~1 pooled SD: instantaneous "
        "pose alone is expected to be weak on this pair")
    log("")
    log(f"  REACHING vs RELEASING: mahalanobis {sep_rl:.3f} pooled SD "
        f"(manipulation vs its closer directional phase {sep_manip_min:.3f})")
    log(f"    verdict: {rr['verdict']}")

    pose_body = {
        "artifact": POSE_OUT, "branch_id": P.BRANCH_ID, "plan_sha256": plan_sha,
        "purpose": ("ask, before interpreting any classifier score, whether the "
                    "three phases are separable in INSTANTANEOUS shared10 pose "
                    "space"),
        "space": {"name": P.SHARED10["name"], "n_features": 10,
                  "features": P.SHARED10["api_order"], "unit": "degrees"},
        "stratum": {"name": "INTERIOR",
                    "margin_frames": P.BOUNDARY["margin_frames"],
                    "n_frames": int(interior.sum())},
        "per_phase": stats,
        "pairwise_separation": pairs,
        "pca_visualisation": {
            "note": ("PCA is fitted on ALL interior frames for VISUALISATION "
                     "ONLY.  It is never a model input and no classifier in this "
                     "branch uses it"),
            "explained_variance_ratio_first8": [float(v) for v in evr[:8]],
            "per_phase_projection": pc_phase,
            "pca2d_nearest_centroid_balanced_accuracy_visual_aid_only": vis_ba,
            "components": {f"PC{i+1}": [float(v) for v in Vt[i]]
                           for i in range(3)},
        },
        "nearest_neighbour_phase_mixing": {
            "method": ("for each interior frame of a held-out subject, the nearest "
                       "neighbour among ALL interior frames of the OTHER subjects; "
                       "repeated per subject; deterministic subsampling"),
            "anchors_per_subject": NN_ANCHORS // 4,
            "reference_pool_per_subject": NN_REF // 4,
            "per_subject": mix,
            "aggregate_same_phase_rate": agg,
            "chance_rate": 1.0 / 3.0,
        },
        "variance_decomposition": decomp,
        "reaching_vs_releasing": rr,
    }
    sha_p = C.write_json(os.path.join(C.LANE, POSE_OUT), pose_body)

    # =====================================================================
    # VELOCITY GEOMETRY
    # =====================================================================
    log("")
    log("=" * 78)
    log("STAGE 6b - VELOCITY GEOMETRY: do similar poses carry opposite motion?")
    log("=" * 78)
    X2 = z["R2_POSE_VELOCITY"]
    pose = z["R1_POSE"]
    vel = X2[:, 10:]
    mu = pose[interior].mean(axis=0)
    sd = pose[interior].std(axis=0, ddof=0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    posez = (pose - mu) / sd

    def sign_agreement(idx_a, idx_b, k=KNN_K):
        """For each anchor in idx_a, compare velocity signs with its k nearest
        neighbours in idx_b (standardised pose space)."""
        A, B = posez[idx_a], posez[idx_b]
        VA, VB = vel[idx_a], vel[idx_b]
        agree = np.empty(A.shape[0])
        step = 1500
        for s0 in range(0, A.shape[0], step):
            d = ((A[s0:s0 + step, None, :] - B[None, :, :]) ** 2).sum(axis=2)
            j = np.argpartition(d, k, axis=1)[:, :k]
            a = np.sign(VA[s0:s0 + step])[:, None, :]
            b = np.sign(VB[j])
            agree[s0:s0 + step] = (a == b).mean(axis=(1, 2))
        return agree

    n_per = min(15000, int(((y == 1) & interior).sum()),
                int(((y == 3) & interior).sum()))
    ra_idx = subsample(np.flatnonzero((y == 1) & interior), n_per, rng)
    rl_idx = subsample(np.flatnonzero((y == 3) & interior), n_per, rng)
    log(f"  anchors per phase: {n_per}, k = {KNN_K}")

    cross = np.concatenate([sign_agreement(ra_idx, rl_idx),
                            sign_agreement(rl_idx, ra_idx)])
    within_reach = sign_agreement(ra_idx, ra_idx)
    within_rel = sign_agreement(rl_idx, rl_idx)
    within = np.concatenate([within_reach, within_rel])
    log(f"  CROSS-phase (reaching anchor vs releasing neighbours) sign agreement "
        f"= {cross.mean():.4f} (sd {cross.std(ddof=1):.4f})")
    log(f"  WITHIN-phase sign agreement = {within.mean():.4f} "
        f"(sd {within.std(ddof=1):.4f})")
    log(f"  difference (within - cross) = {within.mean() - cross.mean():+.4f}")

    # global velocity sign structure per phase
    per_phase_vel = {}
    for c in C.PHASES:
        sel = (y == c) & interior
        V = vel[sel]
        per_phase_vel[C.PHASE_NAME[c]] = {
            "mean_velocity_deg_per_s": [float(v) for v in V.mean(axis=0)],
            "mean_over_channels": float(V.mean()),
            "frac_channels_negative_mean": float((V.mean(axis=0) < 0).mean()),
            "sign_entropy": float(-np.mean([
                (lambda p: 0.0 if p in (0.0, 1.0) else
                 -(p * np.log(p) + (1 - p) * np.log(1 - p)))((V[:, j] > 0).mean())
                for j in range(V.shape[1])])),
        }
    sign_flip = {}
    for a in (1, 3):
        for b in (1, 3):
            if a >= b:
                continue
            ma = np.array(per_phase_vel[C.PHASE_NAME[a]]["mean_velocity_deg_per_s"])
            mb = np.array(per_phase_vel[C.PHASE_NAME[b]]["mean_velocity_deg_per_s"])
            sign_flip[f"{C.PHASE_NAME[a]}_vs_{C.PHASE_NAME[b]}"] = {
                "n_channels_with_opposite_mean_velocity_sign": int(
                    ((ma > 0) != (mb > 0)).sum()),
                "n_channels": int(ma.size),
                "cosine_between_mean_velocity_vectors": float(
                    ma @ mb / max(1e-12, np.linalg.norm(ma) * np.linalg.norm(mb))),
                "mean_abs_velocity_deg_per_s": {
                    C.PHASE_NAME[a]: float(np.abs(ma).mean()),
                    C.PHASE_NAME[b]: float(np.abs(mb).mean())},
            }
    log("")
    for k, v in sign_flip.items():
        log(f"  {k:<28} opposite-sign channels "
            f"{v['n_channels_with_opposite_mean_velocity_sign']}/{v['n_channels']}"
            f"  cosine {v['cosine_between_mean_velocity_vectors']:+.4f}")

    vel_body = {
        "artifact": VEL_OUT, "branch_id": P.BRANCH_ID, "plan_sha256": plan_sha,
        "purpose": ("test the hypothesis 'pose is similar, direction differs' for "
                    "REACHING vs RELEASING"),
        "method": P.GEOMETRY["velocity"],
        "k_neighbours": KNN_K,
        "anchors_per_direction": int(n_per),
        "matched_neighbour_sign_agreement": {
            "definition": ("fraction of (anchor channel, neighbour channel) pairs "
                           "whose VELOCITY SIGN agrees, among the k nearest "
                           "neighbours in standardised shared10 pose space"),
            "cross_phase_mean": float(cross.mean()),
            "cross_phase_sd": float(cross.std(ddof=1)),
            "within_phase_mean": float(within.mean()),
            "within_phase_sd": float(within.std(ddof=1)),
            "within_minus_cross": float(within.mean() - cross.mean()),
            "within_reaching_mean": float(within_reach.mean()),
            "within_releasing_mean": float(within_rel.mean()),
            "chance_sign_agreement": 0.5,
            "interpretation_rule": (
                "if CROSS-phase sign agreement at matched pose locality is "
                "markedly BELOW within-phase agreement, then two phases can "
                "occupy similar poses with opposite motion - the premise of the "
                "OBS-B hypothesis"),
        },
        "per_phase_mean_velocity": per_phase_vel,
        "directional_velocity_contrast": sign_flip,
    }
    sha_v = C.write_json(os.path.join(C.LANE, VEL_OUT), vel_body)
    log("")
    log(f"  wrote {POSE_OUT}  sha256={sha_p[:16]}")
    log(f"  wrote {VEL_OUT}  sha256={sha_v[:16]}")
    log(f"  elapsed {time.time() - t0:.1f} s")
    fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
