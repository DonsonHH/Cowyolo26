"""Enumerate discrete completion times under the declared provisional centre ranges."""
from pathlib import Path
from itertools import product
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    path=ROOT/'input/manual_center_ranges_v1.json';manual=load(path);contacts=load(ROOT/'results/native_timing/manifest.json')
    old_path=PROJECT/'overhead_positive_reference_20261028/reference/assistant_event_draft_v1.json';old=load(old_path)
    assert sha(old_path)==manual['original_draft_sha256']==contacts['original_draft_sha256']
    assert manual['gate_y']==864 and manual['new_model_predictions']==0
    allrows=[];sample_count=0;total_scenarios=0
    for row in manual['rows']:
        ID=row['reference_ID'];sequence=next(r for r in contacts['sequences'] if r['reference_ID']==ID)
        support={r['frame0']:r for r in sequence['source_rows']};prior=next(r for r in old['candidates'] if r['reference_ID']==ID)
        obs=[]
        for frame,lo,hi in row['samples']:
            assert frame in support and 0<=lo<=hi<=1440
            source=Path(support[frame]['source_path']);assert sha(source)==support[frame]['source_sha256']
            state='B' if lo>864 else 'N' if hi<=864 else 'U'
            obs.append({'frame0':frame,'nominal_time_s':frame/25,'native_centre_y_working_range':[lo,hi],'state':state,
                        'source_image_path':str(source),'source_sha256':sha(source)})
        assert obs[0]['state']=='N' and all(b['frame0']-a['frame0']==5 for a,b in zip(obs,obs[1:]))
        assert [r['state'] for r in obs[-3:]]==['B']*3
        unknown=[i for i,r in enumerate(obs) if r['state']=='U'];scenarios=[];events=set()
        for choice in product([False,True],repeat=len(unknown)):
            membership={i:val for i,val in zip(unknown,choice)};run=0;event=None;states=[]
            for i,r in enumerate(obs):
                inside=r['state']=='B' or (r['state']=='U' and membership[i]);states.append('B' if inside else 'N')
                run=run+1 if inside else 0
                if run==3 and event is None:event=r['frame0']
            assert event is not None;events.add(event);scenarios.append({'uncertain_samples_as_B':list(choice),'resolved_states':states,'first_three_B_completion_frame0':event})
        values=sorted(events);oldrange=prior['destination_transition_review_frame0_interval']
        allrows.append({'reference_ID':ID,'window':prior['window'],'direction':prior['direction'],'observations':obs,
                        'origin_evidence_retained_frame0':prior['origin_evidence_frame0'],'note':row['note'],
                        'uncertain_samples':len(unknown),'scenarios':scenarios,'possible_completion_frames0_under_manual_ranges':values,
                        'possible_nominal_times_s':[f/25 for f in values],'completion_frame0_hull':[min(values),max(values)],
                        'completion_hull_width_s':(max(values)-min(values))/25,'single_grid_time_under_working_ranges':len(values)==1,
                        'previous_review_target_frame0':oldrange,'all_grid_candidates_inside_previous_review_target':min(values)>=oldrange[0] and max(values)<=oldrange[1],
                        'exact_human_accepted_event_frame0':None,'independently_accepted':False,
                        'interpretation':'Conditional on assistant working pixel intervals and the prior visual association; not certified measurement error or accepted GT.'})
        sample_count+=len(obs);total_scenarios+=len(scenarios)
    assert len(allrows)==12 and sample_count==68 and total_scenarios==40
    result={'status':'PROVISIONAL_EVENT_TIMING_SETS_DERIVED_FROM_MANUAL_PIXEL_RANGES','created_UTC':datetime.now(timezone.utc).isoformat(),
            'source_sha256':manual['source_sha256'],'original_draft_sha256':sha(old_path),'manual_input_sha256':sha(path),
            'native_contact_manifest_sha256':sha(ROOT/'results/native_timing/manifest.json'),
            'annotation_authority':manual['annotation_authority'],'native_pixel_gate_y':864,'stable_samples':3,'source_stride':5,'nominal_FPS':25,
            'candidate_count':12,'pixel_working_range_rows':sample_count,'uncertain_sample_rows':sum(r['uncertain_samples'] for r in allrows),
            'resolved_binary_scenarios':total_scenarios,'candidate_timing_values_total':sum(len(r['possible_completion_frames0_under_manual_ranges']) for r in allrows),
            'events':allrows,'exact_single_grid_times':sum(r['single_grid_time_under_working_ranges'] for r in allrows),
            'intervals_are_conditional_working_ranges_not_confidence_intervals':True,'all_exact_human_event_frames_unfilled':True,
            'independent_human_acceptance_received':False,'eligible_for_final_scoring':False,'new_model_predictions_or_training':False,
            'previous_confirmed12_source_clip_unchanged':True,'whole_goal_complete':False}
    out=ROOT/'reference';out.mkdir(exist_ok=False);dest=out/'assistant_event_timing_v2.json';dest.write_bytes((json.dumps(result,indent=2)+'\n').encode())
    (out/'freeze_record.json').write_bytes((json.dumps({'timing_draft_sha256':sha(dest),'manual_input_sha256':sha(path),
        'original_draft_sha256':sha(old_path),'eligible_for_final_scoring':False},indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k!='events'}),flush=True)
    print(json.dumps([{'ID':r['reference_ID'],'frames0':r['possible_completion_frames0_under_manual_ranges'],'width_s':r['completion_hull_width_s']} for r in allrows]),flush=True)
if __name__=='__main__':main()
