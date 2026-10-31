from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, x):
    assert not p.exists(), p
    p.write_text(json.dumps(x, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
s = load(ROOT/'delivery/results/roi/summary.json')
v = load(ROOT/'results/independent_verification.json')
m = load(ROOT/'results/media_verification.json')
assert s['actual_detector_source_image_forwards'] == s['active_predictor_inference_image_calls'] == 39810
assert v['counter_observation_ticks'] == 41010 and v['independent_counter_paths'] == 90
assert v['raw_boxes_matrix_inverse_verified'] == 16286 and v['maximum_inverse_absolute_error'] == 0
assert v['actual_model_NN_anchor_hash_rows'] == 120 and v['actual_NN_input_array_checks'] == 24
assert m['strict_decoded_video_frames'] == 3924 and m['independently_recomputed_anchor_panel_counts'] == 48
groups = []
for size,variant in [(192,'plain'),(192,'rot90'),(256,'plain'),(256,'rot90'),(320,'rot90')]:
    rows = [r for r in s['paired_full_vs_roi'] if r['scene']=='original' and r['counter']=='handoff_events' and r['condition'].startswith(f'S{size}_{variant}_')]
    rows.sort(key=lambda r:r['condition'])
    assert len(rows)==3
    groups.append({'size':size,'variant':variant,'full':[r['full_down'] for r in rows],'crop':[r['crop_down'] for r in rows]})
assert groups[1]['crop']==[10,10,10] and groups[1]['full']==[6,5,5]
files=[ROOT/'media_delivery/results/media_v2/all18_full_crop_counts.png']
files += [ROOT/'media_delivery'/x['path'] for x in load(ROOT/'media_delivery/results/media_v2/media_metadata.json')['preview_frames']]
assert len(files)==9
visual={'created_UTC':datetime.now(timezone.utc).isoformat(),'figures_actually_viewed':9,'panels_actually_viewed':54,
 'files':[{'path':str(p.resolve()),'sha256':sha(p),'panels':6,'actually_viewed':True} for p in files],
 'observations':['All six chart panels and all36 values legible; three historical320plain controls labelled.',
 'All eight source-frame panels show same source scene and orange lane geometry; full/crop count labels visible.',
 'Full-input wall false positives and crop misses remain visible; green IDs are temporary tracks, not cow identities.',
 'Movies are only8912..10873, held5Hz predictions at25fps; neither real-time board playback nor event-level GT.']}
save(ROOT/'results/visual_review.json',visual)
table='\n'.join(f"| {r['size']} | {r['variant']} | {' / '.join(map(str,r['full']))} | {' / '.join(map(str,r['crop']))} |" for r in groups)
toros=[]
for r in s['paired_full_vs_roi']:
    if r['scene']=='toros' and r['counter']=='handoff_events':
        a,b=r['full_TP_FP_FN'],r['crop_TP_FP_FN']
        toros.append(f"| {r['condition']} | {r['sample_stride']} | {' / '.join(map(str,a))} | {' / '.join(map(str,b))} |")
report=f'''# 新低分辨率权重：固定通道输入对照

固定裁剪使192直角增强模型的三个seed从6／5／5提高到10／10／10，仍未达到人工确认的12头。256及320直角模型接近12，但这里是服务器FP32结果；板上吞吐和量化后计数需要另验。继续采用结果读取前固定的`S192_rot90_seed26`进入量化资格检查，保留其10头结果，不据此挑选数到12的seed。

## 这一轮只改输入范围

沿用上一阶段15个冻结末轮权重。原片裁剪原坐标`[870,0,1920,1440]`后顺时针90度；Toros裁剪`[0,108,1920,1026]`。conf0.2、跟踪、两种计数规则及源坐标ROI均保持。先逐项重现45条整幅跟踪轨迹与90份计数事件清单，再执行39810次真实网络推理；新增41010个跟踪时刻、90条计数路径。没有新增训练、门限搜索或板上动作。

原片保留0–10873帧跟踪历史，只统计8912–10873。表内依次为seed26／27／28，均为A→B，反向计数均0。

| 输入尺寸 | 训练组 | 整幅输入 | 固定通道裁剪 |
| --- | --- | --- | --- |
{table}

历史320普通增强控制为整幅10／8／10、裁剪10／10／11，图与普通增强视频已标明其来自旧模型。256普通增强的seed27、28发生退步，完整保留。上述原片只有人审总数12，不能计算可靠逐事件Precision、Recall或F1；数到12也可能包含漏计与重计抵消。这一片段已反复用于开发，不能作为独立测试集。

## 公开反向片段仍是主要弱点

发布方轨迹按既定规则导出6次完整通行；下表为TP／FP／FN，stride1为30Hz回放、stride6为5Hz回放。这些是给定采样时刻的算法对照，不代表板卡实际吞吐。配对规则及2秒容差保持。

| 模型 | stride | 整幅TP／FP／FN | 裁剪TP／FP／FN |
| --- | --- | --- | --- |
{chr(10).join(toros)}

裁剪并未解决跨来源退化。当前模型不满足最终采用条件；优先完成固定192候选的部署与量化损失实测，再依据普通俯视数据和独立标注决定后续训练。

## 视频与数据

- [直角增强seed26：三尺寸整幅／裁剪对照](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/media_delivery/results/media_v2/seed26_rot90_full_vs_crop.mp4>)
- [普通增强seed26对照（320为历史控制）](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/media_delivery/results/media_v2/seed26_plain_full_vs_crop.mp4>)
- [全部18个条件的图](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/media_delivery/results/media_v2/all18_full_crop_counts.png>) · [完整90行配对CSV](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/results/paired_full_vs_roi.csv>)
- [独立复算](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/results/independent_verification.json>) · [视频完整解码核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/results/media_verification.json>)

视频均严格导出8912–10873共1962帧，25fps播放、显示每5帧更新的5Hz预测。临时track ID并不是奶牛永久身份。原12头成功版本保持，下一步仍需真实FPGA／ARM检测、板上跟踪计数、输入采集和后台身份识别的联合验证。
'''
(ROOT/'固定裁剪结果与部署下一步.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

本轮15新模型固定通道输入实验及输出自审已完成，整体科研与同板系统目标保持进行中。

- Slurm130559为COMPLETED／0:0。39810实际前向与活动预测器计数相等；45整幅轨迹、90计数清单在新推理前完全复现。
- 独立以矩阵逆变换复算16286个框，最大误差0；41010观察、90计数路径、60组Toros事件评分及90配对行核对一致。120次实际网络输入锚点对应24份张量，与上一固定裁剪像素控制完全相同；本轮没有把重复张量核对称为重新独立标注。
- 两个视频共3924帧严格解码通过，8视频帧与PNG锚点比较通过，48面板累计计数由缓存事件独立重算；36个SVG柱的几何高度与原始值一致。已实际查看9图54面板，未裁去不利结果。
- 首个渲染作业130563因路径类型错误在5秒时FAILED／1:0，保留原脚本和日志。仅修正路径类型后130564于1分47秒COMPLETED／0:0，产物另存media_v2；没有重跑网络或改模型选择。
- 192直角seed26仍为10而非12；Toros仍低召回。当前结果不能支持独立泛化、永久身份恢复、整链5FPS或最终论文结论。

下一步固定192直角seed26，使用仅训练集的128图校准，复用已实测的O8编译链；先核对量化和整数执行，再上板。后台身份和输入调度需后续实际并发测量。
''',encoding='utf-8')
plan=ROOT/'计划与验收.md'
plan.write_text(plan.read_text(encoding='utf-8')+'\n\n## 已执行结果（保留上述冻结时状态）\n\n130559完成39810真实前向，90计数路径与逆变换独立复算通过；130563渲染失败保留，130564修正版完成。3924视频帧、36图柱与48面板计数核对后，9图54面板已实际查看。192直角三seed均10；主候选仍固定seed26。详见《固定裁剪结果与部署下一步.md》。\n',encoding='utf-8')
original=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'
assert sha(original)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
evidence=['protocol/crop_v1.json','protocol/execution_v1.json','protocol/media_v1.json','tools/run_crop.py','tools/render_media_v2.py',
 'results/transfer_verification.json','results/independent_verification.json','results/media_verification.json','results/visual_review.json',
 'delivery/results/roi/summary.json','results/paired_full_vs_roi.csv','evidence/media_v2_fix.json']
record={'status':'15_NEW_MODELS39810_CROP_FORWARDS90_COUNTER_PATHS_AND54_VISUAL_PANELS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'fixed_crop_phase_complete':True,'condition_count':15,
 'real_new_detector_forwards':39810,'counter_observation_ticks':41010,'counter_paths':90,'raw_boxes_inverse_verified':16286,
 'actual_NN_anchor_hashes':120,'unique_actual_NN_arrays':24,'paired_original_groups':groups,'primary_case':'S192_rot90_seed26',
 'primary_original_down_count':10,'human_confirmed_total':12,'original_event_level_GT':False,'new_independent_test':False,
 'publisher_formal_scoring_conditions':60,'strict_decoded_video_frames':3924,'movies':2,'SVG_bars':36,
 'figures_actually_viewed':9,'panels_actually_viewed':54,'old320plain_controls_included':True,
 'inference_job':'130559','failed_media_job':'130563','completed_media_job':'130564',
 'new_training_updates':0,'board_actions':0,'global_pipeline_replaced':False,'model_selected_using_new_crop_count':False,
 'original_human12_milestone_preserved':True,'retained_artifact_hashes':{original.relative_to(PROJECT).as_posix():sha(original)},
 'foreground_background_joint5FPS_proven':False,'whole_goal_complete':False,
 'evidence_hashes':{r:sha(ROOT/r) for r in evidence},
 'documents':[{'path':str((ROOT/r).resolve()),'sha256':sha(ROOT/r)} for r in ['计划与验收.md','固定裁剪结果与部署下一步.md','Review与当前状态.md']]}
save(ROOT/'results/final_review.json',record)
print(json.dumps({k:v for k,v in record.items() if k not in ['evidence_hashes','documents','retained_artifact_hashes']}))
