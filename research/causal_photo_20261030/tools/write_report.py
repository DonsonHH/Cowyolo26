from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def link(relative,label):return '['+label+'](<'+str((ROOT/relative).resolve()).replace('\\','/')+'>)'
v=load(ROOT/'results/independent_verification.json');ref=load(ROOT/'results/reference_independent_verification.json');tim=load(ROOT/'results/timing_and_event_diagnosis.json');p=load(ROOT/'protocol/run_v1.json');photo=load(ROOT/'results/readonly_independent_verification.json')
assert v['actual_O8_timed_forwards']==2309 and v['actual_background_identity_jobs']==39
table='\n'.join('| '+r['run']+' | '+str(r['processed_frames'])+' | '+str(r['skipped_slots'])+' | '+str(r['deadline_misses'])+' | '+format(r['processed_per_second_over_offered_duration'],'.3f')+' | '+str(r['source_down_count'])+' | '+format(r['P95_release_to_count_ms'],'.1f')+' |' for r in v['cases'])
back='\n'.join('| '+r['run']+' | '+str(r['actual_jobs'])+' | '+str(r['accepted_provisional_predictions'])+' | '+format(r['max_queue_wait_ms']/1000,'.2f')+' | '+format(r['max_enqueue_to_result_ms']/1000,'.2f')+' |' for r in v['backgrounds'])
text=f'''# 因果抓拍已实机运行，当前JPEG环策略不采用

2026年10月30日。**保留当帧抓拍作为既有比较，不把本轮“每帧读取JPEG＋因果选择＋空闲身份后台”设为默认。** 两次因果运行均计10次，但吞吐4.834／4.796FPS，253／281个处理帧超过200ms，身份请求最长74.94／80.89秒完成。几何边界可以改善，完整系统代价明显，且没有永久身份真值可证明识别更准。

最新六次计数为10／10／10／10／9／9，人工总量仍12。完整不跳帧O8视频的10次、上一阶段六次全部10次和本阶段9／10次都保留，不能只引用较好的一轮。两个网络仍确实在同一PYNQ-Z2执行；本阶段没换权重、O8固件、跟踪或阈值。

## 先固定规则，再查看全部照片

每条临时轨迹只用当前及过去1秒内、最多6个已处理时刻的已确认框；不读取未来帧作选择，不用真实身份或图库分数。候选分数固定为：可见框面积×(1−与其他确认框的最大交叠占比)×min(1,最小边界余量／16px)，同分取较近帧。1秒和16px是事前工程选择，没有最优性或新颖性主张。重叠代理不等于实际遮挡，也看不到未确认／漏检邻牛。

事前计划、载荷和代码在第一次照片比较及本轮板上推理前冻结；因果性、过期、调用者修改隔离和临时ID隔离检查通过。旧完整实机轨迹的10事件、60候选只读配对，7次选到更早照片，7次边界余量增加、3次重叠代理下降；清晰度代理3升4降，其余相同。全部20个照片面板已查看，邻牛混入与过曝仍存在，不能只展示改善案例。

{link('results/readonly_photos/all_pairs_page1.png','10事件照片配对第1页')} · {link('results/readonly_photos/all_pairs_page2.png','第2页')} · {link('results/readonly_independent_verification.json','几何与像素复算')}

## 两轮顺序反转的真实周期负载

固定mosaic050_seed26、192输入、原yolo26_optimization_8、同一身体编码器和图库／拒识门限。顺序为前台独占→当帧后台→因果后台，再反转。两种后台均在每帧前SIGSTOP并waitpid确认，前台后SIGCONT，PNG0、nice10、单线程。每次392个5Hz时隙、78.4秒；按时只取最新帧，并从同模型实际raw恢复0–8910的1783次前史。两轮是设备重复，不是独立牧场会话。

| 实际顺序／策略 | 处理帧／392 | 跳过 | 迟到帧 | 吞吐FPS | 计数／人工12 | P95释放至计数ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

迟到的分母是已处理帧，跳过时隙另列；吞吐用整个78.4秒计算。实际前台2309次，8次准入和12次预热另计。2309份完整raw逐字节等于既有同模型完整实机输出，13007个含前史观察、12条计数路径均独立重算。没有为了凑齐任务或计数补入已跳过帧。

计时起点是已就绪的192 BGR回放输入；因果组新增每个实际处理时刻的高分辨率JPEG读取、缓存、选帧及入队调用，不含真实相机曝光／接收。所有高分JPEG来自既有1050×1440通道回放，RFID是全部未读模拟。当前实现把缓存与选帧一起改变，不是仅打分公式的纯因果对照。

## 较小的几何计算，较大的输入与等待成本

因果组JPEG读取平均46.40／47.85ms，P95为63.56／70.64ms；选择器平均0.242／0.226ms。网络平均约140.05／143.28ms；整个前台平均202.08／206.04ms，已越过200ms预算。分量观测指向高分JPEG读取是大头；此前已校验读过全部文件，页缓存与换页状态未隔离，不能单独宣称SD是唯一原因。

| 后台条件 | 实际任务 | 接受的候选数 | 最大排队秒 | 最大入队至完成秒 |
| --- | ---: | ---: | ---: | ---: |
{back}

因果组可用空闲窗口不足，后台接近饥饿；第二轮网络本身平均约170ms，完整请求却等待至80.89秒。因此不能只报网络推理时延。实际任务39而非预计40：二轮当帧只触发9次；不同条件不能称相同身份负载。

清理后6帧JPEG负载峰值4,418,520字节。读新帧后再过期，瞬间7帧负载重算为5,149,692字节；异步队列、pickle副本、解码RGB、图库与网络另占内存。父进程累计VmHWM235576kB不能分配成各策略增量；VmSwap从0发展至最高82688kB，提示顺序运行状态并不相同，不作内存因果归因。{link('实现边界与事后核对.md','完整口径')}及{link('补充计时口径.md','异步入队计时说明')}保留计划与实现差异。

## 全部39张实际照片与独立网络参考

四组实际任务10／10／10／9，每组接受1个候选。四次都为同一f9790照片、候选009、分数约0.854908，照片文件SHA相同；这是同一回放画面的重复，不是四头牛，更不是身份正确率。因果组各7次选到更早帧，却未新增接受候选。清晰度、候选分数与正确身份不是同一指标。

{link('results/actual_photo_panels/r1_current_frame.png','一轮当帧10图')} · {link('results/actual_photo_panels/r1_causal_ring.png','一轮因果10图')} · {link('results/actual_photo_panels/r2_causal_ring.png','二轮因果10图')} · {link('results/actual_photo_panels/r2_current_frame.png','二轮当帧9图')}

39张照片均按冻结高分源JPEG和实际当时框复算到完全相同像素，再核对输入张量、576维输出、图库各ID分数、Top-1和拒识。26个重复输入的实际ARM raw与已有／本轮重复完全相同。另在Slurm130642上，用原Torch编码器对39查询＋30图库做69次CPU前向：输入差0，查询最大归一化特征差3.293e−6、图库4.046e−6，78种查询／图库组合的候选及接受决定一致；阈值和数值门禁沿用此前固定值，未调参。作业完成0:0、4秒；短作业sacct内存采样不能作为网络峰值内存。

跳帧改变临时ID及事件时刻。仅按“事件帧＋临时ID＋方向”字面配对只有7对，25条条件记录未配对，全部保留；没有强行改编号匹配，也没有据这7对推出总体照片或身份优越性。缺永久身份真值，无法判定改变后的候选更正确。{link('results/paired_identity_observations.json','全部字面配对及未配对记录')} · {link('results/reference_independent_verification.json','服务器网络与检索复核')}

## 两次9的入口缺口诊断

二轮当帧跳过9050–9090等入口帧，对应暂定／确认轨迹5在A区最多1次有效观察；二轮前台独占只跳9515和10440，其中21在9510合法前史＋9520确认后只有2次连续入口证据。后续入口片段也最多2次，虽在9790到B区，仍不触发。

事后只读计数探针保留完整旧轨迹，不重跑检测／跟踪：不删除10；只删9515为9；只删10440仍10；删二轮独占的两帧为9；删二轮当帧的实际11时隙为9。它说明该计数证据对特定缺帧敏感，不能当作重跑完整跟踪的结果，更不能把帧号特判用作部署。原规则保持，{link('results/entry_skip_probe.json','全部探针及入口观察')}和所有不利结果保留。

## 复核、采用决定与下一步

板端父PID4205、四身份子进程及采集PID5686均终态且消失；共享锁空闲，SSH／Jupyter与原O8 bit读取正常。结果包22,544,311字节，SHA51b596b59e9e0280ce13895e2da473d874554be40ba7f9060a01761baac59c15，179文件逐项校验；服务器参考包275686字节、9文件亦校验。原协议继承了旧阶段的描述性“模型已改变”和旧归一化记录摘要；新增{link('protocol/runtime_binding_clarification_v1.json','元数据澄清')}绑定实际同一新模型已有256码核验，未覆盖冻结协议或改变运行参数。没有重训、固件升级、相机或真实RF读取。

本轮否决的是这个具体“逐帧文件读取＋压缩环＋空闲后台”的组合实现，不是证明所有因果抓拍都不可行。下一步应先把相机／回放输入的实际取得、缓冲复制、释放调度与入口缺帧做成可测的独立环节；比较由输入端维护的有界压缩缓冲或按需保存的代价，不能把输入成本搬出计时后宣称免费。身份收益需在固定同事件／同轨迹照片对照及带永久ID的新会话上证明，不按图库分数挑照片。

同时继续独立通行参考、普通俯视新会话与漏检／确认／掉帧分解。计数仍未达到人审12，永久身份、真实耳标异常及最终论文贡献未完成。{link('results/independent_verification.json','完整实机复算')} · {link('results/timing_and_event_diagnosis.json','全部时序分量')} · {link('计划与验收.md','事前计划')}
'''
file=ROOT/'因果抓拍实机结果与不采用决定.md';assert not file.exists();file.write_text(text,encoding='utf-8')
review='''# 因果抓拍Review与当前状态

- 事前冻结单候选规则、真实O8／ARM模型及六次顺序；没有按身份分数选帧或改变阈值。
- 2309实际O8输出、13007观察、12计数路径、39实际照片／张量／检索逐项核查；69次新Torch参考、78检索决定一致。
- 原只读20面板和实际39面板均查看；邻牛、过曝、未配对25条和身份真值缺失保留，接受1不称正确1。
- 两次因果4.834／4.796FPS、253／281迟到及最长74.94／80.89秒均不利；全局默认不采用。
- 10／10／10／10／9／9未隐藏。两次9的入口证据只有1或2次，单帧删除探针明确为事后计数诊断，不是全链重跑或生产特判。
- 六帧稳态／七帧瞬时、异步队列副本、累计RSS／swap和完整性预读单列；未假装摄像头输入或零开销缓存。
- 元数据继承错误以新附加记录澄清；冻结载荷未改，8准入和全部raw精确门禁保持。名为collection_complete的早期观察仍显示进程在跑，最终使用明确终态读取，不靠文件名判断完成。
- 板端父、四子及采集进程消失；服务器130642完成0:0。设备服务与O8保持。没有新训练或独立最终测试。
- IMPORTANT：两轮不同计数使实际身份负载不同，7字面配对不足以推出选择规则的总体身份收益；不强制按临时ID匹配成永久身份。
- BLOCKER：独立逐事件／永久身份、真实同通道双向／RF及最终主张仍待补。整体目标继续。
'''
file=ROOT/'Review与当前状态.md';assert not file.exists();file.write_text(review,encoding='utf-8')
print(json.dumps({'reports_written':2,'phase_adopted':False,'whole_goal_complete':False}))
