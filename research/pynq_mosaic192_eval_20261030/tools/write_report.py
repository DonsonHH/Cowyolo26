from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def link(p,label):return '['+label+'](<'+str(Path(p).resolve()).replace('\\','/')+'>)'
q=load(ROOT/'delivery/results/quality/summary.json');v=load(ROOT/'results/independent_board_verification.json');vis=load(ROOT/'results/visual_review.json')
assert q['ORT_actual_forwards']=={'FP32':4225,'QDQ':4225} and v['actual_video_model_forwards']==2654 and vis['panels_actually_viewed']==16
counts=[]
for mode in ['FP32','QDQ']:
    source=next(r for r in q['video_metrics'] if r['scene']=='original' and r['mode']==mode and r['counter']=='handoff_events')
    external=[next(r['formal_event_metrics'] for r in q['video_metrics'] if r['scene']=='toros' and r['mode']==mode and r['counter']=='handoff_events' and r['stride']==stride) for stride in [6,1]]
    counts.append((mode,source['down'],[[r[k] for k in ['TP','FP','FN']] for r in external]))
source=next(r for r in v['source_counts'] if r['scene']=='original' and r['counter']=='handoff_events')
external=[next(r for r in v['publisher_event_scores'] if r['stride']==stride and r['counter']=='handoff_events') for stride in [6,1]]
counts.append(('实际O8',source['down'],[[r[k] for k in ['TP','FP','FN']] for r in external]))
table='\n'.join('| '+name+' | '+str(n)+' | '+'／'.join(map(str,t[0]))+' | '+'／'.join(map(str,t[1]))+' |' for name,n,t in counts)
t=v['timing_ms'];old=load(PROJECT/'pynq_rot192_eval_20261029/results/independent_board_verification.json')
text=f'''# 新mosaic0.5主候选：完整量化与真实PYNQ视频结果

2026年10月30日。固定mosaic050_seed26已完成8450次FP32／QDQ评价、2654次实际O8视频前向和真实ARM跟踪计数。**实际板端原片计数为{source['down']}，人工总量12；反向5Hz为{'／'.join(map(str,counts[-1][2][0]))}。** 这是新权重的实际板端结果，仍不能把单片改善写成完整牧场系统成功。

## 三种实现全部保留

| 实现 | 原片向下计数／人工12 | Toros5Hz TP／FP／FN | Toros30Hz源采样控制 TP／FP／FN |
| --- | ---: | --- | --- |
{table}

Toros为已用的侧视反向压力对照，发布方轨迹导出6次完整通行，时间容差2秒；不当作同一真实通道的双向普通俯视试验。30Hz只表示同一raw缓存按每帧送入计数器，不是板端实际FPS。原片只确认总数12，缺独立逐事件真值，不能把总数比例当逐头准确率。

旧mosaic1.0实际O8为原片11、反向5Hz1／0／5。本轮同时看原片与外部方向，不把一项改善覆盖另一项退步，也没有自动全局替换模型。新候选是否采用还要结合周期负载、普通俯视新会话和独立评分。

## 固定内容与实现证据

checkpoint SHA `628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb`；192、原通道裁剪和朝向、conf0.2、ByteTrack、入口交接及三次稳定规则保持。128训练校准图已在前序准入核对，验证／源片／Toros不用于校准。没有重新烧写bit或替换全局Pillow／NumPy，也没有把跟踪ID当永久牛号。

1571张开发验证图有1864个可见躯干AABB参考，固定IoU0.5一对一匹配：FP32为1838，QDQ为1839，未匹配预测230／241。这不是COCO mAP，也不是视频计数或身份准确率。新前向之前8个输入锚点与旧冻结GPU张量逐字节一致；2654个无损PNG又逐张重建输入张量hash。

实际板端每个视频输入都运行新的完整O8网络和实际ARM计数器；原片保留0–10873历史，只统计／展示8912–10873，Toros全部479源时刻。2654份完整300候选raw和6条计数路径均取回；8个视频锚点与原生整数CPU完整raw逐字节一致。QDQ与真实O8仍有{v['QDQ_ORT_vs_actual_O8_different_raw_frame_rows']}个raw时刻不同，不能用导出图替代实机证明。

## 实机耗时的具体范围

| 阶段 | 全2654帧平均ms |
| --- | ---: |
| 192PNG读取 | {t['PNG_read_ms']['mean']:.2f} |
| 预处理 | {t['preprocess_ms']['mean']:.2f} |
| 审计用输入hash | {t['input_hash_check_ms']['mean']:.2f} |
| 真实O8网络 | {t['tensor_to_raw_ms']['mean']:.2f} |
| 框解码与坐标恢复 | {t['decode_restore_ms']['mean']:.2f} |
| 跟踪与计数 | {t['tracker_counter_ms']['mean']:.2f} |
| raw写入／记录 | {t['raw_memorymap_and_row_save_ms']['mean']:.2f} |
| PNG→计数及raw保存总计 | {t['PNG_to_counter_with_raw_save_ms']['mean']:.2f} |

总计P95为{t['PNG_to_counter_with_raw_save_ms']['p95']:.2f}ms，最大{t['PNG_to_counter_with_raw_save_ms']['max']:.2f}ms，{v['frame_times_over200ms']}帧处理时间超过200ms。这里没有5Hz周期释放或真实相机，不能将“处理耗时>200ms”与周期中的释放至计数迟到混为同一指标，也不能由单独均值证明前后台约5FPS。

![新权重三实现及实际板端耗时](<{(ROOT/'media_delivery/results/media/quality_and_actual_board.png').as_posix()}>)

{link(ROOT/'media_delivery/results/media/FP32_QDQ_actual_PYNQ_8912_10873.mp4','三栏源视频：FP32／QDQ／实际PYNQ')}，1962帧、25fps播放。画面显示原生上下文，192输入的推理结果按5Hz采样保持；播放帧率不等于网络速度。四个实际编码锚点及12个累计数面板已核对。

## 执行与自审

服务器130635完成／0:0，2分33秒；8450个ORT前向和8个原生视频锚点单独计数。板端PID28957完成2654视频前向＋2预热，安全关闭后已不存在，已知O8 bit保持。启动SSH等待曾超时，后续读取同一PID确认活跃后继续监测，没有重复启动。

独立复算3142个图像关联、12个服务器事件路径、全部板端原坐标框与2734个跟踪时刻／6个计数路径、8个原生锚点；实际raw、源帧和方向评价均保留。19根实际SVG柱、完整1962帧严格解码、5图16面板已审阅。视频只输出用户指定8912–10873范围，没有切走漏计时段。

本轮是已用开发材料的实现与系统评价，未新增独立测试、永久身份标签或现场相机／RFID证据。接下来{link(PROJECT/'pynq_mosaic192_joint_20261030/计划与验收.md','同板两轮顺序反转周期验证')}会使用新模型实际前史、实际照片与真实身份网络，单独记录吞吐、迟到及后台等待。

{link(ROOT/'results/independent_board_verification.json','完整板端独立复算')} · {link(ROOT/'results/independent_quality_verification.json','量化质量复算')} · {link(ROOT/'results/media_verification.json','视频及图核查')}
'''
path=ROOT/'新候选量化与真实视频结果.md';assert not path.exists();path.write_text(text,encoding='utf-8')
review=f'''# 新候选完整视频Review与当前状态

新mosaic0.5主seed26的FP32／QDQ及真实O8完整视频已经执行与自审，阶段范围止于无周期PNG回放；同板周期及身份结果另记。

- 保留原片计数{source['down']}／人工12、Toros侧视压力与30Hz源采样的限定，不用总数替代逐事件真值。
- 8450ORT、2654实际O8前向、8原生锚点和所有raw／轨迹取回，QDQ并非板端raw。
- 19SVG柱、1962帧严格解码和5图16面板完成数值与视觉核查。
- 启动SSH等待超时后追踪同一活跃PID，未重启；全部自有视频进程终态已核验。
- IMPORTANT：本轮仍是开发材料，实际相机／RFID、独立事件与永久身份参考不足；没有自动采用新模型。
'''
path=ROOT/'Review与当前状态.md';assert not path.exists();path.write_text(review,encoding='utf-8')
print(json.dumps({'actual_O8_original_down':source['down'],'actual_O8_Toros5Hz_TP_FP_FN':counts[-1][2][0],'mean_PNG_to_counter_ms':t['PNG_to_counter_with_raw_save_ms']['mean'],'whole_goal_complete':False}))
