from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    p=load(ROOT/'protocol/duplicate_v1.json');a=load(ROOT/'results/audit.json');v=load(ROOT/'results/independent_verification.json')
    assert a['protocol_sha256']==v['protocol_sha256']==sha(ROOT/'protocol/duplicate_v1.json')
    assert v['audit_sha256']==sha(ROOT/'results/audit.json') and v['conditions']==6 and v['condition_frames']==2874
    assert v['high_overlap_pair_frames']==len(a['all_high_overlap_pairs'])==75 and v['episode_count']==len(a['episodes'])==48
    assert v['all_IoU_matrix_entries_recomputed']==88101 and v['maximum_pair_IoU_difference']==0.
    sources={}
    for row in p['input_files']:
        assert sha(row['path'])==row['sha256'];sources[row['path']]=row['sha256']
    for c in p['conditions']:
        for row in c['files'].values():assert sha(row['path'])==row['sha256'];sources[row['path']]=row['sha256']
    assert len(sources)==30
    rows=a['conditions'];assert [r['frames_with_high_overlap_ID_pairs'] for r in rows]==[1,2,2,22,22,23]
    assert [r['high_overlap_pair_frames'] for r in rows]==[2,3,3,22,22,23]
    assert [r['GT_primary_supported_pair_frames'] for r in rows]==[1,1,1,13,13,13]
    assert [r['GT_sensitivity_supported_pair_frames'] for r in rows]==[1,1,1,22,22,23]
    assert [r['direct_raw_duplicate_pair_frames'] for r in rows]==[0,0,0,9,9,10]
    assert [a['raw_cache_metrics'][m]['frames_with_raw_overlap_pairs'] for m in ['generic','pilot']]==[40,93]
    assert [a['raw_cache_metrics'][m]['raw_overlap_pair_frames'] for m in ['generic','pilot']]==[50,101]
    assert all(not e['both_IDs_emit_event_in_episode'] for e in a['episodes'])
    known=a['known_case_frame120'];assert known['frame']==120 and known['track_IDs']==[1,8]
    assert known['sensitivity_same_GT'] and not known['primary_same_GT']
    assert abs(known['raw_link']['raw_pair_IoU']-.8955011970160278)<1e-12 and known['direct_raw_duplicate_pair']
    q=load(ROOT/'protocol/render_v1.json');negative=q['special_cases'][1]
    assert negative['frame']==323 and negative['GT_a']['ID']==7 and negative['GT_b']['ID']==16
    assert negative['GT_a']['IoU']>.5 and negative['GT_b']['IoU']>.5 and not negative['sensitivity_same_GT']
    render=load(ROOT/'results/render_v2_local_verification.json');assert render['manual_visual_QA']=='PASS'
    assert render['audit_sha256']==sha(ROOT/'results/audit.json') and render['files']==19 and render['raster_full_decodes']==13
    assert render['render_record_sha256']==sha(ROOT/'render_v2_delivery/results/render_record_v2.json')
    assert render['native_frames_visually_inspected']==4 and render['representative_panels_visually_inspected']==6 and render['special_panels_visually_inspected']==2
    for row in render['visual_evidence_files']:
        f=ROOT/'render_v2_delivery/results/figures_v2'/row['file'];assert sha(f)==row['sha256']
        with Image.open(f) as image:image.load()
    for folder in ['render_delivery','render_v2_delivery']:
        manifest=load(ROOT/folder/'delivery_manifest.json');assert len(manifest)==19
        for row in manifest:
            f=ROOT/folder/row['path'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
    correction=load(ROOT/'results/layout_correction_record.json');assert not correction['audit_changed'] and not correction['case_selection_or_chart_data_changed']
    assert correction['original_source_sha256']==sha(ROOT/'tools/render.py') and correction['corrected_source_sha256']==sha(ROOT/'tools/render_v2.py')
    assert sha(ROOT/'tools/render_v2.py')==sha(ROOT/'render_v2_delivery/tools/render_v2.py')
    original=load(PROJECT/'external_method_regression_20261028/results/final_review.json')
    assert original['main_official_TP']==[6,6,6,6] and original['main_pilot_TP']==[2,2,2,3]
    assert original['summary_sha256']==p['previous_summary_sha256']
    current=load(PROJECT/'lost_recovery_20261028/results/catalog_intake_verification.json')
    assert current['conditions']==29 and not current['source_accuracy_computed']
    status=(ROOT/'results/final_status.txt').read_text(encoding='utf-8')
    for job in [130297,130299]:
        line=next(s for s in status.splitlines() if s.startswith(str(job)+'|'));assert '|COMPLETED|0:0|' in line and '|4gpu|2|4G|' in line and 'gres/gpu' not in line
    docs=[ROOT/'计划与验收.md',ROOT/'双ID冗余审计与研究决策.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            link=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',link):
                line=re.match(r'^(.*):(\d+)$',link);f=Path(line[1] if line else link);assert f.exists(),f
                if line:assert 1<=int(line[2])<=len(f.read_text(encoding='utf-8').splitlines())
                links.append(link)
    result={'status':'SIX_OUTPUT_REDUNDANCY_DIAGNOSTICS_RAW_BOX_LINKS_AND_PHYSICAL_ID_LIMITS_REVIEWED',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/duplicate_v1.json'),
      'audit_sha256':sha(ROOT/'results/audit.json'),'conditions':6,'condition_frames':2874,
      'candidate_pair_frames':75,'contiguous_episodes':48,'independent_IoU_matrix_elements':88101,
      'source_artifact_hashes_reverified':30,'candidate_frame_counts':[1,2,2,22,22,23],
      'candidate_pair_frame_counts':[2,3,3,22,22,23],'primary_geometric_support_counts':[1,1,1,13,13,13],
      'sensitivity_geometric_support_counts':[1,1,1,22,22,23],'raw_direct_link_counts':[0,0,0,9,9,10],
      'known_case_raw_pair_IoU':known['raw_link']['raw_pair_IoU'],'distinct_two_cow_counterexample_preserved':True,
      'event_and_geometric_track_metrics_separate':True,'source_predictions_and_scores_changed':False,
      'final_render_delivery_files':19,'old_layout_delivery_retained_separately':True,
      'final_rasters_full_decoded':13,'native_frames_viewed':4,'representative_panels_viewed':6,'special_panels_viewed':2,
      'plot_data_and_visual_QA_passed':True,'caption_clipping_corrected_without_data_change':True,
      'local_links_checked':len(links),'documents':[{'path':str(d),'sha256':sha(d)} for d in docs],
      'physical_duplicate_rate_established':False,'ID_merging_or_new_thresholds_implemented':False,
      'new_independent_reference_received':False,'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,
      'previous_goal_turn_classification':'progress: fixed external methods evaluated and overlapping-ID case observed',
      'this_goal_turn_classification':'progress: all frozen outputs audited; raw duplicate evidence and distinct-cow counterexample verified',
      'next_priority':'Independent human event reference, new sessions and board validation before further model selection',
      'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='documents'}))
if __name__=='__main__':main()
