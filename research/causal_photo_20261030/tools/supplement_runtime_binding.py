from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=load(ROOT/'protocol/run_v1.json');prior=load(PROJECT/'pynq_mosaic192_joint_20261030/protocol/run_v1.json')
assert all(p[k]==prior[k] for k in ['foreground_source_model','graph_sha256','resident_plan_sha256','background_encoder','O8_bit_sha256','runtime_files','registered_IDs','fixed_identity_threshold'])
q=load(PROJECT/'pynq_mosaic192_joint_20261030/results/new_input_quant256_equivalence.json')
assert q['model_checkpoint_sha256']==p['foreground_source_model'] and q['divide_vs_multiply_quantized_codes_exact'] and len(q['codes'])==256
record={'status':'INHERITED_DESCRIPTIVE_METADATA_CLARIFIED_WITHOUT_CHANGING_FROZEN_RUN','created_UTC':datetime.now(timezone.utc).isoformat(),
 'frozen_run_protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'previous_protocol_sha256':sha(PROJECT/'pynq_mosaic192_joint_20261030/protocol/run_v1.json'),
 'model_graph_plan_encoder_gallery_threshold_and_runtime_hash_list_identical_to_previous_joint':True,
 'inherited_mosaic_model_and_calibration_changed_relative_to_prior_joint_phase_value':p['mosaic_model_and_calibration_changed_relative_to_prior_joint_phase'],
 'actual_model_or_calibration_change_in_this_photo_stage':False,
 'inherited_input_quant256_digest':p['input_quant256_equivalence_sha256'],
 'correct_existing_new_mosaic_input_quant256_file':str((PROJECT/'pynq_mosaic192_joint_20261030/results/new_input_quant256_equivalence.json').resolve()),
 'correct_existing_new_mosaic_input_quant256_sha256':sha(PROJECT/'pynq_mosaic192_joint_20261030/results/new_input_quant256_equivalence.json'),
 'previous_new_mosaic_quantization_check_precedes_current_run':True,'correction_is_metadata_not_numeric_gate_or_parameter_change':True,
 'all8_anchor_and_all_actual_periodic_raw_parity_still_required':True,'frozen_protocol_overwritten':False,'new_forwards':0,'whole_goal_complete':False}
f=ROOT/'protocol/runtime_binding_clarification_v1.json';assert not f.exists();f.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'model_changed':False,'frozen_protocol_overwritten':False,'current_quant256_existing_gate_confirmed':True}))
