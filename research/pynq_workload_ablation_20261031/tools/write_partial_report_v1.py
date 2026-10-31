"""Write the failed-plan report from independently verified saved results."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
verification = load(ROOT / 'results/independent_verification.json')
tracker = load(ROOT / 'results/tracker_reference_verification.json')
plan = load(ROOT / 'protocol/run_v2.json')
final = load(ROOT / 'delivery/failed_final_state_v1.json')
jobs = load(ROOT / 'results/actual_job_rows.json')
assert verification['task_status'] == 'FAILED' and verification['completed_timed_cases'] == 5
assert tracker['observation_ticks'] == 10663 and tracker['counter_paths'] == 10
assert not final['kernel_memory_matches'] and final['services'] == {'ssh': 'active', 'jupyter': 'active'}
cases = verification['cases']
comparisons = []
for left_index, right_index in [(0, 1), (0, 2), (2, 3), (3, 4)]:
    left, right = cases[left_index], cases[right_index]
    tables = [{row['frame0']: row for row in load(ROOT / 'delivery/results' / case['run'] / 'timing_rows.json')} for case in [left, right]]
    frames = sorted(set(tables[0]) & set(tables[1]))
    deltas = np.asarray([tables[1][frame]['model_ms'] - tables[0][frame]['model_ms'] for frame in frames])
    comparisons.append({'left': left['run'], 'right': right['run'], 'common_frames': len(frames),
                        'all_shared_frames_used': True, 'mean_right_minus_left_call_envelope_ms': float(np.mean(deltas)),
                        'median_right_minus_left_call_envelope_ms': float(np.median(deltas)),
                        'description_only_order_cache_memory_and_resource_competition_not_separated': True})
comparison_record = {'created_UTC': datetime.now(timezone.utc).isoformat(),
                     'status': 'POSTHOC_ALL_SHARED_FRAME_LATENCY_DESCRIPTIONS_NO_CAUSAL_FACTOR_ESTIMATE',
                     'comparisons': comparisons, 'new_model_forwards': 0, 'thresholds_changed': False}
with (ROOT / 'results/shared_frame_timing.json').open('x', encoding='utf-8') as stream:
    json.dump(comparison_record, stream, indent=2)
    stream.write('\n')

link = lambda label, path: f'[{label}](<{Path(path).resolve().as_posix()}>)'
result_lines = []
resource_lines = []
backend_lines = []
for case in cases:
    result_lines.append(f"| {case['run']} | {int(case['input_producer'])}／{int(case['identity_workload'])} | {case['processed_frames']}／392 | {case['skipped_slots']} | {case['deadline_misses']} | {case['processed_per_second_over_offered_duration']:.3f} | {case['P95_release_to_count_ms']:.2f} | {case['source_down_count']} |")
    resource_lines.append(f"| {case['run']} | {case['mean_model_ms']:.2f} | {case['mean_JPEG_wait_ms']:.2f} | {case['foreground_VmSwap_kB_at_end'] / 1024:.2f} | {case['process_major_faults_delta']} | {case['system_vmstat_deltas']['pswpin']}／{case['system_vmstat_deltas']['pswpout']} |")
    if case['actual_background_jobs']:
        backend_lines.append(f"| {case['run']} | 10 | {case['maximum_identity_queue_ms']:.2f} | {case['maximum_identity_result_ms']:.2f} | {case['mean_identity_network_ms']:.2f} | {case['accepted_predictions_without_identity_GT']} |")
comparison_lines = [f"| {row['left']} → {row['right']} | {row['common_frames']} | {row['mean_right_minus_left_call_envelope_ms']:+.2f} | {row['median_right_minus_left_call_envelope_ms']:+.2f} |" for row in comparisons]
accepted = [job for job in jobs if job['accepted']]
assert len(accepted) == 3 and len({job['photo_sha256'] for job in accepted}) == 1
figure = ROOT / 'reference_delivery/results/figures/chronological_workload.png'
manifest = load(ROOT / 'reference_delivery/results/figure_manifest.json')
assert sha(figure) == manifest['files'][0]['sha256']
visual = {'created_UTC': datetime.now(timezone.utc).isoformat(), 'status': 'ACTUAL_RENDERED_PNG_VISUALLY_REVIEWED',
          'figure_file': str(figure.resolve()), 'sha256': sha(figure),
          'observed': ['All five observed throughput points and five miss/skip pairs are legible.',
                       'Sixth readiness timeout and last two unstarted cases are blank shaded regions, not zero-valued data.',
                       'Axes, unit labels, footnote, legend and title fit without clipping.'],
          'new_model_forwards': 0, 'independent_human_annotation': False}
with (ROOT / 'results/figure_visual_review.json').open('x', encoding='utf-8') as stream:
    json.dump(visual, stream, indent=2)
    stream.write('\n')

report = f'''# PYNQ-Z2高分输入与身份负载：五轮完成及后台启动超时

2026年10月31日。**本轮192输入仍未达到稳定5FPS；八轮冻结方案只完成五个正式时段，第6轮在等待后台READY超过40秒后失败。** 原失败任务没有重启或补跑。五轮原始检测、计数、照片／特征与完整跟踪关联均已复核，不能把“已保存部分复核通过”写成“八轮实验成功”。

本阶段是在{link('实际计数触发四轮恢复', PROJECT / 'identity_trigger_pair_20261030/实际计数触发四轮恢复结果与时序取舍.md')}之后做的资源诊断。它保持固定10照片任务以控制负载，不按本轮计数触发，因此不能替代实际触发系统或独立事件评价。

## 1. 冻结了什么，实际执行了多少

相同192检测权重、原accepted O8、跟踪和计数器，低分辨率帧已就绪。每个正式时段提供392个200毫秒时隙，共78.4秒；对应原片8915–10870的5帧抽样，评价范围仍为用户确认12次完整通行的8912–10873橙框通道。

I表示逐时隙读取、SHA校验、保存到有界银行并固定／取回高分JPEG；W表示向后台发布相同10照片、身体框和相对发布时间的身份任务。W关闭时仍启动相同编码器并预热一次，使后台存在与模型驻留这一前提相同。后台是板上ARM单线程、nice+10、CPU0/1，前台同为CPU0/1；模型、图库和阈值不变。

| 条件 | I：逐帧高分取得 | W：正式身份任务 | 原计划重复 |
|---|---|---:|---:|
| A | 关 | 0 | 2 |
| B | 开 | 0 | 2 |
| C | 关 | 10 | 2 |
| D | 开 | 10 | 2 |

冻结顺序A→B→C→D→D→C→B→A。实际只完成A／B／C／D／D：第6个C只完成前史和两次检测预热、一次身份预热，正式时钟和身份任务尚未开始；最后B／A没有开始。不得为缺失的重复填零、复制旧阶段数据或计算平衡八轮效应。

每轮开始前都对392张JPEG做同样的完整hash读取，约24.97–33.05秒，在正式时段外；这会影响缓存前提，不能称冷启动存储实验。没有清全局cache、关闭swap、调整CPU频率或停止其他服务。I开启时后台任务仍从原文件读取，保持相同照片／tensor，I含生产与缓冲语义而非单个read调用。

## 2. 实际结果：五轮全部保留

| 轮次 | I／W | 处理 | 跳过时隙 | 处理后>200ms | 处理率FPS | 释放至计数P95ms | 下行计数／人工12 |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(result_lines)}
| r6_C | 0／1 | 正式未开始 | — | — | — | — | — |
| r7_B | 1／0 | 未开始 | — | — | — | — | — |
| r8_A | 0／0 | 未开始 | — | — | — | — | — |

上行计数五轮均0。跳过与迟到是不同口径：前者分母为392提供时隙，后者只在已处理帧中判断。处理率始终除以78.4秒，不用纯网络时间换算全链路FPS。相对人工总数12的绝对差为5／4／2／2／9；没有独立逐事件JSON，不能把这些差直接命名为漏检头数或计算事件Precision／Recall。

| 有身份负载的轮次 | 完成任务 | 最大排队ms | 最大入队至结果ms | 身份网络均值ms | 阈值接受（无身份GT） |
|---|---:|---:|---:|---:|---:|
{chr(10).join(backend_lines)}

三轮均执行同一10照片，主阈值{plan['fixed_identity_threshold']:.12f}下各接受1个；合计3次接受对应同一固定照片重复，不能称找回3头奶牛。更高的既有阈值{plan['secondary_Cows_threshold']:.12f}下均不接受。照片、输入、原始特征及分数与此前固定负载参考逐字节一致，因此本轮没有增加独立身份正确率证据，也没有重新校准阈值。

## 3. 换页和调用时间是线索，尚无因果归因

| 轮次 | O8调用包络均值ms | 前台取图等待均值ms | 父进程末VmSwap MiB | 父进程major fault增量 | 系统换入／换出页增量 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(resource_lines)}

“O8调用包络”包含Python调用、原生执行和拷贝，I开启时还包括pin；它不是纯PL计算时间。父进程VmHWM为累计峰值271,884kB，不能拆作各条件独立峰值。资源计数采样并非原子时段边界：前四轮起始样本早于时钟约75–95毫秒，第5轮晚37.018878毫秒，结束样本晚约1.44–93.70毫秒。表中增量只描述这些已记录采样窗口。

为排除“仅仅换了一组输入帧”这一解释，另用每一对实际共同处理的全部帧比较调用包络；这是事后描述，没有进行模型前向或显著性检验：

| 左轮→右轮 | 全部共同帧 | 右减左均值ms | 右减左中位数ms |
|---|---:|---:|---:|
{chr(10).join(comparison_lines)}

两次D都慢，但D第二次还明显退化。C的吞吐又高于A，说明不能据单次差值声称身份网络没有代价。镜像后半组缺失，条件与时间顺序、缓存／换页状态仍混在一起。本轮不提供已分离的I主效应、W主效应或交互因果效应。

![按执行顺序保留五轮及缺失正式时段](<{figure.resolve().as_posix()}>)

图由Matplotlib按已核验JSON生成，实际PNG已打开检查；SVG同步保留。灰色区域表示没有正式时段，不表示0FPS。

## 4. 第6轮为何失败，目前能确认什么

父进程1310在`ready.get(timeout=40)`抛出`_queue.Empty`。子进程1561随后留下正常终态：一次162.14ms网络预热、0正式任务，无子进程异常；父任务已结束，图内存释放未报错、共享锁可取得，六个后台PID均已退出。

原实验、失败终态和采集的boot ID均为e7059099，当前O8文件hash与冻结值一致。失败后SSH／Jupyter为active，内核日志未发现OOM相关记录。**本次没有重启或OOM的日志证据；也没有证据证明READY已经在40秒内发布。** 尚缺导入完成、编码器装载、预热前后、READY入队及父进程收到的分段时间，不能把该超时归为模型崩溃、供电故障或IPC故障。

逐轮重新创建后台是本次控制方法的一部分。第6轮启动超时不自动等同为单个长期驻留服务会在同一时间失败。此前USB阶段自行复位的供电原因也尚未被独立测量证实，两类现象应分开。

新boot起初`PL.bitfile_name`为空；本轮正式准备在持锁后明确加载原accepted O8。这是本次新实验的既有硬件加载，不是为恢复上一阶段凑终态。既有bit／hwh、权重、库和默认Notebook文件均未改写。失败发生在最终硬件错误寄存器采样前，因此没有最终`error=0x0`记录；不将正常close替代该字段。

## 5. 复核和前向预算

| 板上实际图前向 | 次数 |
|---|---:|
| 五轮正式O8检测 | 1748 |
| O8既有锚点准入 | 8 |
| O8预热（包括第6轮准备） | 12 |
| 三轮固定正式身份 | 30 |
| 六个后台身份预热 | 6 |
| 合计 | 1804 |

原预算上界3208，没有把未执行部分算入实际调用。采集和本机复算增加0次模型前向；已有同输入参考复用，新增CPU模型参考为0。

原失败包16,856,960字节，164成员／163清单逐项hash通过；1748实际raw均与既有同帧O8逐字节相同。1176个生产记录、997个前台接收、765个实际取图与模型调用重叠案例核验通过；这些并不代表真实相机曝光。

服务器按{link('use-renly-slurm', Path('C:/Users/Donson/.codex/skills/use-renly-slurm/SKILL.md'))}流程先核验主机／队列，再在cu03以1CPU、4G、10分钟上限执行任务130931，实际4秒、COMPLETED／0:0、错误日志空。五轮完整关联10663时刻／2338跟踪行、10条计数路径均复算，ID和事件精确相同，坐标差实际0；神经模型前向0。短任务的sacct RSS采样没有用于内存结论。

参考包5,801,192字节，40成员／39清单通过，下载发生在采集命令和归档完成之后。原始失败、协议、记录、照片与参考包均保留；成功八轮用采集／核验代码没有执行。

自审另保留两处口径修正：冻结协议遗留旧四轮`expected_timed_O8_maximum=1568`，实际可执行八轮及新字段上界3136／3208明确；不改已执行协议。第一版独立核验假定起始资源样本必早于时钟，在第5轮被实际数据否定；v1失败与v2记录真实采样窗口均保存，没有修改模型结果。

## 6. 接下来如何收敛

先形成有边界的启动测量，再决定改动。优先检验：①spawn子进程是否重复导入前台PYNQ／OpenCV等模块，额外占用驻留内存；预测为仅移动前台导入位置就降低子进程PSS与启动时间。②高分输入／工作集换页是否拖慢调用；预测为同帧、同任务、同缓存前提下的受限工作集减少换页并改善尾时延。③READY发布晚还是父进程接收晚；用分段时间戳区分，先不放宽40秒。

当前有一个17分钟级、可自动判定失败的原始实验，但没有验证过的秒级最小复现；不把离线读取错误栈当作已重现启动路径。按{link('diagnosing-bugs', Path('C:/Users/Donson/.codex/skills/diagnosing-bugs/SKILL.md'))}，本轮止于实测基线、失败保存和候选可证伪预测，尚未宣告根因或修复完成。省去立即重复重型实验，是为了先建立能区分上述假设的测量边界。

后续每次只改一个变量，使用新目录／协议／预算，保留本次失败。若仅做导入内存探针，单独报告其启动与驻留范围；只有重回相同完整周期负载且重复完成，才讨论5FPS改善。真实相机／RFID、独立逐事件JSON、原12次通行的永久牛号和实测功耗仍需补证据。

论文可以据此写入一个可复核的运行失败和时序取舍；目前不能以“192下稳定实时”“准确找回掉标牛”作结论。完整研究路线仍见{link('研究阶段总结', PROJECT / '研究阶段总结_20261030.md')}，论文草稿v3保留为此前已核验结果的版本。

## 7. 可复现入口

- {link('冻结方案', ROOT / '计划与验收.md')}；{link('实际执行协议v2', ROOT / 'protocol/run_v2.json')}。
- {link('原失败终态', ROOT / 'delivery/results/terminal.json')}；{link('失败后的设备状态', ROOT / 'delivery/failed_final_state_v1.json')}。
- {link('本机独立复算', ROOT / 'results/independent_verification.json')}；{link('完整关联参考复核', ROOT / 'results/tracker_reference_verification.json')}。
- {link('共享帧时序描述', ROOT / 'results/shared_frame_timing.json')}；{link('实际图片自审', ROOT / 'results/figure_visual_review.json')}。
'''
review = '''# 本阶段自审与状态

八轮实验在第6轮准备时报错，保持FAILED；前五轮全部结果完成复核，不补成八轮成功。报告按原始时隙计算FPS，逐列复核迟到、跳过、P95、计数、固定身份工作量及其排队／完成时延。

两次D的不利结果和三轮缺失均显示。明确资源采样窗口偏移、累计VmHWM、调用包络与纯PL时间的区别；没有通过系统计数推断换页为唯一原因。READY超时与子进程正常预热终态并列，未认领模型崩溃或重启。

1748实际raw、30身份照片／tensor／特征／分数、1176生产记录、997接收、10计数状态路径已独立复算。服务器130931以0模型前向复核10663观察／2338跟踪行，事件ID精确一致；原始包和参考包完整取回，实际PNG已查看。

板上1804次图前向包括第6轮两次检测预热及一次身份预热，不只统计正式任务。采集0、CPU神经参考0。主阈值3次接受是同一固定照片重复，无永久身份GT。人工12为总数，未冒充逐事件标注。

保留冻结协议的继承字段冲突与独立核验v1的错误边界假定；v2核验修正的是检查前提，原数据没有更改。未使用的成功八轮工具保留为未执行，不作为证据。当前根因、最小复现和修复均未完成，整体研究目标仍继续。

此为助手自审及程序复算，不是独立人工标注复核、同行评审或投稿验收。
'''
for name, value in [('高分输入与身份负载_五轮结果和启动超时.md', report), ('Review与当前状态.md', review)]:
    with (ROOT / name).open('x', encoding='utf-8') as stream:
        stream.write(value)
print(json.dumps({'status': 'FAILED_PLAN_REPORT_WRITTEN_FROM_VERIFIED_RESULTS',
                  'lines': len(report.splitlines()), 'shared_frame_comparisons': comparisons,
                  'whole_goal_complete': False}))
