from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=load(ROOT/'delivery/results/quality/summary.json');v=load(ROOT/'results/independent_board_verification.json');m=load(ROOT/'results/media_verification.json');visual=load(ROOT/'results/visual_review.json')
assert q['ORT_actual_forwards']=={'FP32':4225,'QDQ':4225} and q['native_integer_actual_forwards']==8 and v['actual_video_model_forwards']==2654
assert [r['TP'] for r in q['validation_metrics']]==[1838,1839]
assert [r['down'] for r in q['video_metrics'] if r['scene']=='original' and r['counter']=='handoff_events']==[10,10]
assert next(r['down'] for r in v['source_counts'] if r['scene']=='original' and r['counter']=='handoff_events')==10
for stride,expected in [(6,[3,0,3]),(1,[4,0,2])]:
    metric=next(r for r in v['publisher_event_scores'] if r['stride']==stride and r['counter']=='handoff_events');assert [metric[k] for k in ['TP','FP','FN']]==expected
assert v['actual8_video_anchor_CPU_integer_raw_bytes_exact'] and v['counter_observation_ticks']==2734 and v['independent_counter_paths']==6
assert v['QDQ_ORT_vs_actual_O8_different_raw_frame_rows']==2654 and v['frame_times_over200ms']==193
assert m['strict_decoded_video_frames']==1962 and m['SVG_bar_geometries']==19 and visual['panels_actually_viewed']==16
for r in visual['files']:assert r['actually_viewed'] and sha(r['path'])==r['sha256']
execution=load(ROOT/'protocol/execution_v1.json');assert execution['protocol_sha256']==sha(ROOT/'protocol/eval_v1.json') and execution['script_sha256']==sha(ROOT/'tools/evaluate_quality.py')
for name,digest in execution['input_and_geometry_hashes'].items():assert sha(ROOT/name)==digest
final=load(ROOT/'board_delivery/final_state.json');assert final['proc_exists'] is False
documents=[];links=0
for name in ['计划与验收.md','新候选量化与真实视频结果.md','Review与当前状态.md']:
    file=ROOT/name;text=file.read_text(encoding='utf-8');assert '\ufffd' not in text
    for match in re.finditer(r'\]\(<([^>]+)>\)',text):assert Path(match[1]).exists();links+=1
    documents.append({'path':str(file.resolve()),'sha256':sha(file),'lines_read_and_reviewed':len(text.splitlines())})
files=['protocol/eval_v1.json','protocol/execution_v1.json','protocol/board_video_v1.json','protocol/media_v1.json',
    'results/quality_transfer_verification.json','results/independent_quality_verification.json','results/independent_board_verification.json',
    'results/media_verification.json','results/visual_review.json','delivery/results/quality/summary.json','board_delivery/results/record.json',
    'board_delivery/results/terminal.json','board_delivery/final_state.json','evidence/board_payload.json','evidence/board_launch.json',
    'evidence/launch_inspection01.json','evidence/board_status08.json','evidence/board_collection.json','evidence/media_collection.txt',
    'tools/evaluate_quality.py','tools/board_video.py','tools/frozen_input.py','tools/render_media.py','tools/verify_board.py','tools/verify_media.py']
result={'status':'MOSAIC050192_QUALITY2654_REAL_O8_VIDEO_FORWARDS6_ARM_COUNTER_PATHS_AND16_PANELS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'checkpoint_sha256':'628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb',
    'real_ORT_quality_forwards':8450,'native_integer_video_anchor_forwards':8,'actual_O8_video_forwards':2654,'actual_O8_warmups':2,
    'validation_FP32_QDQ_matched_references':[1838,1839],'FP32_QDQ_actual_O8_original_counts':[10,10,10],
    'actual_O8_Toros5Hz_TP_FP_FN':[3,0,3],'actual_O8_Toros30Hz_TP_FP_FN':[4,0,2],
    'actual8_video_anchor_raw_bytes_exact':True,'QDQ_ORT_equals_actual_O8_raw':False,'QDQ_different_raw_frame_rows':2654,
    'actual_ARM_counter_observation_ticks':2734,'actual_ARM_counter_paths':6,'mean_PNG_to_counter_ms':v['timing_ms']['PNG_to_counter_with_raw_save_ms']['mean'],
    'P95_PNG_to_counter_ms':v['timing_ms']['PNG_to_counter_with_raw_save_ms']['p95'],'processing_over200ms_frames':193,
    'strict_decoded_video_frames':1962,'SVG_bars_checked':19,'figures_actually_viewed':5,'panels_actually_viewed':16,
    'all_input_PNG_tensors_verified':2654,'actual_board_process_terminal_and_absent':True,'SSH_launch_timeout_not_restarted':True,
    'new_training_updates':0,'new_independent_test':False,'real_camera_or_RFID':False,'simultaneous_identity_in_this_record':False,
    'new_model_joint5FPS_proven_in_this_record':False,'prior_deployed_candidate_replaced':False,'whole_goal_complete':False,
    'local_links_checked':links,'documents':documents,'evidence_hashes':{name:sha(ROOT/name) for name in files}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['documents','evidence_hashes']}))
