"""Freeze camera-only calibration after native review and before model outputs."""
from pathlib import Path
import argparse,hashlib,json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--axis',choices=['x','y'],required=True)
    parser.add_argument('--roi',nargs=2,type=float,required=True);a=parser.parse_args()
    assert 0<=a.roi[0]<a.roi[1]<=1
    target=ROOT/'protocol/inference_v1.json';assert not target.exists()
    admission=ROOT/'admission_delivery/results/admission/summary.json';data=json.loads(admission.read_text(encoding='utf-8'))
    assert len(data['videos'])==4 and data['models_run'] is False
    visual=ROOT/'evidence/native_visual_review.json';review=json.loads(visual.read_text(encoding='utf-8'))
    assert review['source_pixels_seen_before_new_model_predictions'] is True
    assert review['camera_axis_selected']==a.axis and review['perpendicular_ROI_selected']==a.roi
    source=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';frozen=json.loads(source.read_text(encoding='utf-8'))
    contract=frozen['source_event_record']['pipeline_contract'];module_hash={}
    for name,src in [('zone_counter.py',PROJECT/'confirmation_handoff_20261028/input/zone_counter.py'),
                     ('confirmation_counter.py',PROJECT/'confirmation_handoff_20261028/tools/confirmation_counter.py')]:
        dest=ROOT/'input'/name;assert not dest.exists();dest.write_bytes(src.read_bytes());module_hash[name]=sha(dest)
    assert module_hash['zone_counter.py']==contract['base_counter_sha256'] and module_hash['confirmation_counter.py']==contract['handoff_module_sha256']
    p={'name':'Two frozen models on four metadata-selected ordinary overhead Cows2021 sessions',
       'selection_protocol_sha256':sha(ROOT/'protocol/sessions_v1.json'),'admission_summary_sha256':sha(admission),
       'native_visual_review_sha256':sha(visual),'accepted_12_candidate_sha256':sha(source),
       'camera':{'rotation_degrees':0,'axis':a.axis,'perpendicular_ROI':a.roi,'calibrated_from_native_scene_before_predictions':True,
                 'A_to_B':'left_to_right' if a.axis=='x' else 'top_to_bottom'},
       'imgsz':640,'detector_confidence':.2,'NMS_IoU':.5,'observation_hz':5,'cold_start_each_clip':True,
       'counter':{'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.0},'counter_variant':'confirmation_handoff',
       'tracker':'Installed original ByteTrack with unchanged defaults; no pure-IoU or Lost-eligibility modification',
       'ultralytics_version':'8.4.63','input_module_sha256':module_hash,
       'models':[{'name':'official_yolo26n','checkpoint_path':'/share/home/renly/projects/idcoo_research_20261026/models/yolo26n.pt',
                  'checkpoint_sha256':'9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef'},
                 {'name':'accepted_seed26','checkpoint_path':'/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/results/training/seed26/weights/last.pt',
                  'checkpoint_sha256':frozen['checkpoint_sha256']}],
       'conditions_expected':8,'all_selected_sessions_retained':True,'new_training_updates':0,'event_GT_available':False,
       'count_accuracy_F1_or_final_unseen_test_not_claimed':True,'whole_goal_complete':False}
    target.write_text(json.dumps(p,indent=2),encoding='utf-8');print(json.dumps(p),flush=True)

if __name__=='__main__':main()
