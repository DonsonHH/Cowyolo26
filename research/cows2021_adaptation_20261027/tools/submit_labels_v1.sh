set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
audit=root/'results/image_audit_01/summary.json';s=json.loads(audit.read_text())
assert s['status']=='ALL_8380_DEVELOPMENT_IMAGES_DECODED_OVERLAP_SCREENED_LABEL_LOADER_PENDING'
assert s['decoded_images']==8380 and s['decode_errors']==0
assert s['cross_role_dHash_le2_review_pairs']==0
crc=json.loads((root/'results/source_archive_CRC_audit.json').read_text())
assert crc['status']=='ALL_8380_NATIVE_JPEGS_MATCH_OFFICIAL_ZIP_MEMBER_CRC_AND_SIZE'
assert crc['mismatches']==[] and crc['images_checked']==8380
assert crc['native_byte_manifest_sha256']==s['byte_manifest_sha256']
assert not (root/'data_v1').exists() and not (root/'results/labels_v1').exists()
versions={r['path']:r for r in json.loads((root/'results/training_tools_v1.json').read_text())}
for name in ['tools/prepare_labels.py']:
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==versions[name]['sha256']
print(json.dumps({'image_and_official_byte_checks_pass':True,'labels_and_actual_loader_next':True}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable "$stage/tools/labels.slurm" 01 v1)
printf '%s\n' "$jobid" > "$stage/results/labels_v1_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
