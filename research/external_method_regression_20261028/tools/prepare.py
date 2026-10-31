from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    observed=load(ROOT/'results/input_inspection.json');p=load(PROJECT/'lost_recovery_20261028/protocol/lost_v1.json')
    target=ROOT/'protocol/regression_v1.json';assert not target.exists();target.parent.mkdir(exist_ok=True)
    inp=ROOT/'input';inp.mkdir(exist_ok=True)
    for name in ['secondstage_tracker.py','zone_counter.py','confirmation_counter.py','event_metrics.py']:
        dest=inp/name;assert not dest.exists();shutil.copyfile(PROJECT/'lost_recovery_20261028/input'/name,dest)
    shutil.copyfile(PROJECT/'lost_recovery_20261028/tools/lost_tracker.py',inp/'lost_tracker.py')
    shutil.copyfile(PROJECT/'counting_eval_20261026/delivery/counting_evaluation/annotations/publisher_gt_original.txt',inp/'publisher_gt_original.txt')
    files=observed['files'];models=[]
    for name,checkpoint in [('generic','/models/yolo26n.pt'),('pilot','/results/detection_pilot/five_epoch_dev/weights/best.pt')]:
        folder=f'/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis/results/capture/{name}'
        weight=next(r for r in files if r['path'].endswith(checkpoint))
        models.append({'name':name,'checkpoint':weight,'cache_files':[r for r in files if r['path'].startswith(folder+'/')],
           'prior_events':next(r['events'] for r in observed['capture_summary'] if r['model']==name),
           'expected_prior_TP':6 if name=='generic' else 2})
    assert [len(m['cache_files']) for m in models]==[5,5]
    result={'name':'Fixed cattle passage algorithm cross-scene regression on already-used Toros reference',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'source':'Toros original-time footage',
      'source_sha256':'1172810976a09e1a75a8b0a69edf21038393aa6f6b1c1273b8d7c34f62146a6c',
      'source_fps':30,'source_frames':479,'image_shape_H_W':[1080,1920],
      'roi_axis':'x','perpendicular_roi_y':[.1,.95],
      'counter':{'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.},
      'timing_scope':'Keep originalToros protocol: all30Hz frames, 3samples=2/30s; not the5Hz sourceclip0.4s observation duration',
      'models':models,'installed_source':p['installed_source'],'matching_source_sha256':p['matching_source_sha256'],
      'input_modules':{path.name:sha(path) for path in inp.glob('*.py')},
      'publisher_GT_sha256':sha(inp/'publisher_gt_original.txt'),
      'reference_author_summary':next(r for r in files if '/author_gt_audit/' in r['path']),
      'reference_events':observed['author_reference']['events'],
      'reference_scope':'Sixeventsderivedfrompublishertrajectorywithfrozenzone rule; not new independent test; GT clip/edge findings retained',
      'variants':['installed','secondstage_iou','allow_lost_iou'],
      'main_method_paths':['installed_confirmed_only','installed_handoff','secondstage_iou_handoff','allow_lost_iou_handoff'],
      'diagnostic_paths':'confirmed-only events for each modifiedtracker also retained/scored',
      'required_exact_baselines':['alloriginalposttrackerboxes','alloriginalROItracks','sixandtwo originalevents','known6and2 referenceTP'],
      'event_matching_tolerance_s':2.,'no_parameter_selection_or_training_on_reference':True,
      'source_original_protocol_sha256':sha(PROJECT/'counting_eval_20261026/annotations/evaluation_protocol_v1.json'),
      'new_detector_forwards':0,'training_updates':0,'new_independent_test':False,
      'source_MultiCam_independent_truth_received':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    assert len(result['reference_events'])==6 and {e['direction'] for e in result['reference_events']}=={'B->A'}
    target.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'protocol_sha256':sha(target),'models':2,'tracker_runs':6,'counter_paths':12,'main_method_conditions':8}))
if __name__=='__main__':main()
