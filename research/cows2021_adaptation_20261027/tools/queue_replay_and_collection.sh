set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
test "$(cat "$stage/results/training_job_id.txt")" = 129918
test ! -e "$stage/results/inference_job_id.txt"
test ! -e "$stage/results/collection_job_id.txt"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
versions={r['path']:r for r in json.loads((root/'results/replay_and_sample_tools_v1.json').read_text())}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['tools/infer_fixed_models.py','tools/infer.slurm','tools/collect.slurm']:
    assert sha(root/name)==versions[name]['sha256']
update=json.loads((root/'results/collection_transport_filter_update.json').read_text())
assert sha(root/'tools/collect.py')==update['new_script_sha256']
assert not (root/'results/inference').exists() and not (root/'delivery.tar.gz').exists()
for name in ['zone_counter.py','event_metrics.py']:
    assert (root.parent/'phase2/tools'/name).is_file()
print(json.dumps({'replay_and_collection_code_hashes_verified':True,
                  'checkpoint_freeze_required_by_replay':True,'source_or_Toros_prediction_already_performed':False}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
inferid=$(sbatch --parsable --dependency=afterok:129918 "$stage/tools/infer.slurm")
collectid=$(sbatch --parsable --dependency="afterok:$inferid" "$stage/tools/collect.slurm")
printf '%s\n' "$inferid" > "$stage/results/inference_job_id.txt"
printf '%s\n' "$collectid" > "$stage/results/collection_job_id.txt"
printf 'training=129918\ninference=%s\ncollection=%s\n' "$inferid" "$collectid"
squeue -j "129918,$inferid,$collectid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
