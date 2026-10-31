"""Replay all frozen full/crop raw boxes through the NumPy deployment port."""
from pathlib import Path
from datetime import datetime,timezone
import json,gzip,hashlib,os,socket,sys
import numpy as np
from frame_pipeline import FramePipeline
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.loads(json.dumps(x))
def main():
 assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
 p=load(ROOT/'regression_v1.json')
 for r in p['files']:assert sha(ROOT/r['file'])==r['sha256']
 out=ROOT/'results/regression';out.mkdir(parents=True,exist_ok=False)
 reports=[];total=0;output_boxes=0
 for source in p['caches']:
  rawpath=Path(source['raw_file']);tracepath=Path(source['trace_file'])
  assert sha(rawpath)==source['raw_sha256'] and sha(tracepath)==source['trace_sha256']
  raw=gz(rawpath);expected=gz(tracepath);byframe={r['frame0']:r['predictions'] for r in raw}
  pipeline=FramePipeline(source['spec'],p['tracker_config'],p['counter_kwargs'])
  actual={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[],'effective_tracker_config':p['tracker_config']}
  for frame in range(0,source['spec']['decode_end_exclusive'],source['stride']):
   result=pipeline.update(frame,byframe[frame]);actual['observations'].append(result['observation'])
   for name in ['post_tracker','confirmed_only_events','handoff_events']:actual[name].extend(result[name])
  if canonical(actual)!=expected:
   (out/'first_mismatch.json').write_text(json.dumps({'source':source,'actual':actual,'expected':expected},indent=2)+'\n')
   raise AssertionError((source['mode'],source['scene'],source['condition'],source['stride']))
  total+=len(actual['observations']);output_boxes+=len(actual['post_tracker'])
  reports.append({k:source[k] for k in ['mode','scene','condition','stride']}|{'observation_ticks':len(actual['observations']),'post_tracker_rows':len(actual['post_tracker']),'complete_trace_exact':True})
  if len(reports)%15==0:print(json.dumps({'traces':len(reports),'ticks':total}),flush=True)
 assert len(reports)==90 and total==82020
 assert 'torch' not in sys.modules,'Deployment port unexpectedly loaded Torch'
 result={'status':'ALL90_FULL_AND_CROP_TRACES180_COUNTER_PATHS82020_TICKS_EXACT_WITHOUT_TORCH',
  'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'regression_v1.json'),
  'trace_count':len(reports),'counter_paths':180,'observation_ticks':total,'post_tracker_rows':output_boxes,'torch_imported':False,
  'traces':reports,'real_network_forwards':0,'board_regression_executed':False,'whole_goal_complete':False}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='traces'}),flush=True)
if __name__=='__main__':main()
