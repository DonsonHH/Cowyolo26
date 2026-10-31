from pathlib import Path
import json,hashlib,ast
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
source=(PROJECT/'lowres_roi_20261029/tools/verify_independent.py').read_text()
source=source.replace("ROOT/'protocol/roi_v1.json'","ROOT/'protocol/crop_v1.json'")
source=source.replace('31848','39810').replace('32808','41010').replace('len(gate[\'traces\'])==36','len(gate[\'traces\'])==45')
source=source.replace("s['baseline_full_cache_counter_paths_exact']==72","s['baseline_full_cache_counter_paths_exact']==90")
source=source.replace("s['new_crop_counter_paths']==72","s['new_crop_counter_paths']==90")
start=source.index("prior=PROJECT/'lowres_baseline_20261029/delivery'")
end=source.index('def event_optimum(',start)
replacement='''prior=PROJECT/'detector_factorial_20261029/delivery/results/evaluation'
assert sha(prior/'summary.json')==p['full_input_summary_sha256']
assert sha(PROJECT/'detector_factorial_20261029/delivery/results/all_checkpoints_frozen.json')==p['all15_checkpoint_freeze_sha256']
gate=load(OUT/'full_input_cache_regression_gate.json');assert gate['new_model_forwards_at_gate']==0 and gate['tracker_updates']==41010
assert len(gate['traces'])==45 and all(x['entire_trace_exact'] for x in gate['traces']) and sum(x['observation_ticks'] for x in gate['traces'])==41010
tensorrows=load(OUT/'input_tensor_controls.json');assert len(tensorrows)==120
for row in tensorrows:
    key=row['scene']+'_f'+str(row['frame0'])+'_s'+str(row['input_size'])
    assert row['tensor_sha256']==p['expected_NN_input_hashes_24_source_frame_sizes'][key]
controls=PROJECT/'lowres_roi_20261029/delivery/results/roi/pixel_controls'
for scene in p['videos']:
    for frame in scene['pixel_control_frames']:
        for size in [192,256,320]:
            name=scene['name']+'_f'+str(frame)+'_s'+str(size)+'_NN.npz'
            with np.load(OUT/'pixel_controls'/name) as new:array=new['actual_input']
            with np.load(controls/name) as old:expected=old['actual_input']
            assert array.shape==expected.shape==(3,size,size) and array.dtype==expected.dtype==np.float32 and array.tobytes()==expected.tobytes()
'''
source=source[:start]+replacement+source[end:]
source=source.replace("load(prior/'results/baseline/video_metrics.json')","load(prior/'video_metrics.json')")
source=source.replace('paths==72 and formal==48','paths==90 and formal==60')
source=source.replace('ALL39810_RAW_TICKS_MATRIX_INVERSES72_COUNTER_PATHS_AND_PAIR_TABLES_INDEPENDENTLY_VERIFIED','ALL39810_RAW_TICKS_MATRIX_INVERSES90_COUNTER_PATHS_AND_PAIR_TABLES_INDEPENDENTLY_VERIFIED')
source=source.replace("'actual_NN_input_array_checks':24","'actual_NN_input_array_checks':24,'actual_model_NN_anchor_hash_rows':120,'actual_input_array_bytes_exact_to_prior_fixed_crop':True")
ast.parse(source);file=ROOT/'tools/verify_independent.py';assert not file.exists();file.write_text(source,newline='\n')
print('Preparedindependent39810rawtick90pathand24actualinput-byteverifier;notrun')
