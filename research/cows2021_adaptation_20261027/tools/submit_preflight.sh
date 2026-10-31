set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib,time
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
label_path=root/'results/labels_v1/summary.json';labels=json.loads(label_path.read_text())
assert labels['status']=='DERIVED_LABELS_AND_REAL_ULTRALYTICS_LOADER_PASS'
assert labels['dHash_candidate_review_still_pending'] is False
assert labels['loader_results']==[{'split':'train','images':6809,'actual_loaded_annotation_rows':8888},
                                 {'split':'val','images':1571,'actual_loaded_annotation_rows':1864}]
path=root/'results/labels_v1/prepared_image_label_manifest.json'
assert sha(path)==labels['prepared_manifest_sha256']
rows=json.loads(path.read_text());assert len(rows)==8380
started=time.perf_counter()
for row in rows:
    image=Path(row['image_alias']);label=Path(row['label_path'])
    assert image.resolve().is_relative_to(root/'raw_images')
    assert image.stat().st_size==row['bytes'] and sha(image)==row['sha256']
    assert sha(label)==row['label_sha256']
record={'status':'ALL_SOURCE_BYTES_AND_LABELS_UNCHANGED_AFTER_REAL_LOADER','images':len(rows),
        'label_summary_sha256':sha(label_path),'prepared_manifest_sha256':sha(path),
        'elapsed_s':time.perf_counter()-started,'image_or_model_forward':False}
target=root/'results/source_immutability_after_loader.json';assert not target.exists()
target.write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
assert not (root/'results/preflight.json').exists() and not (root/'results/training').exists()
versions={r['path']:r for r in json.loads((root/'results/training_tools_v1.json').read_text())}
for name in ['protocol/detector_v1.json','tools/preflight.py','tools/common.py']:
    assert sha(root/name)==versions[name]['sha256']
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable "$stage/tools/preflight.slurm")
printf '%s\n' "$jobid" > "$stage/results/preflight_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
