from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,csv,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n')
def main():
    accepted=load(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json')
    assert accepted['human_total']==accepted['predicted_down']==12 and accepted['per_event_correctness_proven'] is False
    baseline=PROJECT/'confirmation_handoff_20261028/delivery/results/replay_v2/seed26';events=load(baseline/'handoff_events.json');obs=load(baseline/'observations.json')
    assert sha(baseline/'handoff_events.json')==accepted['source_event_record']['events_sha256']
    ids={e['track_id'] for e in events};assert len(ids)==12 and len(events)==12
    tracks=list(csv.DictReader((baseline/'source_tracks.csv').open()));reference=defaultdict(dict)
    for row in tracks:
        tid=int(row['track_id']);frame=int(row['source_frame'])
        if tid in ids:reference[frame][tid]={'xyxy':[float(row[k]) for k in ['x1','y1','x2','y2']],
            'axis_position':float(row['axis_position']),'origin':'BASELINE640_CONFIRMED_TRACK','confidence':float(row['confidence'])}
    rawpath=PROJECT/'counting_recovery_20261028/delivery/results/replay_v2/full640_5hz_seed26/pretracker_boxes.csv';raw=defaultdict(list)
    for row in csv.DictReader(rawpath.open()):raw[int(row['frame'])].append({'xyxy':[float(row[k]) for k in ['x1','y1','x2','y2']],'confidence':float(row['confidence'])})
    accepted_rows=[]
    for tick in obs:
        for row in tick['accepted_history']:
            if row['track_id'] not in ids:continue
            frame=row['observation_source_frame'];tid=row['track_id'];position=row['axis_position']
            candidates=[]
            for pred in raw[frame]:
                x1,y1,x2,y2=pred['xyxy'];cx=(x1+x2)/(2*2560);cy=(y1+y2)/(2*1440)
                if .34<cx<.75 and abs(cy-position)<=.0001:candidates.append(pred)
            assert len(candidates)==1,(row,len(candidates));assert tid not in reference[frame]
            reference[frame][tid]={'xyxy':candidates[0]['xyxy'],'axis_position':position,'origin':'EXACT_UNIQUE_RAW640_PRIOR_ADMITTED_BY_BASELINE',
                                  'confidence':candidates[0]['confidence']}
            accepted_rows.append({'track_id':tid,'frame0':frame,'confirmation_frame0':row['confirmation_source_frame'],
                 'axis_position':position,'unique_raw640_match':True,'raw_axis_delta':abs(sum(candidates[0]['xyxy'][1::2])/(2*1440)-position)})
    assert len(accepted_rows)==12
    ref=[]
    for frame in range(0,10874,5):
        for tid,row in reference[frame].items():
            assert frame>=8912 and frame<=10873
            x1,y1,x2,y2=row['xyxy'];assert abs((y1+y2)/(2*1440)-row['axis_position'])<=.0001
            ref.append({'frame0':frame,'reference_track_id':tid,**row})
    caches=[]
    old=PROJECT/'lowres_baseline_20261029/delivery/results/baseline';oldp=load(PROJECT/'lowres_baseline_20261029/protocol/baseline_v2_path_fix.json')
    for c in oldp['conditions']:
        folder=old/'original'/c['condition'];caches.append({'condition':'old_'+c['condition'],'group':'prior_frozen_detector','size':c['input_size'],'seed':None if c['model']=='official' else int(c['model'][4:]),
           'raw_file':str((folder/'raw_predictions.json.gz').resolve()),'trace_file':str((folder/'stride5_counter_trace.json.gz').resolve()),
           'summary_file':str((folder/'stride5_summary.json').resolve())})
    training=PROJECT/'detector_factorial_20261029';newp=load(training/'protocol/evaluation_v1.json')
    for c in newp['new_conditions']:
        folder=training/'delivery/results/evaluation/original'/c['condition'];caches.append({'condition':c['condition'],'group':'new_'+('rot90' if c['right_angle'] else 'plain'),
          'size':c['input_size'],'seed':c['seed'],'raw_file':str((folder/'raw_predictions.json.gz').resolve()),'trace_file':str((folder/'stride5_counter_trace.json.gz').resolve()),
          'summary_file':str((folder/'stride5_summary.json').resolve())})
    assert len(caches)==27
    for c in caches:
        for kind in ['raw','trace','summary']:c[kind+'_sha256']=sha(Path(c[kind+'_file']))
    save(ROOT/'input/reference_boxes.json',ref);save(ROOT/'input/reference_admissions.json',accepted_rows)
    save(ROOT/'input/reference_events.json',[{'frame0':e['source_frame'],'time_s':e['time_s'],'track_id':e['track_id'],'direction':e['direction']} for e in events])
    for name in ['zone_counter.py','confirmation_counter.py']:shutil.copyfile(PROJECT/'detector_factorial_20261029/input'/name,ROOT/'input'/name)
    p={'status':'FROZEN_BEFORE_NEW_LOWRES_EVENT_DIAGNOSIS','created_host_UTC':datetime.now(timezone.utc).isoformat(),
      'source_frame0_scope_inclusive':[8912,10873],'width':2560,'height':1440,'source_fps':25,'inference_stride':5,
      'caches':caches,'IoU_thresholds':[.5,.3],'primary_IoU':.5,'counter':{'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.},
      'perpendicular_ROI':[.34,.75],'reference_tracks':12,'reference_box_samples':len(ref),'reference_raw_prior_admissions':12,
      'reference_is_independent_ground_truth':False,'actual_animal_identity_claimed':False,
      'oracles':['presence_using_reference_center','raw_box_center_assisted_identity','post_confirmed_plus_valid_admitted_center_assisted_identity'],
      'correspondence':'Perframeone-to-one,maxcardinalitythenmaximumtotalIoU;fixedthreshold;tiesflagged.',
      'new_post_admission':'Onlyactualcounteradmissions;currentconfirmedIDmustmatchreference;previousrawmatchsame_referenceandaxiswithin1e-4;unresolvedkept.',
      'primary_case':'S192_rot90_seed26','no_new_hyperparameters_or_crop_search':True,
      'input_sha256':{f.name:sha(f) for f in sorted((ROOT/'input').iterdir()) if f.is_file()},
      'baseline_candidate_sha256':sha(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'),
      'prior15_training_review_sha256':sha(training/'results/final_review.json'),
      'model_forwards':0,'training_updates':0,'board_actions':0,'whole_goal_complete':False}
    save(ROOT/'protocol/audit_v1.json',p);print(json.dumps({'protocol_sha256':sha(ROOT/'protocol/audit_v1.json'),'caches':27,'reference_box_ticks':len(ref),'unique_admissions':12}))
if __name__=='__main__':main()
