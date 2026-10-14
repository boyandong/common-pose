#!/bin/bash
# GATE 4A — remaining frozen analysis steps (post-TTA, post-predictor).
# Sequential, detached-friendly, each step tee'd to its own log.
set -uo pipefail
ENV=/root/miniconda3/envs/emg2pose-gate3
LANE=/root/work/common-pose/experiments/upstream_substitution/gate4a_reliability_feasibility
cd "$LANE" || exit 2
mkdir -p logs artifacts work

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
echo "PIPELINE_DONE"
