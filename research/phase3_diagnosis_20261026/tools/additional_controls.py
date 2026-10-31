"""Check whether unassigned tracker IDs explain the reference-ID intervention."""
from pathlib import Path
from collections import defaultdict
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'counting_eval_20261026/tools'))
from zone_counter import ZoneCounter
allrows=list(csv.DictReader((ROOT/'results/layers/frame_assignments.csv').open()))
results=[];region=[]
for model in ['generic','pilot']:
    for threshold in [.5,.3]:
        rows=[r for r in allrows if r['model']==model and float(r['association_iou'])==threshold and r['kind']=='post']
        frames=defaultdict(dict)
        for r in rows:
            if r['tracker_id']:frames[int(r['frame'])][int(r['reference_id'])]=float(r['prediction_cx'])
        count=ZoneCounter();events=[]
        for f in range(479):
            for e in count.update(f/30,frames[f]):e['frame']=f;events.append(e)
        results.append({'model':model,'association_iou':threshold,'condition':'only_post_boxes_with_actual_id_then_reference_id_replacement','events':events,'matched_boxes_without_actual_id':sum(not r['tracker_id'] for r in rows)})
for rid in [1,14,7,16,22,17]:
    for kind in ['raw','post']:
        rows=[r for r in allrows if r['model']=='pilot' and float(r['association_iou'])==.5 and int(r['reference_id'])==rid and r['kind']==kind]
        row={'reference_id':rid,'kind':kind,'matched_frames':len(rows)}
        for zone in ['A','B']:
            fs=sorted({int(r['frame']) for r in rows if (float(r['prediction_cx'])<.4 if zone=='A' else float(r['prediction_cx'])>.6)})
            maximum=run=0;last=None
            for f in fs:
                run=run+1 if last is not None and f==last+1 else 1;last=f;maximum=max(maximum,run)
            row['max_consecutive_'+zone]=maximum
        region.append(row)
record={'scope':'Additional ambiguity check for empty tracker IDs and stable-region coverage; reference-assisted diagnostic only','id_presence_control':results,'stable_region_runs_primary_iou05':region}
(ROOT/'results/layers/additional_controls.json').write_text(json.dumps(record,indent=2))
print(json.dumps({'id_presence_control_events':[{'model':r['model'],'iou':r['association_iou'],'events':len(r['events'])} for r in results]},indent=2))
