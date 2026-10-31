"""No neural forwards: locate baseline trace equality failure causally."""
from pathlib import Path
import os,socket,sys,json,gzip,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
sys.path.insert(0,str(PROJECT/'pynq_frontend_port_20261029'))
from frame_pipeline import FramePipeline
p=json.loads((ROOT/'protocol/study_v1.json').read_text())
prior=Path(p['prior_quality_remote'])
video=p['videos'][0]
records=[]
for mode in ['FP32','QDQ']:
    # The failed run had already exactly compared both original raw outputs
    # against these caches; this probe performs only tracking on cached boxes.
    raw=json.loads(gzip.decompress((prior/'original'/mode/'raw_predictions.json.gz').read_bytes()))
    byframe={r['frame0']:r['predictions'] for r in raw}
    pipe=FramePipeline(video,p['tracker_config'],p['counter_kwargs'])
    trace={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
    for frame in range(0,video['decode_end_exclusive'],5):
        row=pipe.update(frame,byframe[frame]);trace['observations'].append(row['observation'])
        for key in ['post_tracker','confirmed_only_events','handoff_events']:trace[key].extend(row[key])
    expected=json.loads(gzip.decompress((prior/'original'/mode/'stride5_counter_trace.json.gz').read_bytes()))
    direct=trace==expected
    normalized=json.loads(json.dumps(trace))
    assert not direct and normalized==expected,mode
    key_types=sorted({type(k).__name__ for row in trace['observations'] for k in row['confirmed_positions']})
    expected_types=sorted({type(k).__name__ for row in expected['observations'] for k in row['confirmed_positions']})
    assert key_types==['int'] and expected_types==['str']
    records.append({'mode':mode,'observation_ticks':len(trace['observations']),'direct_equality':direct,
        'after_JSON_roundtrip_full_trace_exact':normalized==expected,'before_key_types':key_types,'stored_key_types':expected_types,
        'model_forwards':0,'counter_or_tracker_parameters_changed':False})
result={'status':'BASELINE_TRACE_FAILURE_IS_JSON_INT_VS_STRING_KEYS_ALL_VALUES_EVENTS_AND_IDS_EXACT',
    'job_id':os.environ['SLURM_JOB_ID'],'records':records,'new_model_forwards':0,'new_training_updates':0}
target=ROOT/'results/baseline_trace_probe.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
