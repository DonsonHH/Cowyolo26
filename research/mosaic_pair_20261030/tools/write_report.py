from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/evaluation_v2'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def link(p,label):return '['+label+'](<'+str(Path(p).resolve()).replace('\\','/')+'>)'
s=load(OUT/'summary.json');v=load(ROOT/'results/independent_verification.json');m=load(ROOT/'results/media_verification.json')
controls=load(ROOT/'delivery/results/control_weight_reproduction.json');transfer=load(ROOT/'results/transfer_verification.json')
assert controls['all3_state_dicts_exact'] and v['gradient_gate_record_rows_checked']==7350 and m['strict_decoded_video_frames']==1962
def metric(arm,seed,scene='original',stride=5):
    return next(r for r in s['video_metrics'] if r['condition']==arm+'_seed'+str(seed) and r['scene']==scene and r['stride']==stride and r['counter']=='handoff_events')
def score(r):return '／'.join(str(r['formal_event_metrics'][k]) for k in ['TP','FP','FN'])
table=[];static=[]
for seed in [26,27,28]:
    a,b=metric('mosaic100',seed),metric('mosaic050',seed)
    table.append(f"| {seed} | {a['down']} → {b['down']} | "+score(metric('mosaic100',seed,'toros',6))+' → '+score(metric('mosaic050',seed,'toros',6))+' | '+score(metric('mosaic100',seed,'toros',1))+' → '+score(metric('mosaic050',seed,'toros',1))+' |')
    x=next(r for r in s['validation_metrics'] if r['condition']=='mosaic100_seed'+str(seed));y=next(r for r in s['validation_metrics'] if r['condition']=='mosaic050_seed'+str(seed))
    static.append(f"| {seed} | {x['TP']} → {y['TP']} | {x['unmatched_prediction']} → {y['unmatched_prediction']} |")
checkpoint=ROOT/'delivery/results/training/mosaic050_seed26/weights/last.pt'
frozen=load(ROOT/'delivery/results/all_six_checkpoints_frozen.json');primary=next(r for r in frozen['models'] if r['condition']['name']=='mosaic050_seed26')
assert sha(checkpoint)==primary['sha256']
candidate={'status':'DEVELOPMENT_CANDIDATE_RETAINED_FOR_PTQ_AND_SAME_O8_REAL_BOARD_QUALIFICATION_NOT_DEPLOYED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'name':'mosaic050_seed26','local_checkpoint':str(checkpoint.resolve()),
    'remote_checkpoint':primary['checkpoint'],'checkpoint_sha256':primary['sha256'],'input_size':192,
    'primary_seed_preselected_not_chosen_for_source_total':26,'FP32_original_down':10,'original_human_total':12,
    'FP32_Toros5Hz_TP_FP_FN':[3,0,3],'FP32_Toros30Hz_TP_FP_FN':[4,0,2],
    'new_model_quantized_or_O8_executed':False,'prior_deployed_candidate_replaced':False,
    'inference_crop_orientation_threshold_and_counter_changed':False,
    'next_reference_contract':'reuse_explicit_ordered_FP32_nonconv_reference_from_pynq_o8_sizes_20261030;preserve_legacy_reference_differences_if_any',
    'next_calibration':'training_only128_fixed_images;no_original_or_Toros_or_final_holdout_pixels',
    'whole_goal_complete':False}
dest=ROOT/'results/retained_candidate.json';assert not dest.exists();dest.write_text(json.dumps(candidate,indent=2)+'\n',encoding='utf-8')
report=f'''# 192配对训练：反向压力结果改善，原片仍未恢复12头

2026年10月30日。**mosaic0.5值得继续量化与实机检验，暂不替换板端模型。** 在六个新训练的固定对照中，seed26／27的Toros5Hz正确匹配都由1升至3，FP均0；原片三seed由10／10／10变为10／10／11。seed28的反向结果没有提高，静态匹配还下降，全部结果保留。

下一步沿用此前已固定的主seed26，保留mosaic050_seed26作PTQ／O8候选；没有因为seed28原片多计1头就切换主seed。它的原片FP32仍为10，人工总量12，也尚未生成新QDQ或PYNQ结果。旧192实际O8计数11和约5FPS同板记录继续作为历史部署基线，不能与新FP32反向3／6拼成一个已上板成功系统。

## 为什么做这个对照

训练覆盖审计显示原图低亮度／低对比代理不少；真实mosaic1.0加载器一轮交付20292个框，其中5466个短边<24px。这个观察支持检验增强强度，不证明mosaic就是漏计原因，也不证明0.5最优。数据、框定义及疑似重复标注详见{link(PROJECT/'training_coverage_20261030/训练覆盖审计与下一组对照.md','训练覆盖审计')}。

两个配置只改变mosaic概率1.0／0.5，均为192、额外均匀直角旋转、同一官方YOLO26n初始化、6809训练图／8888躯干框、1571开发验证图、batch32、AdamW和10轮。未向训练集加入源片或Toros，也未读取保留日期像素；那一对发布方疑似重复框在两分支都保持，未混入标签清洗因素。

两分支会消耗不同的加载器随机调用并产生不同拼图组成，不能说逐像素增强完全相同。独立直角旋转序列与优化器更新索引在每对seed中确实一致；共同初值摘要也逐组通过。两个分支各两次真实CUDA优化更新短跑先通过，4次短跑更新及其权重全部丢弃，另计于正式训练之外。

## 所有视频结果：单元格均为mosaic1.0 → 0.5

原片从frame0顺序保留全部历史，到10873；每5帧预测，只统计人审的8912–10873完整通行范围。所有原片向上均0。Toros使用发布方轨迹导出的6次完整反向通行，以2秒容差先作时间最大匹配，再判断方向；它仍是已用过的侧视压力对照，不是普通俯视训练数据或同一通道双向现场试验。

| seed | 原片向下计数／人工12 | Toros5Hz TP／FP／FN | Toros30Hz采样控制 TP／FP／FN |
| --- | --- | --- | --- |
{chr(10).join(table)}

原片只有总量确认，不能把10／12或11／12当作逐头准确率。Toros30Hz只是同一检测缓存的源采样控制，不是PYNQ推理速度。三个seed和两条计数路径的全部36组结果都在原始记录中，表中为既定入口交接计数路径。

## 静态定位：未匹配预测减少，召回并非全部提高

下表用同一CW90开发图、1864个可见躯干AABB和IoU0.5一对一匹配。它不是COCO mAP，也不能直接将“未匹配预测”改称牧场误报警数。

| seed | 匹配参考／1864：1.0 → 0.5 | 未匹配预测：1.0 → 0.5 |
| --- | --- | --- |
{chr(10).join(static)}

seed28匹配参考少20个，不能写成三个seed的召回均提高。当前只支持这一组已用开发材料上的局部取舍，没有新增独立测试或统计显著性结论。mosaic本身是常规训练方法，这个配对也不自动构成论文算法创新。

![全部六模型的固定对照](<{(ROOT/'delivery/results/media/all_six_mosaic_controls.png').as_posix()}>)

{link(ROOT/'delivery/results/media/original_seed26_mosaic100_vs050_FP32.mp4','固定主seed26：两种配置的源视频并排回放')}。仅8912–10873，1962帧／25fps播放；预测和计数按5Hz样本保持。视频展示原生源图及192网络预测，T为临时track ID，不是登记牛号；没有新增板端或永久身份识别主张。

## 真实训练与控制复现

六组各10轮、2130批、1225次优化器更新、68090次图像呈现，总计12780批、7350正式更新、408540次图像呈现。每批NN输入摘要、真实旋转、loss和每次有限／非零梯度门禁记录及时落盘；本机核对记录齐全，但没有保存和独立重算全部原始梯度张量。

三个新mosaic1.0对照与旧固定192直角模型逐项比较：每个708个参数／缓冲状态张量全部相同，三组合计2124个状态张量一致。checkpoint容器包含路径、时间等元数据，其整文件哈希不同不等于参数变化。

所有六个末轮last.pt在新源图推理之前共同冻结，未用best.pt或视频计数选seed。正式评价实际运行25350次源图条件前向，inference hook计数也为25350。之前9条缓存轨迹／8202时刻先严格复现；原始48份NN锚点hash与既定输入相同。

独立复算9426组图像匹配、22373个框的逆变换、16404个跟踪观察及36个事件路径、24个发布方时间匹配，均通过。框逆变换最大差约0.000145原生像素。1962帧视频完整严格解码、4个实际编码锚点与8个累计数面板、30根SVG柱也已核对。

## 执行记录与保留的问题

六个训练主任务130622_0–5均COMPLETED／0:0，各用时约6分11秒至6分32秒。130621短跑9秒；130630正式评价2分54秒；130631媒体1分14秒；130632参数控制核对2秒，均0:0。

首个评价130628在旧缓存严格回归处失败，尚未运行新模型源图前向。130629无网络探针确认：九条轨迹所有数值、ID和事件均相同，仅比较对象缺少旧缓存已有的effective_tracker_config字段。v2补齐元数据，保持完整严格相等及原数值／计数门限，复用同一冻结权重，没有重训。

两个训练stderr只有pin-memory线程异常标题；其文件时间晚于condition_complete记录约1.219秒与0.056秒。完整批次、更新及权重均已核验，但异常的详细栈与根因未取得，不能宣称所有训练日志完全干净或已修复清退问题。原始日志保留，列入后续运行器核查。

所有材料已取回，结果包{transfer['archive_bytes']:,}字节，SHA256 `{transfer['archive_sha256']}`，{transfer['members']}文件；六份last.pt、best.pt、原始raw、批次／梯度记录、失败日志与媒体均保留。

## 下一步与可直接使用的文件

1. 保留预先固定的mosaic050_seed26开发候选，以训练图校准并编译同O8权重；先核对FP32／QDQ／整数参考及8张实机向量，再看完整视频。采用显式浮点运算顺序参考，不覆盖旧参考的差异。
2. 只有新模型的真实O8视频计数、两网络／照片处理周期负载重新验证后，才决定部署替换。原片是否恢复12、跨来源改善是否保留，以及约5FPS的吞吐／迟到／后台等待都需分别实测。
3. 原片已反复用于开发，独立逐事件JSON、真实双向普通俯视及永久身份参考仍缺；最终论文主张继续受这些证据范围约束。

{link(checkpoint,'主候选last.pt')} · {link(ROOT/'results/retained_candidate.json','候选身份与SHA')} · {link(ROOT/'results/independent_verification.json','独立复算')} · {link(ROOT/'results/media_verification.json','视频／图核查')} · {link(ROOT/'delivery/results/control_weight_reproduction.json','三组参数状态复现')}
'''
path=ROOT/'配对训练结果与量化候选.md';assert not path.exists();path.write_text(report,encoding='utf-8')
review='''# 配对训练Review与当前状态

六个新训练、统一25350源图推理与全部媒体复算完成。mosaic0.5只保留为进一步量化的开发候选，未替换板端模型；整体科研目标继续。

| 级别 | 核查与处理 |
| --- | --- |
| 已核查 | 6个末轮权重共同冻结，12780批、7350梯度门禁记录和408540图像呈现齐全；不冒称保存全部梯度原数组 |
| 已核查 | 三组新控制各708个状态张量完全复现旧模型；3对旋转／优化器索引一致，不说mosaic图像完全相同 |
| 已核查 | 9426图像关联、36事件路径、48输入hash、30SVG柱及1962帧严格解码通过 |
| 已实际查看 | 5图12面板：全部seed数值、4张实际编码视频锚点；固定seed26，未按结果选择演示seed |
| 已处理 | 首次评价只缺元数据字段，0新源图前向；补字段后9条轨迹严格相等，未改变阈值或重训 |
| IMPORTANT | 原片仍10／10／11，不能选seed28冒充主模型恢复12；seed28静态召回和反向不改善均保留 |
| IMPORTANT | 两个pin-memory线程退出异常标题在完成记录之后出现，详细根因未证实，日志并非全部干净 |
| BLOCKER | 新候选尚未量化／上板，独立事件与永久身份参考仍缺，不能宣布最终科研或部署验收完成 |
'''
p=ROOT/'Review与当前状态.md';assert not p.exists();p.write_text(review,encoding='utf-8')
print(json.dumps({'report':str(path),'retained_candidate':'mosaic050_seed26','prior_deployed_model_replaced':False,'whole_goal_complete':False}))
