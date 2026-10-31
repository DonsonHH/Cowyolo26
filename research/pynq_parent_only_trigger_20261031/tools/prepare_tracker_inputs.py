from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/'protocol/run_v1.json');v=load(ROOT/'results/independent_verification.json')
assert v['actual_O8_timed_forwards']==1532 and v['counter_observation_ticks_with_history']==8664
stage=ROOT/'tracker_input';stage.mkdir(exist_ok=False)
for row in p['runtime_files']:
 marker='/cow_research_numpy_tracker_20261029/'
 if marker in row['file']:
  name=row['file'].split(marker,1)[1];source=PROJECT/'pynq_frontend_port_20261029'/name
  assert sha(source)==row['sha256'];target=stage/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
history=json.loads(gzip.decompress((PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/raw_predictions.json.gz').read_bytes()))
history=[row for row in history if row['frame0']<8915];assert len(history)==1783
with gzip.GzipFile(filename=str(stage/'history.json.gz'),mode='wb',mtime=0)as f:f.write(json.dumps(history,separators=(',',':')).encode())
cases=[]
for run in p['runs']:
 folder=stage/run['run'];folder.mkdir()
 for name in['actual_raw.npz','counter_trace.json.gz']:(folder/name).write_bytes((ROOT/'delivery/results'/run['run']/name).read_bytes())
 cases.append({'run':run['run'],'raw':f"tracker_input/{run['run']}/actual_raw.npz",'trace':f"tracker_input/{run['run']}/counter_trace.json.gz"})
replay=ROOT/'tools/replay_tracker.py'
with replay.open('xb')as f:f.write((PROJECT/'identity_trigger_pair_20261030/tools/replay_tracker.py').read_bytes())
files=sorted([path for path in stage.rglob('*')if path.is_file()]+[replay])
protocol={'status':'FROZEN_FOUR_PARENT_ONLY_TRIGGER_SCHEDULE_ASSOCIATION_REPLAYS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'video':p['video'],'tracker_config':p['tracker_config'],'counter_kwargs':p['counter_kwargs'],'cases':cases,
 'box_tolerance_pixels':.002,'axis_tolerance':2e-6,'IDs_and_events_exact_required':True,'model_forwards':0,
 'files':[{'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path)}for path in files]}
with(stage/'protocol.json').open('x',encoding='utf-8')as f:json.dump(protocol,f,indent=2);f.write('\n')
print(json.dumps({'status':'FOUR_TRACKER_INPUTS_FROZEN_WITHOUT_DANGLING_STANDALONE_SLURM_DEPENDENCY','files':len(files),'new_model_forwards':0}))
