"""Fast actual-counter replay from frozen O8 observations; red on missing12."""
from pathlib import Path
import argparse,json,gzip,importlib.util,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
parser=argparse.ArgumentParser();parser.add_argument('--require-total',type=int);a=parser.parse_args()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
sys.path.insert(0,str(PROJECT/'pynq_frontend_port_20261029'))
import cow_tracker.confirmation_counter as counter
rows=[]
for name,path,expected in [('old_mosaic100',PROJECT/'pynq_rot192_eval_20261029/board_delivery/results_v2/original/stride5_counter_trace.json.gz',11),
    ('new_mosaic050',PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/stride5_counter_trace.json.gz',10)]:
    trace=json.loads(gzip.decompress(path.read_bytes()))
    engine=counter.ConfirmationHandoffCounter(lower=.4,upper=.6,stable_samples=3,maximum_gap_s=2.)
    events=[]
    for row in trace['observations']:
        confirmed={int(k):v for k,v in row['confirmed_positions'].items()};tentative={int(k):v for k,v in row['tentative_positions'].items()}
        for event in engine.update(row['time_s'],confirmed,tentative,set(row['confirmed_IDs'])):events.append({**event,'frame0':row['frame0']})
    assert events==trace['handoff_events']
    chosen=[e for e in events if 8912<=e['frame0']<=10873]
    total=sum(e['direction']=='A->B' for e in chosen);assert total==expected
    rows.append({'model':name,'observation_ticks':len(trace['observations']),'down_count':total,'events_exact_to_real_ARM_output':True})
print(json.dumps({'actual_counter_replay':rows,'human_confirmed_total':12,'human_event_GT_available':False,'new_neural_forwards':0}),flush=True)
if a.require_total is not None:assert rows[-1]['down_count']==a.require_total,('new model count',rows[-1]['down_count'],'required human total',a.require_total)
