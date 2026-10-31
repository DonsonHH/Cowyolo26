from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
summary=load(ROOT/'delivery/results/pairs/summary.json');probe=load(ROOT/'delivery/results/input_controls/summary.json');verify=load(ROOT/'results/input_controls_verification.json')
assert verify['pair_baseline_repeat_cases']==64 and verify['prior320_sample_all_boxes_correspond_at_IoU0999']
p=load(ROOT/'protocol/pairs_v1.json')
decision={'status':'PRESERVE_COUNTING_BASELINE_AND_PRIORITIZE_INPUT_SCALE_ORIENTATION_TRAINING_BEFORE_CROP_LOCALIZER',
'created_UTC':datetime.now(timezone.utc).isoformat(),'main_summary_sha256':sha(ROOT/'delivery/results/pairs/summary.json'),
'probe_summary_sha256':sha(ROOT/'delivery/results/input_controls/summary.json'),
'pair_geometry_audit_sha256':sha(ROOT/'results/independent_verification.json'),
'evidence':['Val640CW90rectTrue bodymatches official1141 seed26592 seed27505 seed28226 outof1864.',
'Input8fixedimages12references:seed26CW640rectTrue4versusCW320rectTrue11;seed272versus10;seed282versus7.',
'RotationinverseIoUinvariantand64first/lastmainrepeatsreproduced;notexplainedbynativecoordinateconversion.',
'Samefixed8seed26squareCW6404versusCW32011,sochangingrectpaddingalonedoesnotrescueit.',
'Complete919referenceboxes:512idealAABBenvelopeshavemorethan25%areaoutsidethepublishedrotatedreference.',
'Only2920/8888trainreferencecasesgetmatchedcroptargets;traininglocalizeronlyonthesewouldomit5968missedreferences.'],
'pipeline_or_weights_changed':False,'imgsz320_global_adoption':False,'frame_or_camera_resolution_selection_rule_added':False,
'all4models_and_all3seeds_retained':True,'existing_human12_count_milestone_preserved':True,
'localizer_training_started':False,'identity_reference_generated':False,'source_event_identity_accuracy_computed':False,
'next_training_factorial':{'resolution':[320,640],'right_angle_rotation_augmentation':['none','uniform90degree_steps'],
'existing_control':'Existing320noextra-rotation3seedcheckpoints retainedasoriginalcontrol.',
'new_candidate_groups':['640noextra-rotation','320right-angle-augmentation','640right-angle-augmentation'],
'seeds':[26,27,28],'planned_new_training_runs':9,
'training_images':'Same6809date-trainbodylabels;actualstepsandaugmentsettingsmustbefrozenbeforeexecution.',
'selection':'Allgroups/seedsreported;nochoiceonoriginalhuman12counts;check640/nativeandCWrotationgeometry,thenregressoriginal12andpublishedreverse6.',
'current_protocol_only_not_training_execution':True},
'followup_body_geometry':'Afterdetectionstability,compareactualtorsoorientationlocalizationandidentityquerycoveragewithoutusingrboxasidentitytruth.',
'final_scope':'Publicdata development;sourceisolatedcount/identityreferencesandPYNQ-Z2jointperformance stillrequired.',
'FPGA_execution_verified':False,'whole_goal_complete':False}
file=ROOT/'results/training_route_decision.json';assert not file.exists();file.write_text(json.dumps(decision,indent=2)+'\n')
print(json.dumps({'decision':decision['status'],'actual_new_detector_forwards':summary['detector_actual_image_forwards']+probe['actual_source_image_forwards'],'planned_new_training_runs':9,'training_started':False}))
