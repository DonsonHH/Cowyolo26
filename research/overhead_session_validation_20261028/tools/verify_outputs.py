"""Check transferred bytes, native geometry, event replay and every delivered video."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,importlib.util,json,subprocess,sys
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)

def main():
    out=ROOT/'results/local_verification';out.mkdir(parents=True,exist_ok=False)
    p=load(ROOT/'protocol/inference_v1.json');selection=load(ROOT/'protocol/sessions_v1.json')
    delivery=ROOT/'inference_delivery';summary=load(delivery/'results/inference/summary.json')
    admission=load(ROOT/'admission_delivery/results/admission/summary.json');fetch=load(ROOT/'evidence/fetch_manifest_resumed.json')
    assert summary['protocol_sha256']==sha(ROOT/'protocol/inference_v1.json')
    assert sha(delivery/'protocol/inference_v1.json')==sha(ROOT/'protocol/inference_v1.json')
    assert p['admission_summary_sha256']==sha(ROOT/'admission_delivery/results/admission/summary.json')
    assert len(summary['conditions'])==8 and len(admission['videos'])==len(fetch['files'])==4
    sys.path.insert(0,str(ROOT/'input'))
    from confirmation_counter import ConfirmationHandoffCounter
    from zone_counter import ZoneCounter
    for name,digest in p['input_module_sha256'].items():assert sha(ROOT/'input'/name)==sha(delivery/'input'/name)==digest
    media=[];source_bytes=0;http_bytes=0;prefix_bytes=0
    for f in fetch['files']:
        local=Path(f['local_path']);assert sha(local)==f['sha256'] and local.stat().st_size==f['bytes']
        folder=local.parent;digest=hashlib.sha256();start=0
        if f['preserved_prefix_bytes']:
            prefix=ROOT/'input/prefixes'/(f['sequence']+'.avi.prefix');b=prefix.read_bytes();assert len(b)==f['preserved_prefix_bytes']
            old=load(ROOT/'evidence/stage_transfer_stop.json');bound=next(r for r in old['preserved_prefixes'] if r['sequence']==f['sequence'])
            assert sha(prefix)==bound['sha256'];digest.update(b);start=len(b);prefix_bytes+=len(b)
            overlap=next(r for r in f['range_reads'] if r['file']=='prefix_overlap.bin')
            assert (folder/overlap['file']).read_bytes()==b[-overlap['bytes']:]
        for r in f['range_reads']:
            assert sha(folder/r['file'])==r['sha256'] and (folder/r['file']).stat().st_size==r['bytes']
            assert r['end_exclusive']-r['start']==r['bytes'] and r['object_bytes']==f['bytes']
            if r['file'].startswith('resumed_part_'):
                assert r['start']==start;digest.update((folder/r['file']).read_bytes());start=r['end_exclusive']
        assert start==f['bytes'] and digest.hexdigest()==f['sha256']
        source_bytes+=f['bytes'];http_bytes+=f['successful_range_HTTP_bytes']
        clip=next(r for r in admission['videos'] if r['sequence']==f['sequence'])
        assert f['sha256']==clip['source_sha256']
        media.append((local,clip['frames'],clip['fps'],'original_AVI'))
        media.append((ROOT/'admission_delivery'/clip['native_proxy'],clip['frames'],clip['fps'],'native_H264'))
    assert source_bytes==162888404 and prefix_bytes==11534336 and http_bytes==151485144
    counter_updates=0;coordinate_rows=0;predicted=[];timelines=[];contacts=[]
    for r in summary['conditions']:
        folder=delivery/'results/inference'/r['sequence']/r['model'];obs=load(folder/'observations.json');events=load(folder/'handoff_events.json')
        source=next(v for v in admission['videos'] if v['sequence']==r['sequence']);assert r['frames']==source['frames'] and len(obs)==r['samples']==27
        assert [o['frame0'] for o in obs]==list(range(0,r['frames'],6))
        boxes=list(csv.DictReader((folder/'post_tracker_boxes.csv').open(encoding='utf-8')));positions=defaultdict(dict)
        for b in boxes:
            if not b['track_id']:continue
            ID=int(b['track_id']);frame=int(b['frame0']);x=(float(b['x1'])+float(b['x2']))/(2*1280);y=(float(b['y1'])+float(b['y2']))/(2*720)
            if .05<y<.9:positions[frame][ID]=x;coordinate_rows+=1
        candidate=ConfirmationHandoffCounter(**p['counter']);ordinary=ZoneCounter(**p['counter']);replayed=[];plain=[];IDsteps=defaultdict(list)
        for o in obs:
            frame=o['frame0'];time=o['time_s'];assert abs(time-frame/30)<1e-12
            confirmed={int(k):v for k,v in o['confirmed_positions'].items()};tentative={int(k):v for k,v in o['tentative_positions'].items()}
            assert confirmed.keys()==positions[frame].keys()
            for ID,value in confirmed.items():
                assert abs(value-positions[frame][ID])<1e-12
                IDsteps[ID].append({'frame0':frame,'axis':value,'zone':'A' if value<.4 else 'B' if value>.6 else 'M'})
            for output,target in [(candidate.update(time,confirmed,tentative,set(o['confirmed_IDs'])),replayed),(ordinary.update(time,confirmed),plain)]:
                for e in output:e['frame0']=frame;target.append(e)
            assert candidate.last_acceptances==o['accepted_history'];counter_updates+=1
        assert replayed==events and plain==load(folder/'confirmed_only_events.json')
        assert sum(e['direction']=='A->B' for e in events)==r['predicted_A_to_B']
        assert sum(e['direction']=='B->A' for e in events)==r['predicted_B_to_A']
        raw=list(csv.DictReader((folder/'raw_detector_boxes.csv').open(encoding='utf-8')))
        assert len(raw)==r['raw_detector_rows'] and len(boxes)>=r['tracked_ROI_rows']
        predicted.append({'sequence':r['sequence'],'model':r['model'],'predicted_A_to_B':r['predicted_A_to_B'],
                          'predicted_B_to_A':r['predicted_B_to_A'],'raw_rows':len(raw),'tracked_ROI_rows':r['tracked_ROI_rows'],
                          'raw_nonempty_samples':len({int(b['frame0']) for b in raw}),'events':events})
        timelines.append({'sequence':r['sequence'],'model':r['model'],'confirmed_ID_steps':dict(IDsteps),
                          'interpretation':'Zone observations are predictions, not independent reference trajectories.'})
        movie=folder/'predictions.mp4';assert sha(movie)==r['movie_sha256'];media.append((movie,r['frames'],r['fps'],'prediction_H264'))
        snapdir=out/'snapshots'/r['sequence']/r['model'];snapdir.mkdir(parents=True)
        anchors=[0,(r['frames']-1)//2,r['frames']-1]
        expression='+'.join(f'eq(n\\,{n})' for n in anchors)
        cmd=['ffmpeg','-hide_banner','-v','error','-threads','2','-i',str(movie),'-vf','select='+expression,'-fps_mode','vfr',str(snapdir/'frame_%02d.png')]
        proc=subprocess.run(cmd,capture_output=True,check=True);assert not proc.stderr
        images=sorted(snapdir.glob('frame_*.png'));assert len(images)==3
        contacts.append((r,images,anchors))
    assert counter_updates==216 and coordinate_rows==83
    media_rows=[]
    for path,expected,fps,kind in media:
        cmd=['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,nb_read_frames,r_frame_rate,avg_frame_rate,codec_name','-of','json',str(path)]
        proc=subprocess.run(cmd,capture_output=True,check=True);assert not proc.stderr,proc.stderr
        value=json.loads(proc.stdout);assert len(value['streams'])==1;s=value['streams'][0]
        assert (s['width'],s['height'])==(1280,720) and int(s['nb_read_frames'])==expected
        num,den=map(int,s['r_frame_rate'].split('/'));assert num/den==fps==30
        media_rows.append({'path':str(path),'sha256':sha(path),'kind':kind,'decoded_frames':expected,'ffprobe':value})
    assert len(media_rows)==16 and sum(r['decoded_frames'] for r in media_rows)==2548
    paired=[]
    for seq in [r['sequence'] for r in selection['selected']]:
        arms=[next(t for t in contacts if t[0]['sequence']==seq and t[0]['model']==m) for m in ['official_yolo26n','accepted_seed26']]
        canvas=Image.new('RGB',(1280,1240),'#111827');d=ImageDraw.Draw(canvas)
        d.text((15,8),f'Fixed ordinary overhead session: {seq}',font=font(25),fill='white')
        d.text((15,39),'Official YOLO26n (left) | Accepted seed26 (right) | Predictions; event truth pending',font=font(21),fill='#fbbf24')
        for col,(r,images,anchors) in enumerate(arms):
            for row,(path,n) in enumerate(zip(images,anchors)):
                with Image.open(path) as im:im.load();small=im.convert('RGB').resize((640,360))
                canvas.paste(small,(col*640,80+row*385));d.text((col*640+7,80+row*385+362),f'Frame0 {n}',font=font(19),fill='white')
        dest=out/(seq+'_two_models.jpg');canvas.save(dest,quality=94);paired.append({'sequence':seq,'path':dest.name,'sha256':sha(dest)})
    (out/'per_ID_zone_observations.json').write_text(json.dumps(timelines,indent=2),encoding='utf-8')
    result={'status':'FOUR_SOURCE_RECONSTRUCTIONS_EIGHT_COUNTER_PATHS_AND_SIXTEEN_FULL_VIDEO_DECODES_VERIFIED',
            'source_bytes':source_bytes,'preserved_prefix_bytes':prefix_bytes,'successful_HTTP_range_bytes':http_bytes,
            'conditions':8,'counter_updates_replayed':counter_updates,'ROI_positions_independently_recomputed':coordinate_rows,
            'media_files_full_decoded':16,'media_frames_full_decoded':2548,'prediction_snapshots_extracted':24,
            'predictions':predicted,'media':media_rows,'paired_figures':paired,'event_accuracy_or_F1_established':False,
            'visual_QA':'PENDING_MANUAL_IMAGE_REVIEW','FPGA_execution_verified':False,'whole_goal_complete':False}
    (ROOT/'results/output_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['media','paired_figures','predictions']},ensure_ascii=False),flush=True)
    print(json.dumps(predicted),flush=True)

if __name__=='__main__':main()
