#!/usr/bin/env bash
# Usage: bash submit_wave.sh g000 0
set -euo pipefail
BASE=/public/home/tanghui/GB_SDC_TrackVis
GROUP=${1:?group}; WAVE=${2:?wave}
[[ "$GROUP" =~ ^g[0-9]{3}$ ]] || { echo 'Invalid group' >&2;exit 2; }
[[ "$WAVE" =~ ^[0-9]+$ ]] && (( WAVE<=60 )) || { echo 'Invalid wave' >&2; exit 2; }
[[ -s "$BASE/ref_major_v1/manifests/$GROUP.patients.txt" ]] || exit 3
# strict wave ordering: previous wave must have been merged and committed
if (( WAVE>0 )); then
  prior=$((WAVE-1)); check="$BASE/ref_major_v1/states/$GROUP/c000_wave$(printf '%03d' "$prior").ok"
  [[ -s "$check" ]] || { echo "Previous wave not reduced: $check" >&2;exit 4; }
fi
n=$((601-WAVE*10));((n>10)) && n=10
root="$BASE/ref_major_v1/submissions/$GROUP";mkdir -p "$root"
marker="$root/w$(printf '%03d' "$WAVE").jobs"
if [[ -e "$marker" ]];then echo "Already submitted: $(cat "$marker")";exit 5;fi
# manual semaphore: no duplicate submission for a wave
( set -C; printf 'SUBMITTING\n' > "$marker" ) 2>/dev/null || exit 6
job=$(sbatch --parsable --array="0-$((n-1))%10" --export=ALL,GROUP="$GROUP",WAVE="$WAVE" "$BASE/scripts/ref_major_map.slurm") || { rm -f "$marker";exit 7; }
echo "MAP_JOB=$job" > "$marker"
red=$(sbatch --parsable --dependency=afterok:"$job" --export=ALL,GROUP="$GROUP",WAVE="$WAVE" "$BASE/scripts/ref_major_reduce.slurm") || { echo 'Reducer submission failed; map submitted. Manually submit reducer after all map tasks complete.' >&2;exit 8; }
printf 'REDUCE_JOB=%s\n' "$red" >> "$marker"
echo "$GROUP wave=$WAVE map=$job reduce=$red"
