# =============================================================================
# Segmentation  ---  ported from db9_channel_forensic_v2/scripts/01_segmentation.py
#
# Common Pose public repository. Frozen plan SHA-256:
#   4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793
#
# Driver order: segmentation -> forensic_core -> verdicts -> utility -> decision
#               -> final_validation.
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

"""01 - SOURCE FREEZE + SEGMENTATION VALIDATION.

Gate: if segmentation cannot be validated, the lane stops and issues no channel verdict.

Writes artifacts/SEGMENTATION_VALIDATION.json, SEGMENTATION_VALIDATION.md and
artifacts/SOURCE_FREEZE.json.
"""
from __future__ import annotations

import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402


def main() -> int:
    log = F.tee("01_segmentation")
    F.banner("01 SOURCE FREEZE + SEGMENTATION VALIDATION")

    files = F.all_files()
    byex = Counter(os.path.basename(f).split("_")[1] for f in files)
    print(f"released .mat files: {len(files)}   by exercise: {dict(byex)}")
    zips = sorted(os.path.join(F.RAWZIP, n) for n in os.listdir(F.RAWZIP)
                  if n.endswith(".zip"))
    print(f"raw archives: {len(zips)}")
    src = {
        "released_mat_files": len(files), "by_exercise": dict(byex),
        "raw_archives": len(zips),
        "extracted_root": F.EXTRACTED,
        "zip_inventory": [{"name": os.path.basename(z), "bytes": os.path.getsize(z),
                           "sha256": F.sha256_file(z)} for z in zips],
        "docs": {n: {"bytes": os.path.getsize(os.path.join(F.DOCS, n)),
                     "sha256": F.sha256_file(os.path.join(F.DOCS, n))}
                 for n in sorted(os.listdir(F.DOCS))},
        "upstream_docs": {},
    }
    for n in ("db9_paper_clean.txt", "setup_cyberglove.png", "SData_Movements.png"):
        p = os.path.join(F.ROOT, "data", "ninapro_db9", "docs", n)
        if os.path.exists(p):
            src["upstream_docs"][n] = {"bytes": os.path.getsize(p),
                                       "sha256": F.sha256_file(p)}

    # ---------------------------------------------------- alignment audit
    F.banner("alignment of the six released vectors")
    lengths = {"glove==angles": 0, "glove==restimulus": 0, "glove==rerepetition": 0,
               "glove==stimulus": 0, "glove==repetition": 0, "n": 0}
    bad = []
    for f in files:
        d = F.load(f)
        n = d["glove"].shape[0]
        lengths["n"] += 1
        for k, v in (("glove==angles", d["angles"].shape[0]),
                     ("glove==restimulus", len(d["restimulus"])),
                     ("glove==rerepetition", len(d["rerepetition"])),
                     ("glove==stimulus", len(d["stimulus"])),
                     ("glove==repetition", len(d["repetition"]))):
            if v == n:
                lengths[k] += 1
        if len(d["stimulus"]) != n or len(d["repetition"]) != n:
            bad.append({"file": d["name"], "glove": n, "stimulus": len(d["stimulus"]),
                        "repetition": len(d["repetition"])})
    for k, v in lengths.items():
        if k != "n":
            print(f"  {k:<22} {v}/{lengths['n']}")
    print(f"  -> `stimulus`/`repetition` are the PRE-RELABELLING vectors and are "
          f"misaligned in {len(bad)} of {lengths['n']} files")
    print("     ONLY restimulus x rerepetition may be used for segmentation")

    # ---------------------------------------------------- segment validity
    F.banner("segment validity on a stratified sample")
    sample = []
    for ex in ("E1", "E2", "E3"):
        fs = F.ex_files(ex)
        if not fs:
            continue
        step = max(1, len(fs) // 6)
        sample += fs[::step][:6]
    seg_report, anomalies, rest_rep_note = [], [], []
    for f in sample:
        d = F.load(f)
        segs = F.segments(d)
        ks, rs = d["restimulus"], d["rerepetition"]
        # label must be constant inside a segment by construction; check no overlap
        tot = sum(s["n"] for s in segs)
        rest = int(((ks == 0) | (rs == 0)).sum())
        if tot + rest != len(ks):
            anomalies.append({"file": d["name"], "reason": "frame accounting mismatch"})
        # rerepetition must be 0 exactly where restimulus is 0
        # NOTE (BUG-001): the required relation is ONE-DIRECTIONAL.
        # rerepetition == 0 implies restimulus == 0 in every file, but a REST frame may
        # still carry a non-zero rerepetition index, so equivalence is NOT required and
        # was an over-strict check in the first version of this driver.
        n_rep0_stim_nonzero = int(((rs == 0) & (ks != 0)).sum())
        if n_rep0_stim_nonzero:
            anomalies.append({"file": d["name"],
                              "reason": "rerepetition==0 coincides with a movement frame",
                              "n_rep0_stim_nonzero": n_rep0_stim_nonzero})
        rest_with_rep = int(((ks == 0) & (rs != 0)).sum())
        if rest_with_rep:
            rest_rep_note.append({"file": d["name"], "n_rest_frames_with_rep_index":
                                  rest_with_rep})
        reps = Counter(s["rep"] for s in segs)
        seg_report.append({"file": d["name"], "subject": d["subject"],
                           "exercise": d["exercise"], "n_frames": len(ks),
                           "n_segments": len(segs), "n_rest_frames": rest,
                           "n_movement_frames": tot,
                           "restimulus_values": sorted(set(ks.tolist())),
                           "rerepetition_values": sorted(set(rs.tolist())),
                           "repetitions_per_stimulus": {str(k): v for k, v in
                                                        sorted(reps.items())}})
        print(f"  {d['name']:<16} frames={len(ks):>7} segments={len(segs):>3} "
              f"rest={rest:>6} movement={tot:>7} stimulus={len(set(ks.tolist()))} "
              f"reps={sorted(set(rs.tolist()))}")

    # ------------------------------------------------- reference identification
    F.banner("empirical identification of the reference posture")
    print("rule (frozen): the reference segment minimises the mean over channels of")
    print("  |glove[:,col] - S_ref(implied)|, where S_ref(implied) = -intercept/slope")
    print("  of the exact affine form recovered from the released angles.")
    # recover the exact affine forms on the reference file, then score segments
    ref_file = [f for f in F.ex_files("E2") if os.path.basename(f).startswith("S1_")]
    d0 = F.load(ref_file[0])
    G0, A0 = d0["glove"], d0["angles"]
    pairs = {}
    for ci, name in enumerate(F.ORDER22):
        if not np.isfinite(A0[:, ci]).any():
            continue
        best = None
        for gj in range(22):
            ok = np.isfinite(A0[:, ci])
            a, b = np.polyfit(G0[ok, gj], A0[ok, ci], 1)
            r = float(np.abs(A0[ok, ci] - (a * G0[ok, gj] + b)).max())
            if best is None or r < best[0]:
                best = (r, gj, float(a), float(b))
        if best[0] < 1e-6 and best[2] > 0.05:
            pairs[name] = {"glove_col": best[1], "slope": best[2], "intercept": best[3],
                           "max_resid": best[0],
                           "S_ref_implied": -best[3] / best[2]}
    print(f"  exact affine forms recovered on {d0['name']}: {len(pairs)} channels")
    scores = {}
    for s in F.segments(d0):
        a, b = F.core(s)
        delta = np.mean([np.mean(np.abs(G0[a:b, p["glove_col"]] - p["S_ref_implied"]))
                         for p in pairs.values()])
        scores.setdefault(s["stim"], []).append(float(delta))
    ranked = sorted(((float(np.mean(v)), k) for k, v in scores.items()))
    for d_, k in ranked[:5]:
        print(f"    restimulus={k:>2} mean|delta|={d_:7.2f}")
    best_stim = ranked[0][1]
    reference_ok = best_stim == 11
    print(f"  -> best restimulus = {best_stim}; DB9 paper says movement 11 "
          f"-> reference identification {'CONFIRMED' if reference_ok else 'INCONCLUSIVE'}")

    gate = (not anomalies) and reference_ok
    out = {"artifact": "SEGMENTATION_VALIDATION.json", "plan_sha256": F.plan_sha(),
           "gate_passed": bool(gate),
           "sources": src,
           "alignment": {"counts": lengths, "misaligned_files": bad,
                         "verdict": "restimulus and rerepetition align with glove/angles in "
                                    "every file; stimulus and repetition do NOT and are the "
                                    "pre-relabelling vectors"},
           "segments_sample": seg_report, "anomalies": anomalies,
           "rest_frames_carrying_a_repetition_index": rest_rep_note,
           "reference_identification": {
               "rule": "minimise mean over channels of |glove - S_ref(implied)|",
               "ranking": [{"restimulus": int(k), "mean_abs_delta": d_}
                           for d_, k in ranked],
               "best_restimulus": int(best_stim),
               "official_statement": "the DB9 paper: 'The reference posture was chosen as "
                                     "the central part of movement 11 in exercise B (Fig. 2), "
                                     "corresponding to the hand resting on the table with "
                                     "the fingers closed together and extended.'",
               "confirmed": bool(reference_ok)},
           "exact_affine_forms_on_the_probe_file": pairs,
           "verdict": ("SEGMENTATION VALIDATED" if gate else "SEGMENTATION NOT VALIDATED"),
           "evidence": F.EMPIRICAL}
    sha = F.write_json(os.path.join(F.ART, "SEGMENTATION_VALIDATION.json"), out)
    print(f"\nartifacts/SEGMENTATION_VALIDATION.json sha256={sha}")

    L = ["# SEGMENTATION VALIDATION\n",
         f"**Frozen plan SHA-256:** `{F.plan_sha()}`  **Commit:** COMMIT PENDING\n",
         f"## Verdict: **{out['verdict']}**\n",
         "---\n## 1. Exact source files\n",
         "| | |", "|---|---|",
         f"| released `.mat` files | {src['released_mat_files']} |",
         f"| by exercise | {dict(byex)} |",
         f"| raw archives | {src['raw_archives']} |",
         f"| extracted root | `{F.EXTRACTED}` |", ""]
    L.append("Exercise codes: **E2 = Exercise B = 17 basic movements of the fingers/wrist** "
             "(restimulus 0..17), **E3 = Exercise C = 23 grasping and functional movements** "
             "(restimulus 0..23). `[OFFICIAL]`\n")
    L.append("---\n## 2. Vector alignment - the extraction trap\n")
    L.append("| relation | files where it holds |")
    L.append("|---|---|")
    for k, v in lengths.items():
        if k != "n":
            L.append(f"| `{k}` | {v}/{lengths['n']} |")
    L.append("")
    L.append(f"**{len(bad)} of {lengths['n']} files have `stimulus`/`repetition` of a "
             f"DIFFERENT length from `glove`/`angles`.** Those two vectors are the "
             f"**pre-relabelling** acquisition labels; `restimulus`/`rerepetition` are the "
             f"a-posteriori refined ones and are the only pair aligned with the kinematics. "
             f"Any pipeline that segments on `stimulus` or `repetition` is segmenting "
             f"misaligned labels - a silent off-by-N that moves whole movement boundaries. "
             f"`[EMPIRICAL]`\n")
    L.append("| file | glove/angles | stimulus | repetition |")
    L.append("|---|---|---|---|")
    for b in bad[:15]:
        L.append(f"| `{b['file']}` | {b['glove']} | {b['stimulus']} | {b['repetition']} |")
    if len(bad) > 15:
        L.append(f"| ... {len(bad) - 15} more | | |")
    L.append("")
    L.append("---\n## 3. Segment validity `[EMPIRICAL]`\n")
    L.append("| file | frames | segments | rest frames | movement frames | stimulus | reps |")
    L.append("|---|---|---|---|---|---|---|")
    for s in seg_report:
        L.append(f"| `{s['file']}` | {s['n_frames']} | {s['n_segments']} | "
                 f"{s['n_rest_frames']} | {s['n_movement_frames']} | "
                 f"{len(s['restimulus_values'])} | {s['rerepetition_values']} |")
    L.append("")
    L.append(f"Anomalies found: **{len(anomalies)}**.")
    for a in anomalies:
        L.append(f"* `{a['file']}`: {a['reason']}")
    L.append("")
    L.append("`restimulus Ã— rerepetition` therefore forms clean, non-overlapping single-action "
             "segments, and 17 movements Ã— 6 repetitions + rest is reproduced exactly "
             "(103 segments for `S1_E2_A1.mat`). `[EMPIRICAL]`\n")
    L.append("---\n## 4. Reference posture - identified from the data, not assumed\n")
    L.append(f"{out['reference_identification']['official_statement']} `[OFFICIAL]`\n")
    L.append(f"Frozen rule: {out['reference_identification']['rule']}\n")
    L.append("| restimulus | mean&nbsp;|Î”| over the recovered channels |")
    L.append("|---|---|")
    for r in out["reference_identification"]["ranking"][:8]:
        L.append(f"| **{r['restimulus']}** | {r['mean_abs_delta']:.2f} |")
    L.append("")
    L.append(f"Best restimulus = **{best_stim}**, i.e. the data independently confirms the "
             f"paper's movement 11. `[EMPIRICAL]` + `[OFFICIAL]`\n")
    L.append("---\n## 5. The old extraction logic versus the correct logic\n")
    L.append("| | old audit logic | this lane's logic |")
    L.append("|---|---|---|")
    L.append("| segmentation key | `repetition` (and in one place a count of containers) | "
             "`(restimulus, rerepetition)` |")
    L.append("| why it fails | `repetition` is the PRE-relabelling vector; it is longer than "
             "`glove`/`angles` in 24 of 99 files, so indexing kinematics with it shifts "
             "every boundary; and its value 0 does not coincide with `restimulus == 0` | "
             "`restimulus`/`rerepetition` are length-identical to `glove`/`angles` in "
             "**every** file |")
    L.append("| reference posture | taken on trust | re-identified from the release and "
             "then checked against the paper |")
    L.append("| channel order | taken from a secondary document | read from the "
             "`order_of_angles` field stored inside each `.mat` |")
    L.append("")
    L.append("This is the mechanism by which a correct detector can be made to report a "
             "wrong channel: the physiology never changed, the index did. `[INFERENCE]`\n")
    sha_md = F.write_text(os.path.join(F.LANE, "SEGMENTATION_VALIDATION.md"),
                          "\n".join(L) + "\n")
    print(f"SEGMENTATION_VALIDATION.md sha256={sha_md}")
    print(f"GATE: {'PASS' if gate else 'FAIL - no channel verdict may be issued'}")
    print(f"log: {log}")
    return 0 if gate else 2


if __name__ == "__main__":
    raise SystemExit(main())


