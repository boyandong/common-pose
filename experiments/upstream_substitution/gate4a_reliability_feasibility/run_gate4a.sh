#!/bin/bash
# GATE 4A — run the full single-user reliability-score feasibility screen.
# Sequential; each step logs to its own file. No step modifies Gate3/Gate3B.
set -uo pipefail
ENV=/root/miniconda3/envs/emg2pose-gate3
LANE=/root/work/common-pose/experiments/upstream_substitution/gate4a_reliability_feasibility
cd "$LANE" || exit 2

echo "=== plan hash (must equal the frozen record) ==="
sha256sum GATE4A_PLAN.md
cat GATE4A_PLAN.sha256

mkdir -p logs artifacts work

echo
echo "=== [1/6] AUDIT TTA TRANSFORMS ==="
"$ENV/bin/python" -X utf8 scripts/audit_tta_transforms.py 2>&1 | tee logs/tta_transform_audit_stdout.txt
echo "AUDIT_EXIT=${PIPESTATUS[0]}"

echo
echo "=== [2/6] TTA INFERENCE ==="
"$ENV/bin/python" -X utf8 scripts/run_tta_inference.py 2>&1 | tee logs/tta_inference_stdout.txt
echo "TTA_EXIT=${PIPESTATUS[0]}"

echo
echo "=== [3/6] TASK-ERROR PREDICTOR (stage-grouped OOF) ==="
"$ENV/bin/python" -X utf8 scripts/run_task_error_predictor.py 2>&1 | tee logs/task_error_predictor_stdout.txt
echo "TEP_EXIT=${PIPESTATUS[0]}"

echo
echo "=== [4/6] BUILD RELIABILITY SCORES ==="
"$ENV/bin/python" -X utf8 scripts/build_reliability_scores.py 2>&1 | tee logs/gate4a_stdout.txt
echo "BUILD_EXIT=${PIPESTATUS[0]}"

echo
echo "=== [5/6] EVALUATE CANDIDATE SCORES ==="
"$ENV/bin/python" -X utf8 scripts/evaluate_gate_scores.py 2>&1 | tee logs/gate4a_evaluate_stdout.txt
echo "EVAL_EXIT=${PIPESTATUS[0]}"

echo
echo "=== [6/6] INDEPENDENT VERIFY ==="
"$ENV/bin/python" -X utf8 scripts/verify_gate4a.py 2>&1 | tee logs/gate4a_verify_stdout.txt
echo "VERIFY_EXIT=${PIPESTATUS[0]}"

echo
echo "=== artifacts ==="
ls -la artifacts/
echo "=== logs ==="
ls -la logs/
echo "=== disk ==="
df -h / | tail -1
