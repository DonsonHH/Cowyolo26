from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'rot192_event_diagnosis_20261030'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
for name in ['input','protocol','evidence']:(ROOT/name).mkdir(exist_ok=True)
for source in (OLD/'input').iterdir():
    if not source.is_file() or source.name.endswith('_summary.json'):continue
    f=ROOT/'input'/source.name
    if f.exists():assert f.read_bytes()==source.read_bytes()
    else:f.write_bytes(source.read_bytes())
p=load(OLD/'protocol/audit_v1.json');caches=[]
for condition,base,review in [('old_O8',PROJECT/'pynq_rot192_eval_20261029/board_delivery/results_v2/original',PROJECT/'pynq_rot192_eval_20261029/results/final_review.json'),
    ('new_O8',PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original',PROJECT/'pynq_mosaic192_eval_20261030/results/final_review.json')]:
    verified=load(review);assert verified['whole_goal_complete'] is False
    record=load(base.parent/'record.json');scene=next(r for r in record['scenes'] if r['scene']=='original')
    summary=ROOT/'input'/(condition+'_summary.json');save(summary,[r for r in scene['metrics'] if r['stride']==5])
    raw=base/'raw_predictions.json.gz';trace=base/'stride5_counter_trace.json.gz'
    caches.append({'condition':condition,'group':'two_frozen_real_O8_models','size':192,'seed':26,'raw_file':str(raw.resolve()),'raw_sha256':sha(raw),
        'trace_file':str(trace.resolve()),'trace_sha256':sha(trace),'summary_file':str(summary.resolve()),'summary_sha256':sha(summary),
        'review_file':str(review.resolve()),'review_sha256':sha(review)})
for key in ['prior15_training_review_sha256','actual_model_count_regression','created_UTC']:p.pop(key,None)
p.update({'status':'FROZEN_BEFORE_TWO_REAL_O8_MODELS_READ_ONLY_EVENT_COMPARISON','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'caches':caches,'actual_model_count_regression':[11,10],'conditions':2,'expected_cases':4,'expected_associations':2864,'expected_reference_rows':2324,
    'expected_oracle_paths':12,'source_used_for_development':True,'reference_boxes_are_development640_model_outputs_not_GT':True,
    'input_sha256':{f.name:sha(f) for f in (ROOT/'input').glob('*') if f.is_file()},'model_forwards':0,'training_updates':0,'board_actions':0,'whole_goal_complete':False})
script=(OLD/'tools/run_audit.py').read_text(encoding='utf-8')
script=script.replace('len(allcases)==6 and casepaths==18 and referencerows==3*2*581','len(allcases)==4 and casepaths==12 and referencerows==2*2*581')
script=script.replace('THREE_FIXED_NUMERIC_IMPLEMENTATIONS_SIX_CASES18_REFERENCE_CONDITIONED_PATHS_COMPLETE','TWO_REAL_O8_MODELS_FOUR_CASES12_REFERENCE_CONDITIONED_PATHS_COMPLETE')
script=script.replace("'cached_conditions':3","'cached_conditions':2").replace("'counter_oracle_paths':18","'counter_oracle_paths':12")
file=ROOT/'tools/run_audit.py';assert not file.exists();file.write_text(script,encoding='utf-8',newline='\n');ast.parse(script)
verifier=(OLD/'tools/verify_independent.py').read_text(encoding='utf-8')
verifier=verifier.replace('checks==6 and oracles==18 and rows_checked==3486 and assignments==4296','checks==4 and oracles==12 and rows_checked==2324 and assignments==2864')
verifier=verifier.replace('ALL6_ROT192_IMPLEMENTATION_CASES3486_REFERENCE_ROWS4296_ASSOCIATIONS_AND18_COUNTER_PATHS_VERIFIED','ALL4_O8_MODEL_CASES2324_REFERENCE_ROWS2864_ASSOCIATIONS_AND12_COUNTER_PATHS_VERIFIED')
file=ROOT/'tools/verify_independent.py';assert not file.exists();file.write_text(verifier,encoding='utf-8',newline='\n');ast.parse(verifier)
p['analysis_script_sha256']=sha(ROOT/'tools/run_audit.py');p['separate_verifier_sha256']=sha(file)
save(ROOT/'protocol/audit_v1.json',p)
red=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/replay_count.py'),'--require-total','12'],capture_output=True,text=True,encoding='utf-8')
assert red.returncode!=0 and 'required human total' in red.stderr and '"down_count": 10' in red.stdout
save(ROOT/'evidence/target_count_red_replay.json',{'returncode':red.returncode,'stdout':red.stdout,'stderr':red.stderr,'no_new_neural_forwards':True,
    'scope':'actual_counter_on_frozen_O8_observations;human_total_only;red_is_unresolved_quality_not_software_crash'})
print(json.dumps({'cases':4,'oracle_paths':12,'real_O8_counts':[11,10],'new_neural_forwards':0}))
