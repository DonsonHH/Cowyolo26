from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'pynq_rot192_eval_20261029';COMPILE=PROJECT/'pynq_rot192_compile_20261029'
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
ROOT.mkdir(exist_ok=False)
for d in ['tools','protocol','input','results','evidence']:(ROOT/d).mkdir()
summary=load(COMPILE/'delivery/results/qualification/summary.json');assert summary['checkpoint_sha256']=='7b01cead4841f17d561f2a6bd768f9b229f1b3bd142818d8302135d3c69ffd45'
crop=load(PROJECT/'factorial_lane_crop_20261029/protocol/crop_v1.json')
shutil.copyfile(PROJECT/'detector_factorial_20261029/input/validation_images.json',ROOT/'input/validation_images.json')
shutil.copyfile(PROJECT/'lowres_baseline_20261029/tools/geometry.py',ROOT/'tools/geometry.py')
shutil.copyfile(PROJECT/'factorial_lane_crop_20261029/input/event_metrics.py',ROOT/'input/event_metrics.py')
p={'status':'FROZEN_BEFORE_NEW_ROT192_QUALITY_EVALUATION','created_UTC':datetime.now(timezone.utc).isoformat(),
 'model':'S192_rot90_seed26','size':192,'checkpoint_sha256':summary['checkpoint_sha256'],
 'FP32_onnx':REMOTE+'/pynq_rot192_compile_20261029/results/qualification/frozen_S192_rot90_seed26.onnx',
 'FP32_onnx_sha256':summary['FP32_onnx_sha256'],
 'QDQ_onnx':REMOTE+'/pynq_rot192_compile_20261029/results/qualification/cow_allconv_int8_normalized.onnx',
 'QDQ_onnx_sha256':summary['QDQ_onnx_sha256'],
 'compiled_program':REMOTE+'/pynq_rot192_compile_20261029/results/qualification/compiled/program',
 'compiled_graph_sha256':summary['graph_sha256'],'resident_plan_sha256':summary['resident_plan_sha256'],
 'counter_kwargs':crop['counter_kwargs'],'videos':crop['videos'],
 'expected_NN_input_hashes':{k:v for k,v in crop['expected_NN_input_hashes_24_source_frame_sizes'].items() if k.endswith('_s192')},
 'validation_manifest_sha256':sha(ROOT/'input/validation_images.json'),'validation_images':1571,'validation_references':1864,
 'validation_orientation':'CW90,full image,192square letterbox, conf0.2',
 'comparison':'FP32ORTandQDQORTonidentical192inputs;CPUfixedintegeronly8videoanchors;lateractualO8wholevideoqualityseparate.',
 'ORT_actual_forwards_planned':8450,'CPU_integer_video_anchor_forwards':8,'board_input_PNGs_expected':2654,
 'FP32_previous_prediction_coordinate_tolerance_pixels':.05,'FP32_previous_confidence_tolerance':.00001,
 'frame_scope_original_inclusive':[8912,10873],'original_full_history_retained':True,
 'publisher_Toros_event_tolerance_s':2.,'prediction_confidence':.2,'maximum_detections':300,
 'no_model_threshold_or_crop_selection':True,'new_training_updates':0,'new_independent_test':False,
 'source_Toros_or_validation_used_for_calibration':False,'PYNQ5FPS_proven':False,'whole_goal_complete':False}
assert len(p['expected_NN_input_hashes'])==8
(ROOT/'protocol/eval_v1.json').write_text(json.dumps(p,indent=2)+'\n')
(ROOT/'计划与验收.md').write_text('''# 固定192模型量化损失与实际视频计数

使用已经在O8实机8训练向量中逐字节一致的新192直角seed26模型，不再选择权重。128张校准训练图保持，验证集和两源视频仅用于评估。

1. 对1571验证图和2175原片／479Toros源时刻，以完全相同192张量运行FP32 ONNX与QDQ ONNX，共8450实际前向；保留全部原始输出、躯干参考匹配、三条采样轨迹和两计数器。与此前FP32缓存比较，不能把QDQ当板端整数输出。
2. 保存全部2654个实际视频输入为无损PNG，8个锚点与此前真实网络张量逐字节对应。对这8个视频锚点另跑完整原生整数CPU参考，供实际板上比较。
3. 在PYNQ-Z2上对全部2654源时刻执行O8模型和移植后的真实跟踪计数，保留完整raw、事件、逐阶段耗时及终态。原片保留0–10873历史，只统计8912–10873；不切走漏检时段。Toros同组raw按1／6步长回放。
4. 无损输入由服务器从公开源图准备。该回放可以检验模型与板上计数，实际摄像头采集、5Hz调度、后台身份并发需另验，不能由平均张量耗时推断。

原片人工12头只约束总量；开发片不是独立测试。所有失败和退步均保留，原640成功版本不替换。
''',encoding='utf-8')
print(json.dumps({'phase':str(ROOT),'protocol_sha256':sha(ROOT/'protocol/eval_v1.json'),'ORT_forwards_planned':8450,'later_actual_board_video_forwards_planned':2654}))
