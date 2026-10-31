from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,os,socket,subprocess,tarfile
import cv2
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/confirmation_handoff_20261028');OUT=ROOT/'results/replay_v2'
PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))

def independent(frames):
    state={};events=[]
    for frame in range(0,10874,5):
        seen=frames.get(frame,{});time=frame/25
        for tid,s in state.items():
            if tid not in seen:s['zone']=None;s['n']=0
        for tid,y in seen.items():
            s=state.setdefault(tid,{'last':-1e30,'start':None,'zone':None,'n':0})
            if time-s['last']>2:s.update(start=None,zone=None,n=0)
            s['last']=time;region='A' if y<.4 else 'B' if y>.6 else None
            if region is None:s.update(zone=None,n=0);continue
            s['n']=s['n']+1 if s['zone']==region else 1;s['zone']=region
            if s['n']>=3 and s['start']!=region:
                old=s['start'];s['start']=region
                if old is not None and frame>=8912:events.append({'time_s':time,'track_id':tid,'direction':old+'->'+region,'source_frame':frame})
    return events

def verify(p):
    summary=load(OUT/'summary.json');assert summary['protocol_sha256']==sha(ROOT/'protocol/handoff_v1.json')
    checks=[];totals={'trace_frames':0,'tentative_observations':0,'accepted_history':0}
    for c in summary['conditions']:
        seed=c['seed'];dest=OUT/f'seed{seed}';source=next(s for s in p['sources'] if s['seed']==seed);prior=Path(source['remote_folder'])
        trace=load(dest/'observations.json');assert [r['source_frame'] for r in trace]==list(range(0,10874,5))
        confirmed={};active={};tentative={};raw=defaultdict(list);prior_ids=defaultdict(set)
        for r in read(prior/'pretracker_boxes.csv'):
            if .34<(float(r['x1'])+float(r['x2']))/5120<.75:raw[int(r['frame'])].append((float(r['y1'])+float(r['y2']))/2880)
        for r in read(prior/'all_posttracker_boxes.csv'):
            if r['track_id']!='':prior_ids[int(r['frame'])].add(int(r['track_id']))
        roi=defaultdict(dict)
        for r in read(prior/'source_warmup_tracks.csv')+read(prior/'source_tracks.csv'):roi[int(r['source_frame'])][int(r['track_id'])]=float(r['axis_position'])
        for r in trace:
            frame=r['source_frame'];confirmed[frame]={int(k):v for k,v in r['confirmed_positions'].items()}
            active[frame]=set(r['confirmed_ids']);tentative[frame]={int(k):v for k,v in r['tentative_positions'].items()}
            assert confirmed[frame]==roi.get(frame,{}) and active[frame]==prior_ids.get(frame,set())
            assert not active[frame]&set(tentative[frame])
            for y in tentative[frame].values():
                assert raw[frame] and min(abs(y-v) for v in raw[frame])<=1e-6
            totals['tentative_observations']+=len(tentative[frame])
        expanded={f:dict(v) for f,v in confirmed.items()};known=set();acceptances=[]
        for r in trace:
            f=r['source_frame'];expected=[]
            for tid in sorted(active[f]-known):
                if tid in tentative.get(f-5,{}):
                    y=tentative[f-5][tid];expanded[f-5][tid]=y
                    expected.append({'track_id':tid,'observation_time_s':(f-5)/25,'confirmation_time_s':f/25,
                        'axis_position':y,'observation_source_frame':f-5,'confirmation_source_frame':f})
            assert sorted(r['accepted_history'],key=lambda x:x['track_id'])==expected
            acceptances+=expected;known.update(active[f])
        assert acceptances==load(dest/'history_acceptances.json')
        baseline=independent(confirmed);candidate=independent(expanded)
        assert baseline==load(dest/'baseline_events.json')==load(dest/'disabled_events.json')==load(prior/'source_events.json')
        assert candidate==load(dest/'handoff_events.json')
        assert all(e['track_id'] in active[e['source_frame']] and e['track_id'] in confirmed[e['source_frame']] for e in candidate)
        keys=[(e['source_frame'],e['track_id'],e['direction']) for e in candidate];assert len(keys)==len(set(keys))
        assert len({r['track_id'] for r in acceptances})==len(acceptances)
        assert c['baseline_down']==sum(e['direction']=='A->B' for e in baseline) and c['handoff_down']==sum(e['direction']=='A->B' for e in candidate)
        assert not c['removed_events']
        totals['trace_frames']+=len(trace);totals['accepted_history']+=len(acceptances)
        checks.append({'seed':seed,'baseline_events':len(baseline),'handoff_events':len(candidate),
           'source_tracks_and_all_confirmed_IDs_exact':True,'independent_event_paths':3,'accepted_prefixes':len(acceptances),
           'all_events_at_current_confirmed_observation':True,'duplicate_identical_event_keys':0,
           'physical_duplicate_cow_events_independently_ruled_out':False})
    r={'status':'THREE_SEEDS_NINE_EVENT_PATHS_AND_CAUSAL_HANDOFF_TRACES_INDEPENDENTLY_VERIFIED',
       'job_id':os.environ['SLURM_JOB_ID'],'source_summary_sha256':sha(OUT/'summary.json'),
       'protocol_sha256':sha(ROOT/'protocol/handoff_v1.json'),'module_sha256':sha(ROOT/'tools/confirmation_counter.py'),
       'checks':checks,**totals,'independent_source_accuracy':None,'board_execution':False}
    save(ROOT/'results/independent_verification.json',r);print(json.dumps(r),flush=True);return summary

def render(summary):
    q=load(ROOT/'protocol/media_v1.json');source=Path(q['source_video']);assert sha(source)==q['source_sha256']
    codec='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    states=[]
    for c in summary['conditions']:
        folder=OUT/f'seed{c["seed"]}';byframe=defaultdict(list)
        for row in read(folder/'source_warmup_tracks.csv')+read(folder/'source_tracks.csv'):byframe[int(row['source_frame'])].append(row)
        writer=cv2.VideoWriter(str(folder/'view_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),25.,(1280,720));assert writer.isOpened()
        states.append({'summary':c,'folder':folder,'rows':byframe,'events':load(folder/'handoff_events.json'),'writer':writer})
    cap=cv2.VideoCapture(str(source));assert (cap.get(5),int(cap.get(3)),int(cap.get(4)))==(25.,2560,1440)
    for frame in range(10874):
        ok,image=cap.read();assert ok,frame
        if frame<8912:continue
        native=cv2.resize(image,(1280,720),interpolation=cv2.INTER_AREA);sample=frame-frame%5
        for s in states:
            view=native.copy();seed=s['summary']['seed'];down=sum(e['direction']=='A->B' and e['source_frame']<=frame for e in s['events']);up=sum(e['direction']=='B->A' and e['source_frame']<=frame for e in s['events'])
            for x in [.34,.75]:cv2.line(view,(round(x*1280),0),(round(x*1280),719),(0,177,255),2)
            for y in [.4,.6]:cv2.line(view,(round(.34*1280),round(y*720)),(round(.75*1280),round(y*720)),(0,177,255),2)
            for r in s['rows'][sample]:
                x1,y1,x2,y2=[round(float(r[k])/2) for k in ['x1','y1','x2','y2']]
                cv2.rectangle(view,(x1,y1),(x2,y2),(112,237,149),2);cv2.putText(view,f'id {r["track_id"]}',(x1,max(62,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,(112,237,149),2)
            cv2.rectangle(view,(0,0),(1280,56),(18,24,28),-1)
            cv2.putText(view,f'Confirmation handoff | same full640 5Hz | seed{seed}',(16,25),cv2.FONT_HERSHEY_SIMPLEX,.66,(240,242,240),2)
            cv2.putText(view,f'Source {frame} sample {sample} | predicted down {down} up {up}',(16,48),cv2.FONT_HERSHEY_SIMPLEX,.59,(220,228,225),1)
            cv2.rectangle(view,(0,690),(1280,720),(18,24,28),-1)
            cv2.putText(view,'Development predictions. Same tracker boxes. One tentative observation admitted only on confirmation.',(16,710),cv2.FONT_HERSHEY_SIMPLEX,.53,(220,228,225),1)
            s['writer'].write(view)
            if frame in [9310,9345,9420,10873]:assert cv2.imwrite(str(s['folder']/f'f{frame}.jpg'),view)
    cap.release();records=[]
    for s in states:
        s['writer'].release();folder=s['folder'];target=folder/'view.mp4';assert not target.exists()
        run=subprocess.run([codec,'-hide_banner','-nostdin','-n','-i',str(folder/'view_raw.mp4'),'-an','-threads','2','-c:v','libx264','-preset','veryfast','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],capture_output=True)
        (ROOT/'logs'/f'media_seed{s["summary"]["seed"]}.log').write_bytes(run.stderr);assert run.returncode==0
        run=subprocess.run([codec,'-v','error','-nostdin','-xerror','-i',str(target),'-f','null','-'],capture_output=True);assert run.returncode==0,run.stderr[-500:]
        cap=cv2.VideoCapture(str(target));assert (cap.get(5),int(cap.get(7)),int(cap.get(3)),int(cap.get(4)))==(25.,1962,1280,720);cap.release()
        records.append({'seed':s['summary']['seed'],'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),'bytes':target.stat().st_size,'frames':1962,'fps':25,'strict_decode':'PASS'})
    save(ROOT/'results/render_verification.json',{'source_sha256':q['source_sha256'],'new_inference':False,'files':records})

def collect():
    files=[ROOT/'protocol/handoff_v1.json',ROOT/'protocol/replay_implementation_v2.json',ROOT/'protocol/media_v1.json',ROOT/'input/zone_counter.py',ROOT/'job_id.txt',ROOT/'v2_job_id.txt']
    files+=list((ROOT/'tools').glob('*.py'))+list((ROOT/'tools').glob('*.slurm'))
    files+=[ROOT/'results/independent_verification.json',ROOT/'results/render_verification.json',OUT/'summary.json',OUT/'behavior_server_green.txt']
    for folder in sorted(OUT.glob('seed*')):files+=[p for p in folder.iterdir() if p.is_file() and p.name!='view_raw.mp4']
    # Replay jobs are terminal. Current verification stdout stays outside this archive.
    files+=list((ROOT/'logs').glob('replay*.out'))+list((ROOT/'logs').glob('replay*.err'))+list((ROOT/'logs').glob('media_seed*.log'))
    assert len(files)==len(set(files))
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    mp=ROOT/'results/delivery_manifest.json';save(mp,manifest);archive=ROOT/'results/delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tf:
        for path in sorted(files):tf.add(path,arcname=path.relative_to(ROOT).as_posix())
        tf.add(mp,arcname='delivery_manifest.json')
    record={'manifest_files':len(manifest),'archive_members':len(manifest)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
    save(ROOT/'results/delivery_record.json',record);print(json.dumps(record),flush=True)
if __name__=='__main__':
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
    p=load(ROOT/'protocol/handoff_v1.json');summary=verify(p);render(summary);collect()
