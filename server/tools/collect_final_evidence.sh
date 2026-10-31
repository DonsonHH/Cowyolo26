set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
test -s "$ROOT/results/slurm_jobs_final.txt"
"$ROOT/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib,os,sys,importlib.metadata as m
root=Path('/share/home/renly/projects/idcoo_research_20261026')
required=[root/'results/detection_pilot/training_record.json',root/'results/multicam_count_finetuned_dev/summary.json',root/'results/counting_finetuned_dev/all_summaries.json']
for p in required:
 if not p.is_file():raise RuntimeError('Missing expected final artifact: '+str(p))
rows=[]
for p in sorted((root/'data').rglob('*')):
 if p.is_file() and not p.is_symlink() and (p.suffix.lower() in ('.avi','.mp4','.zip') or p.name.endswith('.manifest.json') or p.name=='summary.json'):
  rows.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size})
versions={}
for k in ('ultralytics','torch','torchvision','opencv-python','numpy','pillow','scipy','lap','polars'):
 try:versions[k]=m.version(k)
 except m.PackageNotFoundError:versions[k]=None
out={'project_root':str(root),'files':rows,'python':sys.version,'packages':versions,'scope':'local inference under Slurm, not PYNQ board measurements'}
(root/'results/server_inventory.json').write_text(json.dumps(out,indent=2))
sources=[]
for p in sorted((root/'tools').glob('*')):
 if p.is_file():sources.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'results/source_hashes.json').write_text(json.dumps(sources,indent=2))
PY
mkdir -p "$ROOT/results/delivery_bundle/evidence" "$ROOT/results/delivery_bundle/media" "$ROOT/results/delivery_bundle/config"
cp "$ROOT/results/slurm_jobs_final.txt" "$ROOT/results/queue_final.txt" "$ROOT/results/server_inventory.json" "$ROOT/results/source_hashes.json" "$ROOT/results/delivery_bundle/evidence/"
cp "$ROOT/results/detection_pilot/training_record.json" "$ROOT/results/delivery_bundle/evidence/"
cp "$ROOT/results/detection_pilot/five_epoch_dev/results.csv" "$ROOT/results/delivery_bundle/evidence/"
cp "$ROOT/results/detection_pilot/five_epoch_dev/args.yaml" "$ROOT/results/delivery_bundle/config/"
cp "$ROOT/data/opencows2020/derived_detection/data.yaml" "$ROOT/results/delivery_bundle/config/"
cp "$ROOT/data/opencows2020/derived_detection/summary.json" "$ROOT/results/delivery_bundle/evidence/cleaning_summary.json"
cp "$ROOT/results/media_audit_round2/media_audit.json" "$ROOT/results/delivery_bundle/evidence/"
cp "$ROOT/results/multicam_count_finetuned_dev/summary.json" "$ROOT/results/delivery_bundle/evidence/multicam_finetuned_summary.json"
cp "$ROOT/results/multicam_count_finetuned_dev/predicted_events.csv" "$ROOT/results/delivery_bundle/evidence/multicam_finetuned_events.csv"
cp "$ROOT/results/counting_finetuned_dev/all_summaries.json" "$ROOT/results/delivery_bundle/evidence/cows21_finetuned_summaries.json"
cp "$ROOT/results/multicam_count_dev/summary.json" "$ROOT/results/delivery_bundle/evidence/multicam_pretrained_summary.json"
cp "$ROOT/results/counting_dev/all_summaries.json" "$ROOT/results/delivery_bundle/evidence/pretrained_summaries.json"
cp "$ROOT/results/multicam_count_finetuned_dev/annotated.mp4" "$ROOT/results/delivery_bundle/media/multicam_finetuned_dev.mp4"
cp "$ROOT/results/counting_finetuned_dev/2020-03-09_12-19-46/annotated.mp4" "$ROOT/results/delivery_bundle/media/cows2021_finetuned_dev.mp4"
cp "$ROOT/results/multicam_count_finetuned_dev/"active_contact_*.jpg "$ROOT/results/delivery_bundle/media/"
tar -czf "$ROOT/results/idcoo_audit_delivery.tar.gz" -C "$ROOT/results/delivery_bundle" .
sha256sum "$ROOT/results/idcoo_audit_delivery.tar.gz" "$ROOT/results/detection_pilot/five_epoch_dev/weights/best.pt"
