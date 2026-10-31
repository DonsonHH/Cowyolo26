from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,sys,subprocess
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
p=load(PROJECT/'factorial_lane_crop_20261029/protocol/crop_v1.json');cfg=load(ROOT/'tracker_config.json')
caches=[]
for mode,local,remote in [('crop',PROJECT/'factorial_lane_crop_20261029/delivery/results/roi',REMOTE+'/factorial_lane_crop_20261029/results/roi'),
                          ('full',PROJECT/'detector_factorial_20261029/delivery/results/evaluation',REMOTE+'/detector_factorial_20261029/results/evaluation')]:
 for spec in p['videos']:
  for condition in p['conditions']:
   folder=local/spec['name']/condition['condition'];target=remote+'/'+spec['name']+'/'+condition['condition']
   for stride in spec['counter_replay_strides']:
    raw=folder/'raw_predictions.json.gz';trace=folder/f'stride{stride}_counter_trace.json.gz'
    caches.append({'mode':mode,'scene':spec['name'],'condition':condition['condition'],'stride':stride,
      'raw_file':target+'/'+raw.name,'raw_sha256':sha(raw),'trace_file':target+'/'+trace.name,'trace_sha256':sha(trace),
      'spec':{k:spec[k] for k in ['width','height','fps','axis','perpendicular_ROI','decode_end_exclusive']}})
assert len(caches)==90
files=sorted(x for x in (ROOT/'cow_tracker').glob('*.py'))+[ROOT/'frame_pipeline.py',ROOT/'tracker_config.json']
protocol={'status':'FROZEN_BEFORE_PORT_REGRESSION','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'tracker_config':cfg,'counter_kwargs':p['counter_kwargs'],'caches':caches,'trace_count':90,'counter_paths':180,
 'observation_ticks':82020,'full_trace_exact_required_in_reference_environment':True,
 'board_coordinate_tolerance_pixels':.002,'board_ID_event_and_counter_observation_keys_exact_required':True,
 'source_changes_scope':'Package imports, NumPy-only boxes interface, hard fail instead of automatic dependency install; AABB math and LAP0.5.13 unchanged.',
 'files':[{'file':x.relative_to(ROOT).as_posix(),'sha256':sha(x)} for x in files],
 'real_network_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
file=ROOT/'regression_v1.json';assert not file.exists();file.write_text(json.dumps(protocol,indent=2)+'\n')
script=f'''#!/bin/bash
#SBATCH --job-name=cow-numpy-track-port
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output={REMOTE}/{ROOT.name}/logs/regression-%j.out
#SBATCH --error={REMOTE}/{ROOT.name}/logs/regression-%j.err
set -euo pipefail
cd {REMOTE}/{ROOT.name}
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
../env/bin/python -B regression.py
'''
(ROOT/'regression.slurm').write_text(script,newline='\n')
print(json.dumps({'frozen_traces':90,'counter_paths':180,'ticks':82020,'protocol_sha256':sha(file)}))
