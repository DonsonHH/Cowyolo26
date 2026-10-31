from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def link(p,label):return '['+label+'](<'+str(Path(p).resolve()).replace('\\','/')+'>)'
v=load(ROOT/'results/independent_verification.json');visual=load(ROOT/'results/visual_review.json')
assert v['cases']==4 and v['assignment_problems']==2864 and visual['panels_actually_viewed']==9
rows=[]
for condition in ['old_O8','new_O8']:
    case=load(ROOT/'results'/condition/'iou03/case.json')
    for refid in [94,103]:
        track=next(r for r in case['tracks'] if r['reference_track_id']==refid)
        raw=track['longest_stable_region_runs']['raw_box_center_assisted_identity'];post=track['longest_stable_region_runs']['post_confirmed_plus_valid_admitted_center_assisted_identity']
        rows.append('| '+condition+' | '+str(refid)+' | '+str(track['raw_correspondence_samples'])+'/'+str(track['reference_box_samples'])+' | '+str(raw['A'])+' | '+str(post['A'])+' | '+str(track['actual_direct_corresponding_down_events'])+' |')
text=f'''# 新模型少计的1次：确认阶段丢失入口观察，而非全部缺暗色样本

2026年10月30日。真实计数类重放旧／新O8记录，全部2175时刻的事件与板端输出精确相同，分别11／10。通过旧640开发框的空间对应，新模型的额外缺失落在**开发参照103的通行**：原始框可形成三次入口观察，确认及合法交接只留下两次。原先参照94在两模型中仍没有足够入口证据。

这定位的是固定开发缓存里的机制；参照103是旧模型临时轨迹，不是人审GT或永久牛号。原片人工只确认总数12，因此不能由空间参照直接宣称新增漏掉了哪一头已确认身份的牛。

## 固定只读比较

两模型均为192、同一固定通道／朝向和原计数规则；只读旧mosaic1.0与新mosaic0.5的真实O8完整raw／轨迹，没有新增网络或训练。原片仍保留0–10873历史，仅统计8912–10873。

使用同一581个开发框、12条开发轨迹，分别在IoU0.5和0.3下作一对一最大数／最大IoU对应，保留所有对象和不能对应的事件。两档都显示旧实际事件对应11条开发参照，新为10条；旧缺94，新缺94与103，没有未对应事件。

| 缓存 | 开发参照 | 原始框对应／参照时刻 | 实际原始中心入口最长连续 | 确认＋合法交接入口最长连续 | 实际直接对应通行 |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

表列IoU0.3，0.5的103同样是原始3、确认2。借参照ID或中心的辅助路径没有用于在线计数；它们的计数并非单调误差上界，不能把几条路径直接相减并称为纯检测或纯跟踪误差。

## 确认失败发生在9550帧

新模型在9520产生暂定23，随后早期检测断续；9545帧重新产生暂定25。9550帧检测分数为0.28858277，达到高分集合0.25和建轨0.25的要求，但未确认阶段仍用`1-IoU×score`，门限0.7。即使IoU=1，其代价也至少0.71141723，仍不可匹配。

实际插桩随后测得该对纯IoU代价0.21052730、融合代价0.77217180。原轨迹25被丢弃，新建26，9555确认时只能追加入9550这一个先前暂定观察，合计两次入口；9550之前的9545不属于26。入口稳定要求仍为三次，不能通过稍后出口很长的轨迹补造入口。

这与剩余94的检测缺口不同。原生图中该差异对象有明显白色花纹和邻牛干扰，也不支持把所有新增漏计统一归为缺少暗色训练图。训练覆盖审计此前已表明低亮度代理并不少。

![三个实际源帧、旧／新轨迹及相同192输入](<{(ROOT/'results/reference103_entry_confirmation.png').as_posix()}>)

图中蓝框为旧640开发参照，橙色为原始检测、绿色为确认框；没有人工GT。9545／9550／9555均从源frame0顺序解码，旧新192输入像素逐字节相同，说明此比较中的输入处理没有变化。

## 已做的干预与采用范围

后续{link(PROJECT/'unconfirmed_iou_20261030/计划与验收.md','仅未确认阶段改纯IoU的111缓存对照')}检验这个瓶颈，原始raw、第一／第二关联、置信度、未确认0.7门限、区域与稳定3次不变。它在新O8缓存中恢复到11，但不同模型／30Hz反向有退步，因此不直接改成全局默认。

该控制是服务器重放真实板端raw，并不是改后算法已实际上板；本轮也没有通过为9550写生产特判或凭参照ID补事件。单帧诊断只用于确认机制，不能作为部署规则。

## 自审与下一步

4个模型／IoU条件、2324参照行、2864关联问题、12条辅助计数路径独立复算通过，9个图像面板已经实际查看。`replay_count.py --require-total 12`仍会失败，这是未达到人工总量的真实信号，不宣称问题已完全修好。最初工具准备时的目录过滤和包导入问题发生在分析前，修正后没有改变任何旧缓存。

继续分开处理两条线：103需要兼顾确认稳定与错误关联风险；94需要连续可用的入口检测证据。新规则只有在全部开发回归、独立通行和实机时序充分验证后才采用，不能凭单例恢复一头就结束研究。随后仍按计划比较当帧抓拍与只用过去帧的质量选择，身份正确率需要对应真值。

{link(ROOT/'results/independent_verification.json','完整数值复算')} · {link(ROOT/'results/visual_review.json','图像与输入核查')} · {link(ROOT/'evidence/target_count_red_replay.json','目标总数的失败复现')}
'''
f=ROOT/'新旧O8计数差异与确认瓶颈.md';assert not f.exists();f.write_text(text,encoding='utf-8')
review='''# 新旧O8差异Review与当前状态

- 11／10来自真实计数类对实际ARM记录的精确回放，仍未达到人审12。
- 103是开发模型空间参照，不是人审框、永久身份或新增独立测试。
- 原始入口3与确认入口2分开；辅助路径不作为单调上界或可部署补框。
- 三个原生帧和9面板实际查看，旧新192输入相同；实际代价由下一控制阶段插桩确认。
- 两个初始本机准备问题没有修改旧缓存；没有新模型前向、训练或板端动作。
- IMPORTANT：单点解释和单因素控制都不自动构成全局采用或论文新颖性。
- BLOCKER：独立事件与永久身份参考、普通俯视真实双向仍待补，整体目标继续。
'''
f=ROOT/'Review与当前状态.md';assert not f.exists();f.write_text(review,encoding='utf-8')
evidence=['protocol/audit_v1.json','protocol/visual_v1.json','results/summary.json','results/independent_verification.json',
    'results/visual_review.json','results/visual_manifest.json','evidence/target_count_red_replay.json',
    'tools/replay_count.py','tools/run_audit.py','tools/verify_independent.py','tools/render_case.py','tools/verify_visual.py']
documents=[{'path':str((ROOT/name).resolve()),'sha256':sha(ROOT/name)} for name in ['计划与验收.md','新旧O8计数差异与确认瓶颈.md','Review与当前状态.md']]
r={'status':'TWO_REAL_O8_MODELS4_CASES2324_REFERENCE_ROWS12_PATHS_AND9_NATIVE_INPUT_PANELS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_counter_replay_counts':[11,10],'human_total12_still_not_met':True,
    'analysis_cases':4,'reference_rows':2324,'association_problems':2864,'reference_conditioned_counter_paths':12,'reference_is_independent_GT':False,
    'old_unmatched_development_tracks':[94],'new_unmatched_development_tracks':[94,103],
    'reference103_new_raw_entry_longest':3,'reference103_new_post_plus_legal_prior_entry_longest':2,
    'native_source_frames_checked':3,'actual_192_input_pairs_byte_equal':3,'panels_actually_viewed':9,
    'new_model_forwards':0,'new_training_updates':0,'actual_board_actions':0,'global_counter_or_tracker_changed':False,'whole_goal_complete':False,
    'documents':documents,'evidence_hashes':{name:sha(ROOT/name) for name in evidence}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ['documents','evidence_hashes']}))
