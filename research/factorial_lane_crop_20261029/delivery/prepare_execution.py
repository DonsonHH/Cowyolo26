from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,ast
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads((ROOT/'protocol/crop_v1.json').read_text());assert len(p['models'])==15 and p['new_inference_job_submitted'] is False
tools=ROOT/'tools';tools.mkdir(exist_ok=False);inputs=ROOT/'input';inputs.mkdir(exist_ok=False)
for name in ['zone_counter.py','confirmation_counter.py','event_metrics.py']:
    shutil.copyfile(PROJECT/'detector_factorial_20261029/input'/name,inputs/name)
original=PROJECT/'lowres_roi_20261029/tools/run_roi.py';source=original.read_text()
start=source.index("    protocol=load(ROOT/'protocol/roi_v1.json')")
end=source.index("    out=ROOT/'results/roi'",start)
replacement='''    protocol=load(ROOT/'protocol/crop_v1.json');baseline=Path(protocol['full_input_results_remote'])
    assert sha(baseline/'summary.json')==protocol['full_input_summary_sha256']
    assert sha(baseline.parent/'all_checkpoints_frozen.json')==protocol['all15_checkpoint_freeze_sha256']
    assert sha(Path(protocol['counter_module_remote']))==protocol['counter_module_sha256']
    execution=load(ROOT/'protocol/execution_v1.json');assert execution['protocol_sha256']==sha(ROOT/'protocol/crop_v1.json')
    assert execution['run_script_sha256']==sha(Path(__file__))
    for name,digest in execution['input_module_sha256'].items():assert sha(ROOT/'input'/name)==digest
    counter_root=Path(protocol['counter_module_remote']).parents[1]
    sys.path[:0]=[str(counter_root/'tools'),str(counter_root/'input')]
    import run_baseline_v2 as prior
    prior.protocol=load(counter_root/'protocol/baseline_v2_path_fix.json')
    assert prior.protocol['counter_kwargs']==protocol['counter_kwargs'] and prior.protocol['prediction']==protocol['prediction']
'''
source=source[:start]+replacement+source[end:]
source=source.replace("baseline/'results/baseline'/spec['name']","baseline/spec['name']")
source=source.replace("baseline/'results/baseline/video_metrics.json'","baseline/'video_metrics.json'")
source=source.replace('31848','39810').replace('32808','41010')
source=source.replace('len(reg)==36','len(reg)==45').replace('len(tensor_rows)==96','len(tensor_rows)==120').replace('len(all_metrics)==72','len(all_metrics)==90')
source=source.replace('ALL36_FULLINPUT_TRACES_AND72_COUNTER_EVENT_LISTS_EXACT_BEFORE_ROI_FORWARD','ALL45_FULLINPUT_TRACES_AND90_COUNTER_EVENT_LISTS_EXACT_BEFORE_ROI_FORWARD')
source=source.replace('ALL12_FIXED_CHANNEL_INPUT_CONDITIONS_AND72_COUNTER_PATHS_COMPLETE','ALL15_NEW_MODELS_FIXED_CHANNEL_INPUT_AND90_COUNTER_PATHS_COMPLETE')
source=source.replace("'condition_count':12","'condition_count':15").replace("'baseline_full_cache_traces_exact':36","'baseline_full_cache_traces_exact':45")
source=source.replace("'baseline_full_cache_counter_paths_exact':72","'baseline_full_cache_counter_paths_exact':90").replace("'new_crop_counter_paths':72","'new_crop_counter_paths':90")
source=source.replace("sha(ROOT/'protocol/roi_v1.json')","sha(ROOT/'protocol/crop_v1.json')")
anchor="identity=(active['spec']['name'],meta['frame0'],size);digest=hashlib.sha256(array.tobytes()).hexdigest()"
assert source.count(anchor)==1
source=source.replace(anchor,anchor+"\n                controlkey=identity[0]+'_f'+str(identity[1])+'_s'+str(identity[2])\n                assert digest==protocol['expected_NN_input_hashes_24_source_frame_sizes'][controlkey],controlkey")
ast.parse(source);script=tools/'run_crop.py';script.write_text(source,newline='\n')
record={'status':'EXECUTION_BOUND_BEFORE_NEW_INFERENCE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'protocol_sha256':sha(ROOT/'protocol/crop_v1.json'),'adapted_from_verified_script_sha256':sha(original),'run_script_sha256':sha(script),
 'input_module_sha256':{f.name:sha(f) for f in inputs.iterdir()},'all15_weights_and_old24_actual_NN_inputs_bound':True,
 'new_network_forwards_expected':39810,'new_counter_paths_expected':90,'whole_goal_complete':False}
file=ROOT/'protocol/execution_v1.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'run_script_sha256':sha(script),'execution_protocol_sha256':sha(file),'syntax_checked':True,'not_executed':True}))
