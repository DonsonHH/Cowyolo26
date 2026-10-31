set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protocol=root/'protocol/detector_v1.json'
smoke_path=root/'results/preflight.json';smoke=json.loads(smoke_path.read_text())
assert smoke['status']=='PASS_ACTUAL_TRAIN_LOADER_AND_TWO_DISCARDED_CUDA_UPDATES'
assert smoke['protocol_sha256']==sha(protocol)
assert smoke['formal_training_updates']==0 and smoke['smoke_weights_saved_or_used_for_formal_training'] is False
assert len(smoke['loss_and_gradient_history'])==2 and smoke['changed_parameter_tensors']>0
assert smoke['source_or_Toros_forward'] is False and smoke['validation_or_candidate_final_query_forward'] is False
unchanged=json.loads((root/'results/source_immutability_after_loader.json').read_text())
assert unchanged['status']=='ALL_SOURCE_BYTES_AND_LABELS_UNCHANGED_AFTER_REAL_LOADER'
assert unchanged['label_summary_sha256']==smoke['label_loader_summary_sha256']
assert unchanged['prepared_manifest_sha256']==smoke['prepared_manifest_sha256']
crc=json.loads((root/'results/source_archive_CRC_audit.json').read_text())
assert crc['mismatches']==[] and crc['images_checked']==8380
assert not (root/'results/training').exists()
versions={r['path']:r for r in json.loads((root/'results/training_tools_v1.json').read_text())}
for name in ['tools/train_detector.py','tools/observed_trainer.py','tools/common.py','protocol/detector_v1.json']:
    assert sha(root/name)==versions[name]['sha256']
print(json.dumps({'formal_training_gates_pass':True,'protocol_sha256':sha(protocol),
                  'data_images':8380,'seeds':[26,27,28],'epochs_each':10,'smoke_weights_used':False}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable "$stage/tools/train.slurm")
printf '%s\n' "$jobid" > "$stage/results/training_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
