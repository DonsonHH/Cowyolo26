from pathlib import Path,PurePosixPath
from collections import defaultdict
import csv,hashlib,json,shutil,tarfile
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(newline='',encoding='utf-8')))
def main():
    r=load(ROOT/'results/probe_delivery_record.json');archive=ROOT/'results/probe_delivery.tar.gz';dest=ROOT/'probe_delivery'
    assert not dest.exists() and sha(archive)==r['sha256'] and archive.stat().st_size==r['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==r['manifest_sha256']
        items=json.loads(raw);expected={x['path']:x for x in items};members=tf.getmembers()
        assert len(items)==len(expected)==r['manifest_files']==10 and len(members)==r['archive_members']==11
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    protocol=load(ROOT/'protocol/clock_v1.json');cases=load(ROOT/'protocol/case_probe_v1.json')
    summary=load(dest/'results/case_probe/summary.json');assert summary['probe_protocol_sha256']==sha(ROOT/'protocol/case_probe_v1.json')==sha(dest/'protocol/case_probe_v1.json')
    details=[];states_checked=0
    for case,result in zip(cases['cases'],summary['cases']):
        source=next(x for x in protocol['sources'] if x['name']==case['source']);rel=source['remote_folder'].split('/counting_recovery_20261028/',1)[1]
        folder=PROJECT/'counting_recovery_20261028/delivery'/rel;tid=case['target_ID']
        observations=load(dest/'results/case_probe'/result['trace_file']);assert sha(dest/'results/case_probe'/result['trace_file'])==result['sha256']
        rows=read(folder/'source_warmup_tracks.csv')+read(folder/'source_tracks.csv')
        positions={int(row['source_frame']):float(row['axis_position']) for row in rows if int(row['track_id'])==tid}
        frames={row['source_frame']:row for row in observations};raw=defaultdict(list)
        for row in read(folder/'pretracker_boxes.csv'):raw[int(row['frame'])].append([*[float(row[k]) for k in ['x1','y1','x2','y2']],float(row['confidence']),0])
        state=None
        for frame in range(0,9391,5):
            pos=positions.get(frame);now=frame/25
            if pos is None:
                if state:state.update(candidate=None,streak=0)
            else:
                if state is None:state={'origin':None,'candidate':None,'streak':0,'last_seen':-1e30}
                if now-state['last_seen']>2:state.update(origin=None,candidate=None,streak=0)
                state['last_seen']=now;zone='A' if pos<.4 else 'B' if pos>.6 else None
                if zone is None:state.update(candidate=None,streak=0)
                else:
                    state['streak']=state['streak']+1 if state['candidate']==zone else 1;state['candidate']=zone
                    if state['streak']>=3:state['origin']=zone
            if frame in frames:
                observed=frames[frame];assert observed['counter_state']==state and observed['target_output_y']==pos
                assert observed['all_raw_boxes']==raw[frame];states_checked+=1
        seen=[x for x in observations if x['target_tracker_state']]
        unconfirmed=[x['source_frame'] for x in observations if any(t['pool']=='tracked_pool' and not t['is_activated'] for t in x['target_tracker_state'])]
        origins=[];previous=None
        for x in observations:
            origin=x['counter_state']['origin'] if x['counter_state'] else None
            if origin!=previous:origins.append({'frame':x['source_frame'],'origin':origin});previous=origin
        details.append({'seed':source['seed'],'target_ID':tid,'first_internal_presence':seen[0]['source_frame'],
          'internal_track_start_frame':seen[0]['target_tracker_state'][0]['start_source_frame'],
          'unconfirmed_frames':unconfirmed,'first_ROI_output_frame':min(positions),
          'A_output_frames':[f for f,y in positions.items() if y<.4],
          'B_output_frames':[f for f,y in positions.items() if y>.6],
          'counter_origin_transitions':origins,'full_replay_exact':result['full_original_tracks_history_events_exact']})
    assert states_checked==63
    record=load(ROOT/'results/stability_case_record.json');assert record['visual_QA']=='PENDING'
    for row in record['figures']:assert sha(ROOT/'source_case'/row['file'])==row['sha256']
    for row in record['raw_frames']:assert sha(ROOT/'source_case'/row['file'])==row['sha256']
    shutil.copyfile(ROOT/'results/stability_case_record.json',ROOT/'results/stability_case_record_before_visual_QA.json')
    record.update(visual_QA='PASS',manual_observations=[
       'All9nativeframes and all3sixpanel overlayfigures inspected; orangegates remainfixed.',
       'seed26 ID95 and seed27 ID57 highlight the whitepatterned object onleft; seed28 ID117 highlights the darker object behind it.',
       'Do not equate nearbytime selectedIDs acrossall3seeds with the samephysicalcow or independent reference.'])
    (ROOT/'results/stability_case_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    out={'status':'TEN_PROBE_FILES_AND_63_COUNTER_STATES_NATIVE_RAW_INPUTS_VERIFIED','cases':details,
         'counter_states_checked':63,'files':10,'visual_figures':4,'native_frames':9,'selected_track_rows':31,
         'independent_ground_truth':False,'detector_or_counter_changed':False,'whole_goal_complete':False}
    target=ROOT/'results/probe_local_verification.json';assert not target.exists();target.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':main()
