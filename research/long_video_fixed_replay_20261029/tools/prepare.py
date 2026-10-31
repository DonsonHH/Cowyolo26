"""Freeze four checkpoints, source pipeline and observation windows before new inference."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=ROOT/'protocol';out.mkdir(exist_ok=False);inputs=ROOT/'input';inputs.mkdir(exist_ok=False)
    current=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';accepted=json.loads(current.read_text(encoding='utf-8'))
    assert accepted['predicted_down']==accepted['human_total']==12 and sha(current)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
    timing=PROJECT/'event_timing_refinement_20261029/reference/assistant_event_timing_v2.json'
    assert sha(timing)=='188079a8754c495485c284b8e0a29519181100033166fe953e9f7547c600dc6a'
    t=json.loads(timing.read_text(encoding='utf-8'));assert t['eligible_for_final_scoring'] is False
    models=[{'name':'official','seed':None,'checkpoint':REMOTE+'/models/yolo26n.pt',
             'sha256':'9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef'}]
    for seed,digest in [(26,'51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74'),
                        (27,'132b62e8918429ac6e0202eae1a6924550a1c3e1634545c6e4e174f25c921226'),
                        (28,'93b8746381cd997d98dba809685ba53f7779da750750aa39bea24646c843a216')]:
        local=PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{seed}/weights/last.pt';assert sha(local)==digest
        models.append({'name':f'seed{seed}','seed':seed,'checkpoint':REMOTE+f'/cows2021_adaptation_20261027/results/training/seed{seed}/weights/last.pt','sha256':digest})
    modules={}
    for name,src in [('native_restore.py',PROJECT/'counting_recovery_20261028/tools/native_restore.py'),
                     ('zone_counter.py',PROJECT/'confirmation_handoff_20261028/input/zone_counter.py'),
                     ('confirmation_counter.py',PROJECT/'confirmation_handoff_20261028/tools/confirmation_counter.py')]:
        target=inputs/name;target.write_bytes(src.read_bytes());modules[name]=sha(target)
    contract=accepted['source_event_record']['pipeline_contract']
    assert modules['zone_counter.py']==contract['base_counter_sha256'] and modules['confirmation_counter.py']==contract['handoff_module_sha256']
    previous=json.loads((PROJECT/'external_method_regression_20261028/protocol/regression_v1.json').read_text(encoding='utf-8'))
    source=PROJECT/'overhead_long_session_20261028/input/2023-08-17T13-25-38.mp4';assert sha(source)==t['source_sha256']
    windows=[{'name':'group_passage','start_frame0':2375,'end_frame0_exclusive':4375},
             {'name':'late_single','start_frame0':5000,'end_frame0_exclusive':5625},
             {'name':'person_control','start_frame0':9625,'end_frame0_exclusive':10125}]
    p={'name':'Four frozen YOLO26n checkpoints on native long-session video; unscored prediction comparison',
       'source_video':REMOTE+'/overhead_positive_reference_20261028/input/2023-08-17T13-25-38.mp4','source_sha256':sha(source),
       'native_size_WH':[2560,1440],'nominal_source_fps':25,'first_source_frame0':0,'end_source_frame0_exclusive':10125,
       'sample_stride':5,'expected_observation_ticks_each_model':2025,'windows':windows,'models':models,
       'clockwise90':True,'imgsz':640,'confidence':.2,'NMS_IoU':.5,'crop_x':[0,2560],
       'ROI_center_x_open_interval':[.34,.75],'counter':{'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.0},
       'counter_variants':['confirmed_only','confirmation_handoff'],'tracker':'bytetrack.yaml','ultralytics':'8.4.63',
       'input_module_sha256':modules,'installed_source':previous['installed_source'],'matching_source_sha256':previous['matching_source_sha256'],
       'current_confirmed12_candidate_sha256':sha(current),'original_assistant_draft_sha256':t['original_draft_sha256'],
       'timing_draft_sha256':sha(timing),'timing_reference_authority':'assistant_provisional_native_visual_review','reference_scoring_eligibility':False,
       'all_models_and_counter_conditions_retained':True,'no_retraining_or_inference_parameter_sweep':True,
       'new_reference_correctness_not_established_by_predictions':True,'formal_accuracy_or_F1_computation_allowed':False,
       'FPGA_execution_verified':False,'whole_goal_complete':False}
    target=out/'replay_v1.json';target.write_bytes((json.dumps(p,indent=2)+'\n').encode())
    print(json.dumps({'protocol_sha256':sha(target),'models':[m['name'] for m in models],'observation_ticks_each_model':2025,
                      'total_model_forwards_expected':8100,'counter_paths':8,'formal_scoring_allowed':False}),flush=True)
if __name__=='__main__':main()
