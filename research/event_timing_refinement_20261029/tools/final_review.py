"""Recheck actual conditional timing evidence, preserving annotation authority limits."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from collections import Counter
from itertools import product
import hashlib,json,re
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
UP=PROJECT/'overhead_positive_reference_20261028'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    manual_path=ROOT/'input/manual_center_ranges_v1.json';manual=load(manual_path)
    timing_path=ROOT/'reference/assistant_event_timing_v2.json';timing=load(timing_path);freeze=load(ROOT/'reference/freeze_record.json')
    verification=load(ROOT/'results/independent_verification.json');contacts_path=ROOT/'results/native_timing/manifest.json';contacts=load(contacts_path)
    old_path=UP/'reference/assistant_event_draft_v1.json';old=load(old_path)
    assert sha(old_path)==manual['original_draft_sha256']==timing['original_draft_sha256']=='35a6e0d5b4454cc2a6e6057c750f84cd6cf5d02f5d3fc73c4c1683c80b149bb7'
    assert sha(timing_path)==freeze['timing_draft_sha256']==verification['timing_draft_sha256']=='188079a8754c495485c284b8e0a29519181100033166fe953e9f7547c600dc6a'
    assert sha(manual_path)==freeze['manual_input_sha256']==verification['manual_input_sha256']==timing['manual_input_sha256']
    assert sha(contacts_path)==timing['native_contact_manifest_sha256']
    assert manual['source_sha256']==timing['source_sha256']==old['source_sha256']=='8210a5bf206dd7f2356bc3d4653b439ab6de12ccfdc8209fe301ac7f02807058'
    origin_manifest=load(UP/'focused_delivery/results/focused/summary.json')
    origin_rows={(w['name'],r['frame0']):r for w in origin_manifest['windows'] for r in w['samples']}
    rasters=[];source_records=[];panel_frames=[]
    for row in contacts['sequences']:
        prior=next(r for r in old['candidates'] if r['reference_ID']==row['reference_ID'])
        start,end=prior['destination_transition_review_frame0_interval']
        assert row['expanded_source_frames0']==list(range(start-25,end+11,5))
        for r in row['source_rows']:
            original=origin_rows[(row['window'],r['frame0'])];p=Path(r['source_path'])
            assert p==UP/'focused_delivery'/original['file'] and sha(p)==r['source_sha256']==original['sha256']
            assert r['native_crop_y_range']==[250,1400]
            with Image.open(p) as im:assert im.size==(1050,1440)
            panel_frames.append((row['reference_ID'],r['frame0']));source_records.append({'path':str(p),'sha256':sha(p)})
        for r in row['pages']:
            p=Path(r['path']);assert sha(p)==r['sha256']
            with Image.open(p) as im:im.load();assert im.size==(1360,1710)
            rasters.append({'path':str(p),'sha256':sha(p),'size':[1360,1710]})
    assert len(panel_frames)==172 and len(rasters)==23 and len(set(panel_frames))==172
    samples=0;scenarios=0;labels=Counter();widths=Counter();outside=[];values_total=0
    for event,entry in zip(timing['events'],manual['rows']):
        assert event['reference_ID']==entry['reference_ID']
        prior=next(r for r in old['candidates'] if r['reference_ID']==event['reference_ID'])
        assert event['direction']==prior['direction']=='A->B' and event['origin_evidence_retained_frame0']==prior['origin_evidence_frame0']
        assert event['independently_accepted'] is False and event['exact_human_accepted_event_frame0'] is None
        sequence=[]
        for row,(frame,lo,hi) in zip(event['observations'],entry['samples']):
            assert row['frame0']==frame and row['native_centre_y_working_range']==[lo,hi]
            assert (event['reference_ID'],frame) in set(panel_frames)
            label='B' if lo>864 else 'N' if hi<=864 else 'U';assert label==row['state']
            sequence.append(label);labels[label]+=1;samples+=1
        assert sequence[0]=='N' and sequence[-3:]==['B']*3
        indices=[i for i,x in enumerate(sequence) if x=='U'];event_values=set()
        for assignment in product('NB',repeat=len(indices)):
            resolved=sequence.copy()
            for i,x in zip(indices,assignment):resolved[i]=x
            first=''.join(resolved).index('BBB');event_values.add(entry['samples'][first+2][0]);scenarios+=1
        assert sorted(event_values)==event['possible_completion_frames0_under_manual_ranges']
        assert event['completion_frame0_hull']==[min(event_values),max(event_values)]
        assert event['completion_hull_width_s']==(max(event_values)-min(event_values))/25
        widths[event['completion_hull_width_s']]+=1;values_total+=len(event_values)
        if min(event_values)<prior['destination_transition_review_frame0_interval'][0] or max(event_values)>prior['destination_transition_review_frame0_interval'][1]:outside.append(event['reference_ID'])
    assert (samples,scenarios,values_total)==(68,40,32) and labels=={'N':12,'U':20,'B':36}
    assert dict(widths)=={.4:8,.2:4} and outside==['R03'] and timing['exact_single_grid_times']==0
    for key in ['independent_human_acceptance_received','eligible_for_final_scoring','new_model_predictions_or_training','whole_goal_complete']:assert timing[key] is False
    assert verification['binary_scenarios_checked']==40 and verification['old_review_target_exceeded_by']==['R03']
    visual_path=ROOT/'evidence/visual_review.json';visual=load(visual_path)
    assert visual['native_ruler_pages_viewed']==23 and visual['native_ruler_panels_viewed']==172
    assert visual['illustration_visual_acceptance'].startswith('PASS') and visual['eligible_for_final_scoring'] is False
    figure=ROOT/visual['illustration_path'];assert sha(figure)==verification['plot_sha256']
    with Image.open(figure) as im:im.load();assert im.size==(1380,1500)
    rasters.append({'path':str(figure),'sha256':sha(figure),'size':[1380,1500]});assert len(rasters)==24
    source12=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';candidate=load(source12)
    assert sha(source12)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b' and candidate['human_total']==candidate['predicted_down']==12
    assert sha(Path(candidate['checkpoint_path']))==candidate['checkpoint_sha256']
    assert sha(PROJECT/'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json')=='26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac'
    docs=[ROOT/'计划与验收.md',ROOT/'完成时间细化与复核重点.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for p in docs:
        text=p.read_text(encoding='utf-8');assert '\ufffd' not in text and '\r\r' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
    main=(ROOT/'完成时间细化与复核重点.md').read_text(encoding='utf-8').splitlines();header=next(i for i,l in enumerate(main) if l.startswith('| 候选 |'))
    assert main[header+1].startswith('| ---') and all(main[header+i].startswith('| [R') for i in range(2,14))
    result={'status':'TWELVE_CONDITIONAL_EVENT_TIMING_SETS_AND_NATIVE_PIXEL_LIMITS_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
            'original_draft_sha256_preserved':sha(old_path),'refined_timing_draft_sha256':sha(timing_path),'manual_input_sha256':sha(manual_path),
            'source_sha256':timing['source_sha256'],'native_ruler_pages_visually_reviewed':23,'native_ruler_panels_visually_reviewed':172,
            'manual_working_range_rows':68,'region_labels':dict(labels),'binary_scenarios_independently_checked':40,'conditional_timing_values':32,
            'conditional_width_histogram_seconds':dict(widths),'single_exact_grid_times':0,'old_review_target_exceeded_by':['R03'],
            'manual_ranges_are_calibrated_measurements':False,'independent_human_acceptance_received':False,'eligible_for_final_scoring':False,
            'new_model_forwards':0,'new_training_updates':0,'new_network_downloads':0,'new_Slurm_jobs':0,
            'raster_files_full_decoded':24,'new_different_clip_user_confirmed12_preserved':True,'current_29_condition_catalog_unchanged':True,
            'FPGA_execution_verified':False,'browser_playback_verified':False,'local_links_checked':len(links),
            'documents':[{'path':str(p),'sha256':sha(p)} for p in docs],'source_records':source_records,'rasters':rasters,
            'evidence_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [manual_path,timing_path,contacts_path,visual_path,
                ROOT/'reference/freeze_record.json',ROOT/'results/independent_verification.json']},
            'previous_goal_turn_classification':'progress: source-native draft12 and review evidence frozen before model outputs',
            'this_goal_turn_classification':'progress: native ruler review and68 provisional centre ranges narrowed timing sets, exposing R03 beyond prior review target',
            'next_priority':'Independent event/reference acceptance; fixed-model paired replay with interval uncertainty retained, plus board evidence when available',
            'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_bytes((json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
    print(json.dumps({k:v for k,v in result.items() if k not in ['documents','source_records','rasters','evidence_hashes']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
