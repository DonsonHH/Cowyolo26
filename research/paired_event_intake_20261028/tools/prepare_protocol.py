from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
target=ROOT/'protocol/evaluation_v1.json';assert not target.exists();target.parent.mkdir(exist_ok=True)
files={'matcher':PROJECT/'counting_eval_20261026/tools/event_metrics.py',
       'intake_inspector':PROJECT/'evaluation_intake_20261028/tools/inspect_annotation.py',
       'annotation_validator':PROJECT/'phase3_diagnosis_20261026/tools/validate_annotations.py'}
value={'name':'Extend current paired candidate intake with fixed original event matching',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'catalog_sha256':sha(ROOT/'results/frozen_prediction_catalog_v2.json'),
       'source_frame_scope_inclusive':[8912,10873],'source_fps':25,'matching_tolerance_s':2.,
       'matching_rule':'Original time-only maximum-cardinality then minimum-total-time-error Hungarian assignment; direction judged afterward',
       'source_files':{k:{'path':str(p),'sha256':sha(p)} for k,p in files.items()},'scipy_version':'1.16.1',
       'same_frame_events_preserved':True,'temporal_candidate_ambiguity_reported_without_changing_matching':True,
       'required_before_real_scores':['intake_pass','manual_provenance_and_native_frame_review_record','binding_SHA_and_scope_checks'],
       'test_fixtures_never_promoted_to_reference':True,'current_source_is_reused_development_data':True,
       'new_reference_received':False,'new_inference':False,'board_execution':False,'whole_goal_complete':False}
target.write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({'evaluation_protocol_sha256':sha(target),'matcher_sha256':value['source_files']['matcher']['sha256']}))
