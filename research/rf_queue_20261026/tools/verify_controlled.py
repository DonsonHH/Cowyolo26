"""Independent RF outcomes and tick-ledger arithmetic; no runtime module imports."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,tarfile

ROOT=Path(__file__).resolve().parents[1]
record=json.loads((ROOT/'results/bundle_record.json').read_text());bundle=ROOT/'results/rf_queue_delivery.tar.gz'
assert bundle.stat().st_size==record['bytes'] and hashlib.sha256(bundle.read_bytes()).hexdigest()==record['sha256']
dest=ROOT/'delivery'
if not dest.exists():
    dest.mkdir()
    with tarfile.open(bundle) as tf:tf.extractall(dest,filter='data')
files=json.loads((dest/'delivery_manifest.json').read_text())
for row in files:
    path=(dest/row['path']).resolve();assert path.is_relative_to(dest.resolve())
    assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
for relative in ['tools/association.py','tools/queue_simulator.py','tools/run_controlled.py','protocol/controlled_rf_queue_v1.json']:
    assert hashlib.sha256((ROOT/relative).read_bytes()).digest()==hashlib.sha256((dest/relative).read_bytes()).digest()
out=dest/'results/controlled';summary=json.loads((out/'summary.json').read_text());p=summary['protocol'];q=p['queue']
truth=json.loads((out/'inputs/scoring_truth_only.json').read_text());registry=json.loads((out/'inputs/runtime_tag_registry.json').read_text())
cache=json.loads((out/'inputs/runtime_visual_candidates.json').read_text())
def count(truth,outputs):
    byid={r['event_id']:r for r in outputs};assert len(byid)==len(outputs)
    c=Counter()
    for t in truth:
        r=byid.get(t['event_id']);pred=None if r is None else r['identity_candidate']
        state='M' if r is None else 'U' if pred is None else 'C' if pred==t['expected_identity'] else 'W'
        c[state]+=1
    return {'N':len(truth),**{k:c[k] for k in ['C','W','U','M']},'extra_outputs':sum(r['event_id'] not in {t['event_id'] for t in truth} for r in outputs)}
def reid(name,snapshot):
    r=cache[name].get(snapshot)
    return r['predicted_identity'] if r is not None and r['similarity']>=r['threshold'] else None

rf_verified=[]
for row in summary['rf_cases']:
    case=out/'rf_cases'/row['scenario'];events=json.loads((case/'runtime_passages.json').read_text());reads=json.loads((case/'runtime_reads.json').read_text())
    expected=[];used=set()
    # Derive the one-code/one-window association from immutable observations.
    for event in sorted(events,key=lambda r:(r['closed']+5,r['event_id'])):
        deadline=event['closed']+5
        eligible=lambda e,r:r['reader']==e['reader'] and e['opened']-1<=r['captured']<=e['closed']+1
        candidates=[r for r in reads if r['valid'] and r['received']>=r['captured'] and r['received']<=deadline and r['read_id'] not in used and eligible(event,r)]
        codes={r['code'] for r in candidates}
        shared=any(sum(other['opened']<=deadline and eligible(other,r) for other in events)>1 for r in candidates)
        if len(codes)==1 and not shared and next(iter(codes)) in registry:
            identity=registry[next(iter(codes))];used.update(r['read_id'] for r in candidates)
        else:identity=reid(row['condition'],event['snapshot_id']) if event['snapshot_id'] else None
        expected.append({'event_id':event['event_id'],'identity_candidate':identity})
    actual=json.loads((case/(row['condition']+'_outputs.json')).read_text())
    assert {r['event_id']:r['identity_candidate'] for r in expected}=={r['event_id']:r['identity_candidate'] for r in actual}
    computed=count(truth,actual);assert all(row['score'][k]==v for k,v in computed.items())
    rf_verified.append({'scenario':row['scenario'],'condition':row['condition'],**computed})

traces={};trace_checks=[]
for file in sorted((out/'queue_cases').glob('*/*_cost*.json')):
    trace=json.loads(file.read_text());timeline=trace['resource_timeline'];counts=Counter(timeline)
    assert len(timeline)==q['horizon_ticks'] and dict(counts)==trace['resource_ticks']
    jobs=trace['jobs'];assert len(jobs)==trace['jobs_total']
    assert sum(j['work_ticks'] for j in jobs)==counts['background']
    assert Counter(j['status'] for j in jobs)==trace['background_status_counts']
    assert all(0<=j['work_ticks']<=trace['background_cost_ticks'] for j in jobs)
    assert len(trace['foreground_records'])==trace['foreground_frames']==120
    assert sum(q['foreground_cost_ticks']-r['remaining'] for r in trace['foreground_records'])==counts['frontend']
    late=sum(r['status'] in ['LATE','EXPIRED'] or r['status']=='PENDING_AT_HORIZON' and r['deadline_tick']<=1200 for r in trace['foreground_records'])
    assert late==trace['foreground_deadline_misses']
    maximum=0
    for t in range(q['horizon_ticks']):
        waiting=sum(j['ready_tick']<=t and (j['started_tick'] is None or j['started_tick']>=t) and
                    (j['finished_tick'] is None or j['finished_tick']>t) and j['status'] not in ['REJECTED_CAPACITY','DISABLED'] for j in jobs)
        maximum=max(maximum,waiting)
    assert maximum==trace['max_waiting']<=q['waiting_capacity']
    if trace['policy'] in ['cooperative','fits_next_gap','disabled']:
        assert trace['foreground_deadline_misses']==0
        assert all(timeline[t]=='frontend' for start in range(0,1200,10) for t in range(start,start+3))
    if trace['policy']=='nonpreemptive':
        for j in jobs:
            if j['started_tick'] is not None:
                end=j['finished_tick'] if j['status'] in ['COMPLETED','COMPLETED_LATE'] else 1200
                assert all(kind=='background' for kind in timeline[j['started_tick']:end])
    if trace['policy']=='fits_next_gap':
        for j in jobs:
            if j['status']=='COMPLETED':assert j['finished_tick']<=j['started_tick']+(10-j['started_tick']%10)
    for job in jobs:
        if job['status']=='COMPLETED':assert job['finished_tick']<=job['deadline_tick'] and job['work_ticks']==trace['background_cost_ticks']
        if job['status']=='COMPLETED_LATE':assert job['finished_tick']>job['deadline_tick']
        assert job['finished_tick'] is None or job['finished_tick']<=1200
    relative=file.relative_to(out).as_posix();traces[relative]=trace
    trace_checks.append({'trace':relative,'jobs':len(jobs),'completed':trace['jobs_on_time'],'frontend_misses':late,'integrity':'PASS'})

queue_verified=0
for row in summary['queue_cases']:
    trace=traces[row['trace_file']];truth_q=json.loads((out/'queue_cases'/row['load']/'scoring_truth_only.json').read_text())
    outputs=[{'event_id':j['job_id'],'identity_candidate':reid(row['condition'],j['snapshot_id']) if j['status']=='COMPLETED' else None} for j in trace['jobs']]
    computed=count(truth_q,outputs);assert all(row['score'][k]==v for k,v in computed.items())
    assert row['jobs_on_time']==sum(j['status']=='COMPLETED' for j in trace['jobs'])
    queue_verified+=1
assert len(rf_verified)==40 and len(traces)==36 and queue_verified==180
record={'status':'PASS','manifest_files_verified':len(files),'bundle_sha256':record['sha256'],
        'independent_rf_conditions':len(rf_verified),'independent_queue_condition_scores':queue_verified,
        'queue_trace_arithmetic_checks':len(trace_checks),'rf_condition_counts':rf_verified,'trace_checks':trace_checks,
        'scope':'Independent observation association, outcome denominators, capacity/resource/deadline trace arithmetic; not hardware timing or a second live neural inference run'}
(ROOT/'results/independent_verification.json').write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k not in ['rf_condition_counts','trace_checks']},indent=2))
