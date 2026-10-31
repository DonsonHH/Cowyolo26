set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
summary_path=root/'results/download_attempt_02/summary.json'
summary=json.loads(summary_path.read_text())
assert summary['status']=='ALL_8380_DEVELOPMENT_IMAGE_BYTES_STAGED_DECODE_PENDING'
assert summary['saved_images']==8380 and summary['failed_images']==0
assert summary['roles']=={'train':6809,'validation':1571}
manifest_path=summary_path.parent/'image_manifest.json'
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==summary['image_manifest_sha256']
archive=json.loads((root/'results/archive_index_probe/summary.json').read_text())
assert summary['total_image_bytes']==archive['selected_uncompressed_bytes']==2747795477
assert not (root/'results/image_audit_01').exists()
initial={r['path']:r for r in json.loads((root/'results/auxiliary_tools_v1.json').read_text())}
for name in ['tools/audit_images.py','tools/audit.slurm']:
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==initial[name]['sha256']
print(json.dumps({'complete_byte_manifest_verified':True,'images':8380,'bytes':summary['total_image_bytes'],
                  'selected_archive_byte_total_matches':True,'image_decode_still_pending':True}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable "$stage/tools/audit.slurm" 02 01)
printf '%s\n' "$jobid" > "$stage/results/image_audit_01_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
