from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
data = load(ROOT / 'results/independent_verification.json')
assert data['actual_ARM_identity_warmups'] == 4 and not data['periodic_5FPS_tested']
rows = []
phases = []
for case in data['cases']:
    name = '原导入' if case['variant'] == 'original' else '前台导入留在父进程'
    rows.append(f"| {case['run']} | {name} | {case['module_import_ms']/1000:.3f} | {case['start_to_READY_received_ms']/1000:.3f} | {case['child_Pss_kB']/1024:.2f} | {case['parent_Pss_kB']/1024:.2f} | {case['two_sample_Pss_sum_kB']/1024:.2f} |")
    phases.append(f"| {case['run']} | {case['encoder_construct_and_bin_hash_ms']:.2f} | {case['gallery_and_input_read_ms']:.2f} | {case['warm_network_ms']:.2f} | {case['post_warm_to_READY_put_ms']:.2f} | {case['READY_put_call_to_parent_received_ms']:.2f} |")
link = lambda label, path: f'[{label}](<{Path(path).resolve().as_posix()}>)'
report = f'''# 后台重复导入成本：四次实机启动测量

2026-10-31。**把前台导入限制在父进程，四次小规模对照中READY由15.4–17.0秒降到约2.36秒，两进程顺次采样PSS合计低37.5–37.9MiB。** 这是启动与驻留成本的证据；未重现原第6轮的40秒超时，也未运行周期负载，不能称已解决完整系统5FPS。

## 实验对应哪个问题

{link('原八轮失败报告', PROJECT / 'pynq_workload_ablation_20261031/高分输入与身份负载_五轮结果和启动超时.md')}只完成5个正式时段，第6轮准备等待READY超时，但子进程后来完成了正常预热。当前探针检查spawn是否让后台重复加载只供前台使用的PYNQ、OpenCV、原生图、设备初始化、解码和跟踪模块。 [Python 3.10官方文档](https://docs.python.org/3.10/library/multiprocessing.html#the-spawn-and-forkserver-start-methods)说明spawn使用新的解释器并导入主模块，因此顶层导入会进入子进程；这里用模块标志和时钟实测这一推断。

原导入与精简导入采用同一个已执行源文件的导入头，两者都省略原未调用函数体；只相差6条导入。顺序冻结为原→精简→精简→原，4个独立父进程。两种父进程都在创建后台前装入相同前台模块，保留相同43,352,064字节的392张192低分帧、相同1783前史及原NativeGraph工作集；父进程静止，不运行检测图、200ms调度或高分JPEG取得。

后台均为nice+10、CPU0/1、单线程同旧编码器／图库，一次相同既有身份预热、0正式查询。40秒Queue等待阈值保留，测量额外记录从spawn前到收到READY的完整时间。boot保持e7059099、O8已加载，本轮没有编程PL。

## 四次全部结果

| 轮次 | 方式 | 子进程模块导入s | spawn前至收到READY s | 子进程PSS MiB | 父进程PSS MiB | 两进程顺次采样PSS合计MiB |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

原导入的后台确实包含`pynq`、`cv2`和`frame_pipeline`；精简两次均没有。两种父进程都具备完整前台，因此没有通过关闭前台工作集获得差值。子进程PSS下降约64.3MiB，但父进程PSS同时上升，共享页分摊也会影响该数值；不能把64.3MiB写成总内存节省。按相邻镜像配对，两进程合计差分别为37.54与37.87MiB。

PSS对共享物理页作比例分摊，smaps_rollup汇总进程各映射；定义采用[Linux 6.6官方/proc文档](https://docs.kernel.org/6.6/filesystems/proc.html)。这里只顺序采样父／子进程，不能当作整板RAM、系统峰值、所有缓存或CMA分配。四次READY时父／子进程VmSwap均0；没有重现旧五轮后累积的换页状态。

| 轮次 | 编码器构造及bin hash ms | 图库／输入读取ms | 身份网络预热ms | 预热结束至put前ms | put调用前至父收到ms |
|---|---:|---:|---:|---:|---:|
{chr(10).join(phases)}

构造列包含同一源码行的权重hash，不是纯构造函数。put前到父收到的2.40–3.38ms包含Queue feeder、IPC与调度，不是纯IPC延迟；异步Queue put返回与父进程收到之间不强加不成立的全序。约20ms预热后间隔含tensor／raw hash和亲和性检查，两种条件相同；完整warmup向量在父进程请求停止之后才落盘，不计入READY路径。

四次均在40秒内READY，未观测到原异常。结果支持“后台存在可测的多余导入成本”，尚不能证明它独自导致原超时。新的父进程、静止前台及缓存状态，与原连续五时段后的状态不同；这里没有做超时因果排除或完整吞吐评价。

## 数值、设备与预算复核

四个预热input与此前导出张量逐字节一致，四个576维raw与原ARM v3实际输出逐字节一致；0正式身份查询，0检测图，0训练，0新增CPU模型参考，总计4次ARM图前向。不是4头牛的身份正确率试验。

完整归档85,156字节、45成员／44清单hash通过，下载在采集器2090终态后进行。控制器1887、4父进程和4后台均已退出，共享锁可取得；当前core错误寄存器0、DMA错误位清零，既有运行文件hash匹配，服务active。本次设备状态不能补作上一阶段未采样的最终错误寄存器记录。

源码核对确认两个探针只差6条导入，静止前台帧银行hash四次相同，全部分段时钟按实际可成立的先后关系复算。原40秒超时仍未被重现，整体目标继续。

## 如何应用这一结果

已经为下一阶段{link('完整八轮父进程导入候选', PROJECT / 'pynq_parent_only_workload_20261031/计划与验收.md')}冻结新协议：在原完整负载代码中只把6条导入移入main，后台／计数／模型／阈值保持，并在原A/B/C/D/D/C/B/A下重新做候选验证。原失败不补跑、不覆盖；新阶段的数字不计入本阶段4次预热。

只有完整周期实测、逐帧输出、身份工作量与全部不利结果核验后，才讨论5FPS进展。人工12仍是通行总数，独立事件JSON、永久牛号、真实相机／RFID及功耗继续待证据。

{link('冻结计划', ROOT / '计划与验收.md')} · {link('执行协议', ROOT / 'protocol/run_v1.json')} · {link('独立复算', ROOT / 'results/independent_verification.json')} · {link('原始设备终态', ROOT / 'delivery/final_state.json')}。
'''
review = '''# 自审与范围

四次导入／READY／内存测量已完成，4个预热输入和ARM raw逐字节核对。子进程单独PSS下降与两进程PSS合计下降分开报告，解释共享页分摊及顺次采样，不把PSS当整板峰值或CMA总量。

区分模块导入、编码器构造加bin hash、图库读取、网络预热、元数据检查与Queue收到的时钟；没有将put到收到写成纯IPC。记录40秒超时未重现、父／子VmSwap均0、静止前台和独立新父进程，不以组件改进宣布原问题已修复。

本阶段4次ARM预热、0检测图、0正式查询、0训练／新CPU模型前向。完整新八轮是另一阶段，旧失败记录和总12人工范围保留。此为助手自审及程序复算，不是现场或独立身份验证。
'''
for name, text in [('后台导入与启动内存_四次测量.md', report), ('Review与当前状态.md', review)]:
    with (ROOT / name).open('x', encoding='utf-8') as stream:
        stream.write(text)
print(json.dumps({'status': 'FOUR_STARTUP_DIAGNOSTIC_REPORT_WRITTEN', 'lines': len(report.splitlines()),
                  'new_model_forwards': 0, 'periodic_5FPS_tested': False}))
