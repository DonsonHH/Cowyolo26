from pathlib import Path
from datetime import datetime,timezone
import os,sys,socket,json,gzip
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
sys.path.insert(0,str(ROOT/'tools'))
import run_control as actual
p=actual.load(ROOT/'protocol/control_v1.json');rows=[]
for c in [r for r in p['caches'] if r['board_reference']]:
    trace,log=actual.replay(c,p,actual.LoggedBase);trace=actual.canonical(trace);expected=actual.gz(c['trace_file'])
    row={'cache':c['id'],'baseline_event_paths':{k:{'actual':trace[k],'expected':expected[k],'exact':trace[k]==expected[k]} for k in ['confirmed_only_events','handoff_events']},
        'new_model_forwards':0,'counter_config_changed':False}
    post_a,post_b=trace['post_tracker'],expected['post_tracker']
    row['post_row_counts']=[len(post_a),len(post_b)]
    mismatch=[]
    if len(post_a)==len(post_b):
        for a,b in zip(post_a,post_b):
            if a!=b:mismatch.append({'actual':a,'expected':b})
    row['first10_post_differences']=mismatch[:10]
    row['post_difference_rows_given_equal_lengths']=len(mismatch)
    rows.append(row)
result={'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'rows':rows,'new_model_forwards':0,'control_variant_executed':False}
f=ROOT/'results/cpu_vs_board_baseline_diagnostic.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({
    'rows':[{'cache':r['cache'],'event_paths_exact':{k:v['exact'] for k,v in r['baseline_event_paths'].items()},'row_counts':r['post_row_counts'],
        'first_event_difference':next(({k:v for k,v in r['baseline_event_paths'].items() if not v['exact']}),{})} for r in rows]}),flush=True)
