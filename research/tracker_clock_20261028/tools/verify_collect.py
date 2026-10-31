"""Independently replay event rules and describe sameinput buffer effects."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,tarfile
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def normalize(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]

def independent_counter(rows,stride,required):
    samples=defaultdict(dict)
    for row in rows:samples[int(row['source_frame'])][int(row['track_id'])]=float(row['axis_position'])
    state={};events=[]
    for frame in range(0,10874,stride):
        now=frame/25;positions=samples.get(frame,{})
        for tid,s in state.items():
            if tid not in positions:s['candidate']=None;s['n']=0
        for tid,pos in positions.items():
            assert 0<=pos<=1
            s=state.setdefault(tid,{'last':-1e30,'origin':None,'candidate':None,'n':0})
            if now-s['last']>2:s.update(origin=None,candidate=None,n=0)
            s['last']=now;zone='A' if pos<.4 else 'B' if pos>.6 else None
            if zone is None:s.update(candidate=None,n=0);continue
            s['n']=s['n']+1 if s['candidate']==zone else 1;s['candidate']=zone
            if s['n']<required or s['origin']==zone:continue
            old=s['origin'];s['origin']=zone
            if old and frame>=8912:events.append({'time_s':now,'track_id':tid,'direction':old+'->'+zone,'source_frame':frame})
    return events

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    protocol=ROOT/'protocol/clock_v1.json';p=load(protocol);summary=load(ROOT/'results/summary.json')
    assert summary['protocol_sha256']==sha(protocol) and len(summary['conditions'])==7
    gate=load(ROOT/'results/exact_replay_gate.json');assert len(gate['conditions'])==5
    records=[];flow_rows=0
    for c in summary['conditions']:
        source=next(r for r in p['sources'] if r['name']==c['cached_source']);folder=ROOT/'results'/c['name']
        history=normalize(read(folder/'source_warmup_tracks.csv'));tracks=normalize(read(folder/'source_tracks.csv'))
        for r in history+tracks:
            assert r['source_frame']%source['stride']==0 and 0<=r['source_frame']<=10873
            assert .34<(r['x1']+r['x2'])/5120<.75 and r['axis_position']==(r['y1']+r['y2'])/2880
        events=independent_counter(history+tracks,source['stride'],source['stable_samples'])
        assert events==load(folder/'source_events.json')
        assert c['predicted_down']==sum(e['direction']=='A->B' for e in events) and c['predicted_up']==sum(e['direction']=='B->A' for e in events)
        assert c['ROI_track_rows']==len(tracks) and c['history_rows']==len(history)
        assert c['nominal_lost_budget_s']==c['track_buffer']*source['stride']/25
        if c['exact_prior_replay_required']:
            old=Path(source['remote_folder']);assert c['track_buffer']==30
            assert tracks==normalize(read(old/'source_tracks.csv')) and history==normalize(read(old/'source_warmup_tracks.csv'))
            assert events==load(old/'source_events.json') and c['exact_tracks_history_events_match'] is True
        else:
            control=next(r for r in p['controls'] if r['name']==c['name'])
            assert c['track_buffer']==control['track_buffer'] and c['only_tracker_config_difference']=={'track_buffer':[30,c['track_buffer']]}
        state=load(folder/'scoped_tracker_states.json');assert len(state)==len(range((8912+source['stride']-1)//source['stride']*source['stride'],10874,source['stride']))
        assert all(r['tracker_update']==r['frame']//source['stride']+1 for r in state)
        flow_rows+=len(history)+len(tracks)
        records.append({'name':c['name'],'events':len(events),'ROI_tracks':len(tracks),'history':len(history),'native_axis_and_event_replay':'PASS'})
    comparisons=[]
    for control in p['controls']:
        base=ROOT/'results'/('exact_'+control['source']);candidate=ROOT/'results'/control['name']
        original=load(base/'source_events.json');new=load(candidate/'source_events.json')
        st0=load(base/'scoped_tracker_states.json');st1=load(candidate/'scoped_tracker_states.json')
        assert [r['frame'] for r in st0]==[r['frame'] for r in st1]
        noid=lambda events:[{k:v for k,v in e.items() if k!='track_id'} for e in events]
        changed=[r0['frame'] for r0,r1 in zip(st0,st1) if r0!=r1]
        row0=load(base/'summary.json');row1=load(candidate/'summary.json')
        comparisons.append({'control':control['name'],'same_cached_source':control['source'],
          'baseline_buffer':30,'control_buffer':control['track_buffer'],
          'baseline_events':len(original),'control_events':len(new),'events_exact_with_ID':original==new,
          'event_times_and_directions_exact_without_ID':noid(original)==noid(new),
          'scoped_tracks_exact':normalize(read(base/'source_tracks.csv'))==normalize(read(candidate/'source_tracks.csv')),
          'warmup_tracks_exact':normalize(read(base/'source_warmup_tracks.csv'))==normalize(read(candidate/'source_warmup_tracks.csv')),
          'tracker_state_difference_frames':len(changed),'first_tracker_state_difference_frame':changed[0] if changed else None,
          'ROI_IDs_before_after':[row0['ROI_track_IDs'],row1['ROI_track_IDs']],
          'changed_states_do_not_prove_real_world_count_improvement':True})
    result={'status':'SEVEN_EVENT_REPLAYS_FIVE_EXACT_REGRESSIONS_AND_TWO_CONFIG_ONLY_CONTROLS_VERIFIED',
       'job_id':os.environ['SLURM_JOB_ID'],'source_job_id':summary['job_id'],'protocol_sha256':sha(protocol),
       'summary_sha256':sha(ROOT/'results/summary.json'),'conditions':records,'flow_rows_verified':flow_rows,
       'comparisons':comparisons,'new_detector_forwards':0,'training_updates':0,
       'independent_source_accuracy':None,'board_execution':False,'whole_goal_complete':False}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    files=[protocol,ROOT/'job_id.txt']+list((ROOT/'tools').glob('*.py'))+list((ROOT/'tools').glob('*.slurm'))
    for c in summary['conditions']:files+=list((ROOT/'results'/c['name']).iterdir())
    files += [ROOT/'results/summary.json',ROOT/'results/exact_replay_gate.json',ROOT/'results/independent_verification.json']
    files += list((ROOT/'logs').glob('replay-*'))
    assert len(files)==len(set(files)) and all(path.is_file() for path in files)
    manifest=[{'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)} for path in sorted(files)]
    mp=ROOT/'results/delivery_manifest.json';mp.write_text(json.dumps(manifest,indent=2))
    archive=ROOT/'results/delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tf:
        for path in sorted(files):tf.add(path,arcname=path.relative_to(ROOT).as_posix())
        tf.add(mp,arcname='delivery_manifest.json')
    record={'manifest_files':len(manifest),'archive_members':len(manifest)+1,'bytes':archive.stat().st_size,
            'sha256':sha(archive),'manifest_sha256':sha(mp)}
    (ROOT/'results/delivery_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
if __name__=='__main__':main()
