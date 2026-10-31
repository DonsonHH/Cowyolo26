"""Inspect saved300-query heads; no new confidence setting is adopted."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,gzip,importlib.util,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('unfiltered_head_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
geo=importlib.util.module_from_spec(spec);spec.loader.exec_module(geo)
reference=[r for r in load(ROOT/'input/reference_boxes.json') if r['reference_track_id']==94];assert len(reference)==15
quality=PROJECT/'pynq_rot192_eval_20261029/delivery/results/quality_v2';board=PROJECT/'pynq_rot192_eval_20261029/board_delivery/results_v2/original'
rows=[]
fp=np.load(quality/'original_all_raw.npz');actual=np.load(board/'all_raw.npy',mmap_mode='r')
for mode,arrays in [('FP32',fp['FP32']),('QDQ',fp['QDQ']),('actual_O8',actual)]:
 source=board/'raw_predictions.json.gz' if mode=='actual_O8' else quality/'original'/mode/'raw_predictions.json.gz'
 stored=json.loads(gzip.decompress(source.read_bytes()));stored={r['frame0']:r['predictions'] for r in stored}
 for ref in reference:
  array=arrays[ref['frame0']//5].copy();box=array[:,:4].copy();gain=min(192/1050,192/1440)
  box[:,[0,2]]=(box[:,[0,2]]-0)/gain;box[:,[1,3]]=(box[:,[1,3]]-26)/gain
  box[:,[0,2]]=np.clip(box[:,[0,2]],0,1440);box[:,[1,3]]=np.clip(box[:,[1,3]],0,1050)
  native=np.asarray([[float(v[1])+870,1440-float(v[2]),float(v[3])+870,1440-float(v[0])] for v in box])
  kept=np.flatnonzero(array[:,4]>=.2);assert len(kept)==len(stored[ref['frame0']])
  for index,row in zip(kept,stored[ref['frame0']]):assert np.max(np.abs(native[index]-row['xyxy']))<.0003
  overlaps=np.asarray([geo.iou(ref['xyxy'],v) if v[2]>v[0] and v[3]>v[1] else 0. for v in native])
  best=int(np.argmax(overlaps));record={'mode':mode,'frame0':ref['frame0'],'reference94_axis_position':ref['axis_position'],
   'maximum_IoU_all300':float(overlaps[best]),'score_at_maximum_IoU':float(array[best,4]),'maximum_IoU_query_native_box':native[best].tolist(),
   'maximum_score_at_IoU05':max([float(array[i,4]) for i in np.flatnonzero(overlaps>=.5)],default=None),
   'maximum_score_at_IoU03':max([float(array[i,4]) for i in np.flatnonzero(overlaps>=.3)],default=None),
   'current02_IoU05_matched_head_queries':int(((array[:,4]>=.2)&(overlaps>=.5)).sum()),
   'current02_IoU03_matched_head_queries':int(((array[:,4]>=.2)&(overlaps>=.3)).sum())}
  rows.append(record)
fp.close()
result={'status':'ALL45_REFERENCE94_FRAME_MODE_HEADS300_QUERIES_INSPECTED_WITHOUT_NEW_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),
 'reference_track_is_GT':False,'new_model_forwards':0,'confidence_threshold_changed':False,'rows':rows,'whole_goal_complete':False}
file=ROOT/'results/unfiltered_reference94_heads.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'actual_O8_reference15':[{k:r[k] for k in ['frame0','maximum_IoU_all300','score_at_maximum_IoU','maximum_score_at_IoU03']} for r in rows if r['mode']=='actual_O8']}))
