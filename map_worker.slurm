#!/usr/bin/env bash
#SBATCH --job-name=SDC_REFMAP
#SBATCH --partition=general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=12:00:00
#SBATCH --output=/public/home/tanghui/GB_SDC_TrackVis/logs/refmap_%A_%a.out
#SBATCH --error=/public/home/tanghui/GB_SDC_TrackVis/logs/refmap_%A_%a.err
set -euo pipefail
BASE=/public/home/tanghui/GB_SDC_TrackVis
PY=/public/home/tanghui/software/sdc_fast_env/bin/python
export FSLDIR=/public/apps/neuroscience/fsl/6.0.4
export FSLOUTPUTTYPE=NIFTI_GZ
export PATH="$(dirname "$PY"):$FSLDIR/bin:$PATH"
unset PYTHONPATH PYTHONHOME || true
: "${GROUP:?}"; : "${WAVE:?}"
RI=$(( WAVE*10 + SLURM_ARRAY_TASK_ID ))
TOTAL=$(wc -l < "$BASE/ref_major_v1/manifests/references.txt")
if (( RI>=TOTAL ));then echo "SKIP ref $RI";exit 0;fi
"$PY" "$BASE/scripts/ref_major_map.py" --group "$GROUP" --reference-index "$RI" --patient-chunk 50
