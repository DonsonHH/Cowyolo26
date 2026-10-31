from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,gzip,tarfile

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
source=PROJECT/'pynq_frontend_port_20261029';plan=load(ROOT/'protocol/run_v1.json');stage=ROOT/'tracker_input';stage.mkdir(exist_ok=False)
for row in plan['runtime_files']:
 marker='/cow_research_numpy_tracker_20261029/'
 if marker in row['file']:
  name=row['file'].split(marker,1)[1];p=source/name;assert sha(p)==row['sha256'];out=stage/'source'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(p.read_bytes())
history=json.loads(gzip.decompress((PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/raw_predictions.json.gz').read_bytes()))
history=[r for r in history if r['frame0']<8915];assert len(history)==1783
with gzip.GzipFile(filename=str(stage/'history.json.gz'),mode='wb',mtime=0)as f:f.write(json.dumps(history,separators=(',',':')).encode())
cases=[]
for row in plan['runs']:
 folder=stage/row['run'];folder.mkdir();original=ROOT/'delivery/results'/row['run']
 for name in['actual_raw.npz','counter_trace.json.gz']:(folder/name).write_bytes((original/name).read_bytes())
 cases.append({'run':row['run'],'raw':'tracker_input/'+row['run']+'/actual_raw.npz','trace':'tracker_input/'+row['run']+'/counter_trace.json.gz'})
remote='/share/home/renly/projects/idcoo_research_20261026/identity_trigger_pair_20261030'
slurm=f'''#!/bin/bash
#SBATCH --job-name=cow-trigger-track
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output={remote}/logs/tracker-%j.out
#SBATCH --error={remote}/logs/tracker-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd {remote}
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py
''';script=ROOT/'tools/tracker_replay.slurm';assert not script.exists();script.write_bytes(slurm.encode())
files=[p for p in stage.rglob('*')if p.is_file()]+[ROOT/'tools/replay_tracker.py',script]
protocol={'status':'FROZEN_FULL_ASSOCIATION_REPLAY_OF_ACTUAL4_INPUT_SCHEDULES','created_UTC':datetime.now(timezone.utc).isoformat(),'video':plan['video'],'tracker_config':plan['tracker_config'],'counter_kwargs':plan['counter_kwargs'],'cases':cases,'box_tolerance_pixels':.002,'axis_tolerance':2e-6,'IDs_and_events_exact_required':True,'model_forwards':0,'files':[{'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}for p in sorted(files)]};(stage/'protocol.json').write_bytes((json.dumps(protocol,indent=2)+'\n').encode());a=ROOT/'tracker_input_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for p in files+[stage/'protocol.json']:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
v={'archive':str(a),'bytes':a.stat().st_size,'sha256':sha(a),'members':len(files)+1,'new_model_forwards':0};(ROOT/'evidence/tracker_input_bundle.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
