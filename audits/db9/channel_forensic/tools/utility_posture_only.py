# =============================================================================
# Utility posture only  ---  ported from db9_channel_forensic_v2/scripts/04b_utility_posture_only.py
#
# Common Pose public repository. Frozen plan SHA-256:
#   4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793
#
# Driver order: segmentation -> forensic_core -> verdicts -> utility -> decision.
# `verdicts` freezes TRUSTED_DB9_POSE_v1 and `utility` asserts against that frozen
# subset, so it must run after it.
#
# The Ninapro DB9 release is not redistributed with this repository. Paths are supplied
# through the environment; `fx_common` is the single place that reads them.
#
# Edits relative to the archived original: I/O plumbing only --- local absolute paths
# moved to environment variables, and the numeric filename prefixes dropped. No numeric
# logic, threshold, seed, verdict vocabulary or assertion count was changed.
# =============================================================================

"""04b - POSTURE-ONLY TASK VARIANT.

Exercise B mixes 9 hand-shape movements with 8 wrist movements.  TRUSTED_DB9_POSE_v1
deliberately contains no wrist channel, so the mixed 17-class task measures the subset
against a target it was never meant to carry.  This driver re-runs the identical protocol on
the hand-shape movements only (official ids 1-8 and 17).

This is a task re-definition using the OFFICIAL movement list, not a channel re-selection.
The trusted subset is read from disk and never modified.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("u", os.path.join(F.SCRIPTS, "utility.py"))
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)

HAND_SHAPE = [1, 2, 3, 4, 5, 6, 7, 8, 17]
WRIST = [9, 10, 11, 12, 13, 14, 15, 16]
CANON = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "PIP2", "DIP2", "MCP3_f",
         "PIP3", "DIP3", "MCP4_f", "PIP4", "DIP4", "MCP5_f", "PIP5", "DIP5"]


def build(cols, keep_classes):
    Xs, ys, ss = [], [], []
    for f in F.ex_files("E2"):
        d = F.load(f)
        for sg in F.segments(d):
            if sg["stim"] not in keep_classes:
                continue
            a, b = F.core(sg)
            ang = d["angles"][a:b, :][:, cols]
            ok = np.isfinite(ang).all(axis=1)
            if not ok.any():
                continue
            Xs.append(np.deg2rad(ang[ok]))
            ys.append(np.full(int(ok.sum()), sg["stim"]))
            ss.append(np.full(int(ok.sum()), d["subject"]))
    return np.vstack(Xs), np.concatenate(ys), np.concatenate(ss)


def main() -> int:
    log = F.tee("04b_utility_posture_only")
    F.banner("04b POSTURE-ONLY TASK VARIANT")
    tr = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"), encoding="utf-8"))
    print(f"official Exercise B movement ids used as the HAND-SHAPE task: {HAND_SHAPE}")
    print(f"wrist-only ids excluded from the target: {WRIST}")
    print(f"TRUSTED_DB9_POSE_v1 ({tr['n_keep']}): {tr['keep_names']}  "
          f"sha256={F.sha256_file(os.path.join(F.LANE, 'TRUSTED_DB9_POSE_v1.json'))}")

    probe = F.load(F.ex_files("E2")[0])["angles"]

    def cols_of(names):
        out, used = [], []
        for n in names:
            for cand in (n, n.replace("_F", "_f")):
                if cand in F.IDX and np.isfinite(probe[:300, F.IDX[cand]]).any():
                    out.append(F.IDX[cand]); used.append(cand); break
        return sorted(set(out)), used

    ca, ua = cols_of(CANON)
    cb, ub = cols_of(tr["keep_names"])
    res = {}
    for arm, cols, used in (("A_historical_canonical16", ca, ua),
                            ("B_TRUSTED_DB9_POSE_v1", cb, ub)):
        X, y, s = build(cols, HAND_SHAPE)
        pred = U.loso(X, y, s)
        r = U.evaluate(pred, y, s, arm)
        r["columns"] = used
        res[arm] = r
        print(f"\n  arm {arm}: X={X.shape} classes={r['n_classes']} subjects={r['n_subjects']}")
        print(f"    Acc={r['accuracy']:.4f}  BA={r['balanced_accuracy']:.4f}  "
              f"macroF1={r['macro_f1']:.4f}  chance={r['chance_balanced_accuracy']:.4f}")
        print(f"    per-class recall: "
              f"{ {k: round(v, 3) for k, v in sorted(r['per_class_recall'].items())} }")
        print(f"    worst subject BA={r['worst_subject_balanced_accuracy']:.4f} "
              f"median={r['median_subject_balanced_accuracy']:.4f}")
        print(f"    classes with recall <0.5: {r['classes_with_recall_below_0_5']}  "
              f"collapse={r['class_collapse']}")

    a, b = res["A_historical_canonical16"], res["B_TRUSTED_DB9_POSE_v1"]
    loss = {"delta_accuracy": b["accuracy"] - a["accuracy"],
            "delta_balanced_accuracy": b["balanced_accuracy"] - a["balanced_accuracy"],
            "delta_macro_f1": b["macro_f1"] - a["macro_f1"],
            "relative_balanced_accuracy": b["balanced_accuracy"] / a["balanced_accuracy"]}
    print(f"\n  utility loss on the HAND-SHAPE task: dBA={loss['delta_balanced_accuracy']:+.4f} "
          f"(relative {loss['relative_balanced_accuracy']:.3f})")

    out = {"artifact": "POSTURE_UTILITY_POSTURE_ONLY.json", "plan_sha256": F.plan_sha(),
           "task": "Exercise B HAND-SHAPE movements only (official ids 1-8, 17)",
           "excluded_wrist_ids": WRIST,
           "rationale": "TRUSTED_DB9_POSE_v1 contains no wrist channel by construction "
                        "(WRIST_F INCONCLUSIVE, WRIST_A DROP), so the mixed 17-class task "
                        "penalises it for a target it was never designed to carry",
           "trusted_subset_sha256":
               F.sha256_file(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json")),
           "protocol": "identical to driver 04: subject-held-out, train-fold-only "
                       "standardisation, one shared LinearDiscriminantAnalysis per fold, "
                       "radians, central 60 % of every segment",
           "arms": res, "utility_loss": loss, "evidence": F.EMPIRICAL}
    sha = F.write_json(os.path.join(F.ART, "POSTURE_UTILITY_POSTURE_ONLY.json"), out)
    print(f"\nartifacts/POSTURE_UTILITY_POSTURE_ONLY.json sha256={sha}")
    print(f"log: {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
