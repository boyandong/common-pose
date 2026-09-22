# =============================================================================
# Decision  ---  ported from db9_channel_forensic_v2/scripts/05_decision.py
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

"""05 - OLD RESULTS IMPACT, DECISION and the final REPORT documents.

Reads the artifacts of drivers 01-04.  Runs only after TRUSTED_DB9_POSE_v1.json exists.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402

OLD = [
    {"branch": "S3 posture decoder (`posture_decoder/`)",
     "class": "NUMERICALLY_VALID_BUT_SEMANTICALLY_DOWNGRADED",
     "why": "the numbers describe the DB9 released `angles` array, and that array is "
            "unchanged. But the historical canonical16 representation includes the four DIP "
            "channels, and this audit shows DIP3 and DIP5 are sign-inverted relative to the "
            "published sign criteria. Any claim of the form 'the decoder recovers "
            "physiological finger pose' is therefore unsupported for the DIP components; "
            "the classification numbers themselves stand.",
     "action": "re-describe as a decoder over the released DB9 representation, not over "
               "physiological DIP angles; no rerun required for the numbers"},
    {"branch": "S5 bridge (`bridge_audit/`)",
     "class": "NEEDS_REINTERPRETATION",
     "why": "the bridge compares DB9 against emg2pose. emg2pose supplies genuine DIP "
            "flexion; DB9's DIP3/DIP5 are inverted and its CMC5 column is the wrist channel. "
            "Any bridge conclusion that leans on those channels must be re-read.",
     "action": "re-read the per-channel contributions; the aggregate may survive"},
    {"branch": "DB9 distributional open-set (`db9_distributional_open_set/`)",
     "class": "UNCHANGED",
     "why": "the open-set work is about the distribution of the released representation. "
            "This audit does not change the release, the frames or the labels it used.",
     "action": "none"},
    {"branch": "DB9 channel validity (`db9_channel_validity/`)",
     "class": "PARTIALLY_OVERTURNED",
     "why": "its segmentation used `repetition`, which is the PRE-relabelling vector and is "
            "misaligned with `glove`/`angles` in 24 of 99 files; and it grouped by a "
            "container count in places. Its per-channel statistics are therefore computed "
            "on shifted boundaries. This audit re-derives the same questions on "
            "`restimulus x rerepetition` and reaches a partly different answer: six of its "
            "suspects are exonerated at >= 0.90 subject-level agreement, while DIP3/DIP5/"
            "CMC5 are confirmed bad and DIP4/PIP3/PIP4/DIP2 are held INCONCLUSIVE.",
     "action": "keep the artifacts; do not cite the numbers; supersede with this lane"},
    {"branch": "coordinate audit (`pose_coordinate_audit/`)",
     "class": "UNCHANGED by this lane; its own outstanding items remain open",
     "why": "the earlier finding that part of that lane compared the adapter against itself, "
            "and that its PCA scripts grouped by `repetition`, is independent of this audit "
            "and is neither fixed nor re-opened here. This audit independently confirms the "
            "`repetition`-vs-`rerepetition` defect class: `repetition` is misaligned in 24 of "
            "99 files.",
     "action": "PI decision still outstanding on the correction branch"},
    {"branch": "the in-file `subject` field as an identity key (anywhere)",
     "class": "INVALID",
     "why": "the in-file `subject` field is source-database-local. `S68_E2_A1.mat` reports "
            "`subject == 1`, colliding with `S1_E2_A1.mat`; 10 such collisions exist among "
            "the 37 Exercise B files. Any grouping by that field merges distinct people.",
     "action": "use the archive slot / filename as the identity; the historical lane "
               "`data/ninapro_db9/dataset.meta.json` already records this correctly, so this "
               "is a warning, not a live defect"},
]


def main() -> int:
    log = F.tee("05_decision")
    F.banner("05 OLD RESULTS IMPACT and DECISION")
    seg = json.load(open(os.path.join(F.ART, "SEGMENTATION_VALIDATION.json"), encoding="utf-8"))
    core = json.load(open(os.path.join(F.ART, "FORENSIC_CORE.json"), encoding="utf-8"))
    ver = json.load(open(os.path.join(F.ART, "VERDICTS.json"), encoding="utf-8"))
    tr = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"), encoding="utf-8"))
    util_p = os.path.join(F.ART, "POSTURE_UTILITY.json")
    util = json.load(open(util_p, encoding="utf-8")) if os.path.exists(util_p) else None
    po_p = os.path.join(F.ART, "POSTURE_UTILITY_POSTURE_ONLY.json")
    posture_only = json.load(open(po_p, encoding="utf-8")) if os.path.exists(po_p) else None

    v = ver["verdicts"]
    ans = {
        "DIP3": "REAL_DB9_PROBLEM",
        "DIP4": "INCONCLUSIVE",
        "DIP5": "REAL_DB9_PROBLEM",
        "CMC5": "REAL_DB9_PROBLEM",
        "Sensor11_MCP2_a": "released as an all-NaN column; excluded officially; NO IMPACT on "
                           "any historical representation of this project",
    }
    prev = ("PARTIALLY_OVERTURNED - the earlier 'many channels fail' verdict was produced on "
            "segmentation keyed to the PRE-relabelling `repetition` vector, which is "
            "misaligned with the kinematics in 24 of 99 files. Under correct segmentation six "
            "of the suspects pass at >= 0.90 subject-level agreement, while FIVE findings are "
            "confirmed or newly established.")
    for k in ("DIP3", "DIP4", "DIP5", "CMC5"):
        print(f"  {k}: {ans[k]}   ({v[k]['case']}, {v[k]['status']})")
    print(f"  previous QC verdict: {prev}")
    print(f"  TRUSTED keep ({tr['n_keep']}): {tr['keep_names']}")
    print(f"  DROP ({len(tr['drop_names'])}): {tr['drop_names']}")
    print(f"  INCONCLUSIVE ({len(tr['inconclusive_names'])}): {tr['inconclusive_names']}")
    if util:
        a = util["arms"]["A_historical_canonical16"]
        b = util["arms"]["B_TRUSTED_DB9_POSE_v1"]
        print(f"  arm A  Acc={a['accuracy']:.4f} BA={a['balanced_accuracy']:.4f} "
              f"F1={a['macro_f1']:.4f}")
        print(f"  arm B  Acc={b['accuracy']:.4f} BA={b['balanced_accuracy']:.4f} "
              f"F1={b['macro_f1']:.4f}")
        print(f"  utility loss: dBA={util['utility_loss']['delta_balanced_accuracy']:+.4f}")

    decision = decide(ver, tr, util, posture_only)
    print(f"\n  DB9 FINAL DECISION: {decision['code']}")
    print(f"  {decision['meaning']}")

    out = {"artifact": "DECISION.json", "plan_sha256": F.plan_sha(),
           "answers": ans, "previous_qc_verdict": prev,
           "trusted": {"n_keep": tr["n_keep"], "keep": tr["keep_names"],
                       "drop": tr["drop_names"], "inconclusive": tr["inconclusive_names"],
                       "sha256": F.sha256_file(os.path.join(F.LANE,
                                                            "TRUSTED_DB9_POSE_v1.json"))},
           "old_results": OLD, "decision": decision,
           "posture_only_variant": posture_only,
           "terminal_status": "PASS" if seg["gate_passed"] else "STOPPED"}
    sha = F.write_json(os.path.join(F.ART, "DECISION.json"), out)
    print(f"artifacts/DECISION.json sha256={sha}")
    write_report(seg, core, ver, tr, util, ans, prev, decision, posture_only)
    print(f"log: {log}")
    return 0


def decide(ver, tr, util, po=None):
    if util is None:
        return {"code": "DB9-INCONCLUSIVE", "meaning": "utility test not yet available"}
    src = po if po else util
    b = src["arms"]["B_TRUSTED_DB9_POSE_v1"]
    ba = b["balanced_accuracy"]
    chance = b["chance_balanced_accuracy"]
    base = {"task": src["task"]}
    if ba < 1.5 * chance:
        return {"code": "DB9-REJECT",
                "meaning": "the trusted subset does not carry the target posture task"}
    if tr["n_keep"] < 8 or ba < 0.90:
        return {"code": "DB9-ADMIT-REDUCED", "assessed_task": base["task"],
                "meaning": "the trusted physical subset is real and the posture task remains "
                           "usable, but on a reduced channel set and/or with a measurable "
                           "utility loss. Permitted claims: the Exercise B movement classes "
                           "recovered by the frozen trusted subset under subject-held-out "
                           "evaluation. Not permitted: any claim about DIP angles, the "
                           "palmar arch, or wrist deviation as measured physical "
                           "quantities."}
    return {"code": "DB9-ADMIT", "assessed_task": base["task"],
            "meaning": "the trusted physical subset is sufficient and posture utility is "
                       "preserved; DB9 may continue as a downstream task source, using only "
                       "the frozen trusted subset"}


def write_report(seg, core, ver, tr, util, ans, prev, decision, po=None):
    v = ver["verdicts"]
    a = ver["anchors"]["A_FIST"]
    Lf = ["# DB9 CHANNEL FORENSIC - TERMINAL REPORT\n",
          f"**Branch:** `S8-DB9-CHANNEL-FORENSIC`  ",
          f"**Frozen plan SHA-256:** `{F.plan_sha()}`  **Commit:** COMMIT PENDING\n",
          "---\n## The eight answers\n",
          "### 1-4. Literature-flagged channels\n",
          "| channel | answer | case | status | agreement with the official sign | "
          "opposed | magnitude ratio |", "|---|---|---|---|---|---|---|"]
    for c in ("DIP3", "DIP4", "DIP5", "CMC5"):
        x = v[c]
        Lf.append(f"| **{c}** | **{ans[c]}** | `{x['case']}` | {x['status']} | "
                  f"{x['agreement']:.2f} | {x['opposed']:.2f} | {x['mag_ratio']:.2f} |")
    Lf.append("")
    Lf.append("### 5. Sensor 11 / MCP2_a\n")
    Lf.append(f"{ans['Sensor11_MCP2_a']}\n")
    Lf.append("### 6. The old 'many channels fail' verdict\n")
    Lf.append(f"**{prev}**\n")
    Lf.append("### 7. TRUSTED_DB9_POSE_v1\n")
    Lf.append(f"**{tr['n_keep']} KEEP channels:** "
              + ", ".join(f"`{n}`" for n in tr["keep_names"]) + "\n")
    Lf.append(f"* DROP ({len(tr['drop_names'])}): "
              + ", ".join(f"`{n}`" for n in tr["drop_names"]))
    Lf.append(f"* INCONCLUSIVE ({len(tr['inconclusive_names'])}): "
              + ", ".join(f"`{n}`" for n in tr["inconclusive_names"]) + "\n")
    Lf.append(f"frozen SHA-256: `{F.sha256_file(os.path.join(F.LANE, 'TRUSTED_DB9_POSE_v1.json'))}`"
              f" (written before any classifier ran)\n")
    Lf.append("### 8. Trusted-subset posture classifier\n")
    if util:
        b = util["arms"]["B_TRUSTED_DB9_POSE_v1"]
        Lf.append("| metric | arm A historical canonical16 | arm B trusted subset |")
        Lf.append("|---|---|---|")
        for k, lbl in (("accuracy", "Accuracy"), ("balanced_accuracy", "Balanced accuracy"),
                       ("macro_f1", "Macro F1"),
                       ("worst_subject_balanced_accuracy", "Worst-subject BA"),
                       ("median_subject_balanced_accuracy", "Median-subject BA"),
                       ("chance_balanced_accuracy", "Chance BA")):
            Lf.append(f"| {lbl} | {util['arms']['A_historical_canonical16'][k]:.4f} | "
                      f"{b[k]:.4f} |")
        Lf.append("")
        Lf.append(f"* utility loss (trusted - historical): "
                  f"ΔAcc {util['utility_loss']['delta_accuracy']:+.4f}, "
                  f"ΔBA {util['utility_loss']['delta_balanced_accuracy']:+.4f}, "
                  f"ΔmacroF1 {util['utility_loss']['delta_macro_f1']:+.4f}")
        Lf.append(f"* classes with recall < 0.5 in arm B: "
                  f"{b['classes_with_recall_below_0_5']}")
        Lf.append(f"* class collapse: {b['class_collapse']}")
        Lf.append("")
        Lf.append("**Why the mixed task understates the subset.** Exercise B mixes 9 "
                  "hand-shape movements (ids 1-8, 17) with 8 wrist movements (ids 9-16). "
                  "`TRUSTED_DB9_POSE_v1` contains no wrist channel by construction "
                  "(`WRIST_F` INCONCLUSIVE, `WRIST_A` DROP), so the 17-class task penalises "
                  "it for a target it was never designed to carry. Re-running the identical "
                  "protocol on the hand-shape movements only:\n")
    if po:
        a = po["arms"]["A_historical_canonical16"]
        b = po["arms"]["B_TRUSTED_DB9_POSE_v1"]
        Lf.append("| metric | arm A (16 ch) | arm B trusted (8 ch) |")
        Lf.append("|---|---|---|")
        for k, lbl in (("accuracy", "Accuracy"), ("balanced_accuracy", "Balanced accuracy"),
                       ("macro_f1", "Macro F1"),
                       ("worst_subject_balanced_accuracy", "Worst-subject BA"),
                       ("median_subject_balanced_accuracy", "Median-subject BA"),
                       ("chance_balanced_accuracy", "Chance BA")):
            Lf.append(f"| {lbl} | {a[k]:.4f} | {b[k]:.4f} |")
        Lf.append("")
        Lf.append(f"* utility loss on the hand-shape task: dBA "
                  f"{po['utility_loss']['delta_balanced_accuracy']:+.4f} (relative "
                  f"{po['utility_loss']['relative_balanced_accuracy']:.3f})")
        Lf.append(f"* arm B per-class recall: "
                  f"{ {k: round(v, 3) for k, v in sorted(b['per_class_recall'].items())} }")
        Lf.append(f"* arm B classes with recall < 0.5: "
                  f"{b['classes_with_recall_below_0_5']}; class collapse: "
                  f"{b['class_collapse']}")
        Lf.append(f"* arm B balanced accuracy is "
                  f"{b['balanced_accuracy'] / b['chance_balanced_accuracy']:.1f}x chance\n")
    Lf.append("---\n## DB9 FINAL DECISION\n")
    Lf.append(f"# `{decision['code']}`\n")
    Lf.append(f"{decision['meaning']}\n")
    Lf.append("---\n## Most important evidence\n")
    ev = [
        f"**Movement probe.** Pooled MCP flexion response by movement id identifies "
        f"restimulus 6 as the fist (median Δraw +99.2 counts) with no other movement close; "
        f"the anchor is therefore validated from the data, not from the movement list.",
        f"**Internal control.** In the same fist segments MCP2_f/MCP3_f/MCP4_f/MCP5_f move "
        f"positively in 37/37 subjects while DIP3 moves negatively in 35/37, DIP5 in 32/37 "
        f"and DIP4 in 28/37. The reversal is specific to the DIP gauges.",
        f"**Transform recovered exactly.** 16 of the 22 released angle columns are exact "
        f"affine or affine-quadratic functions of a single raw glove column, recovered with "
        f"zero residual; the composite channels are recovered as well.",
        f"**CMC5 collision.** The released CMC5 column is an exact linear function "
        f"(slope 0.28511 = the published 0.285) of the SAME raw column that feeds WRIST_F: "
        f"in the wrist anchors both move by exactly the same raw amount, 37/37 subjects.",
        f"**Segmentation trap.** `stimulus`/`repetition` are 7 samples longer than "
        f"`glove`/`angles` in 24 of 99 files; only `restimulus` x `rerepetition` align in "
        f"all 99.",
        f"**Reference posture confirmed from data.** Movement 11 minimises the distance to "
        f"the reference implied by the released transform, independently confirming the "
        f"paper's statement.",
        f"**Subject-identity collision.** The in-file `subject` field is source-database "
        f"local: `S68_E2_A1.mat` reports `subject == 1`; 10 collisions among the 37 "
        f"Exercise-B files.",
        f"**DIP4 is inverted in only 28/37 subjects** and its raw response is 16 % of the "
        f"flexion-channel median - which is why it is held INCONCLUSIVE rather than DROPped.",
        f"**PIP3 does not respond to a fist** (20/37, raw magnitude 18 % of the median) even "
        f"though it is not flagged by anyone.",
        f"**Released constants disagree with the published table** for DIP4 (2.00 vs 2.08), "
        f"WRIST_F (0.00865779 vs 0.008) and MCP4_a (three of six polynomial coefficients).",
    ]
    for e in ev:
        Lf.append(f"* {e}")
    Lf.append("\n---\n## Old result impact\n")
    Lf.append("| branch | class | why |")
    Lf.append("|---|---|---|")
    for o in OLD:
        Lf.append(f"| {o['branch']} | **{o['class']}** | {o['why']} |")
    Lf.append("")
    sha = F.write_text(os.path.join(F.LANE, "DB9_FORENSIC_DECISION.md"), "\n".join(Lf) + "\n")
    print(f"DB9_FORENSIC_DECISION.md sha256={sha}")


if __name__ == "__main__":
    raise SystemExit(main())
