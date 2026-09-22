"""KINMUS_PHASE_COUNTS.json - exact class counts by frame, trial and subject.

Imbalance is checked carefully here because raw accuracy is uninterpretable
without it, and because balanced accuracy is the primary metric for that reason.
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

OUT = "KINMUS_PHASE_COUNTS.json"
MARGIN = P.BOUNDARY["margin_frames"]


def main() -> int:
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    d = C.load_kinmus()
    trials = d["trials"]

    # ------------------------------------------------------------ by frame
    by_frame = Counter()
    for t in trials:
        by_frame[t["phase"]] += t["n_frames"]
    n_frames = sum(by_frame.values())

    interior = C.boundary_mask(trials, MARGIN)
    y = np.concatenate([np.full(t["n_frames"], t["phase"], dtype=np.int64)
                        for t in trials])
    by_frame_interior = Counter(y[interior].tolist())
    by_frame_boundary = Counter(y[~interior].tolist())

    # ------------------------------------------------------------ by trial
    by_trial = Counter(t["phase"] for t in trials)
    # ------------------------------------------------------------ by subject
    per_subject = {}
    by_subject_phase = defaultdict(Counter)
    for t in trials:
        by_subject_phase[t["subject"]][t["phase"]] += 1
    for s in sorted(by_subject_phase):
        c = by_subject_phase[s]
        fr = Counter()
        for t in trials:
            if t["subject"] == s:
                fr[t["phase"]] += t["n_frames"]
        per_subject[str(s)] = {
            "trials_total": int(sum(c.values())),
            "trials_by_phase": {C.PHASE_NAME[k]: int(c.get(k, 0))
                                for k in C.PHASES},
            "frames_total": int(sum(fr.values())),
            "frames_by_phase": {C.PHASE_NAME[k]: int(fr.get(k, 0))
                                for k in C.PHASES},
        }

    def shares(counter):
        tot = sum(counter.values())
        return {C.PHASE_NAME[k]: (counter.get(k, 0) / tot if tot else None)
                for k in C.PHASES}

    # ------------------------------------------------------------ imbalance
    fr_shares = shares(by_frame)
    imbalance = {
        "majority_class_frame_share": max(fr_shares.values()),
        "minority_class_frame_share": min(fr_shares.values()),
        "max_over_min_frame_ratio": (max(by_frame.values())
                                     / max(1, min(by_frame.values()))),
        "trial_counts_equal_by_construction": (
            len(set(by_trial.values())) == 1),
        "why_balanced_accuracy_is_primary": (
            "even a modest frame-share skew makes raw accuracy partly a prior "
            "predictor; balanced accuracy removes that"),
        "majority_baseline_accuracy_expected": max(fr_shares.values()),
        "balanced_random_expected": 1.0 / 3.0,
        "per_subject_trial_counts_uniform": (
            len({v["trials_total"] for v in per_subject.values()}) == 1),
    }

    body = {
        "artifact": OUT,
        "branch_id": P.BRANCH_ID,
        "plan_sha256": plan_sha,
        "task": "phase",
        "classes": {str(k): C.PHASE_NAME[k] for k in C.PHASES},
        "no_collapsing": P.TASK["no_collapsing"],
        "never_predict": P.TASK["never_predict"],
        "by_frame": {
            "total": int(n_frames),
            "counts": {C.PHASE_NAME[k]: int(by_frame.get(k, 0)) for k in C.PHASES},
            "shares": fr_shares,
        },
        "by_frame_interior": {
            "margin_frames": MARGIN,
            "total": int(interior.sum()),
            "counts": {C.PHASE_NAME[k]: int(by_frame_interior.get(k, 0))
                       for k in C.PHASES},
            "shares": shares(by_frame_interior),
        },
        "by_frame_boundary": {
            "total": int((~interior).sum()),
            "counts": {C.PHASE_NAME[k]: int(by_frame_boundary.get(k, 0))
                       for k in C.PHASES},
            "shares": shares(by_frame_boundary),
        },
        "by_trial": {
            "total": len(trials),
            "counts": {C.PHASE_NAME[k]: int(by_trial.get(k, 0)) for k in C.PHASES},
            "shares": shares(by_trial),
        },
        "by_subject": per_subject,
        "imbalance": imbalance,
        "excluded_containers": d["malformed"],
        "excluded_container_note": (
            "three containers are empty and contribute no frames to any count"),
    }
    sha = C.write_json(os.path.join(C.LANE, OUT), body)
    print(f"wrote {OUT}  sha256={sha[:16]}")
    print(f"  frames  total {n_frames}: "
          + ", ".join(f"{C.PHASE_NAME[k]}={by_frame.get(k,0)}" for k in C.PHASES))
    print(f"  frames  interior {int(interior.sum())} "
          f"(margin {MARGIN}): "
          + ", ".join(f"{C.PHASE_NAME[k]}={by_frame_interior.get(k,0)}"
                      for k in C.PHASES))
    print(f"  trials  total {len(trials)}: "
          + ", ".join(f"{C.PHASE_NAME[k]}={by_trial.get(k,0)}" for k in C.PHASES))
    print(f"  frame majority share {imbalance['majority_class_frame_share']:.4f}, "
          f"max/min {imbalance['max_over_min_frame_ratio']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
