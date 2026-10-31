set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
test "$(sacct -j 129722 -X --format=State --noheader | tr -d ' ')" = COMPLETED
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
project=Path('/share/home/renly/projects/idcoo_research_20261026');root=project/'quant_diagnosis'
mixed=json.loads((root/'results/mixed/summary.json').read_text());selected=mixed['frozen_candidate']['selected_recipe']
metadata=root/'catalog/future_holdout/eligibility.json';eligibility=json.loads(metadata.read_text())
assert not eligibility['identity_inference_performed'] and eligibility['image_bytes_downloaded']==0
base=project/'deployment_audit/results/export_audit';original=json.loads((base/'summary.json').read_text())
conditions=[]
for seed in [26,27,28]:
    name=f'C_letterbox_trained_seed{seed}';source=next(r for r in original['identity_conditions'] if r['seed']==seed)
    fp32=base/name/'embedding_fp32.onnx'
    conditions.append({'name':f'FP32_seed{seed}','seed':seed,'method':'FP32','model_path':str(fp32),'model_sha256':hashlib.sha256(fp32.read_bytes()).hexdigest(),'threshold':source['original_fp32_threshold']})
    for method in ['full_conv_qdq',selected]:
        row=next(r for r in mixed['conditions'] if r['seed']==seed and r['candidate']==method)
        path=Path(row['model_path']);assert hashlib.sha256(path.read_bytes()).hexdigest()==row['model_sha256']
        conditions.append({'name':method+f'_seed{seed}','seed':seed,'method':method,'model_path':str(path),'model_sha256':row['model_sha256'],'threshold':row['validation_threshold']['threshold']})
record={'status':'FROZEN_BEFORE_FUTURE_IMAGE_BYTES_OR_MODEL_FORWARDS','selected_recipe':selected,'conditions':conditions,
        'mixed_validation_freeze_sha256':hashlib.sha256((root/'results/mixed/candidate_and_thresholds_frozen.json').read_bytes()).hexdigest(),
        'holdout_metadata_sha256':hashlib.sha256(metadata.read_bytes()).hexdigest(),'roles':eligibility['roles'],
        'samples_per_identity':5,'gallery_day':'2023Aug14','query_day':'2023Aug20','source_entries':eligibility['image_entries'],
        'selection':'One recipe across all3seeds chosen on prior validation, all declared seeds reported','scope':'Untouched identity holdout within same farm/camera, curated crop images; no field RFID/board accuracy claim'}
dest=root/'protocol/future_comparison_frozen.json';assert not dest.exists();dest.write_text(json.dumps(record,indent=2))
print(json.dumps({'frozen_models':len(conditions),'selected_recipe':selected,'images_to_stage':len(eligibility['image_entries']),'identities':12}),flush=True)
PY
