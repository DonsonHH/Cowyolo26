"""Create prose from all eight verified workload periods, including adverse data."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
data = load(ROOT / 'results/independent_verification.json')
tracker = load(ROOT / 'results/tracker_reference_verification.json')
drop = load(ROOT / 'results/dropped_frame_counterfactual_verification.json')
state = load(ROOT / 'delivery/results/record.json')
assert len(data['cases']) == 8 and data['actual_ARM_timed_queries'] == 40
assert tracker['counter_paths'] == 16
cases = data['cases']
link = lambda label, path: f'[{label}](<{Path(path).resolve().as_posix()}>)'
main_rows, resource_rows = [], []
for case in cases:
    main_rows.append(f"| {case['run']} | {int(case['input_producer'])}/{int(case['identity_workload'])} | {case['processed_frames']} | {case['skipped_slots']} | {case['deadline_misses']} | {case['processed_per_second_over_offered_duration']:.3f} | {case['P95_release_to_count_ms']:.2f} | {case['source_down_count']} |")
    queue = '—' if case['maximum_identity_queue_ms'] is None else f"{case['maximum_identity_queue_ms']:.2f}"
    end = '—' if case['maximum_identity_result_ms'] is None else f"{case['maximum_identity_result_ms']:.2f}"
    resource_rows.append(f"| {case['run']} | {case['mean_model_ms']:.2f} | {case['mean_JPEG_wait_ms']:.2f} | {case['foreground_VmSwap_kB_at_end']/1024:.2f} | {case['process_major_faults_delta']} | {queue} | {end} |")
d = [case for case in cases if case['condition'] == 'D']
all_slots = all(case['processed_frames'] == 392 for case in cases)
all_deadlines = all_slots and all(case['deadline_misses'] == 0 for case in cases)
same12 = all(case['source_down_count'] == 12 for case in cases)
contrasts = []
for repeat in [1, 2]:
    values = {case['condition']: case['processed_per_second_over_offered_duration'] for case in cases if case['repeat'] == repeat}
    assert set(values) == {'A', 'B', 'C', 'D'}
    contrasts.append({'repeat': repeat, 'I_average_difference_FPS': ((values['B'] - values['A']) + (values['D'] - values['C'])) / 2,
                      'W_average_difference_FPS': ((values['C'] - values['A']) + (values['D'] - values['B'])) / 2,
                      'difference_of_differences_FPS': values['D'] - values['C'] - values['B'] + values['A']})
with (ROOT / 'results/descriptive_contrasts.json').open('x', encoding='utf-8') as stream:
    json.dump({'status': 'MIRROR_ORDER_WITHIN_BOOT_DESCRIPTIVE_CONTRASTS_NOT_POPULATION_CAUSAL_EFFECTS',
               'contrasts': contrasts, 'new_model_forwards': 0}, stream, indent=2)
    stream.write('\n')
figure = ROOT / 'reference_delivery/results/figures/chronological_workload.png'
programming = '正式任务明确重新加载了原O8' if state['explicit_O8_programming'] else '正式任务复用已有O8，没有重新编程PL'
report = f'''# 精简后台导入后的八轮负载：实测与剩余问题

2026-10-31。**本次完整完成A/B/C/D/D/C/B/A八轮。高分JPEG取得与固定10身份任务同时开启的两次D，处理率为{d[0]['processed_per_second_over_offered_duration']:.3f}／{d[1]['processed_per_second_over_offered_duration']:.3f}FPS，计数{d[0]['source_down_count']}／{d[1]['source_down_count']}（人工总数12）。** 完整执行、模型数值一致与目标达成分开判断：八轮是否全部处理392时隙：{'是' if all_slots else '否'}；是否全部时隙在200ms内完成：{'是' if all_deadlines else '否'}；八轮总数是否均为12：{'是' if same12 else '否'}。

## 改动与控制

{link('四次启动探针', PROJECT / 'pynq_startup_probe_20261031/后台导入与启动内存_四次测量.md')}显示，原spawn后台重复导入前台模块。源码只将6条OpenCV／PYNQ／原生图／初始化／解码／跟踪导入移入main，AST检查证明其他运行时语句未变；后台worker文件、模型、阈值和数值路径原样保留。既有O8和权重文件没有改写，{programming}。

同一192检测器、392个200ms时隙，每正式时段78.4秒。I为逐帧高分JPEG读取／SHA／有界银行／pin与take；W为0或固定10原照片身份任务。W关也启动并预热同一后台，NCNN单线程、nice+10、CPU0/1。低分帧预先就绪，每轮计时外做同样完整JPEG hash读取，保持原计时与日志成本；没有清cache、关闭swap、改频率或停止其他服务。

本轮仍是公开回放资源控制，不按本轮通行动态触发，I开启时后台也从原文件取得同照片。源帧抽样8915–10870，人工确认范围8912–10873。只有来源总数12，未收到独立事件JSON或永久牛号。

## 八轮全部结果

| 轮次 | I/W | 处理/392 | 跳过 | 处理后>200ms | FPS | 释放至计数P95ms | 下行计数/人工12 |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(main_rows)}

跳过分母为392提供时隙，迟到只在已处理帧中判断；FPS为处理数／78.4秒。P95从时隙释放算到计数完成，既不是单次网络耗时，也不含未处理时隙。人工总数差不能直接拆为逐事件漏检或F1。

| 轮次 | O8调用包络均值ms | JPEG等待均值ms | 父进程末VmSwap MiB | 父进程major fault增量 | 身份最大排队ms | 身份最大入队至结果ms |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(resource_rows)}

调用包络包含Python、原生执行／拷贝，I开还包含pin，不是纯PL时间。资源快照并非原子时段边界，实际起止偏移均保存在独立核验JSON；本表只描述记录窗口。末VmSwap不等于当轮峰值，累计VmHWM也不当作各条件独立峰值。启动探针的PSS节省量没有外推成周期负载的整板内存节省。

![八轮处理率、迟到与父进程换页状态](<{figure.resolve().as_posix()}>)

同一条件的两个重复、全部不利计数和迟到均保留；本轮只有一个boot、一个源片段，不做跨牧场统计显著性声明。另存的差值只描述本次镜像顺序的I/W对照，不把顺序、缓存或非线性状态变化完全排除。

## 身份与检测数值

四个W开启时段均完成相同10正式照片任务，共40；照片、input、raw、归一化特征、图库分数和既有阈值决定与此前固定负载参考一致。本轮没有重选阈值或更换图库，也没有新增独立身份测试。阈值接受共{sum(case['accepted_predictions_without_identity_GT'] for case in cases)}次，只能按重复固定照片解释，不能称已找回对应数量的不同奶牛。

{data['actual_timed_O8_forwards']}份实际O8输出均与已有同帧raw逐字节相同。所有提供时隙由处理／跳过完整覆盖，{data['producer_source_frames']}生产记录、{data['frontend_received_packets']}前台接收和{data['producer_model_IO_overlap_cases']}实际取图／调用重叠案例核验。完整跟踪关联在CPU复算{tracker['observation_ticks']}观察／{tracker['post_tracker_rows']}跟踪行、16事件路径，临时ID及事件精确一致；它验证实现重放，不证明事件或永久身份正确率。

板端图前向分别为{data['actual_timed_O8_forwards']}正式检测、8准入、16检测预热、40身份正式及8身份预热，共{data['all_new_actual_board_forwards']}，上界3208；四次启动探针另计4，不混入。采集／CPU完整关联／绘图增加0神经前向，相同输入复用既有CPU参考。完整原包和参考包均在终态后下载并逐项hash核验。

## 如何解释相对旧失败的变化

{link('旧八轮计划失败', PROJECT / 'pynq_workload_ablation_20261031/高分输入与身份负载_五轮结果和启动超时.md')}保持原始5个完整时段及第6轮READY超时。本轮是看过该失败和启动探针后的新候选，采用新目录、协议、预算，没有补跑或覆盖原任务。

两阶段虽然同boot，但原试验起初base状态、本轮已有O8，缓存／换页初态也不同。因此新旧差值不能全部归因于6条导入。本次结果只表明候选在记录条件下完成了八轮及对应的实际吞吐；原40秒超时的唯一根因仍未证明。

该实现改进本身不能证明论文创新性。它支持资源边界、初始化成本与吞吐质量取舍的实证；下一步仍需让实际通行触发链路使用同一候选，并补独立事件和永久身份。192以外的256／320此前同O8向量结果仍按原范围成立，本轮未复测，不能据192候选承诺三种尺寸都达5FPS。

## 计9的那轮：离线逐帧补回诊断

r5_D实际跳过9020、9155、9360、9385、9490、9515、9720、10105帧。利用r1_A已经计算且共同帧逐字节一致的raw，逐一只补回其中一帧，再加“全部8帧补回”控制，共9个事后CPU重放；模型、阈值和跟踪规则不变，没有新的神经前向。

只有单独补回9515帧时，计数从9回到完整输入模型参照的10；其余7个单帧补回仍为9，全部补回也是10。9个重放共19519观察／18事件状态路径均独立复算，单帧补回之前的前缀精确不变，全部补回的完整轨迹与r1_A精确相同。

这支持“提供时隙中的关键入口观察被跳过会影响计数”，参照仍是模型的10，不是人工12。此结果重复了已见源片段上的脆弱性，不能称新的独立测试、实际设备补帧性能或恢复某一永久牛号。下一步应评价一般性的有界输入／排队规则与尾延迟，而不是在程序中针对9515帧特判。

{link('全部9个补回结果及范围', ROOT / 'results/dropped_frame_counterfactual_verification.json')}。

## 复现与自审

{link('冻结计划', ROOT / '计划与验收.md')} · {link('执行协议', ROOT / 'protocol/run_v1.json')} · {link('源码只移动6条导入', ROOT / 'evidence/six_imports_only_diff.txt')} · {link('全部本机复算', ROOT / 'results/independent_verification.json')} · {link('完整关联参考', ROOT / 'results/tracker_reference_verification.json')}。
'''
review = '''# 本轮自审

完整八轮的FPS、跳过、迟到、P95、计数和固定身份工作量按实际文件复算；0任务轮次仍保留同样后台驻留／预热。区分启动成本、吞吐、200ms尾延迟和人工总数12，未将实现一致性当作识别准确率。

原5轮失败未补跑，完整候选是新协议及预算。源码仅移动6条导入，模型与阈值不变；新旧初始overlay／缓存／换页不同，未声称所有性能差由该改动独立造成。所有不利轮次、时钟窗口偏移和换页状态均保留。

逐帧raw、40照片输入与特征／分数、完整CPU关联及图表来源均检查；神经前向预算只计实际发生，启动探针的4次预热单列。实际PNG另行打开后才确认视觉检查。当前仍是公开回放固定工作量控制，真实输入、动态触发复测、独立事件、永久牛号及功耗待证据，整体目标继续。
'''
for name, text in [('精简后台导入_八轮负载与剩余问题.md', report), ('Review与当前状态.md', review)]:
    with (ROOT / name).open('x', encoding='utf-8') as stream:
        stream.write(text)
with (ROOT / 'results/outcome_scope.json').open('x', encoding='utf-8') as stream:
    json.dump({'all8_complete': True, 'all_slots_processed': all_slots, 'all_offered_deadlines_met': all_deadlines,
               'all8_total_count_equals_human12': same12, 'steady_state_real_camera5FPS_proven': False,
               'source_event_or_identity_GT_obtained': False, 'whole_goal_complete': False}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': 'ALL8_REPORT_WRITTEN_FROM_VERIFIED_RESULTS', 'lines': len(report.splitlines()),
                  'all_slots_processed': all_slots, 'all_offered_deadlines_met': all_deadlines, 'whole_goal_complete': False}))
