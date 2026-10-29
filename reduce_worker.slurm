#!/usr/bin/env bash
#SBATCH --job-name=SDC_REFRED
#SBATCH --partition=general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/tanghui/GB_SDC_TrackVis/logs/refreduce_%j.out
#SBATCH --error=/public/home/tanghui/GB_SDC_TrackVis/logs/refreduce_%j.err
set -euo pipefail
BASE=/public/home/tanghui/GB_SDC_TrackVis
PY=/public/home/tanghui/software/sdc_fast_env/bin/python
: "${GROUP:?}"; : "${WAVE:?}"
"$PY" "$BASE/scripts/ref_major_reduce.py" --group "$GROUP" --wave "$WAVE" --chunk 50
