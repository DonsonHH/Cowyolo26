"""Evidence-bound review of ordinary overhead long-video admission; no model or truth creation."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from collections import Counter
import hashlib,json,re,subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

def verify_source(folder,expected_size):
    m=load(ROOT/'input'/folder/'manifest.json');src=Path(m['local_path'])
    assert src.stat().st_size==m['source_bytes']==expected_size and sha(src)==m['source_sha256']
    digest=hashlib.sha256();offset=0;chunks=[]
    for r in m['range_reads']:
        f=ROOT/'input'/folder/r['file'];assert sha(f)==r['sha256'] and f.stat().st_size==r['bytes']
        assert r['end_exclusive']-r['start']==r['bytes'] and r['object_bytes']==expected_size
        assert r['Content-Range']==f"bytes {r['start']}-{r['end_exclusive']-1}/{expected_size}"
        if r['file'].startswith('part_'):
            assert r['start']==offset;digest.update(f.read_bytes());offset=r['end_exclusive'];chunks.append(r)
    assert offset==expected_size and digest.hexdigest()==m['source_sha256'] and len(chunks)==63
    return m

def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    selection=load(ROOT/'protocol/selection_v1.json');positive=load(ROOT/'protocol/positive_candidate_v1.json')
    directory=ROOT/'evidence/camera1_2023Aug17_listing.json';cat=load(directory)
    assert len(cat['videos'])==7 and sha(directory)==selection['directory_catalog_sha256']
    assert sha(ROOT/'evidence/camera1_2023Aug17_listing.html')==cat['sha256']
    assert cat['videos'][0]==selection['selected'] and positive['selected']['filename']=='2023-08-17T13-25-38.mp4'
    first=verify_source('video_ranges',260161576);second=verify_source('positive_video_ranges',260358184)
    assert first['protocol_sha256']==sha(ROOT/'protocol/selection_v1.json')
    assert second['protocol_sha256']==sha(ROOT/'protocol/positive_candidate_v1.json')
    assert first['source_sha256']=='482a7d530bb3ab4f9df192fe8ecbc5a3b44f5e46d5ec5877f353d7465ea87b59'
    native=ROOT/'native_review_delivery/results/native_review';s=load(native/'summary.json');v=load(ROOT/'results/native_delivery_verification.json')
    assert s['source_frames']==v['source_frames']==15756 and s['source_fps']==25 and s['duration_s']==630.24
    assert len(s['overview_snapshots'])==128 and len(s['native_30s_anchors'])==23 and len(s['overview_pages'])==11
    assert s['review_movie_frames']==s['review_movie_complete_decode_frames']==v['review_movie_full_decoded_frames']==3152
    assert s['review_movie_duration_s']==630.4 and sha(native/s['review_movie'])==s['review_movie_sha256']
    for row in [*s['overview_snapshots'],*s['native_30s_anchors'],*s['overview_pages']]:assert sha(native/row['file'])==row['sha256']
    frames=[r['frame0'] for r in s['overview_snapshots']];assert frames==sorted(set([*range(0,15756,125),15755]))
    packets=load(ROOT/'evidence/source_packet_clock.json')['packets'];clock=load(ROOT/'evidence/source_packet_clock_summary.json')
    assert len(packets)==clock['packets']==15756
    pts=[int(r['pts']) for r in packets];assert pts==sorted(pts) and len(pts)==len(set(pts))
    histogram=Counter(b-a for a,b in zip(pts,pts[1:]));assert dict(histogram)=={int(k):val for k,val in clock['display_tick_delta_histogram'].items()}
    assert dict(histogram)=={3600:15624,3690:69,3510:62}
    error=max(abs((p-pts[0])/90000-i/25) for i,p in enumerate(pts));assert abs(error-.007)<1e-9 and abs(error-clock['maximum_relative_frame_clock_deviation_s'])<1e-12
    strict=load(ROOT/'decode_diagnosis_delivery/results/decode_diagnosis/summary.json')
    assert strict['ffmpeg_exit_code']==183 and strict['strict_decode_passed'] is False and strict['showinfo_frames_before_stop']==15755
    assert sha(ROOT/'decode_diagnosis_delivery/results/decode_diagnosis/strict_ffmpeg.log')==strict['log_sha256']
    limit=load(ROOT/'evidence/source_decode_limit.json');assert limit['conservative_quarantine_frames0_inclusive']==[15705,15755]
    assert limit['exact_corrupt_frame_certified'] is False and limit['full_video_clean_bitstream'] is False
    keys=[i for i,p in enumerate(packets) if 'K' in p['flags']];context=limit['first_error']['latest_prior_showinfo']['output_frame0']
    assert max(k for k in keys if k<=context)==15705 and keys[-1]==15755
    raw_probe=load(ROOT/'input/next_file_probes/manifest.json');probe=load(ROOT/'next_native_probes_delivery/results/next_native_probes/summary.json')
    assert len(raw_probe['files'])==6 and raw_probe['successful_HTTP_bytes']==probe['HTTP_bytes']==88080396<96*1024*1024
    assert raw_probe['protocol_sha256']==probe['protocol_sha256']==sha(ROOT/'protocol/next_file_probe_v1.json')
    assert sha(ROOT/'next_probes_input.tar')==probe['input_archive_sha256']
    for item in raw_probe['files']:
        assert [r['fraction'] for r in item['range_reads'] if 'fraction' in r]==[.25,.5,.75]
        for r in item['range_reads']:assert sha(ROOT/r['file'])==r['sha256'] and (ROOT/r['file']).stat().st_size==r['bytes']
        if item['filename']==positive['selected']['filename']:
            assert item['source_object_bytes']==second['source_bytes']
            with Path(second['local_path']).open('rb') as complete:
                for r in item['range_reads']:
                    complete.seek(r['start']);block=complete.read(r['bytes'])
                    assert len(block)==r['bytes'] and hashlib.sha256(block).hexdigest()==r['sha256']
    assert len(probe['probes'])==18 and sum(r['native_still_decoded'] for r in probe['probes'])==11
    probe_base=ROOT/'next_native_probes_delivery/results/next_native_probes'
    for r in probe['probes']:
        assert sha(probe_base/r['log'])==r['log_sha256']
        if r['native_still_decoded']:assert sha(probe_base/r['file'])==r['image_sha256']
    images=[]
    for folder in [native,probe_base]:
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() not in ['.jpg','.png']:continue
            with Image.open(p) as im:im.load();size=im.size
            images.append({'path':str(p),'sha256':sha(p),'size':size})
    assert len(images)==174
    native_visual=load(ROOT/'evidence/initial_native_visual_review.json');probe_visual=load(ROOT/'evidence/next_probe_visual_review.json')
    assert native_visual['overview_anchor_frames_viewed']==128 and native_visual['full_clip_total_zero_certified'] is False
    assert probe_visual['native_images_visually_reviewed']==11 and probe_visual['failed_probe_panels']==7
    assert probe_visual['positive_observation']['source_filename']==positive['selected']['filename']
    assert positive['positive_native_visual_review_sha256']==sha(ROOT/'evidence/next_probe_visual_review.json')
    assert positive['selection_is_random_unseen_test'] is False and positive['whole_source_validation_pending'] is True
    # Completion states belong to wrappers; strict FFmpeg exit183 remains a failure.
    statuses=[('130319','native_status_03.txt'),('130320','decode_status_01.txt'),('130326','probes_status_01.txt')]
    for job,filename in statuses:
        text=(ROOT/'evidence'/filename).read_text(encoding='utf-8')
        line=next(line for line in text.splitlines() if line.split() and line.split()[0]==job)
        assert line.split()[3:5]==['COMPLETED','0:0']
    candidate=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'
    assert sha(candidate)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
    c=load(candidate);assert c['human_total']==c['predicted_down']==12 and c['absolute_total_error']==0
    assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
    assert sha(PROJECT/'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json')=='26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac'
    format_proc=subprocess.run(['ffprobe','-v','error','-show_entries','format=format_name,format_long_name,start_time,duration',
                               '-of','json',first['local_path']],capture_output=True,check=True)
    format_value=json.loads(format_proc.stdout);assert format_value['format']['format_name']=='mpeg'
    format_path=ROOT/'evidence/source_format_metadata.json'
    if not format_path.exists():format_path.write_bytes(format_proc.stdout)
    else:assert load(format_path)==format_value
    docs=[ROOT/'计划与验收.md',ROOT/'普通俯视长视频筛选与下一步.md',ROOT/'Review与当前状态.md',PROJECT/'研究进度.md',
          PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
    result={'status':'ORDINARY_LONG_VIDEO_NATIVE_ADMISSION_BACKGROUND_AND_POSITIVE_CANDIDATE_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'first_source_sha256':first['source_sha256'],'first_source_bytes':260161576,
            'first_source_frames_counted':15756,'first_source_duration_s_by_frames':630.24,'source_has_strict_decode_failure':True,
            'strict_ffmpeg_exit_code':183,'conservative_quarantine_frames0':[15705,15755],
            'first_source_full_zero_event_GT_established':False,'first_source_overview_images_viewed':128,
            'review_video_frames_fully_decoded':3152,'packet_clock_entries_checked':15756,'max_clock_deviation_s':error,
            'other_source_files_probed':6,'native_probe_attempts':18,'native_probe_images_viewed':11,'failed_probes_retained':7,
            'probe_HTTP_bytes_including_preserved_guard_attempt':88080396,'all_raster_files_full_decoded':174,
            'positive_candidate':positive['selected']['filename'],'positive_candidate_source_bytes':260358184,
            'positive_candidate_source_sha256':second['source_sha256'],'positive_source_complete_byte_download_verified':True,
            'positive_probe_ranges_match_complete_source_bytes':True,'first_source_actual_container':'MPEG-PS with IMKH private header',
            'positive_source_whole_decode_or_event_GT_verified':False,'model_or_training_calls':0,
            'current_human_confirmed_12_milestone_preserved':True,'current_29_condition_catalog_unchanged':True,
            'random_unseen_test_claimed':False,'new_accuracy_or_F1_claimed':False,'FPGA_execution_verified':False,
            'Slurm_jobs_completed':['130319','130320','130326'],'browser_playback_verified':False,'local_links_checked':len(links),
            'images':images,'documents':[{'path':str(p),'sha256':sha(p)} for p in docs],
            'evidence_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'results/native_delivery_verification.json',ROOT/'evidence/source_packet_clock_summary.json',
                ROOT/'evidence/source_decode_limit.json',ROOT/'results/next_probe_verification.json',ROOT/'evidence/initial_native_visual_review.json',ROOT/'evidence/next_probe_visual_review.json',
                ROOT/'protocol/selection_v1.json',ROOT/'protocol/positive_candidate_v1.json',ROOT/'input/positive_video_ranges/manifest.json']},
            'previous_goal_turn_classification':'progress: four ordinary overhead sessions and eight fixed-model comparisons checked',
            'this_goal_turn_classification':'progress: long background candidate acquired and diagnosed; six remaining files natively probed and cow-present long source fully obtained',
            'next_priority':'Full native admission of the cow-present13-25-38 source, then independent event reference before fixed-model replay',
            'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['images','documents','evidence_hashes']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
