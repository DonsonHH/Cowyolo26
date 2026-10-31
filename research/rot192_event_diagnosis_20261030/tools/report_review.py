from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,gzip
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');head=load(ROOT/'results/unfiltered_reference94_heads.json');visual=load(ROOT/'results/visual_manifest.json')
assert v['cases']==6 and v['oracle_paths']==18 and v['reference_case_rows']==3486
cases={mode:load(ROOT/'results'/mode/'iou05/case.json') for mode in ['FP32','QDQ','actual_O8']}
assert [[r['reference_track_id'] for r in cases[m]['tracks'] if not r['actual_direct_corresponding_down_events']] for m in cases]==[[94,98],[94],[94]]
selected=[r for r in head['rows'] if r['mode']=='actual_O8'];assert len(selected)==15
entry=[r for r in selected if r['reference94_axis_position']<.4];assert len(entry)==7
assert all(r['maximum_score_at_IoU03']<.2 for r in entry)
assert [r['frame0'] for r in entry if r['maximum_score_at_IoU03']>=.05]==[9315,9320]
assert sha(Path(visual['file']))==visual['sha256'] and visual['panels']==9
record={'figures_actually_viewed':1,'panels_actually_viewed':9,'file':visual['file'],'sha256':visual['sha256'],
 'review':'Allthreenativeframes,physicalROIdetailsandactual192inputsopened. Remainingreference94isadarkbodybetweennearbycows;someactualboxescoverneighbours. Blue640referenceisexplicitlynotGT.'}
(ROOT/'results/visual_review.json').write_text(json.dumps(record,indent=2)+'\n')
report='''# 固定192模型：11与12之间的剩余案例

固定192直角seed26的实际O8结果11，人工确认总数12。对已经保存的原始输出做只读分解，剩余未对应的开发参照为旧640轨迹94；它不是正式人工框标注，也不是永久奶牛身份。没有为得到12改计数阈值或关联参数。

## 三个数值实现全部保留

| 实现 | 交接计数 | 没有当帧空间对应事件的640开发参照 |
| --- | --- | --- |
| FP32 ONNX | 10 | 94、98 |
| INT8 QDQ ONNX | 11 | 94 |
| 实际PYNQ O8整数前向 | 11 | 94 |

沿用既定IoU0.5及0.3，一对一将581个640参照框分别对应到原始检测和确认后轨迹。实际O8的参照94在两档IoU下都只有2/15时刻匹配；入口A区最长连续匹配0，出口B区最长2，小于固定稳定要求3。因此只修复临时ID关联不能补出入口证据。

辅助计数路径并不是严格误差上界：部分条件下实际计数大于某条辅助路径，反映框范围、中心与稳定样本口径变化。不能简单相减并宣称得到纯检测／纯跟踪误差。

## 检查全部300个未筛选head输出

每个实现、参照94的15个对应时刻都检查全部300候选，合计45组，未新增网络推理。原始300候选中通常仍有与参照几何接近的框，但分类分数很低，不能只看几何框存在就说检测成功。

实际O8入口七个参照时刻9300–9330，在IoU≥0.3候选中的最高分均低于当前0.2。即使仅作诊断查看0.05，也只出现9315／9320两个相邻入口时刻，仍不足3；这不是一个小幅降低阈值就能可靠解决的案例。没有据此部署0.05，也没有把极低分候选补作真实观察。

参照与相邻牛存在重叠时，高分宽框可能归给邻牛；一对一对应保留该情况。原生画面目视可见中间深色牛体，在192实际输入中与地面和邻牛边界较弱。这支持“优先检查低分辨率暗色／遮挡正例和分类置信度”的后续方向，但单例不能证明训练数据组成是唯一原因。

## 源像素与下一步

[三源帧、原生通道局部和真实192输入九面板](<C:/Users/Donson/Documents/ChatGPT/奶牛/rot192_event_diagnosis_20261030/results/remaining94_source_and_actual_input.png>)显示9310入口、9345中段与9360出口。蓝框来自640开发模型，绿框来自实际O8，图中并未伪造人工GT。原片只输出用户指定8912–10873活动范围，数值诊断仍保留完整前史。

6分析条件、3486参照行、4296关联问题及18辅助计数路径独立复算通过；全部head输出检查、置信度来源和坐标还原均保留。九面板实际查看，未新增训练、推理、板端动作或身份标签。

下一步先完成普通俯视独立标注和跨来源输入准入；针对暗色／遮挡实例做事先冻结的输入或训练控制，完整评估所有事件和负例。新控制可以在明确的开发集上比较，但不能把反复看过的原片写成独立最终测试，也不能以12头总数单独选模型。当前原640成功版本保留。
'''
(ROOT/'固定192剩余未计案例与训练方向.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

三实现6条件的只读诊断完成，18辅助路径和全部关联独立复算。旧640参照94未对应实际O8事件；它是开发参照，未升级为人工GT或永久身份标签。

保存全部300候选分数，入口七个时刻均无IoU≥0.3且分数≥0.2的框。0.05只作保存输出的诊断查询，未采用或搜索最终阈值。部分辅助路径低于实际计数，限制已明确。三个原生帧、局部与实际192输入九面板实际查看，全部不利结果保留。

本轮没有新网络、训练或板端动作。后续优先独立逐事件参考、暗色／遮挡正例和跨场输入控制，不能为凑人工12头修改区域规则。整体科研继续。
''',encoding='utf-8')
docs=[ROOT/f for f in ['计划与验收.md','固定192剩余未计案例与训练方向.md','Review与当前状态.md']]
evidence=['protocol/audit_v1.json','protocol/visual_v1.json','input/reference_boxes.json','input/reference_events.json','results/summary.json',
 'results/independent_verification.json','results/unfiltered_reference94_heads.json','results/visual_manifest.json','results/visual_review.json',
 'results/actual_O8/iou05/case.json','results/actual_O8/iou03/case.json']
r={'status':'THREE_FIXED192_IMPLEMENTATIONS6_CASES18_ORACLE_PATHS_AND45_HEAD_ARRAYS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'source_counts':[10,11,11],'remaining_O8_development_reference_tracks':[94],
 'reference_is_independent_GT':False,'reference_rows':3486,'association_problems':4296,'oracle_paths':18,'unfiltered_head_arrays':45,
 'actual_O8_reference94_raw_matches_at_both_IoU':2,'reference94_samples':15,'entry_A_max_contiguous_matched_samples':0,
 'diagnostic05score_entry_samples':2,'threshold_or_counter_changed':False,
 'figures_actually_viewed':1,'panels_actually_viewed':9,'new_model_forwards':0,'new_training_updates':0,'board_actions':0,'whole_goal_complete':False,
 'evidence_hashes':{f:sha(ROOT/f) for f in evidence},'documents':[{'path':str(f.resolve()),'sha256':sha(f)} for f in docs]}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['evidence_hashes','documents']}))
