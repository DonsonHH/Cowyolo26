from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def link(p,label):return '['+label+'](<'+str((ROOT/p).resolve()).replace('\\','/')+'>)'
v=load(ROOT/'results/independent_verification.json');s=load(ROOT/'delivery_v2/results/record.json')
table='\n'.join('| '+('独立读取' if r['mode']=='read_only' else '实际O8后')+' | '+r['method']+' | '+('未驻留／DONTNEED请求' if r['cache_request']=='cold_requested' else '预读／已驻留')+' | '+format(r['JPEG_wall_ms']['mean'],'.2f')+' | '+format(r['JPEG_process_CPU_ms']['mean'],'.2f')+' | '+str(r['positive_device_read_delta_cases'])+'/32 |' for r in v['groups'])
text=f'''# JPEG成本已定位到非驻留文件读取，完整流水线尚未修复

2026年10月30日。**原先46–48ms的JPEG取得成本主要可由存储读取解释；单纯改成预分配readinto不能消除它。** 128次实际O8前向之后的读取：原bytes方法未驻留42.85ms、预读后3.89ms；readinto为44.37／2.26ms。两种方法的冷读都伴随文件页由未驻留变为驻留、设备读取计数增加，热读均全部驻留且设备增量为0。

这是定位成本的受控微基准，**没有完成新的周期计数、身份并发或5FPS修复**。原完整周期目标检查仍红，保留先前4.834／4.796FPS和253／281迟到；不把预读成本移出计时后宣称系统已更快。模型、计数规则、身份门限及默认策略均保持。

## 事前问题与真实红色命令

先运行`tools/check_target.py`，核验原实机记录SHA后返回PERIODIC_TARGET_RED／退出1。它检查用户的约5FPS目标在原完整周期中的实际表现，不是任造的慢测试。随后按事前顺序检查：文件缓存／存储；分配与复制；计算或内存负载交互。

固定392时隙中的0,26,…,390共16个均匀帧，不依据新性能选择。每个来源在独立读取、实际O8前向后读取两模式中，比较bytes与readinto、DONTNEED请求与先预读，并反转顺序重复两次。共256读取条件，每组32；同16图的条件重复不能当256独立牧场样本。

高分图是已有1050×1440 JPEG，192输入是已有同源BGR。只预载16个192输入，不预载全部260MB高分JPEG。真实O8 measured128、准入8、预热2，共138前向，16个原始输出及128逐条件raw哈希均与同模型完整实机输出精确相同。

## 为什么改用了页驻留证据

第一版父PID7956在第一个计量快照失败，因为板卡没有/proc/self/io；没有测速行、没有O8准入或前向。失败记录和载荷保留。探针确认mincore及整盘stat可用后，新v2目录与协议保持原处理条件，只修正计量方式；第二版PID8461正常完成，未覆盖v1。

mincore提供文件映射页面是否驻留的瞬时快照；DONTNEED仅是释放缓存页的建议，部分页可能保留。因此不能仅凭“cold”名称认定已读盘。本轮所有128个cold条件的前测均有未驻留页，累计20976页，读取后均全驻留；全部128个prewarmed条件前／后已驻留。整盘扇区差只作旁证，包含其他进程及换页的可能，不声称本进程精确读盘字节。[mincore原文说明](https://man7.org/linux/man-pages/man2/mincore.2.html) · [fadvise建议与部分页说明](https://man7.org/linux/man-pages/man2/posix_fadvise.2.html)

块统计使用整块mmcblk0的已完成读取扇区，标准单位512字节。128个cold条件设备计数均增加，128个热条件均0；这比只看wall-time更支持存储路径解释。major faults为0并不否定read系统调用实际触发设备读取。[Linux块统计字段](https://docs.kernel.org/block/stat.html)

## 全部八组结果

| 测量环境 | 方法 | 缓存实测状态 | 平均读取墙钟ms | 平均进程CPUms | 设备读取计数增加条件 |
| --- | --- | --- | ---: | ---: | ---: |
{table}

每个分位数、原始页数、设备计数和256条件见{link('results/independent_verification.json','完整重算')}；原始记录在{link('delivery_v2/results/record.json','实机record')}。O8前向平均约138.21ms；本基准不含跟踪、计数、真实相机或身份并发，网络环境也比392输入的原完整回放轻，不能把185ms左右的较窄“网络＋读图”外层时间写成全系统满足200ms。

独立冷读已需41.96–44.81ms，实际O8后为42.85–44.37ms；本次没有发现O8计算本身额外制造约40ms的读取等待。这不排除原完整负载的换页、排队或其他状态交互。

## 复用buffer还需要算上语义相同的复制

热读时readinto的2.26ms比bytes的3.89ms少约1.62ms，但复用缓冲是可变数据。若要像原队列一样保存不可变JPEG，`bytes(memoryview)`平均另需3.82ms；已有bytes转bytes约0.016ms。仅比较read调用会掩盖这份冻结成本：热读＋冻结约6.08ms，对照约3.90ms。

额外单列的pickle字节载荷约3.38–3.55ms，尚未包含真实IPC交付、完整任务元数据、后台等待与图像解码。因此本轮不采用“readinto天然零拷贝／必然更快”的结论，也不据微基准宣称真实Queue开销已解决。

## 采用决定与下一步

这一轮保留存储路径证据，**不改生产默认、不把先预读当作免费加速**。原5FPS反馈命令仍红，阶段是诊断完成，完整系统修复未完成。

下一步冻结一个实际输入实验：比较串行读取与有界生产者读取，使用相同模型、同一照片选择规则和顺序反转重复。生产者只能在该帧正式释放后取得JPEG；前台的释放至计数时间包含等待输入，不允许提前预读未来帧来做出更好的数字。记录实际读取起止、数据到达、缓冲上界、复制、后台排队、跳帧及入口事件变化；若计算与读取能够实际重叠，再看完整回放是否改善。

该实验仍只能先证明公开回放原型；真实相机／RFID和独立永久身份继续待补，不能承诺所有输入分辨率都达到5FPS。计数的12头人审事实不变，仍需独立逐事件参考与跨会话评价。

两版父任务已终态且消失，原O8 bit保持，锁可用、SSH／Jupyter可访问。v2结果包103243字节、12成员，SHA8791924ccede3e10d439505b1dc936a91ab6b4f089f6b824456408541aa3e09c；逐文件校验及全部raw匹配通过。没有训练、固件变化或新的身份准确率结论。{link('计划与验收.md','原计划')} · {link('计量兼容修正_v2.md','计量修正')} · {link('results/original_periodic_target_red.json','原完整目标红色结果')}。
'''
f=ROOT/'高分输入取得成本与下一步.md';assert not f.exists();f.write_text(text,encoding='utf-8')
review='''# 输入取得成本Review与当前状态

- 先运行真实周期记录的红色目标命令，完整5FPS失败未被较窄微基准替代。
- 三个假设先列，16均匀来源、两环境／两方法／两缓存条件／两次反转重复先冻结；256行与138真实前向完整记录。
- v1缺少进程io接口，0测速／0前向；故障记录保留。v2用实际mincore和整设备统计，未虚构进程级读盘量，未清全局cache或关闭swap。
- 256文件内容与原SHA一致，16全部raw与128逐行哈希对应既有同模型实机输出；8准入和2预热分开。
- 热读全部驻留且设备计数0；冷请求均有未驻留页、读取后驻留且设备计数增加。单看major fault0不等于未读盘。
- bytes／readinto的冻结为不可变副本、pickle和实际IPC范围分别处理，不假装零复制；不以热读数字替代完整输入成本。
- IMPORTANT：128个真实前向不是完整5Hz周期负载，没有跟踪／身份并发；该阶段只定位，不采用新默认策略。
- 两版父进程终态／消失，原O8及服务保持；完整周期目标继续红。整体目标继续。
- BLOCKER：独立逐事件／永久身份、真实相机RF及可靠跨来源计数仍待补。
'''
f=ROOT/'Review与当前状态.md';assert not f.exists();f.write_text(review,encoding='utf-8')
print(json.dumps({'reports_written':2,'full_periodic_fix_claimed':False,'whole_goal_complete':False}))
