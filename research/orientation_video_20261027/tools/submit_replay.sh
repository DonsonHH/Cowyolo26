set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/orientation_video_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/share/home/renly/projects/idcoo_research_20261026/orientation_video_20261027')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prototype=root/'protocol/video_rotation_v1.json'
a=json.loads((root/'results/smoke.json').read_text())
b=json.loads((root/'results/nonempty_seam_smoke.json').read_text())
assert a['status']=='SYNTHETIC_NONEMPTY_EMPTY_RESULTS_AND_REAL_BYTE_TRACK_SEAM_CONTROLS_PASS'
assert b['status']=='REAL_NONEMPTY_NEURAL_BOXES_IN_BOTH_ORIENTATIONS_RESTORE_BEFORE_BYTE_TRACK'
assert a['protocol_sha256']==b['protocol_sha256']==sha(prototype)
assert len(b['records'])==2 and all(r['nonempty_neural_boxes_restored_in_native_camera'] and r['pretracker_boxes'] and r['posttracker_data'] for r in b['records'])
assert not (root/'results/inference').exists()
for row in json.loads((root/'input/staging_manifest.json').read_text()):assert sha(root/row['path'])==row['sha256']
print(json.dumps({'pixel_box_empty_and_real_nonempty_seams_pass':True,'protocol_sha256':sha(prototype),'new_training_updates':0}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%R'
jobid=$(sbatch --parsable "$stage/tools/replay.slurm")
printf '%s\n' "$jobid" > "$stage/results/replay_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%R'
