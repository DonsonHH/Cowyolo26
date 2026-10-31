from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
p=ROOT/'protocol/one_frame_causal_v1.json';assert not p.exists()
p.write_text(json.dumps({'created_host_UTC':datetime.now(timezone.utc).isoformat(),'frame':9550,'single_changed_stage':'unconfirmed_fuse_score_only',
    'all_other_frames_original_fusion':True,'selected_from_diagnosed_cost_failure':True,'not_a_deployment_rule':True,'new_detector_forwards':0,'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
a=ROOT/'causal_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for f in [ROOT/'tools/probe_one_frame.py',p]:tar.add(f,arcname=f.relative_to(ROOT).as_posix())
h=hashlib.sha256(a.read_bytes()).hexdigest();bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'/causal_inputs_v1.tar.gz'],check=True)
s='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE/PHASE
../env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
p=Path('causal_inputs_v1.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='HASH'
with tarfile.open(p) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=4G --time=00:03:00 --job-name=one-frame-causal --output=REMOTE/PHASE/logs/one-frame-%j.out --error=REMOTE/PHASE/logs/one-frame-%j.err --wrap='cd REMOTE/PHASE && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ../env/bin/python -B tools/probe_one_frame.py'
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',h)
f=ROOT/'tools/submit_causal.sh';assert not f.exists();f.write_text(s,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/causal_submission.txt')],check=True)
