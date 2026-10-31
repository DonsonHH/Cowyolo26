"""Reference-assisted stable-zone and actual-ID-presence controls for all three seeds."""
from pathlib import Path
from collections import defaultdict
import csv,json,sys
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/event_diagnosis')
sys.path.insert(0,str(ROOT.parent/'phase2/tools'))
from zone_counter import ZoneCounter


def main():
    rows=list(csv.DictReader((ROOT/'results/layers/frame_assignments.csv').open()))
    p=json.loads((ROOT/'protocol/event_diagnosis_v1.json').read_text());controls=[];regions=[]
    for model in [r['name'] for r in p['models']]:
        for threshold in [.5,.3]:
            selected=[r for r in rows if r['model']==model and float(r['association_iou'])==threshold and r['kind']=='post']
            frames=defaultdict(dict)
            for r in selected:
                if r['tracker_id']:frames[int(r['frame'])][int(r['reference_id'])]=float(r['prediction_cx'])
            counter=ZoneCounter();events=[]
            for f in range(479):
                for e in counter.update(f/30,frames[f]):events.append({**e,'frame':f})
            controls.append({'model':model,'association_iou':threshold,'condition':'only_actual_ID_post_boxes_with_reference_ID_replacement',
                             'events':events,'matched_post_boxes_without_actual_ID':sum(not r['tracker_id'] for r in selected)})
        for rid in [1,14,7,16,22,17]:
            for kind in ['raw','post']:
                selected=[r for r in rows if r['model']==model and float(r['association_iou'])==.5 and int(r['reference_id'])==rid and r['kind']==kind]
                out={'model':model,'reference_id':rid,'kind':kind,'matched_frames':len(selected)}
                for zone in ['A','B']:
                    fs=sorted({int(r['frame']) for r in selected if (float(r['prediction_cx'])<.4 if zone=='A' else float(r['prediction_cx'])>.6)})
                    maximum=streak=0;last=None
                    for f in fs:
                        streak=streak+1 if last is not None and f==last+1 else 1;last=f;maximum=max(maximum,streak)
                    out[f'max_consecutive_{zone}']=maximum
                regions.append(out)
    (ROOT/'results/layers/additional_controls.json').write_text(json.dumps({'scope':'Reference-assisted diagnostic only',
             'id_presence_controls':controls,'stable_region_runs_primary_iou05':regions},indent=2))
    print(json.dumps({'id_presence_event_counts':[{'model':r['model'],'iou':r['association_iou'],'events':len(r['events'])} for r in controls]}),flush=True)


if __name__=='__main__':main()
