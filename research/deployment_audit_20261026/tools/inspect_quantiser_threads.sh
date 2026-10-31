set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
sed -n '/def create_inference_session/,/def /p' "$ROOT/dependencies_offline/onnxruntime/quantization/calibrate.py" | head -n 50
sed -n '/def quantize_static/,/def quantize_dynamic/p' "$ROOT/dependencies_offline/onnxruntime/quantization/quantize.py" | tail -n 115
grep -n 'calib_extra_options\|CalibrationDataReader\|create_calibrator' "$ROOT/dependencies_offline/onnxruntime/quantization/quantize.py" | head -n 15
PYTHONPATH="$ROOT/dependencies_offline" /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/deployment_audit')
s=json.loads((root/'results/export_audit/summary.json').read_text())
print(json.dumps({'detector':{k:v for k,v in s['detector_graph'].items() if k not in ['Conv_details']},
 'identity':[{'name':r['name'],'fp32':{k:v for k,v in r['fp32_evaluation'].items() if k!='per_identity'},'qdq':{k:v for k,v in r['qdq_evaluation'].items() if k!='per_identity'}} for r in s['identity_conditions']]},indent=2))
PY
