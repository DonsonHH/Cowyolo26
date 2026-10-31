set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import os,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/deployment_audit')
pid=int((root/'logs/runtime_stage_pid.txt').read_text());proc=Path('/proc')/str(pid)
record={'stage_pid':pid,'process_present':proc.exists()}
if proc.exists():
    assert proc.stat().st_uid==os.getuid()
    cmd=(proc/'cmdline').read_bytes()
    assert str(root/'dependencies').encode() in cmd
    partial=[]
    for fd in (proc/'fd').iterdir():
        try:
            target=fd.resolve()
            if 'pip-unpack-' in str(target) and target.is_file():partial.append({'wheel':target.name,'bytes_written':target.stat().st_size})
        except (FileNotFoundError,PermissionError):pass
    record['active_wheel_files']=partial
print(json.dumps(record),flush=True)
PY
tail -n 5 "$ROOT/logs/runtime_stage.out"
tail -n 4 "$ROOT/logs/runtime_stage.err"
