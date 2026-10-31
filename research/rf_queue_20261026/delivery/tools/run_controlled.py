"""Run controlled association and queue experiments from frozen real scores."""
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import csv,hashlib,json,os
from association import Passage,Read,Candidate,Resolver,apply_visual,score_ledger
from queue_simulator import simulate

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'rf_queue';SOURCE=PROJECT/'identity_training/results/study'
OUT=ROOT/'results/controlled';OUT.mkdir(parents=True,exist_ok=False)
protocol_path=ROOT/'protocol/controlled_rf_queue_v1.json';p=json.loads(protocol_path.read_text())
assert hashlib.sha256((SOURCE/'summary.json').read_bytes()).hexdigest()==p['source_study_summary_sha256']
study=json.loads((SOURCE/'summary.json').read_text());sources={};cache={}
for condition in p['source_conditions']:
    file=SOURCE/condition['name']/'evaluation_predictions.json'
    assert hashlib.sha256(file.read_bytes()).hexdigest()==condition['prediction_file_sha256']
    sources[condition['name']]=json.loads(file.read_text())
first=sources[p['source_conditions'][0]['name']]
assert len(first)==60
identities=sorted({r['identity'] for r in first})
tags={identity:'tag-'+hashlib.sha256(('synthetic-registry:'+identity).encode()).hexdigest()[:12] for identity in identities}
registry={code:identity for identity,code in tags.items()}
events=[];truth=[]
for i,row in enumerate(first):
    opaque=hashlib.sha256(('constructed-event:'+row['relative_path']).encode()).hexdigest()[:20]
    snapshot=hashlib.sha256(('snapshot:'+row['relative_path']).encode()).hexdigest()
    opened=20+i*50
    events.append(Passage('p-'+opaque,opened,opened+10,snapshot,'A->B' if i%2==0 else 'B->A'))
    truth.append({'event_id':'p-'+opaque,'expected_identity':row['identity'],'snapshot_id':snapshot,'source_query':row['relative_path'],'visual_registered':row['is_known']})
for condition in p['source_conditions']:
    rows=sources[condition['name']]
    assert [r['relative_path'] for r in rows]==[r['relative_path'] for r in first]
    cache[condition['name']]={event.snapshot_id:Candidate(row['predicted_id'],row['similarity'],condition['threshold'],condition['name']) for event,row in zip(events,rows)}
inputs=OUT/'inputs';inputs.mkdir()
(inputs/'runtime_events.json').write_text(json.dumps([asdict(e) for e in events],indent=2))
(inputs/'runtime_tag_registry.json').write_text(json.dumps(registry,indent=2))
(inputs/'runtime_visual_candidates.json').write_text(json.dumps({name:{snapshot:asdict(c) for snapshot,c in values.items()} for name,values in cache.items()},indent=2))
(inputs/'scoring_truth_only.json').write_text(json.dumps(truth,indent=2))
# Observation-only runtime data have no expected ID, class/cohort, source path or query identity fields.
for event in [asdict(e) for e in events]:assert set(event)=={'event_id','opened','closed','snapshot_id','direction','reader'}

rf_results=[]
for scenario in p['rf_scenarios']:
    case_events=list(events);reads=[]
    for i,(event,target) in enumerate(zip(events,truth)):
        code=tags[target['expected_identity']];captured=event.opened+5;received=captured
        if scenario in ['missing_all','missing_snapshot']:continue
        if scenario=='received_after_deadline':received=event.closed+15
        if scenario=='wrong_single_valid_code':code=tags[identities[(identities.index(target['expected_identity'])+1)%len(identities)]]
        reads.append(Read(f'{scenario}-read-{i}',code,captured,received))
        if scenario=='duplicate_same_code':
            reads.extend(Read(f'{scenario}-read-{i}-duplicate-{j}',code,captured+j,received+j) for j in [1,2])
        if scenario=='multi_code_conflict':
            alternate=tags[identities[(identities.index(target['expected_identity'])+1)%len(identities)]]
            reads.append(Read(f'{scenario}-read-{i}-conflict',alternate,captured+1,received+1))
    if scenario=='missing_snapshot':case_events=[Passage(e.event_id,e.opened,e.closed,None,e.direction,e.reader) for e in events]
    if scenario=='visual_event_missed_every_fifth':case_events=[e for i,e in enumerate(events) if i%5!=4]
    case_dir=OUT/'rf_cases'/scenario;case_dir.mkdir(parents=True)
    (case_dir/'runtime_passages.json').write_text(json.dumps([asdict(e) for e in case_events],indent=2))
    (case_dir/'runtime_reads.json').write_text(json.dumps([asdict(r) for r in reads],indent=2))
    for condition in p['source_conditions']:
        resolver=Resolver(case_events,reads,registry)
        horizon=max([e.closed+5 for e in events]+[r.received for r in reads])+1
        for tick in sorted({e.closed+5 for e in case_events}|{r.received for r in reads}|{horizon}):resolver.advance(tick)
        outputs=[apply_visual(result,cache[condition['name']]) for result in resolver.outputs.values()]
        # Persist runtime outputs before the separate scoring function receives truth.
        (case_dir/(condition['name']+'_outputs.json')).write_text(json.dumps(outputs,indent=2))
        score=score_ledger(truth,outputs)
        row={'scenario':scenario,'condition':condition['name'],'score':score,
             'source_counts':dict(Counter(o['source'] for o in outputs)),'reason_counts':dict(Counter(o['reason'] for o in outputs if o['reason'])),
             'late_observation_links':sum(len(o['late_observation_ids']) for o in outputs)}
        rf_results.append(row)

q=p['queue'];queue_results=[]
for load_name,load in q['loads'].items():
    arrivals=[];queue_truth=[]
    for i in range(load['jobs']):
        j=i%len(events);ready=load['first_tick']+(i//load['batch_size'])*load['batch_spacing_ticks'] if load_name=='burst' else load['first_tick']+i*load['spacing_ticks']
        event_id=f'{load_name}-constructed-{i:03d}'
        arrivals.append({'job_id':event_id,'ready_tick':ready,'snapshot_id':events[j].snapshot_id})
        queue_truth.append({'event_id':event_id,'expected_identity':truth[j]['expected_identity']})
    queue_dir=OUT/'queue_cases'/load_name;queue_dir.mkdir(parents=True)
    (queue_dir/'runtime_arrivals.json').write_text(json.dumps(arrivals,indent=2));(queue_dir/'scoring_truth_only.json').write_text(json.dumps(queue_truth,indent=2))
    for cost in q['background_cost_ticks']:
        for policy in q['policies']:
            simulation=simulate(arrivals,policy,service=cost,horizon=q['horizon_ticks'],period=q['foreground_period_ticks'],frontend_cost=q['foreground_cost_ticks'],capacity=q['waiting_capacity'],ttl=q['completion_deadline_after_ready_ticks'])
            file=queue_dir/f'{policy}_cost{cost}.json';file.write_text(json.dumps(simulation,indent=2))
            for condition in p['source_conditions']:
                outputs=[]
                for job in simulation['jobs']:
                    result={'event_id':job['job_id'],'identity_candidate':None,'snapshot_id':job['snapshot_id'],'source':'unresolved','reason':job['status']}
                    if job['status']=='COMPLETED':result=apply_visual(result,cache[condition['name']])
                    outputs.append(result)
                score=score_ledger(queue_truth,outputs)
                queue_results.append({'load':load_name,'background_cost_ticks':cost,'policy':policy,'condition':condition['name'],
                    'score':{k:v for k,v in score.items() if k!='per_event'},'jobs_total':simulation['jobs_total'],'jobs_on_time':simulation['jobs_on_time'],
                    'background_status_counts':simulation['background_status_counts'],'max_waiting':simulation['max_waiting'],
                    'foreground_frames':simulation['foreground_frames'],'foreground_deadline_misses':simulation['foreground_deadline_misses'],
                    'foreground_response_p95_ticks':simulation['foreground_response_p95_ticks'],'trace_file':str(file.relative_to(OUT))})

flat=[]
for row in rf_results:flat.append({'scenario':row['scenario'],'condition':row['condition'],**{k:v for k,v in row['score'].items() if k!='per_event'}})
with (OUT/'rf_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
with (OUT/'queue_summary.csv').open('w',newline='') as f:
    rows=[{k:v for k,v in r.items() if k not in ['score','background_status_counts']}|r['score'] for r in queue_results]
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),'protocol':p,
         'rf_cases':rf_results,'queue_cases':queue_results,'rf_condition_count':len(rf_results),'queue_condition_count':len(queue_results),
         'queue_trace_count':len(q['loads'])*len(q['background_cost_ticks'])*len(q['policies']),
         'scope':p['scope'],'execution_adapter':'Frozen candidate-score cache; the queue cost model does not execute or time neural inference'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'job_id':os.environ['SLURM_JOB_ID'],'rf_conditions':len(rf_results),'queue_conditions':len(queue_results),'queue_traces':summary['queue_trace_count']},indent=2),flush=True)
print(json.dumps({'rf_C_seed26':[{'scenario':r['scenario'],**{k:v for k,v in r['score'].items() if k!='per_event'}} for r in rf_results if r['condition']=='C_letterbox_trained_seed26']},indent=2),flush=True)
