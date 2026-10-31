"""Final evidence review; provisional assistant candidates remain excluded from scoring."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from collections import Counter
import argparse,ast,hashlib,json,re,subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='final_review.json');args=parser.parse_args()
    assert Path(args.output).name==args.output and args.output.endswith('.json')
    target=ROOT/'results'/args.output;assert not target.exists()
    selection=load(ROOT/'protocol/selection_v1.json');source=load(ROOT/'input/video_manifest.json');src=Path(source['local_path'])
    assert src.stat().st_size==source['source_bytes']==260358184 and sha(src)==source['source_sha256']=='8210a5bf206dd7f2356bc3d4653b439ab6de12ccfdc8209fe301ac7f02807058'
    assert selection['upstream_source_sha256']==source['source_sha256'] and selection['new_model_prediction_allowed_this_phase'] is False
    adaptations=load(ROOT/'protocol/source_adaptation.json')
    for row in adaptations['files']:
        previous=PROJECT/'overhead_long_session_20261028/tools'/row['file'];current=ROOT/'tools'/row['file']
        assert sha(previous)==row['upstream_sha256'] and sha(current)==row['adapted_sha256']
        assert previous.read_text(encoding='utf-8').replace('/idcoo_research_20261026/overhead_long_session_20261028',
               '/idcoo_research_20261026/overhead_positive_reference_20261028')==current.read_text(encoding='utf-8')
    original=ROOT/'native_review_delivery/results/native_review';native=load(original/'summary.json');admit=load(ROOT/'results/admission_verification.json')
    assert native['source_sha256']==admit['source_sha256']==source['source_sha256']
    assert native['source_frames']==admit['native_frames_counted']==14107 and native['duration_s']==564.28 and native['source_fps']==25
    assert admit['overview_anchor_images']==114 and admit['all_images_decoded']==144 and admit['conservative_quarantine_frames0_inclusive']==[14056,14106]
    strict=load(ROOT/'decode_diagnosis_delivery/results/decode_diagnosis/summary.json')
    assert strict['ffmpeg_exit_code']==183 and strict['strict_decode_passed'] is False and strict['showinfo_frames_before_stop']==14106
    assert sha(ROOT/'decode_diagnosis_delivery/results/decode_diagnosis/strict_ffmpeg.log')==strict['log_sha256']
    packet_path=ROOT/'evidence/source_packet_clock.json';packets=load(packet_path)['packets'];clock=load(ROOT/'evidence/source_packet_clock_summary.json')
    assert sha(packet_path)==clock['raw_packet_metadata_sha256'] and len(packets)==14107
    pts=[int(p['pts']) for p in packets];assert pts==sorted(pts) and len(pts)==len(set(pts))
    histogram=Counter(b-a for a,b in zip(pts,pts[1:]));assert dict(histogram)=={3600:13963,3690:75,3510:68}
    deviation=max(abs((p-pts[0])/90000-i/25) for i,p in enumerate(pts));assert abs(deviation-.007)<1e-9
    focused=ROOT/'focused_delivery/results/focused';focus=load(focused/'summary.json');fverify=load(ROOT/'results/focused_verification.json');fp=ROOT/'protocol/focused_review_v1.json';pf=load(fp)
    assert focus['protocol_sha256']==sha(fp) and focus['models_used'] is False and focus['sample_images']==625 and focus['contact_images']==125
    assert fverify['all_rasters_decoded']==637 and fverify['full_video_decode_frames']==625
    assert [[w['start_frame0'],w['end_frame0_exclusive']] for w in pf['windows']]==[[2375,4375],[5000,5625],[9625,10125]]
    assert max(w['end_frame0_exclusive'] for w in pf['windows'])<14056
    original_visual=load(ROOT/'evidence/overview_visual_review.json');fv=load(ROOT/'evidence/focused_visual_review.json')
    assert original_visual['overview_image_panels_viewed']==114 and original_visual['new_model_predictions']==0
    assert fv['one_Hz_original_pixel_panels_viewed']==125 and fv['reference_witness_panels_in_final_revision']==72
    assert fv['all_625_5Hz_sample_images_individually_viewed'] is False and fv['independent_human_review_pending'] is True
    # Visual interpretation is recorded separately from numeric checks; no script
    # assertion substitutes for physical association or exact body-centre labels.
    draft_path=ROOT/'reference/assistant_event_draft_v1.json';draft=load(draft_path);freeze=load(ROOT/'reference/freeze_record.json')
    assert sha(draft_path)==freeze['sha256']=='35a6e0d5b4454cc2a6e6057c750f84cd6cf5d02f5d3fc73c4c1683c80b149bb7'
    assert draft['source_sha256']==source['source_sha256'] and draft['annotation_authority']=='assistant_provisional_native_visual_review'
    assert draft['rules_sha256']==sha(ROOT/draft['rules_path']) and draft['focus_protocol_sha256']==sha(fp)
    # This file was updated after the draft only to record a separate marker
    # figure check. Preserve the draft's original visual record as a snapshot.
    visual_snapshot=ROOT/'reference/focused_visual_review_at_freeze_exact.json'
    if not visual_snapshot.exists():
        before=dict(fv);before.pop('representative_overviews_viewed');before.pop('manual_target_marker_visual_check')
        # Invert only the two subsequently added lines without reformatting the
        # original hand-written JSON. The frozen SHA256 must match exactly.
        content=''.join(line for line in (ROOT/'evidence/focused_visual_review.json').read_text(encoding='utf-8').splitlines(keepends=True)
                        if not line.lstrip().startswith(('"representative_overviews_viewed":','"manual_target_marker_visual_check":')))
        assert json.loads(content)==before
        if hashlib.sha256(content.encode()).hexdigest()!=draft['visual_review_sha256']:
            raise AssertionError('Cannot reconstruct exact original visual record; do not rewrite the frozen draft')
        visual_snapshot.write_bytes(content.encode('utf-8'))
    assert sha(visual_snapshot)==draft['visual_review_sha256']
    assert draft['eligible_for_final_scoring'] is False and draft['independent_human_confirmation_received'] is False
    assert draft['exact_event_timestamps_finalized'] is False and draft['new_model_predictions_seen'] is False
    assert len(draft['candidates'])==draft['provisional_downward_candidates']==12
    assert Counter(r['window'] for r in draft['candidates'])=={'group_passage':11,'late_single':1}
    assert [r['reference_ID'] for r in draft['candidates']]==[f'R{i:02d}' for i in range(1,13)]
    witness=load(ROOT/'results/draft_witnesses_v2/manifest.json');old=load(ROOT/'results/draft_witnesses/manifest.json')
    assert sha(ROOT/'results/draft_witnesses_v2/manifest.json')==draft['witness_manifest_sha256']
    for r,w,before in zip(draft['candidates'],witness['candidates'],old['candidates']):
        assert r['direction']=='A->B' and r['exact_event_frame0'] is r['exact_event_time_s'] is None
        assert r['independently_human_accepted'] is False and r['review_status']=='pending_independent_review'
        A=r['origin_evidence_frame0'];B=r['destination_evidence_frame0'];assert A[-1]<B[0]
        for triplet in [A,B]:assert triplet==list(range(triplet[0],triplet[0]+15,5))
        assert r['source_witnesses']==w['witnesses'] and sha(ROOT/r['witness_contact'])==r['witness_contact_sha256']
        for sample in r['source_witnesses']:
            assert sha(ROOT/sample['source_image'])==sample['source_sha256'] and sample['manual_centre_verified'] is False
        if r['reference_ID'] not in ['R01','R02','R03','R04']:assert w['contact_sha256']==before['contact_sha256']
    template=ROOT/'reference/independent_review_TEMPLATE.json';t=load(template)
    assert t['assistant_draft_sha256']==sha(draft_path) and t['source_sha256']==source['source_sha256']
    assert t['new_clip_count_confirmed'] is None and t['complete_event_list_accepted'] is False and t['eligible_for_scoring'] is False
    assert all(r['accepted'] is r['final_event_frame0'] is None for r in t['candidate_reviews'])
    bundle=load(ROOT/'results/review_bundle/manifest.json');marked=load(ROOT/'results/review_bundle/marked_overview_v2.json')
    assert bundle['template_sha256']==sha(template)
    assert bundle['guide_sha256']==sha(ROOT/'results/review_bundle/guide_before_target_markers.md')==marked['pre_marker_guide_sha256']
    line_repair=load(ROOT/'results/review_bundle/guide_lineending_repair.json')
    assert marked['current_guide_sha256']==line_repair['before_sha256']==sha(ROOT/'results/review_bundle/guide_before_lineending_fix.md')
    assert line_repair['after_sha256']==sha(ROOT/'逐事件草案复核入口.md') and marked['points_are_not_measured_torso_centres']
    assert b'\r' not in (ROOT/'逐事件草案复核入口.md').read_bytes() and line_repair['table_rows_contiguous']==12
    assert sha(Path(marked['overview_path']))==marked['overview_sha256'] and marked['candidate_count_or_event_rules_changed'] is False
    media=[]
    for path,n,width,height in [(original/native['review_movie'],2822,480,700),*[(ROOT/'focused_delivery'/w['movie'],w['sample_frames'],480,700) for w in focus['windows']]]:
        proc=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,r_frame_rate','-of','json',str(path)],capture_output=True,check=True)
        assert not proc.stderr;v=json.loads(proc.stdout)['streams'][0]
        assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(width,height,'5/1',n)
        media.append({'path':str(path),'sha256':sha(path),'frames_full_decoded':n})
    assert sum(r['frames_full_decoded'] for r in media)==3447
    images=[]
    folders=[original,focused,ROOT/'results/draft_witnesses',ROOT/'results/draft_witnesses_v2',ROOT/'results/review_bundle']
    for folder in folders:
        for path in sorted(folder.rglob('*')):
            if path.suffix.lower() not in ['.jpg','.png']:continue
            with Image.open(path) as im:im.load();size=im.size
            images.append({'path':str(path),'sha256':sha(path),'size':size})
    assert len(images)==807
    for job,file in [('130333','admission_completion.txt'),('130336','focused_status_03.txt')]:
        text=(ROOT/'evidence'/file).read_text(encoding='utf-8');line=next(r for r in text.splitlines() if r.split() and r.split()[0]==job)
        assert line.split()[3:5]==['COMPLETED','0:0']
    candidate=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';c=load(candidate)
    assert sha(candidate)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b' and c['predicted_down']==c['human_total']==12
    assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
    assert sha(PROJECT/'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json')=='26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac'
    # Scan only actual compute/source preparation files, not unrelated tools.
    imports=[]
    for name in ['prepare_native_review.py','diagnose_decode.py','render_focused.py']:
        tree=ast.parse((ROOT/'tools'/name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(r.name for r in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module or '')
    assert not any(n.startswith(('ultralytics','torch','onnxruntime')) for n in imports)
    docs=[ROOT/'计划与验收.md',ROOT/'新长片通行参考草案与下一步.md',ROOT/'Review与当前状态.md',ROOT/'逐事件草案复核入口.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
    result={'status':'NEW_LONG_SOURCE_ADMISSION_AND_FROZEN_ASSISTANT_EVENT_DRAFT_REVIEWED_NOT_SCORING_GT',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'source_sha256':source['source_sha256'],'source_bytes':260358184,
            'source_frames_counted':14107,'strict_decoder_failure_retained':183,'conservative_source_tail_quarantine':[14056,14106],
            'source_packet_clocks_checked':14107,'maximum_nominal_clock_deviation_s':deviation,'overview_anchor_panels_viewed':114,
            'focused_windows':3,'focused_5Hz_images_decoded':625,'focused_1Hz_panels_viewed':125,'final_A_B_witness_panels_viewed':72,
            'raster_files_full_decoded':807,'preview_videos_full_decoded':4,'preview_video_frames_full_decoded':3447,
            'source_adaptations_only_ROOT_literals':True,'draft_sha256':sha(draft_path),'local_reference_candidates':12,
            'guide_Markdown_table_lineendings_verified':True,
            'exact_visual_snapshot_sha256_bound_to_draft':sha(visual_snapshot),'original_frozen_draft_rewritten':False,
            'group_window_candidates':11,'late_window_candidates':1,'noncow_person_controls':2,
            'new_reference_authority':'assistant_provisional_native_visual_review','independent_human_confirmation_received':False,
            'exact_event_timestamps_finalized':False,'eligible_for_final_scoring':False,'completion_intervals_are_review_targets':True,
            'no_prediction_based_reference_labels':True,'new_model_forward_calls':0,'new_training_updates':0,
            'current_different_clip_user_confirmed12_preserved':True,'current29_condition_catalog_unchanged':True,
            'real_cow_bidirectional_coverage_established':False,'browser_playback_verified':False,'FPGA_execution_verified':False,
            'completed_Slurm_jobs':['130333','130336'],'local_links_checked':len(links),'images':images,'media':media,
            'documents':[{'path':str(p),'sha256':sha(p)} for p in docs],
            'evidence_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'results/admission_verification.json',ROOT/'results/focused_verification.json',
                ROOT/'evidence/source_packet_clock_summary.json',ROOT/'evidence/overview_visual_review.json',ROOT/'evidence/focused_visual_review.json',
                draft_path,ROOT/'reference/freeze_record.json',template,ROOT/'results/review_bundle/marked_overview_v2.json',
                visual_snapshot,
                ROOT/'results/review_bundle/guide_lineending_repair.json',
                ROOT/'protocol/selection_v1.json',ROOT/'protocol/focused_review_v1.json',ROOT/'protocol/manual_reference_rules_v1.json']},
            'previous_goal_turn_classification':'progress: cow-present ordinary overhead long-video source obtained and native source limitations diagnosed',
            'this_goal_turn_classification':'progress: full native admission, focused source review, provisional12-event reference and independent review materials created before new predictions',
            'next_priority':'Refine exact event times from original pixels and obtain independent acceptance; then frozen-model paired scoring and board validation',
            'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['images','media','documents','evidence_hashes']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
