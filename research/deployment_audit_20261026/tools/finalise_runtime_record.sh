set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
mkdir -p "$ROOT/results"
PYTHONPATH="$ROOT/dependencies_offline" /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from importlib.metadata import version
import json,onnx,onnxruntime,numpy,os
root=Path('/share/home/renly/projects/idcoo_research_20261026/deployment_audit')
assert (onnx.__version__,onnxruntime.__version__,numpy.__version__)==('1.19.0','1.23.2','2.2.6')
pid=int((root/'logs/runtime_stage_pid.txt').read_text())
proc=Path('/proc')/str(pid)
assert not proc.exists(),'Slow task download helper should have terminated after successful offline imports'
record={'status':'OFFLINE_TARGET_IMPORT_PASS','original_slow_download_pid':pid,'original_helper_is_no_longer_present':True,
        'initial_record_write_issue':'Missing results directory fixed after import success; no package reinstall or result rerun',
        'dependencies_path':str(root/'dependencies_offline'),
        'versions':{name:version(name) for name in ['onnx','onnxruntime','numpy','protobuf','ml_dtypes','flatbuffers','packaging','sympy','typing_extensions']},
        'shared_training_environment_modified':False,
        'pip_warnings':'Isolated target has packaging26.3 outside an unused langchain bound; pre-existing base xformers2.7.1 requirement vs torch2.8.0 warning retained. Export path import/forward will be checked independently.'}
(root/'results/runtime_ready.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
PY
job=$(cat "$ROOT/logs/job_id.txt")
sacct -j "$job" -P --format=JobID,JobName,State,ExitCode,Elapsed
tail -n 8 "$ROOT/logs/audit-$job.out"
tail -n 8 "$ROOT/logs/audit-$job.err"
