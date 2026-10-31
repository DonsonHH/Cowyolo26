from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def link(p,label):return '['+label+'](<'+str((ROOT/p).resolve()).replace('\\','/')+'>)'
s=load(ROOT/'results/summary_recovered.json');ref=load(ROOT/'results/reference_independent_verification.json');v=load(ROOT/'results/recovery_independent_verification.json')
table='\n'.join('| '+r['run']+' | '+str(r['processed'])+' | '+str(r['skipped'])+' | '+str(r['late'])+' | '+format(r['FPS'],'.3f')+' | '+str(r['count_down'])+' | '+format(r['P95_release_to_frontend_ms'],'.1f')+' | '+format(r['max_enqueue_to_result_ms']/1000,'.2f')+' |' for r in s['cases'])
cpu='\n'.join('| '+r['run']+' | '+str(r['CPU_windows_positive_ticks'])+'/'+str(r['processed'])+' | '+format(r['sum_child_CPU_ticks']/100,'.2f')+' | '+format(r['mean_model_ms'],'.2f')+' | '+format(r['max_queue_wait_ms']/1000,'.2f')+' |' for r in s['cases'])
text=f'''# 后台持续运行缩短等待，但前台吞吐和一次计数退步

2026年10月30日。**不把低优先级持续后台设为默认。** 同一有界JPEG输入和同一O8模型下，持续后台最长身份完成2.56／2.19秒，按帧暂停组为52.51／51.40秒；代价是吞吐4.617／4.273FPS，低于暂停组4.821／4.987FPS。四次计数10／9／10／10，人审总量仍12。后台明显更及时，但没有同时满足前台目标。

实验已在板端完成，随后网线中断；本轮通过串口取回元数据和真实特征，在板端复核原始文件，并用本地同源JPEG重建了全部39张照片及输入。**约20MB原始完整包仍留在板上，尚未完成本机下载**；恢复副本、板端核验和完整归档待取分别记录，不重跑实验凑数据。

## 事前固定的比较

四次顺序为idle_gate→low_priority_parallel→low_priority_parallel→idle_gate。固定mosaic050_seed26、192输入、yolo26_optimization_8、已验证JPEG生产者、过去1秒几何抓拍、PNG0、单线程身体编码器、图库和拒识阈值。每次392个5Hz时隙／78.4秒，从同模型0–8910实际raw重建1783次前史。

idle_gate按帧SIGSTOP且waitpid确认，前台完成后恢复；low_priority_parallel保持nice+10持续运行。没有改全局优先级、CPU频率、固件或网络配置。两组均新增相同的子进程CPU tick边界读取，因此本轮暂停组才是直接基线，不能把历史更好的时序拼进当前处理。

## 四次实际结果

| 实际顺序／策略 | 处理／392 | 跳过 | >200ms | 吞吐FPS | 计数／人工12 | P95前台完成ms | 最长身份完成秒 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

截止时间从全局源时隙释放算起，到检测、跟踪计数、当前高分JPEG等待／选择及入队的前台流程完成。迟到以已处理帧为分母，跳过另计。两次重复是同一公开片段的设备运行，不是独立牧场会话，不给统计显著性结论。

第一轮持续组少处理16帧且计数10→9；第二轮少处理56帧，虽然同为10，仍不能只因没有少计就接受吞吐下降。第一轮迟到177比191少，但第二轮304比187多，P95两轮都更差。所有有利与不利指标都保留。

输入仍为已就绪192回放及实际取得的1050×1440 JPEG，生产者每轮读取392时隙，包括前台跳过的帧。启动完整性检查读过全部JPEG，内核缓存影响没有隔离；正式生产线程只读已释放数据，选择仅用已处理的当前及过去框。真实相机曝光、缩放／编码、双流接收和RFID异常并未接入。

## CPU记录验证了后台确实得到服务

| 运行 | 前台窗口内CPU tick增加次数 | 窗口CPU tick累计折合秒 | 平均模型阶段ms | 最大后台排队秒 |
| --- | ---: | ---: | ---: | ---: |
{cpu}

实际nice均为10，CPU亲和性均为[0,1]。暂停组在所有769个前台边界窗口里子进程都处于T状态，tick增加0；持续组48＋46个窗口累计857＋975个tick，即约18.32秒进程CPU。它支持“取消暂停使后台在前台流程期间获得服务”的机制，而不是仅凭两次较短完成时间推断。

每tick为10ms；快照包含边界读取与粒度误差，不能将这些数字当作神经层精确重叠时间。字段使用进程utime＋stime，未包含另一个PID的CPU，也未改变调度。[Linux进程stat字段](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html)

持续组实际任务9／10，暂停组10／10，共39而非40。第一轮少计会减少负载；不能把该轮2.56秒解释成严格等负载提升。第二轮任务数相同仍有不同照片、事件时间和页缓存／swap状态；两轮只支持系统取舍的观测。

## 全部39张照片与独立数值复算

{link('results/actual_photo_panels/r1_idle_gate.png','第一轮暂停10张')} · {link('results/actual_photo_panels/r1_low_priority_parallel.png','第一轮持续9张')} · {link('results/actual_photo_panels/r2_low_priority_parallel.png','第二轮持续10张')} · {link('results/actual_photo_panels/r2_idle_gate.png','第二轮暂停10张')}

四张接触表39面板全部查看，过曝、邻牛混入和边界变化仍保留。接受候选数1／1／0／1：三个接受均为同一f9790图、候选009、分数0.854908；第二轮持续组的f9790裁剪为约0.829，拒识。无永久身份真值，不能写成找回三头牛或判断拒识为错误。

仅按事件帧＋临时ID＋方向字面配对得到4对、31条条件记录未配对，全部保留。没有改编号凑成同一牛，也不只选成功照片。

1466次完整检测raw在板端独立读取并与旧同模型raw逐字节比较，再取回1466行两端SHA在本机绑定到旧raw；8锚点准入和8预热另计。8598观察／8计数路径、1568个释放后源记录、1466个CPU窗口及39真实后台任务独立复算。没有重训、重新推理原片或放宽计数规则。

39份照片按原生框从本地已有JPEG重建，逐像素SHA与板端原PNG解码后的RGB相同；39份输入张量SHA精确匹配，原始576维特征字节也与板端记录一致。30份重建PNG连文件字节都相同，另外9份只存在容器编码差异，解码像素及输入保持精确，不把重建文件冒充原PNG传输。

服务器130717用原Torch编码器做39查询＋30图库共69次CPU前向，完成0:0、4秒。输入误差0，最大查询归一化特征差2.936e−6、图库4.046e−6，78个查询／图库条件的候选与拒识决定相同。归一化检查沿用原门禁，不将数值实现一致性当身份准确率。

## 连接中断与恢复范围

四次终态和原包已写盘后，电脑先显示网口Disconnected，串口随后确认板端eth0为NO-CARRIER，IP仍192.168.2.99、boot_id未变、ssh和jupyter服务active。没有复位、重启、修改IP或重跑实验。

经串口取得847137字节元数据包和212282字节数值包，两包传输SHA均一致；板端只读审计逐项核对原178个文件，原始整包20018871字节、SHA b87a60784d7f414ae512855d3ed658613d8dc7c2e03cf6ec856d7d61856422a6保留待下载。服务器参考包280545字节／9成员已经取得并验证。

本机最初额外要求重新归一化结果字节一致，有16个向量未满足；与float64参考最大误差2.021e−8，既有门禁为1e−7。保留首次失败后使用早已固定的数值口径；原始特征哈希、照片像素、输入张量和身份决定仍精确核验，没有改动模型或结果。详见{link('串口恢复与数值复核说明.md','恢复与数值口径')}。

## 采用决定与下一步

保留两端取舍，**不采用全程低优先级后台作为默认，也不宣布稳定5FPS、12头计数或身份找回已完成**。新方案确实解决了这一短回放里的长等待，却损害了前台指标。下一步应先定义可接受的前台迟到和身份完成上限，再研究有明确服务预算的后台；固定同一组真实作业／照片的压力回放可以帮助分离调度作用，但不能替代完整真实触发链路。

同时推进普通俯视独立事件参考、永久身份／未登记牛验证。原片和这些条件已多次用于开发，不能当最终独立测试。网络恢复后只取回原完整包并补齐本机归档，不重跑已有实验。当前板卡可经串口审查，网口物理连接仍待恢复。

{link('计划与验收.md','事前计划')} · {link('results/UART_metadata_audit.json','计数／时序／CPU复算')} · {link('results/recovery_independent_verification.json','实际raw与照片／输入／特征绑定')} · {link('results/reference_independent_verification.json','Torch参考')} · {link('results/summary_recovered.json','全部分量及取舍')}
'''
f=ROOT/'后台服务四次实机结果与取舍.md';assert not f.exists();f.write_text(text,encoding='utf-8')
review='''# 后台服务Review与当前状态

- 两轮顺序反转、固定输入生产者／模型／抓拍／计数／拒识，只有后台是否按帧暂停改变；两组相同CPU边界仪器。
- 四次处理378／362／335／391，计数10／9／10／10；持续后台2.56／2.19秒虽比暂停52.51／51.40秒短，吞吐与P95退步，不采用默认。
- 元数据8598观察／8计数路径、1568源记录、1466CPU窗口和39任务复算；暂停组0 tick增长，持续组48／46窗口累计18.32秒进程CPU，不冒充层级精确重叠。
- 网络断开前实验及打包均终态；串口确认同boot_id、IP未变、NO-CARRIER，未复位／改IP／重跑。原20MB整包未本机下载，完整归档仍待恢复。
- 板端独立读取原178文件及1466raw、39照片／输入／特征；串口回传哈希与实际特征，本机39像素／输入精确匹配，30PNG文件字节相同、9仅编码不同。
- 首次额外归一化字节检查失败保留；最大2.021e−8，v2遵循既定1e−7／1e−12复核门禁，原字节哈希不放宽；模型及输出未改。
- 所有39面板查看，4字面配对／31未配对保留，三个接受是同f9790重复图，不称三个正确找回。
- 69次Torch参考／78检索决定一致，130717完成0:0，未干预集群其他作业。
- IMPORTANT：暂停组10任务、持续第一轮9任务，负载不能写成完全相同；重复同视频和未知永久身份仍是开发实验。
- 尚待归档：原始完整结果包本机下载及恢复后的外部SSH／Jupyter验证；当前串口只读复核与重建证据已完成。整体研究目标继续。
'''
f=ROOT/'Review与当前状态.md';assert not f.exists();f.write_text(review,encoding='utf-8')
print(json.dumps({'reports_written':2,'new_default_adopted':False,'full_original_archive_received':False,'whole_goal_complete':False}))
