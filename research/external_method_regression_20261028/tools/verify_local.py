from pathlib import Path,PurePosixPath
from collections import defaultdict
from functools import lru_cache
import csv,hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def read(p):return list(csv.DictReader(Path(p).open(newline='',encoding='utf-8')))
def norm(rows):return [{k:None if v in [None,''] else int(v) if k in ['frame','track_id'] else float(v) for k,v in row.items()} for row in rows]
def counter(frames):
    states={};events=[]
    for frame in range(479):
        time=frame/30;positions=frames.get(frame,{})
        for tid,s in states.items():
            if tid not in positions:s['region']=None;s['n']=0
        for tid,x in positions.items():
            s=states.setdefault(tid,{'last':-1e30,'origin':None,'region':None,'n':0})
            if time-s['last']>2:s.update(origin=None,region=None,n=0)
            s['last']=time;region='A' if x<.4 else 'B' if x>.6 else None
            if region is None:s.update(region=None,n=0);continue
            s['n']=s['n']+1 if s['region']==region else 1;s['region']=region
            if s['n']>=3 and s['origin']!=region:
                old=s['origin'];s['origin']=region
                if old is not None:events.append({'time_s':time,'track_id':tid,'direction':old+'->'+region,'frame':frame})
    return events
def reference_from_publisher(path):
    rows=[list(map(float,row)) for row in csv.reader(Path(path).open())];assert len(rows)==1775
    assert len({(r[0],r[1]) for r in rows})==1775 and len({r[1] for r in rows})==9
    byid=defaultdict(list)
    for r in rows:
        f,tid=int(r[0]),int(r[1]);assert 0<=f<479 and r[4]>0 and r[5]>0
        cx,cy=(r[2]+r[4]/2)/1920,(r[3]+r[5]/2)/1080
        if .1<cy<.95 and 0<=cx<=1:byid[tid].append((f,'A' if cx<.4 else 'B' if cx>.6 else 'M'))
    events=[]
    for tid,observations in byid.items():
        groups=[]
        for f,z in sorted(observations):
            if groups and groups[-1][-1][0]+1==f and groups[-1][-1][1]==z:groups[-1].append((f,z))
            else:groups.append([(f,z)])
        origin=None;last=None
        for group in groups:
            if last is not None and group[0][0]-last>60:origin=None
            last=group[-1][0];z=group[0][1]
            if z=='M' or len(group)<3:continue
            if origin is not None and origin!=z:
                f=group[2][0];events.append({'time_s':f/30,'track_id':tid,'direction':origin+'->'+z,'frame':f})
            origin=z
    return sorted(events,key=lambda e:(e['time_s'],e['track_id']))
def exhaustive(reference,prediction):
    @lru_cache(None)
    def solve(i,mask):
        if i==len(reference):return 0,0.,()
        best=solve(i+1,mask)
        for j,p in enumerate(prediction):
            error=abs(reference[i]['time_s']-p['time_s'])
            if error>2 or mask&(1<<j):continue
            n,total,pairs=solve(i+1,mask|(1<<j));candidate=n+1,total+error,((i,j),)+pairs
            if (candidate[0],-candidate[1])>(best[0],-best[1]):best=candidate
        return best
    return solve(0,0)
def main():
    target=ROOT/'results/local_verification.json';assert not target.exists()
    r=load(ROOT/'results/delivery_record.json');archive=ROOT/'results/delivery.tar.gz';dest=ROOT/'delivery';assert not dest.exists()
    assert sha(archive)==r['sha256'] and archive.stat().st_size==r['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==r['manifest_sha256']
        items=json.loads(raw);expected={x['path']:x for x in items};members=tf.getmembers()
        assert len(items)==len(expected)==r['manifest_files']==68 and len(members)==r['archive_members']==69
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    p=load(ROOT/'protocol/regression_v1.json');s=load(dest/'results/summary.json')
    assert s['protocol_sha256']==sha(ROOT/'protocol/regression_v1.json')==sha(dest/'protocol/regression_v1.json')
    reference=reference_from_publisher(dest/'input/publisher_gt_original.txt');assert reference==p['reference_events']==load(dest/'reference_author_summary.json')['events']
    assert sha(dest/'input/publisher_gt_original.txt')==p['publisher_GT_sha256']
    for name,checksum in p['input_modules'].items():assert sha(ROOT/'input'/name)==sha(dest/'input'/name)==checksum
    records=[];allframes=0;ROIrows=0;accepted_count=0
    for c in s['conditions']:
        folder=dest/'results'/c['name'];post=norm(read(folder/'post_tracker_boxes.csv'));tracks=norm(read(folder/'tracks.csv'))
        byframe=defaultdict(dict);ids=defaultdict(set)
        for row in post:
            if row['track_id'] is not None:ids[row['frame']].add(row['track_id'])
        for row in tracks:
            assert .1<row['cy_norm']<.95 and 0<=row['axis_position']<=1
            byframe[row['frame']][row['track_id']]=row['axis_position']
            actual=next(r for r in post if r['frame']==row['frame'] and r['track_id']==row['track_id'])
            assert (actual['x1']+actual['x2'])/3840==row['axis_position'] and (actual['y1']+actual['y2'])/2160==row['cy_norm']
        if c['variant']=='installed':
            old=dest/'original_cache'/c['model']
            assert post==norm(read(old/'post_tracker_boxes.csv')) and tracks==norm(read(old/'tracks.csv'))
        obs=load(folder/'observations.json');assert [r['frame'] for r in obs]==list(range(479))
        expanded={f:dict(v) for f,v in byframe.items()};known=set();last={}
        for row in obs:
            f=row['frame'];active=set(row['confirmed_IDs']);tentative={int(k):v for k,v in row['tentative_positions'].items()}
            assert active==ids.get(f,set()) and {int(k):v for k,v in row['confirmed_positions'].items()}==byframe.get(f,{})
            admitted=[]
            for tid in sorted(active-known):
                if tid in last:
                    x=last[tid];expanded.setdefault(f-1,{})[tid]=x
                    admitted.append({'track_id':tid,'observation_time_s':(f-1)/30,'confirmation_time_s':f/30,'axis_position':x,'observation_frame':f-1,'confirmation_frame':f})
            assert row['accepted_history']==admitted;accepted_count+=len(admitted);known.update(active);last=tentative
        actual={'confirmed_only':counter(byframe),'handoff':counter(expanded)}
        for counter_name,events in actual.items():
            assert events==load(folder/(counter_name+'_events.json'))
            scored=next(r for r in s['scores'] if r['condition_id']==c['name']+'_'+counter_name)
            m=scored['metrics'];n,error,pairs=exhaustive(reference,events)
            got_tp=sum(reference[i]['direction']==events[j]['direction'] for i,j in pairs)
            assert (n,got_tp,len(events)-got_tp,len(reference)-got_tp)==(m['temporally_matched'],m['TP'],m['FP'],m['FN'])
            assert abs(sum(a['time_error_s'] for a in m['pairs'])-error)<1e-10
            assert len({r['reference_index'] for r in m['pairs']})==len(m['pairs'])==len({r['prediction_index'] for r in m['pairs']})
            for pair in m['pairs']:
                a,b=reference[pair['reference_index']],events[pair['prediction_index']]
                assert abs(a['time_s']-b['time_s'])==pair['time_error_s'] and pair['time_error_s']<=2
                assert pair['direction_correct']==(a['direction']==b['direction'])
            records.append({'condition':scored['condition_id'],'main_method':scored['main_method'],'TP':got_tp,'FP':len(events)-got_tp,'FN':len(reference)-got_tp,
                'wrong_direction':n-got_tp,'summed_pair_time_error':error,'reference_indices_matched':[i for i,j in pairs]})
        allframes+=len(obs);ROIrows+=len(tracks)
    assert len(records)==12 and sum(r['main_method'] for r in records)==8
    main=[r for r in records if r['main_method']]
    assert [r['TP'] for r in main]==[6,6,6,6,2,2,2,3]
    assert all(r['FP']==r['wrong_direction']==0 for r in records)
    result={'status':'ALL68_FILES_REFERENCE_DERIVATION_12_COUNTER_PATHS_AND_EXHAUSTIVE_SCORES_VERIFIED',
      'protocol_sha256':sha(ROOT/'protocol/regression_v1.json'),'summary_sha256':sha(dest/'results/summary.json'),
      'files':68,'reference_rows':1775,'reference_IDs':9,'reference_events':6,
      'tracker_runs':6,'counter_paths':12,'main_method_conditions':8,'update_traces':allframes,'ROI_track_rows':ROIrows,'admitted_history':accepted_count,
      'full_original_baseline_regressions':2,'verified_conditions':records,
      'new_independent_test':False,'MultiCam_source_truth_received':False,'new_detector_forwards':0,'training_updates':0,
      'FPGA_execution_verified':False,'whole_goal_complete':False}
    target.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
