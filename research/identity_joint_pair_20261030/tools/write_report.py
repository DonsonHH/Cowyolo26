from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
v=load(ROOT/'results/independent_verification.json');archive=load(ROOT/'results/board_archive_verification.json');tracking=load(ROOT/'tracker_delivery/results/tracker_replay/summary.json')
assert tracking['status']=='ALL4_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'
jobs=load(ROOT/'results/actual_job_rows.json');pairs=load(ROOT/'results/paired_jobs.json');report='''# 新旧身份模型同板对照：固定照片负载的全部四次结果

2026年10月30日。新域模型与对应重编码图库已经接入真实PYNQ-Z2，完成旧—新—新—旧四次同板对照。本阶段验证系统时序和候选输出，照片的永久牛号未知；接受的候选不能计作正确找回。

## 固定了哪些条件

沿用[执行前计划](计划与验收.md)和[正式协议](protocol/run_v1.json)：同一O8固件、mosaic0.5主seed26检测器、192已就绪低分输入、原跟踪／计数、每次78.4秒／392个5Hz时隙。前台主线程和后台均可用CPU0／1，后台nice+10、NCNN单线程、持续工作，不切换亲和性策略。两种身份编码器分别搭配自己编码的同一30张Aug19图库；Aug14事件的检索仍属回顾实验。

每次按相同偏移发布同一10个JPEG、身体框和照片任务，独立于当前计数结果。实际读取、裁剪、PNG0保存、预处理、真实网络、检索以及NPZ证据写出均发生在板上；没有每帧高分JPEG生产者，也没有现场相机或RFID，RF异常按全部未读模拟。输入预检读过相关JPEG，不能称冷文件实验。前台已就绪图像不含曝光／输入解码，图像完整性和图库核验也不在正式周期内。

共用主工作点为原MultiCam阈值0.8445389603236383，额外固定Cows阈值0.8707458695890389只用于相同分数的附加报告。没有根据接受数或时序改变阈值、图库或发布规则。旧与新是“编码器＋对应图库特征”的对照，不能只替换新查询而沿用旧图库。

## 全部四次实机

| 执行顺序／身份模型 | 处理／392 | 跳过 | >200ms | FPS | P95 ms | 计数／人工12 | 10身份任务最长完成s |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
for i,c in enumerate(v['cases'],1):report+=f"| {i}／{c['identity_model']} | {c['processed_frames']} | {c['skipped_slots']} | {c['deadline_misses']} | {c['processed_per_second_over_offered_duration']:.3f} | {c['P95_release_to_count_ms']:.2f} | {c['source_down_count']} | {c['maximum_identity_result_ms']/1000:.3f} |\n"
report+='''
每个条件只有同一源回放的两次设备重复，顺序虽反转，温度、缓存、swap及后台系统工作变化仍可能影响结果；不作显著性或跨牧场推断。平均吞吐、逐帧200ms截止、计数10／人工12和身份结果分别报告，未将其中一项通过当作整个系统通过。

| 身份模型／轮次 | 主阈值接受／10 | Cows附加阈值接受／10 | 最大排队ms | 实际身份网络均值ms |
|---|---:|---:|---:|---:|
'''
for c in v['cases']:
 group=[j for j in jobs if j['run']==c['run']];report+=f"| {c['identity_model']}／{c['repeat']} | {c['accepted_predictions']} | {c['secondary_Cows_threshold_accepted']} | {c['maximum_identity_queue_ms']:.2f} | {sum(j['network_ms']for j in group)/10:.2f} |\n"
changed=sum(p['old_candidate']!=p['new_candidate']for p in pairs if p['repeat']==1)
report+=f'''
10份不同照片中有{changed}份Top-1候选改变，两个模型各自两次重复的输入、特征及候选决定一致。完整20份同照片新旧配对及所有候选见[配对记录](results/paired_jobs.json)和[40个原始作业](results/actual_job_rows.json)。这些候选没有永久身份真值，不计算“恢复率”或C／W／U。

候选图展示了全部10照片及各模型得分最高的登记参考：[第1页](results/candidate_panels/page1.png) · [第2页](results/candidate_panels/page2.png) · [第3页](results/candidate_panels/page3.png) · [第4页](results/candidate_panels/page4.png) · [第5页](results/candidate_panels/page5.png)。模型输出只是候选，不能由视觉相似或自身分数补造身份真值。

## 计时与资源范围

前台release→count含实际检测、框解码、跟踪／计数和CPU边界采样；raw整包写出在周期结束后，每50帧进度写出仍会影响下一时隙及整体吞吐。后台完成含JPEG／PNG和NPZ证据开销，不用纯网络均值代替完整等待。本轮新增了每任务图库文件hash记录，新旧均执行这一步，但图库文件大小不同，不能声称硬件周期完全相同。

亲和性只核查前台主线程、发布线程及后台实际线程，不声称全部既存库线程严格隔离。内存是进程RSS／HWM／swap口径，没有实测整板功率或每事件能量。发布线程的实际入队抖动、排队和CPU边界分别保存。

## 实现、完整结果与复算

正式运行前，冻结40输入：同30张Aug19图库与10张既有真实照片。CPU Slurm作业130870在cu03完成0:0，Torch40次、NCNN40次，没有训练或转换器前向；原始参考包353,294字节、10成员／9清单文件完整取回。板上资格核验再执行40图＋1预热，每张输入SHA、raw及归一化特征保存，随后生成新模型自己的图库与10查询参考。

正式四次有{v['actual_timed_O8_forwards']}个定时O8前向、8个O8资格向量及8预热；身份正式40次＋4预热，另40资格＋1预热，共85个ARM身份前向。新增板端模型前向总数为{v['all_new_actual_board_forwards']}，CPU参考另80次。没有新训练或留出像素；复算没有增加模型前向。

{v['actual_timed_O8_forwards']}份检测raw与同帧已验证输出逐字节一致；本机独立重算{v['counter_observation_ticks']}个观察时刻、8条计数状态机、40份原照片及输入／模型特征／分数、20份配对。每张原PNG都重新解码，与源JPEG及固定身体框重新裁剪比较；20旧查询与旧特征逐字节相同，20新查询与其资格特征逐字节相同。40图库／查询资格特征与Torch、NCNN参考对比均通过，图库不会跨模型混用。[本机独立复算](results/independent_verification.json)

另外把四次真实处理帧序列和全部raw重新送入冻结NumPy ByteTrack，覆盖关联、确认、位置、交接和两种计数。CPU参考重放使用既有0.002像素／2e-6轴坐标容差，临时ID和完整事件必须精确一致；4条完整轨迹、{tracking['observation_ticks']}时刻全部通过，未调整容差。这是计算复核，不能替代独立人工通行标注。[完整关联重放](tracker_delivery/results/tracker_replay/summary.json)

板端完整原包{archive['archive_bytes']:,}字节、{archive['archive_members']}成员／{archive['manifest_files']}清单文件，SHA为`{archive['archive_sha256']}`，逐块及整包核验完成，所有原始文件保留。父子进程、O8、默认旧encoder、共享锁及板内服务终态均复核，外部网口载波仍0；UART未复位或改波特率。

## 采用决定与下一步

新模型保留为已通过同板执行与数值验证的研究候选。固定10任务的结果还不能决定其在真实通行中的身份正确性；默认模型和阈值继续保留。下一步接回实际计数触发的因果选图和按需身份任务，并保持同样证据边界，分别报告漏事件、实际照片选择、后台等待与未解决状态。

身份独立评价的[20ID协议与校准](../identity_final20_20261030/计划与验收.md)已固定，按10已登记／10未知及匹配10ID图库的校准执行；当前只冻结元数据和已有特征阈值，尚未开启这90张保留身份裁剪。它只检验身份组件，部分来源检测原图已被项目使用，不能声称全项目未见像素或跨牧场测试。独立逐事件JSON及原视频永久牛号对应尚缺，任何新接受都不升级为正确找回，平均约5FPS也不等于完整稳定目标达成。
'''
target=ROOT/'新旧身份模型固定负载同板对照.md';assert not target.exists();target.write_text(report,encoding='utf-8');print(target)
