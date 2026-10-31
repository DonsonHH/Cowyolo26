"""Write evidence-bound conclusions after local independent recomputation."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/study_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def link(path,label):return '['+label+'](<'+str(path.resolve()).replace('\\','/')+'>)'
s=load(OUT/'summary.json');v=load(ROOT/'results/independent_verification.json')
source=load(ROOT/'delivery/results/source_input_verification_v2.json')
cases=load(ROOT/'results/reference94_photometric_audit.json');media=load(ROOT/'results/media_verification.json')
transfer=load(ROOT/'results/transfer_verification.json')
assert s['actual_total_forwards']==25350 and v['counter_paths']==36 and source['input_hashes_exact']==12675
assert media['SVG_bars']==30 and media['input_panels']==30
labels={'none':'原输入','gamma07':'gamma0.7','clahe_y2':'CLAHE-Y2'}
rows=[]
for c in labels:
    for mode in ['FP32','QDQ']:
        val=next(r for r in s['validation_metrics'] if r['condition']==c and r['mode']==mode)
        original=next(r for r in s['video_metrics'] if r['condition']==c and r['mode']==mode and r['scene']=='original' and r['counter']=='handoff_events')
        toros=[next(r['formal_event_metrics'] for r in s['video_metrics'] if r['condition']==c and r['mode']==mode and r['scene']=='toros' and r['stride']==stride and r['counter']=='handoff_events') for stride in [6,1]]
        rows.append(f"| {labels[c]} | {mode} | {val['TP']} | {val['unmatched_prediction']} | {original['down']} | "+'／'.join(str(toros[0][k]) for k in ['TP','FP','FN'])+' | '+'／'.join(str(toros[1][k]) for k in ['TP','FP','FN'])+' |')
table='\n'.join(rows)
case_table='\n'.join(f"| {labels[r['condition']]} | {r['mode']} | {r['IoU05_raw_matches']}／15 | {r['IoU05_reference_entry_longest_run']} | {r['IoU03_raw_matches']}／15 | {r['IoU03_reference_entry_longest_run']} |" for r in cases['summaries'])
text=f'''# 固定192输入亮度／对比度对照：静态指标提高仍可能减少通行计数

2026年10月30日。**不采用本轮两个输入变换替换板端方案。** gamma0.7在静态躯干验证中多匹配11个FP32参考、9个QDQ参考，未匹配预测也减少；但原片计数从10／11下降到8／10。CLAHE的FP32／QDQ均为8，还增加了未匹配预测。当前实际O8原输入计数11／人工总量12的历史实机结果保持，本轮没有生成新的O8或实际相机结果。

## 固定了什么，实际做了什么

沿用S192_rot90_seed26和原FP32／QDQ图，不重新训练、不改变128训练图校准、conf0.2、通道裁剪、朝向、ByteTrack或三次稳定计数。三个输入条件在新结果之前固定：原输入；每通道gamma0.7查表；YCrCb中Y通道CLAHE，clipLimit2、8×8网格。处理只发生在缩小后的有效192图像内容中，114补边保持。

先对原输入真实运行8450次FP32／QDQ前向，全部完整raw与旧成功任务逐字节相同；2654个视频输入和6条完整跟踪轨迹也相同，然后才运行两个新变换。正式对照共25350次前向，覆盖1571验证图、原片2175采样时刻和Toros479采样时刻，保留36个计数路径。

原片从0帧顺序保留历史到10873，仅统计和展示8912–10873活动区间。Toros是已使用过的侧视反向压力对照，不是普通俯视训练集，也不替代同一真实通道的双向测试。Toros的5／30Hz是源采样，不是板端FPS。

## 所有主要结果

“验证匹配”分母为1864个可见躯干AABB，采用IoU0.5一对一对应。“未匹配预测”按这套躯干参考口径计算，不能直接改名为牧场误报警数或COCO mAP。原片只有人审总数12，没有独立逐事件F1。

| 输入 | 实现 | 验证匹配／1864 | 验证未匹配预测 | 原片向下计数／12 | Toros5Hz TP／FP／FN | Toros30Hz控制 TP／FP／FN |
| --- | --- | ---: | ---: | ---: | --- | --- |
{table}

gamma的静态增益没有转化为更完整的通行事件。Toros QDQ仅30Hz控制由1提高到2，5Hz仍为1；不能以这项局部改善覆盖原片退化。CLAHE在QDQ下连静态匹配也从1814降至1810，未匹配预测从563升至756。本轮不继续搜索gamma指数、CLAHE网格或置信度来追原片12头，也不把两种方法的结果扩展成“所有亮度处理都无效”。

![全部六实现条件的数值图](<{(ROOT/'delivery/results/media/all_photometric_controls.png').as_posix()}>)

## 剩余开发案例也不能代替完整评价

对旧640模型参照94的15个时刻，检查全部300个候选，并与同帧其他开发参照一对一对应；共90个head数组、180个对应问题。下表的入口连续长度用参照位置定义，仅用于诊断，不是额外加入在线算法的证据。

| 输入 | 实现 | IoU0.5对应／15 | 入口最长连续 | IoU0.3对应／15 | 入口最长连续 |
| --- | --- | ---: | ---: | ---: | ---: |
{case_table}

这些参照仍是模型框，不是独立人工GT或永久牛号。无论局部对应是否改善，都要服从完整事件和所有负例结果，不能只展示改善的一头牛。

事先固定的全部实际192输入可查看：{link(ROOT/'delivery/results/media/original_actual_inputs_QDQ_boxes.png','原片6源帧×3条件')}、{link(ROOT/'delivery/results/media/toros_actual_inputs_QDQ_boxes.png','Toros4源帧×3条件')}。框为本轮服务器QDQ输出；该图不是新增PYNQ预测。

## 执行、失败与独立复核

Slurm130613为COMPLETED、0:0，7分13秒；130616输入复核和130615媒体分别为1分22秒、2秒且0:0。失败130611保留7492份已完成raw：原片轨迹在内存中使用整数键，直接与JSON字符串键比较导致收尾失败；130612无网络探针完整复现4350观察，JSON往返后所有值、ID和事件相同。v2只修该比较及新目录，没有放宽模型或评价门限。130614复核脚本在首个str路径调用处失败，修正Path封装后由130616完成；未重跑网络。

独立脚本复算{v['validation_matching_problems']}个图像关联、{v['video_raw_rows']}个视频raw时刻、{v['counter_observation_ticks']}个跟踪时刻、36个稳定事件路径和24个发布方时间匹配路径。全部8450基线raw再次对旧本地输出逐字节检查；源视频和验证图重新生成12675个输入hash，均一致，30个预选输入像素也一致。gamma复核改用Python round及NumPy索引；CLAHE复核共用OpenCV原语，不能称另写了一套独立CLAHE算法。图中30根实际SVG柱的几何与数值、30个输入图源链接也已核查。

{link(ROOT/'results/independent_verification.json','完整独立复算')} · {link(ROOT/'delivery/results/source_input_verification_v2.json','源像素核查')} · {link(ROOT/'results/reference94_photometric_audit.json','90数组局部诊断')}

结果包包含成功与失败输出，共{transfer['archive_bytes']:,}字节，SHA256 `{transfer['archive_sha256']}`，{transfer['members']}文件，已取回校验。这里的服务器预处理或推理耗时都不当作PYNQ速度；本轮没有新增板端动作、身份推理、独立测试标签或训练更新。

## 下一步的研究选择

保持原输入192实机版本。下一轮先在**训练集自身**审计暗色、局部遮挡和牛体有效像素的覆盖，再固定一个训练侧对照；不要把源片帧或Toros测试帧补进训练后继续称它们独立测试。若做亮度／遮挡增强，需与相同初始化、训练步数、普通增强和三seed基线配对，所有候选共同冻结后统一评价，不能按原片计数挑seed。

评价继续保留静态定位、连续原始检测、跟踪及稳定区域观察四层。新候选只有在开发效果足够、量化／真实O8输出与实际计数检查通过后，才替换部署候选。独立逐事件JSON、真实双向普通俯视会话和永久身份参考仍是最终论文证据缺口；原片只有人工总量12，不补写逐头准确率。
'''
target=ROOT/'输入亮度对照结果与训练决策.md';assert not target.exists();target.write_text(text,encoding='utf-8')
review=f'''# 本轮Review与当前状态

25350次正式对照前向完成，输入／跟踪／逐事件／媒体的单独复算结果已保存。两个输入变换均未采用，旧O8实机版本与固件保持。本轮是开发诊断，整体目标继续。

| 级别 | 核查与处理 |
| --- | --- |
| 已处理 | 数字键／JSON键比较与str路径助手两次失败，原脚本、日志和7492份失败阶段raw保留；主对照未放宽数值或参数 |
| 已处理 | 不把gamma静态多匹配11／9个参考解释成视频计数改善；原片8／10及CLAHE8／8均保留 |
| 已处理 | Toros侧视压力、30Hz源采样与普通俯视、PYNQ帧率区分 |
| 已核查 | 9426图像关联、36事件路径、24发布方匹配、8450基线数组和12675源输入hash |
| 已核查 | 90个head数组仍以旧640模型框为诊断参照，不提升为人工GT |
| 需最终查看 | 3张图共34面板，数值／像素链接核查已通过；实际视觉查看另记，不能由脚本生成自动认定 |
| BLOCKER | 独立事件JSON与永久身份参考未收到，不能认领最终科研准确率 |
| IMPORTANT | 新输入不是实际O8结果；没有新板端速度、功耗或真实相机／RFID证据 |

{link(ROOT/'计划与验收.md','本轮计划')} · {link(target,'完整结果')} · {link(ROOT/'results/independent_verification.json','复算记录')} · {link(ROOT/'results/media_verification.json','媒体数值核查')}
'''
r=ROOT/'Review与当前状态.md';assert not r.exists();r.write_text(review,encoding='utf-8')
print(json.dumps({'report':str(target),'review':str(r),'new_training_updates':0,'adopted_for_deployment':False}))
