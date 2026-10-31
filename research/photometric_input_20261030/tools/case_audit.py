"""Diagnostic old640 model reference94, never independent ground truth."""
from pathlib import Path
from datetime import datetime,timezone
import json,importlib.util,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/study_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('photometric_case_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
geo=importlib.util.module_from_spec(spec);spec.loader.exec_module(geo)
refs=load(PROJECT/'rot192_event_diagnosis_20261030/input/reference_boxes.json')
byframe={frame:[r for r in refs if r['frame0']==frame] for frame in {r['frame0'] for r in refs}}
target=[r for r in refs if r['reference_track_id']==94];assert len(target)==15
def optimum(matrix,threshold):
    n=len(matrix);m=len(matrix[0]) if n else 0;best=(-1,-1.);winners=[]
    def dfs(i,used,pairs,total):
        nonlocal best,winners
        if i==n:
            value=(len(pairs),total)
            if value[0]>best[0] or value[0]==best[0] and total>best[1]+1e-10:best=value;winners=[pairs]
            elif value[0]==best[0] and abs(value[1]-best[1])<=1e-10:winners.append(pairs)
            return
        dfs(i+1,used,pairs,total)
        for j in range(m):
            if j not in used and matrix[i][j]>=threshold:dfs(i+1,used|{j},pairs+[(i,j)],total+matrix[i][j])
    dfs(0,set(),[],0.)
    return winners
def native_boxes(head):
    boxes=head[:,:4].copy()
    boxes[:,[0,2]]/=np.float32(192/1440)
    boxes[:,[1,3]]=(boxes[:,[1,3]]-26)/np.float32(192/1440)
    boxes[:,[0,2]]=boxes[:,[0,2]].clip(0,1440);boxes[:,[1,3]]=boxes[:,[1,3]].clip(0,1050)
    return np.stack([boxes[:,1]+870,1440-boxes[:,2],boxes[:,3]+870,1440-boxes[:,0]],axis=1).astype(float)
rows=[];summaries=[]
for condition in ['none','gamma07','clahe_y2']:
    with np.load(OUT/condition/'original_all_raw.npz') as archive:
        for mode in ['FP32','QDQ']:
            raw=archive[mode];current=[]
            for ref in target:
                frame=ref['frame0'];head=raw[frame//5];native=native_boxes(head)
                overlaps=np.array([geo.iou(ref['xyxy'],v) if v[2]>v[0] and v[3]>v[1] else 0 for v in native])
                rr=byframe[frame];target_index=next(i for i,r in enumerate(rr) if r['reference_track_id']==94)
                selected=np.flatnonzero(head[:,4]>=.2)
                matrix=[[geo.iou(r['xyxy'],native[j]) if native[j,2]>native[j,0] and native[j,3]>native[j,1] else 0 for j in selected] for r in rr]
                row={'condition':condition,'mode':mode,'frame0':frame,'reference_axis':ref['axis_position'],
                    'head_queries':300,'max_IoU_any_head':float(overlaps.max()),
                    'max_score_IoU03':max([float(head[j,4]) for j in np.flatnonzero(overlaps>=.3)],default=None),
                    'max_score_IoU05':max([float(head[j,4]) for j in np.flatnonzero(overlaps>=.5)],default=None)}
                for threshold,label in [(.3,'IoU03'),(.5,'IoU05')]:
                    winners=optimum(matrix,threshold)
                    present=[any(i==target_index for i,j in pairs) for pairs in winners]
                    row[label+'_target_matched_in_all_optima']=all(present)
                    row[label+'_target_matched_in_any_optimum']=any(present)
                    row[label+'_assignment_ambiguous']=len(winners)>1
                rows.append(row);current.append(row)
            table={'condition':condition,'mode':mode,'reference_samples':15,'head_arrays_checked':15}
            for label in ['IoU03','IoU05']:
                table[label+'_raw_matches']=sum(r[label+'_target_matched_in_all_optima'] for r in current)
                run=longest=0;previous=None
                for r in current:
                    if previous is None or r['frame0']!=previous+5:run=0
                    run=run+1 if r['reference_axis']<.4 and r[label+'_target_matched_in_all_optima'] else 0
                    longest=max(longest,run);previous=r['frame0']
                table[label+'_reference_entry_longest_run']=longest
            summaries.append(table)
result={'status':'SIX_CONDITION_MODE90_HEAD_ARRAYS_AND180_RAW_ASSIGNMENTS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'reference_is_independent_GT':False,
    'target_reference_track':94,'new_network_forwards':0,'confidence_threshold_changed':False,
    'rows':rows,'summaries':summaries,'whole_goal_complete':False}
assert len(rows)==90
dest=ROOT/'results/reference94_photometric_audit.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'summaries':summaries}))
