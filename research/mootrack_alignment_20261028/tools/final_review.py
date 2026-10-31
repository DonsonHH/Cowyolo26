"""Reconcile the specific evidence supporting the MooTrack data-admission report."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import csv,hashlib,json,re,zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    records=[]
    def check(p,expected):
        assert p.is_file() and sha(p)==expected,str(p)
        records.append({'path':str(p),'sha256':expected,'bytes':p.stat().st_size})
    archive=PROJECT/'counting_reference_candidates_20261027/catalog/MooTrack360_TrackEval_evaluation_code.zip'
    check(archive,'26800ea3b6e653e4e9d7c54a2587060bd2a920b4e862f0b84afef624234b6478')
    original_moov=PROJECT/'counting_reference_candidates_20261027/results/MooTrack360_container_probe/moov.bin'
    check(original_moov,'f060958b4bd3120c0e35070f0532930e41a97e349a8d8e448f8d60031b2e18d3')
    author=read(ROOT/'evidence/author/manifest.json')
    commit=read(ROOT/'evidence/author/commit.json');tree=read(ROOT/'evidence/author/tree.json')
    assert author['commit']==commit['sha']=='9782faa9ca2702f29298f0a5af58046a83a79f8d'
    assert tree['sha']==author['commit'] and not tree['truncated']
    # This GitHub response echoes the requested commit in top-level `sha`.
    # Reconstruct real Git tree objects instead of assuming that field is a tree object ID.
    parents={'':[]};expected_tree={'':commit['commit']['tree']['sha']}
    for entry in tree['tree']:
        parent,_,name=entry['path'].rpartition('/');parents.setdefault(parent,[]).append((name,entry))
        if entry['type']=='tree':expected_tree[entry['path']]=entry['sha'];parents.setdefault(entry['path'],[])
    for folder,expected in expected_tree.items():
        items=sorted(parents[folder],key=lambda pair:(pair[0]+('/' if pair[1]['type']=='tree' else '')).encode())
        body=b''.join(e['mode'].lstrip('0').encode()+b' '+name.encode()+b'\0'+bytes.fromhex(e['sha']) for name,e in items)
        assert hashlib.sha1(b'tree '+str(len(body)).encode()+b'\0'+body).hexdigest()==expected,folder
    by_path={r['path']:r for r in tree['tree']}
    for row in author['files']:
        p=ROOT/'evidence/author/files'/row['path'];b=p.read_bytes();check(p,row['sha256'])
        assert len(b)==row['bytes']==by_path[row['path']]['size']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['git_blob_sha1']==by_path[row['path']]['sha']
    assert len(author['files'])==30 and sum(r['bytes'] for r in author['files'])==162203
    assert 'img_resize: 0.5' in (ROOT/'evidence/author/files/README.md').read_text(encoding='utf-8')
    meta=read(ROOT/'results/sample_index/index.json')
    sample_rows=list(csv.DictReader((ROOT/'results/sample_index/samples.csv').open(encoding='utf-8')))
    numeric=['decode_index0','offset','size','dts_ticks','pts_ticks','duration_ticks','display_index0']
    samples=[{k:(int(v) if k in numeric else v) for k,v in r.items()} for r in sample_rows]
    assert len(samples)==meta['sample_count']==53946 and meta['timescale']==30000 and meta['ctts_present'] is False
    for i,s in enumerate(samples):
        assert s['decode_index0']==s['display_index0']==i and s['duration_ticks']==2002
        assert s['dts_ticks']==s['pts_ticks']==2002*i
        assert 0<=s['offset']<s['offset']+s['size']<=18890553141
    assert sum(s['duration_ticks'] for s in samples)==107999892
    ranges_all=[];decoded=[];total=0;sample_ids=[];reconstructed=0
    for sub,summary_path in [('video_ranges','frame_review'),('tail_ranges','tail_review')]:
        folder=ROOT/'evidence'/sub;manifest=read(folder/'manifest.json');summary=read(ROOT/'results'/summary_path/'summary.json')
        assert manifest['source_total_bytes']==18890553141
        assert manifest['full_source_MD5_not_verified'] is True
        for row in manifest['range_reads']:
            check(folder/row['file'],row['sha256']);assert (folder/row['file']).stat().st_size==row['bytes']
            assert row['end_exclusive']-row['start']==row['bytes'] and row['http_status']==206
            assert row['Content-Range']==f"bytes {row['start']}-{row['end_exclusive']-1}/18890553141"
        total+=sum(r['bytes'] for r in manifest['range_reads']);ranges_all.extend(manifest['range_reads'])
        assert sum(r['bytes'] for r in manifest['range_reads'])==manifest['downloaded_bytes']
        for g in manifest['GOPs']:
            rawrow=next(r for r in manifest['range_reads'] if r['file']==g['elementary_file'].replace('.h264','.range.bin'))
            b=(folder/rawrow['file']).read_bytes();base=rawrow['start']
            chosen=samples[g['start_decode_index0']:g['end_decode_index0_exclusive']]
            assert chosen[0]['sync']=='True'
            assert min(s['offset'] for s in chosen)==g['range_start']==base
            assert max(s['offset']+s['size'] for s in chosen)==g['range_end_exclusive']==rawrow['end_exclusive']
            assert sum(s['size'] for s in chosen)==g['sum_video_bytes']
            h=hashlib.sha256()
            for value in meta['parameter_sets_hex']:h.update(b'\0\0\0\1'+bytes.fromhex(value))
            for s in chosen:
                packet=b[s['offset']-base:s['offset']-base+s['size']];assert len(packet)==s['size'];cursor=0
                while cursor<len(packet):
                    length=int.from_bytes(packet[cursor:cursor+4],'big');cursor+=4
                    assert 0<length<=len(packet)-cursor
                    h.update(b'\0\0\0\1'+packet[cursor:cursor+length]);cursor+=length
                assert cursor==len(packet);sample_ids.append(s['decode_index0']);reconstructed+=1
            check(folder/g['elementary_file'],g['elementary_sha256']);assert h.hexdigest()==g['elementary_sha256']
            f=next(f for f in summary['frames'] if f.get('video_display_frame0',f.get('video_frame0'))==g['target_display_index0'])
            native=f.get('native_png',f.get('native'));check(ROOT/'results'/summary_path/native,f['native_sha256'])
            assert f['decoded_frames']==len(chosen)
            with Image.open(ROOT/'results'/summary_path/native) as im:assert im.size==(2944,2944)
            decoded.append(f)
    assert len(ranges_all)==7 and total==44740482<64*1024*1024 and reconstructed==126
    assert len(sample_ids)==len(set(sample_ids))==126 and len(decoded)==5
    control=read(ROOT/'results/index_control.json');assert control['samples_checked']==606
    assert control['status']=='ALL_VIDEO_PACKET_BOUNDARIES_TIMESTAMPS_DURATIONS_AND_SYNC_FLAGS_MATCH_FFPROBE'
    check(Path(control['control_video']),control['sha256'])
    with zipfile.ZipFile(archive) as z:
        gt=z.read('TrackEval_evaluation_code/TrackEval/data/gt/mot_challenge/1hour/gt/gt.txt')
        assert hashlib.sha256(gt).hexdigest()=='595cdad9581382da5f3f406b2259f3d6937b1a131f6d677eca5756bdfcabccbd'
    seen=set();ids=set();frames=set();bounds=[float('inf'),float('inf'),-1,-1]
    for line in gt.decode().splitlines():
        v=line.split(',');assert len(v)==10
        frame,ID=int(v[0]),int(v[1]);key=(frame,ID);assert key not in seen;seen.add(key);ids.add(ID);frames.add(frame)
        x,y,w,h=map(float,v[2:6]);assert x>=0 and y>=0 and w>0 and h>0 and x+w<=1472 and y+h<=1472
        bounds=[min(bounds[0],x),min(bounds[1],y),max(bounds[2],x+w),max(bounds[3],y+h)]
    assert len(seen)==350272 and len(ids)==8 and frames==set(range(1,53921))
    scale=read(ROOT/'results/scale_control/summary.json');tail=read(ROOT/'results/tail_review/summary.json')
    assert bounds==scale['GT_xyxy_extrema_raw']==[350,281,1166,1199]
    assert scale['scale']==2.0 and scale['translation']==[0,0] and scale['diagnostic_not_preregistered'] is True
    assert scale['raw_boxes_outside_1472_square']==scale['scaled_boxes_outside_2944_square']==0
    assert tail['extra_video_frames_after_GT_prefix_hypothesis']==26 and abs(tail['extra_duration_seconds']-26*2002/30000)<1e-12
    assert tail['tail_truncation_is_proven'] is False and tail['frames'][1]['GT_frame1_hypothesis'] is None
    visual=read(ROOT/'evidence/visual_review.json')
    assert visual['native_display_indices0_inspected']==[0,8991,26973,53919,53945]
    assert visual['sampled_publisher_boxes_at_anchors']==24 and visual['annotated_anchor_frames_reviewed']==4
    for key in ['whole_video_visual_QA','full_frame_alignment_certified','full_19GB_source_checksum_verified',
                'new_independent_counting_test_certified','human_independent_event_JSON_received','FPGA_execution_verified','whole_goal_complete']:
        assert visual[key] is False
    for row in visual['viewed_files']:assert (ROOT/row).is_file()
    pictures=[]
    for folder in ['frame_review','scale_control','tail_review']:
        for p in sorted((ROOT/'results'/folder).iterdir()):
            if p.suffix.lower() not in ['.png','.jpg']:continue
            with Image.open(p) as im:im.load();size=im.size
            pictures.append({'path':str(p),'dimensions':size,'sha256':sha(p)})
    assert len(pictures)==21
    # Preserve current source experiments; published counts are not substituted as ground truth.
    catalog_path=PROJECT/'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json'
    check(catalog_path,'26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac')
    catalog=read(catalog_path);assert len(catalog['conditions'])==29 and catalog['frame_scope_inclusive']==[8912,10873]
    catalog_checks=0
    for r in catalog['conditions']:
        for base in ['events','summary','protocol']:
            if base+'_path' in r and base+'_sha256' in r:
                check(Path(r[base+'_path']),r[base+'_sha256']);catalog_checks+=1
        assert r['source_accuracy_verified'] is False
    handoff=sorted([r for r in catalog['conditions'] if r['condition_id'].startswith('confirmation_handoff_20261028/')],key=lambda r:r['seed'])
    assert [r['predicted_A_to_B'] for r in handoff]==[12,11,11] and all(r['predicted_B_to_A']==0 for r in handoff)
    for seed,digest in [(26,'51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74'),
                        (27,'132b62e8918429ac6e0202eae1a6924550a1c3e1634545c6e4e174f25c921226'),
                        (28,'93b8746381cd997d98dba809685ba53f7779da750750aa39bea24646c843a216')]:
        check(PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{seed}/weights/last.pt',digest)
    docs=[ROOT/'计划与验收.md',ROOT/'MooTrack原片对齐核查与准入决策.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for p in docs:
        text=p.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
    result={'status':'BOUNDED_NATIVE_SAMPLES_GT_SCALE_HYPOTHESIS_AND_ADMISSION_LIMITS_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'author_commit':author['commit'],'author_text_files':30,
            'Git_tree_objects_reconstructed_to_commit_tree':len(expected_tree),
            'video_sample_table_entries':53946,'range_requests_checked':len(ranges_all),'range_bytes_checked':total,
            'GOPs':5,'video_samples_reconstructed_and_decode_count_checked':126,'native_frames_visually_inspected':5,
            'GT_anchor_frames_visually_inspected':4,'GT_anchor_boxes':24,'image_files_decoded':len(pictures),
            'GT_rows_independently_rechecked':len(seen),'GT_track_IDs':8,'GT_last_frame1':53920,
            'scale_hypothesis':2.0,'scale_hypothesis_support':'Pinned author half-res setting, whole-GT bounds and four visual anchors; no manual quantitative IoU',
            'time_mapping_hypothesis':'video display0 n -> GT frame1 n+1, not certified for whole prefix',
            'source_tail_extra_frames_under_prefix_hypothesis':26,'control_packets_checked_against_ffprobe':606,
            'catalog_conditions_preserved':29,'catalog_event_summary_protocol_files_reverified':catalog_checks,'current_predicted_down':[12,11,11],
            'new_training_or_model_forwards':False,'new_independent_counting_reference_certified':False,
            'whole_video_GT_alignment_certified':False,'tail_truncation_proven':False,'full_video_MD5_verified':False,
            'FPGA_execution_verified':False,'local_links_checked':len(links),
            'source_records':records,'images':pictures,'documents':[{'path':str(p),'sha256':sha(p)} for p in docs],
            'previous_goal_turn_classification':'progress: six-output duplicate-track audit with raw-box links and distinct-cow counterexample',
            'this_goal_turn_classification':'progress: native video acquired by bounded ranges; spatial mismatch found and author-supported scale control checked',
            'next_priority':'Continuous public-video alignment windows and fixed event admission; independent user reference and real board validation when available',
            'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_records','images','documents']}),flush=True)

if __name__=='__main__':main()
