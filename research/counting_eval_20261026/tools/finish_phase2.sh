set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
sacct -j 129669,129670,129671,129673,129675,129683,129685,129688,129689,129690 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
cat "$ROOT/logs/count-score-129683.err"
/share/home/renly/miniconda3/bin/python - <<'PY'
import os,signal,socket,time,json
from pathlib import Path
pid=505602
proc=Path('/proc')/str(pid)
stopped=False
if proc.exists():
    assert proc.stat().st_uid==os.getuid()
    cmd=(proc/'cmdline').read_bytes().split(b'\0')
    assert b'/share/home/renly/.local/bin/mihomo' in cmd
    assert b'/share/home/renly/.cache/idcoo_us3_20261026' in cmd
    os.kill(pid,signal.SIGTERM)
    stopped=True
for _ in range(30):
    with socket.socket() as s:
        s.settimeout(.2)
        listening=s.connect_ex(('127.0.0.1',27831))==0
    if not listening:
        break
    time.sleep(.1)
assert not listening,'Task proxy listener still present; inspect without changing other services'
print(json.dumps({'task_proxy_pid':pid,'stopped_exact_task_process':stopped,
                  'loopback_port':27831,'listening_after_cleanup':listening,
                  'other_services_modified':False}))
PY
