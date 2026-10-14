#!/usr/bin/env bash
set -euo pipefail
cd /root/work/common-pose/experiments/upstream_substitution/gate4d_task_aware_gate_benchmark_v1
PY=/root/miniconda3/envs/emg2pose-gate3/bin/python
flock -n 9 || exit 75
"$PY" -u analysis/gate4d_analysis.py --tta
"$PY" -u analysis/gate4d_analysis.py --analyze
