# 固定调用预算运行器：推理前审查

日期：2026-11-10。只读检查 `budget_runner.py`、`budget_schedule.py`、`test_budget_runner.py`，并对照既有 `LatestCapture`、TrackingSession 和局部测量选择器。未运行神经模型、未连接网络、未修改源码。以下行号与本次读取版本对应。

| 文件 | 审查版本 SHA-256 |
|---|---|
| budget_schedule.py | `61cd683869db9f02d88fc53e0080fec1401c5fba81eb91b29bcba8dd32baedd8` |
| budget_runner.py | `6fa751a4a82fc27cd0a3177eab184c32928be35865880b411004fe55fc602d41` |
| test_budget_runner.py | `3a942580fe1eee44eb87c692734c91aa7b7ddc95d663c4fabe475f486c8f6677` |

## 结论

调度主路径符合拟定实验：每完整 4 源帧 block 两次真实调用，统一 5 Hz 名义跟踪时钟；局部调用只用本 block 的 primary 图；融合后该图只更新一次；指定帧不可用就失败，没有用未来图补位。未发现成功路径多花调用或把同图算成两次观察的缺陷。

**冻结前应修复下列失败证据问题，并完成 runner 的云端/ARM 软件回归。** 现有三项 fixture 主要覆盖无检测的成功路径和一个缺帧异常，没有验证初始化失败、推理异常及日志/清理故障的终态完整性。

## 必须处理：初始化资源不在 try/finally 内

位置：[budget_runner.py:78](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:78)创建 capture，85–89 行创建 tracker/策略并打开五个输出流；92 行对 source 做 SHA。保护区直到 [第 158 行](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:158)才开始。

实际失败路径：source 在 capture 打开后变为不可读、SHA 读取抛错，或 TrackingSession/策略构造失败、某个输出文件打开失败，都会直接离开 `run`，不调用 capture.close，不关闭此前已开的流，也没有 FAILED summary。构造器检查可能在模型执行前拒绝配置，这类失败同样需要可审计终态。

修复：资源统一初始化为 None/空容器，建立最小 scope/summary 后将 acquisition、配置对象、文件打开、源哈希和模型初始化都置于同一保护区；部分打开也按已获得资源清理。不要因为尚未产生推理就把失败从批次中漏掉。

## 必须处理：finally 内再次出错会丢终态

位置：[budget_runner.py:213](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:213)逐个文件 close 没有捕获异常；215 行 capture.snapshot、memory_snapshot 和222行 summary 写出也不受保护。

后果：一次 close/flush 或 snapshot 故障会使最后的 FAILED/CLEANUP_FAILED summary 根本不生成，还可能遮盖最初的缺帧/推理异常。遇到磁盘满、输出介质错误或 capture 清理异常，这正是最需要留下失败证据的场合。

修复：逐资源捕获清理错误，保留原异常类型/traceback，统计快照失败写独立错误字段而不是阻断终态；尽最大可能写最小 terminal receipt。成功工作量但清理失败时必须保持失败状态/非零 CLI 返回；原始运行失败不能被只剩一个清理异常替换。输出介质完全不可写时，由外部 supervisor 的独立终态记录兜底。

## IMPORTANT：推理尝试与返回成功需要分开记账

位置：[budget_runner.py:125](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:125)先调用 detector，返回后才增加 `model_forwards`、写 ledger、保存 raw 和 receipt。warm-up 第165–166行同样只在返回后计数。

这对**完全成功且已复算的运行**可以建立精确调用数；但若 backend 已进入执行后抛错，失败 summary 会少记该次尝试。还无法从现有 receipt 区分“未进入模型”“模型已返回但 raw 保存失败”和“执行状态未知”。不能把失败轮次记成零次额外工作。

修复：调用前先写带 slot、kind、input SHA 和开始时刻的 attempt；模型返回后记录 return 时刻、output dtype/shape/SHA，再绑定 raw 保存状态。失败时明确 `execution_status=unknown/failed`，不要猜测完成了多少硬件 forward。warm-up 同样单列。input SHA 宜在调用前计算，避免依赖 backend 不修改输入的隐含条件。

成功终态必须复算 `warmup + ledger returned calls == model_forwards`，`global + endpoint + birth == planned calls`，并逐条读取 `.npyseq` 比较 shape/dtype/bytes SHA，确保 raw 序列无缺项/多项/残尾。调用返回与证据落盘之间失败的运行不得进入成功主表。

## IMPORTANT：补足可核验的时间戳和有效配置

当前 `calls.jsonl` 只有调用后的墙钟时刻；局部 receipt 的 `source_time_s` 是 primary 的 PTS，而 release 是后面的 secondary 源帧。因此建议每次 attempt/return 同时保存：observation frame/PTS/due、release frame/PTS/due、preprocess start/end、inference start/end。这样才能独立检查 inference start 不早于该 slot 的 release，并把“图像年龄”与“slot 等待/推理耗时”分开。

代码会强制覆盖 capture buffer=2、history age=None，强制 resize-first native BGR、一次 warm-up 和 tracker nominal=5 Hz，但 summary 的 `config` 保留原输入配置（第77、84、124、165行）。这不是当前预设已产生的错误，但冻结记录应包含 `effective_capture_config`、实际预处理/输入表示、实际 warm-up、plan 参数；不支持的配置应在初始化前拒绝。也应检查 `end_frame0_exclusive == expected_capture_frames`，避免统计窗口标签与实际全片执行不一致。

真实执行的外围冻结还须包含这三个新文件、全部导入源码、wrapper/native library、program/plan 与 firmware bit/HWH/manifest；该 runner 自身只记录 graph/plan 和 device initialization，不能单凭它们声称完整执行链已绑定。

## 已核对的调度性质

- [budget_schedule.py:26](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_schedule.py:26)只安排存在的 first 和 first+2；完整 block=2 调用。尾部仅1/2帧时只有 primary，一旦 first+2 存在才有第二次；无额外 EOF 模型调用。须在协议中明确尾部这一规则，而不是笼统声称任意长度最后一块也两次。
- [budget_runner.py:85](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:85)两策略都给 TrackingSession 5 Hz，真实 PTS 控制 dt。不是通过修改 sample_hz 给某条件不同的 tracker 时钟。
- [budget_runner.py:175](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:175)用 primary 检测与既往状态决定是否 local，不读取 secondary 图内容；随后消费指定 secondary 作为 release 证据。第181行“image became available 之前”注释过强：慢调用时 secondary 可能已经到达，但未被读取/用于资格判断；宜改成“before inspecting the secondary image”。
- global/fallback 分支先 observe primary 再 observe secondary；local 分支暂缓 primary 的唯一 update，融合后才 observe。local 的图像年龄包含等待 secondary slot 的时间，这应保留在时延结果中。
- [budget_runner.py:108](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:108)丢弃非计划帧，遇到编号大于计划帧立即失败；到达检查拒绝未来 release。`LatestCapture` 已验证 CFR PTS，因此当前真实 capture 路径中源编号与 PTS 对齐。没有替换为“最近的未来帧”。
- [budget_schedule.py:56](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_schedule.py:56)约束 slot 次序、global/local 的 observation frame 和64位十六进制 SHA。它验证的是成功返回调用的逻辑账本，不能替代前述 attempt/异常审计。
- 所有源帧尾部会读到 EOF；capture 总帧数与声明不符时失败。采集丢弃/覆盖与 schedule discard 应分别报告。此处 `prefer_history=True` 是为了取得精确指定帧，不可据此宣称历史选择模块得到验证。

## 冻结前最低软件验证

保留现有三项测试，增加初始化/源哈希失败、模型初始化失败、warm-up 异常、slot推理异常、raw保存失败、单个close失败、snapshot失败，以及未来到达包拒绝。增加真实提案与融合的 scripted 检测 fixture，覆盖 birth/endpoint 各一个，不只 patch 掉 merge；验证一次 source frame 只更新一次且有正常非空事件输出。

至少覆盖输入长度1–8的尾部、成功 raw序列复算、缺计划frame后的 FAILED summary/调用attempt数/资源close，以及两个策略有效配置相同。原3项 fixture 的空输出不能证明局部融合或计数事件路径已经执行。

本地三文件 AST 语法检查通过。尝试导入 runner fixture 时本机 Python 缺少 `lap`，在进入 `run` 前即失败；没有宣称本地 runner测试通过。父任务已具备云端/ARM 环境，应在修订后跑这些测试并冻结新源码。本文不启动板端推理。

## 修复后补充复核：冻结 V2 与首组开发实机结果

本节追加于旧审查之后，前文哈希和发现描述保留为历史基线。只读检查当前修订，没有重跑模型、访问板卡或修改源码。

当前 `budget_runner.py` SHA-256 为 `00510a4a80362df50d8ccc88f7abb61dc86229fc0266285299fd7a6ef2ddce0e`；`test_budget_runner.py` 为 `3aaf5f918a63e5a4701ec6c3a41282322bd92e95b1c5cec0a7060dee6581472a`。`budget_schedule.py` 未变。归档 SHA-256 为 `2a4f3cb3ee73888e32e5aa7c3ed71559975e4a567cac8777bcfa1d70a7101726`。

### 已关闭的主要发现

- 外层 [run:247](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:247)现统一保护 `_execute` 中的 setup、源哈希和初始化；capture、逐个打开的文件和成功构造的 detector 进入资源登记表，异常仍关闭已取得资源。源哈希失败测试验证 capture 关闭且 FAILED summary 存在。
- 单个资源 close、计时器 summary、capture.snapshot 的异常不再阻断其他资源清理，并保留 primary error/traceback；成功工作但清理失败会返回 CLEANUP_FAILED。summary 采用临时文件替换，目录仍拒绝覆盖。新增 capture-close 故障测试覆盖了这一主要行为。
- 计划调用有 STARTED、RETURNED 或 FAILED_OR_UNKNOWN_WORK，warm-up 单独标识；推理异常测试明确保存未知工作而不伪造额外成功调用。指定源帧的 CFR PTS 也新增一致性检查。
- 记录了 release source frame/time、attempt 开始与返回时刻，可以检查源 slot 因果顺序；同图一次 update、统一跟踪时钟和尾部调用规则没有因本轮修复而改变。

独立重验 `BUDGET_SOFTWARE_FREEZE_V2.json` 的 58 个源码项：本地文件与归档成员的 SHA 全部一致，归档整体 SHA 也一致。归档另有 supervisor，因此“59 个归档文件”和“58 个冻结源码项”不矛盾。`CLOUD_BUDGET_SOFTWARE_V2_POLL.txt` 记载 Slurm133418 COMPLETED/0:0、173 tests OK；`BOARD_BUDGET_SOFTWARE_V2_POLL.txt` 也记载 173 tests OK。本节根据其保存的实际输出核对，没有把本机缺 lap 的导入失败改写为本机通过。

### 尚余 P2：内存快照异常仍可遮盖原错误并跳过终态

当前 [budget_runner.py:282](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:282)仍在最终 summary 写入保护区之前直接调用 `memory_snapshot()`。该函数会读取 `/proc/meminfo`，并非保证永不抛错。其异常会跳过第286–293行的 terminal 写入。

用当前外层 `run` 的 AST 原函数做纯内存故障注入：`_execute` 抛 `RuntimeError('PRIMARY_FIXTURE_FAILURE')`，memory_snapshot 抛 `OSError('MEMORY_SNAPSHOT_FIXTURE_FAILURE')`。最终对外异常变成后者，terminal write 尝试数为0；前者只剩 exception context。本复现不导入 detector、不创建真实输出文件。

建议把 memory_snapshot 也包成可失败的非必要诊断，错误写进 cleanup/diagnostic 字段；保证它不阻止最小 terminal 写入。新增该故障测试。这个残留不改变本次两个成功实机结果，也不要求删除已经完成的冻结 V2 开发记录。

### 尚余 P2：`inference_elapsed_ms` 不是纯 detector 时间

当前第132行 `call_start` 在第138行 STARTED receipt 的 write/flush 之前；第149行 `call_end` 在 detector 返回并增加计数之后。所以第151行的 `inference_elapsed_ms` 含日志写入开销，写盘慢时会把它算成神经推理耗时。用于完整 attempt-to-return 计时是有效的，用于“detector-only inference latency”则不准确。

可以保留现有 attempt 时间戳，再紧贴 `detector.infer_bgr` 两侧增加独立 detector start/end，或把现字段明确改名/说明为 attempt-to-return。当前事件发布年龄始终从准备源图的到达时刻计算，受此字段命名问题影响的是子阶段计时解释，不是已报438.9/849.2ms发布年龄。

### 次要异常记账与未关闭建议

warm-up 第200行先写 RETURNED，201行才增加返回成功计数；若日志在该次写入抛错，模型实际已返回，summary 仍记 warmup=0。正式 slot 路径已在日志写入前增加成功计数；warm-up 也宜采用相同次序，并将“已返回”和“证据保存成功”分开。成功运行不触发该差异。

输入 SHA 仍在 inference 返回后计算，且没有独立的 preprocessing 起止时间。当前固定 O8 输入路径没有显示输入被原地改写的证据，因此不把它们认定为本次结果错误；若要作更强的输入字节/子阶段耗时审计，沿用前文建议。有效 capture history guard=None 已在本轮协议明确声明；实际配置、窗口和模式均与本次预设一致，但通用 runner 的不支持模式/窗口校验建议尚未完全落实。

新加的三项测试解决了主要异常路径，未新增非空 birth/endpoint 融合的 runner 专属 fixture。当前真实开发轮已实际走到13个局部调用，但它不是对所有融合边界情况的替代测试。下一次源码修订时仍可补这一测试，不为增加测试数重跑已结束的实机开发轮。

### 首组开发实机结果的计算复核

根据 `DEV_PAIR_PROTOCOL_V1.json`、launch记录、终态serial与两份summary serial：

| 策略 | 非热身全局 | endpoint / birth局部 | 非热身总调用 | 热身 | 已知方向总数 | 对既有人工12的绝对误差 | 最大事件发布年龄 |
|---|---:|---:|---:|---:|---:|---:|---:|
| global_pair | 300 | 0 / 0 | 300 | 1 | 9 | 3 | 438.941 ms |
| conditional_local_pair | 287 | 8 / 5 | 300 | 1 | 12 | 0 | 849.213 ms |

599帧的 first=0,4,…,596 共150个，second=2,6,…,598也150个，精确预算为300；两案 model_forwards=301与其一致。条件策略13个局部调用替换13个全局调用，故287+8+5=300。两个 future_frame_violations 均0，stream wall约120.109/120.205s，drain约0.509/0.605s。以上计算自洽，未发现把 warm-up 忽略后冒充等预算或多算局部调用的情况。protocol SHA 与 launch记录一致；协议、launch、软件冻结的归档 SHA 相同。

这是一段已经暴露的 Aug20 开发视频、固定 global→conditional 顺序、每条件一次。可以写“同300次非热身图调用的开发对照中，总数误差由3变0”；不能写成独立测试、3个具体漏计被修复、已证明跨视频优势或统计显著。计算预算应准确称为**相同神经图调用数**；CPU裁剪开销、源帧选择和观察分配本来就是策略差异，不应顺带宣称能耗/全部计算时间严格相等。

当前收到的是保存的终态及summary serial，尚未收到两案完整 attempts/calls/frames/events/raw_outputs.npyseq 的本地副本。因此这里验证的是协议绑定、摘要算术和源码约束，尚未声称完成600个raw输出的独立逐条哈希/事件重算。归档取回后应补这一只读检查；不需要为此再运行模型。采集最大迟到等完整合同字段不在这次精简summary中，不能单凭两项发布年龄就把其余所有门限升级为已逐项复核。

独立硬件探针serial记载一次常量输入的真实O8图返回、`[1,300,6]`且全部有限、core version=`0x80001`、error=`0x0`，并给出正的native计时/传输计数。现存 `graph_executor.cpp:236` 对应DMA提交、等待、计数校验及timer累积。这支持实际PL/DMA路径存在，不能替代功率/资源测量，也不把这一次探针计入300次计数实验预算。两案301次加该探针1次为603次实际图前向，软件回归的“0 model forwards”仍只描述回归阶段。

修复后本审查未发现会否定这组成功等神经调用预算开发结果的计算错误。P2项和未取回raw账本保持显式待办，旧版本的严重发现不继续描述为已完成实机轮的活动缺陷。

## Raw 账本取回后的独立复核（V2 实验保持不变）

本节关闭上一节“尚未收到完整 raw”的证据限制。只读取 `dev_pair_v1_collected`、`DEV_PAIR_VERIFIED_V1.json`、`DEV_PAIR_COLLECTION_V1.json`、`verify_dev_pair.py` 及原 V2 源码归档；没有运行模型、修改实验数据或用当前 V3 源码重新解释 V2 输出。

### 独立核验结果

- 原证据包为2,356,991字节，SHA-256=`d29cb6fd1c93f4bb7866472919641a09a01adeb2b46308d0d5a5029c4c668fe5`，与collection记录一致。全部25个manifest文件重新核对大小和SHA通过；也直接比较每个原归档成员与现有解包文件的字节哈希，排除了仅信任本地manifest的循环验证。protocol、driver分别与launch记录绑定，两个terminal的summary SHA、exit code与实际summary一致。
- 两案分别完整读取300个 `.npyseq` 数组，共600个，均为有限的float32 `[1,300,6]`；每项shape/dtype/输出字节SHA与call receipt一致，文件末尾没有多余数组或残尾。
- 每案非热身attempt恰好300个，各有唯一对应的STARTED→RETURNED，无FAILED_OR_UNKNOWN_WORK；另有一次warm-up的STARTED→RETURNED。逐项核对attempt编号、block/slot、release frame、source PTS与call回执，不只统计状态行数。
- 600个预算slot都按计划顺序执行。每个call开始均不早于其release frame的到达时间，最小余量分别为98.155ms、92.543ms；调用之间没有重叠。global使用release图，local只使用同block的primary图，local未导致同图第二次tracker/counter更新。所有calls、attempts、frames、events和uncertain记录的video/session/run作用域一致。
- 使用**原V2归档中的Transform和decode函数**重新解码所有全局raw；13次局部raw也分别按其实际局部Transform解码并核对候选过滤。逐帧重构seed替换或弱框删除/局部追加，结果与存档的base_detections、candidates、accepted_detection及最终detections逐项一致。13次局部中5次birth、8次endpoint，9次接受了候选。接受数量不等于人工确认正确数量。
- 当前确认轨迹输出的框和置信度均能对应到该图实际送入关联器的测量；没有发现凭外推位置生成的计数框。各帧源编号单调且唯一，global为300次更新，conditional为287次更新。
- 从原events独立累计IN/OUT/NET，逐帧核对counts及最终summary，结果仍为global **9/0/9**、conditional **12/0/12**。事件ID均唯一，起点/完成帧均在实际选择的源图集合，源时序和方向一致。uncertain分别9和4条，数量及作用域也一致，未把它们计入完整通行。
- 两案共同观察的287张全局图，**全部输入SHA相同、全部raw输出SHA也相同**。这额外排除了“同一全局图的O8输出不一致”作为本次总数差异的解释。该检查仍不把局部测量或关联结果认证为动物身份真值。

以上独立结果与 `DEV_PAIR_VERIFIED_V1.json` 的600个raw、300/300预算、287+13分配、9/12与12/12一致。历史总数参考文件的源SHA也与本次Aug20输入一致；参考角色继续是既有用户确认的开发总数，未产生新标注。

### 时序解释与原回放合同

已检查event字段的 `wall_decision_s − time_s` 与decision_age一致，call开始/结束顺序与对应slot一致。V2每个事件的post-flush publication样本没有逐项另存，但可以用事件的pre-write decision age和同源帧的后续frame日志时刻夹住其publication年龄：

| 策略 | 最大decision age下界 | 运行时记录的最大发布年龄 | 对应event帧的后续日志年龄上界 |
|---|---:|---:|---:|
| global_pair | 438.409 ms | 438.941 ms | 438.997 ms |
| conditional_local_pair | 848.639 ms | 849.213 ms | 849.278 ms |

均符合V2冻结代码的计时次序，mean也落在逐事件上下界之间。没有把不能从逐项日志精确再生的post-flush样本说成已经逐项精确重算。observation_age汇总包含frame账本flush，而帧行内的observation_age_ms在该flush之前；progress.json写入发生在这项meter之后。现有验证JSON已正确声明这一边界。`inference_elapsed_ms`仍是含STARTED receipt IO的attempt-to-return，不能用于纯kernel延迟。

取回的完整summary还补齐capture最大迟到193.826/136.097ms；两案observation p95为430.067/467.240ms、maximum为580.013/850.616ms，drain约0.509/0.605s。按原事件≤1000ms、observation p95≤1000ms、max≤1500ms、capture迟到≤500ms、drain≤1s、queue≤2、无未来帧规则，两案均通过。采集全部599帧、无capture错误；summary里的capture分布仍是冻结运行时meter的测量记录，不声称从未存下的599个逐帧capture时间戳重新计算了完整分布。

### 复核脚本本身的P2与审查边界

`verify_dev_pair.py:15–28` 在解包目录已经存在时，只检查“本地文件对本地manifest”，没有再把本地manifest/成员绑定回已验SHA的原归档。理论上，同步改写一个解包文件及本地manifest可以绕过这部分检查。**当前证据没有这个问题**：本审查直接逐成员比较了原归档，全部一致。建议后续自动复核每次都验证这条绑定，不依赖缓存目录的自我描述。

该脚本只计STARTED/RETURNED总行数，未保证每个编号一一对应，未检查uncertain作用域，也未重新解码raw或核对相同输入的跨策略输出。本审查均已额外检查，实际数据通过；这是复核入口可补强的地方，不是本次成功证据被推翻。

21个事件的起点都来自“之后得到确认的同一tracker ID在此前一图的tentative实际观测”；起点图中尚未列出该ID的confirmed输出。这与counter的确认后接纳preceding tentative逻辑相符，不是凭空补帧。当前frames日志未显式存储tentative轨迹及关联矩阵，因此这里不能从confirmed列表独立认证每个起点的身份归属，也没有运行完整Lap关联器再演算。raw、测量和源帧存在性已经核对；独立物理身份/逐事件真值仍不在本次总数审查的结论内。

最终意见：未发现影响这两案成功实机证据的实质不一致。可报告“同一段开发视频、同300次非热身神经图调用，计数绝对误差为3与0，均满足原板端回放时限”；仍不能升级为独立测试、逐事件零漏计、显著性或跨会话优势。原V2源码和结果保留，后续P2修复使用新的V3冻结，不回写本次实验。

## V3 对 V2 的定点修复复核

本节仅检查本地归档差异、冻结清单、测试记录和已冻结协议；未连接板卡，未使用USB、串口或JTAG，没有启动或重跑任何模型。

V3归档SHA-256独立重算为 `cc7b6abf6bad4dca83a9ee725855b7d56e5737b2f347f670cb521325fb1a1878`，与清单及批次协议一致。`budget_runner.py` 的冻结SHA为 `f574bd540aa337dae6bfaf71759c65563c6c943c1032acce9fad0b742c810a53`，`test_budget_runner.py` 为 `9f62a6eabbe6402795bbabb2adc92f2888ebf1609bfda99bed9f8a69d25d8491`。58个清单源码项对本地文件和归档成员全部通过；无新增/删除归档成员，相比V2只有这两个文件内容发生变化。

| 既有运行器发现 | V3差异核对 | 结论 |
|---|---|---|
| memory_snapshot异常遮盖原始错误并跳过terminal | 外层finally单独捕获诊断异常，保留primary error；新增“原始失败+内存诊断失败”及“成功工作+诊断失败”两项测试 | 关闭；前者仍FAILED并保存原错误，后者明确CLEANUP_FAILED |
| warm-up已返回但RETURNED日志写失败时少记成功工作 | 返回成功计数移到RETURNED写入前；新增receipt写失败测试，要求model_forwards与warmup均为1且运行失败 | 关闭 |
| inference_elapsed_ms包含STARTED回执IO | 紧贴infer_bgr两侧取时；旧边界另存attempt_to_return_ms，并在summary声明 | 关闭；新字段是detector API调用时长，不自动等同纯FPGA kernel时长 |
| observation总计时漏掉progress保存 | observation_timing.add移到save之后；summary说明frame行内年龄仍为pre-ledger-write，terminal cleanup排除 | 关闭；两种年龄字段的边界现在明确区分 |

第四项新增故障测试覆盖raw保存失败：成功返回的真实调用及RETURNED attempt仍保留，模型成功工作量不会因后续raw存储故障被抹去；状态保持FAILED。四项新测试与先前失败路径测试结合，针对本轮P2提供了实际行为验证。

`SLURM_SOFTWARE_V3_STATUS.txt`显示Slurm133419 COMPLETED/0:0、177 tests in 11.164s、OK；`ARM_SOFTWARE_V3_STATUS.json`为COMPLETED/0且software_fixtures_only，板上保存的测试日志显示177 tests in 42.556s、OK。这是既有保存记录的只读复核，没有把软件fixture称为新的动物精度或硬件前向验证。

源码差异未改变预算plan、源slot选择、local资格/融合、tracker/counter、模型权重或输入几何。旧V2实机结果继续按V2冻结版本和原计时边界报告；不能把V3的“observation含progress保存”追认成V2已经测过，也不需要为了修订这些诊断/计时项重跑原V2成功证据。

`EQUAL_BUDGET_BATCH_V3_PROTOCOL.json`绑定同一V3源码清单与归档；本地核对16个唯一case，为4段既有开发片×2策略×2重复，每片两次重复的A/B先后顺序相反，均无结果导向的预设删案。协议明确independent_final_test=false、重复不增加独立动物样本、主指标为逐视频已复核方向总数的绝对误差，失败全保留。该检查仅确认冻结协议结构，未查询板端进度或预先把16轮记作成功。

本轮所列运行器P2已关闭，未发现V3相对V2引入新的实质问题。前文另列的V2取证脚本缓存目录绑定建议不属于这两个源码文件的修改范围；V2实际数据已由本审查直接绑定原归档通过，不影响此结论。无需拓展机制或追加新的测试矩阵。

## V3 缺帧失败与 V4 队列准入修复复核

本节只读本地V3失败记录、V4/R2源码归档和软件日志；未连接板卡或使用USB、串口、JTAG，未执行模型。V3失败与最初V4软件失败均继续保留。

### V3实际停止状态

`equal_budget_v3_collected/aug15_r1_B/output/summary.json`与terminal的SHA一致，状态为FAILED，错误为 `Planned frame 588 unavailable; observed 590`。只返回294/325次非热身图调用，另有1次热身；最后完成观察为586，捕获累计592帧（0–591），部分IN=11。批次记录只完成此前两个Aug14案，然后在第三案停止；不能把16案写成完成，也不能把这11用于整片计数误差或视为全片11/12。

已保存的末段调用中有504.173ms、442.794ms等detector API耗时，源时钟持续前进，消费出现积压。最后586图调用返回时约为stream 118.305s，随后取588却读到590。记录支持“生产仍推进、预定帧已被队列淘汰”的诊断，不需要把失败归为模型精度错误。

### V4修复的作用与界限

`PairBudgetPlan`的所有release恰好为0、2、4……。V4在 [budget_runner.py:78](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/budget_runner.py:78)给两策略共同设置publication_stride_frames=2、buffer_frames=2、history age=None；[realtime.py:158](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/realtime.py:158)只把偶数源帧放进pending。每个源帧仍按原5Hz节奏读取、解码、验证PTS并推进frames/last_pts，奇数帧记入not_admitted，不进入占用计划帧位置的队列。

对同一到达前缀588、589、590、591作纯队列演算：

| 两包队列准入 | 到591后保留 |
|---|---|
| V3全部源帧 | `[590,591]`，588已丢失 |
| V4只准入计划偶数帧 | `[588,590]`，588仍可取得 |

因此，此改动**能消除这次已观察到的“未计划奇数帧把588挤掉”的机制**。它没有扩大队列包数、降低源解码帧率、替换未来图，也没有改变图调用plan、模型、阈值、几何、tracker/counter或局部融合算法；两策略采用同一准入规则。

这个结论不是对整段新运行成功的保证。继续到达592后，即使V4队列也变成 `[590,592]`，588仍会丢失。准入过滤增加了同样两包队列对计划图的保留时间，不增加持续处理吞吐能力；长期慢于预算速率或更长突发积压仍会失败。原有 `next_frame` 编号检查和失败终态应继续生效，不能取较新图冒充588，也不能把V3失败事后改成通过。

新snapshot的captured_frames仍代表全部源帧，published_frames代表准入偶数帧，not_admitted_frames代表未准入奇数帧；两者之和应等于captured_frames。overwritten_before_read现在针对已准入队列中的淘汰，不能再把未准入奇数帧计作“丢失的计划观察”。capture lateness meter仍处理全部源帧，不是仅有偶数帧的统计。summary新增queue_admission说明与实际代码一致。

### 软件证据与冻结版本

真实MJPEG文件的软件夹具用10帧输入、无消费者验证：stride1最终pending=`[8,9]`，stride2为`[6,8]`；仍捕获10帧、末源PTS=.45s、未准入5帧、两包队列不变。夹具使用20Hz缩短软件等待，生产budget runner仍校验5Hz输入；这不是一次20Hz动物推理或板端成功证明。另一个新增测试在设备打开前拒绝非法stride和live stride2。

最初V4归档SHA为 `ce436a93c833a4f678fae09f0bbd322c599109aec9a56997452ceb8c5ccca8d6`。其179项软件测试失败1项，日志明确为旧 `LatestCapture.__new__` 测试夹具没有publication_stride_frames，未走生产构造器初始化路径；不是新队列算法在正常构造路径中的失败。该失败日志不删除。

V4_R2归档SHA独立重算为 `8d867877f8f56e048c3aabd0f5880034e118b71e13da389234396caab9e49de9`，58个源码项与归档及本地文件全部匹配。V4初版→R2唯一内容变化是test_review_regressions.py为该旧夹具初始化三个新属性，生产源码没有再次变化。V3→V4_R2仅realtime.py、budget_runner.py及上述两个测试文件改变；plan、模型与计数算法未动。

随后本地保存的Slurm133421状态为COMPLETED/0:0、179 tests in 11.997s、OK；ARM的V4_R2状态也为COMPLETED/0，日志为179 tests in 43.211s、OK，均明确software_fixtures_only且new_model_forwards=0。这关闭了本次软件回归失败，不代表V4动物实机实验已经完成。

审查意见：V4/R2对已观察eviction机制的修复合理，未发现新的实质代码问题。任何后续V4成功结果属于新的队列准入版本，不能覆盖或升级V3的第三案失败；当前部分11保留为失败运行的诊断记录，整片不评分。本节不新增实验或协议矩阵建议。

## V4 全部16案原始证据最终复核

已独立重验原包SHA及196个文件、4120个raw；attempt配对、调用顺序/作用域与累计计数一致。计划16案全完成，无遗漏失败。逐案实际预算相等，各另有1次热身；24组比较中6015对共享全局帧的输入/raw哈希全部一致。

两重复均得A=`11,12,9,9`、MAE=1.50，B=`12,11,11,12`、MAE=0.25。B在Aug15确实较A差，未删去。16案均通过原回放门限；最大发布986.286ms，最大观察1141.255ms，最高逐案观察p95为927.872ms，不能写全部观察低于1秒。

未发现影响成功证据的实质问题；支持同神经调用预算下的这4段开发片比较，不升级为独立测试、事件F1或普遍优势。V3失败继续单列保留。本次仅本地只读核验，无模型运行或板卡/USB操作。

## V5 scheduled_global 单一覆盖修改审查

仅审查本地源码、冻结包、配置和保存的软件日志；未查询板卡或USB，未运行模型/云任务，也未扩展测试矩阵。V5归档SHA独立重算为 `07a1b3b5028101c98b5e6ecee399df19f73b9e3110bfe096a182b914c46cec60`；59个源码项与归档、本地及协议全部一致，protocol SHA与launch一致。Slurm133423记录183项通过（12.002s），ARM记录183项通过（45.393s）；均为software_fixtures_only。

实现符合本轮目标：

- `source_selection`默认仍为latest；该分支继续使用原target_hz与原取帧逻辑。scheduled_global显式要求paced-file、stride2、无历史年龄覆盖和无自适应history，取帧时强制oldest。
- 每次消费的source frame必须精确为0、2、4……；缺帧立即失败。EOF再要求base_model_forwards=`ceil(captured_frames/2)`，且输入帧总数必须符合声明，不能静默跳过计划图。
- 5Hz源仍逐帧读取/解码；tracker名义时钟保持5Hz，SourceSampler单独为2.5Hz。新summary分别记录global target、tracker clock和source_selection，不能将config.sample_hz=5解释为实际5次全局推理/秒。
- 原全局调用后再执行同一图的局部核验，随后只更新一次tracker/counter。局部调用增加model_forwards，不替换后续全局观察；因此总工作量为global+birth+endpoint+warm-up，不是V4的固定神经调用预算。

对实际greedy资格检查协议逐字段比较，五段配置均只变化source_selection、publication_stride_frames由1变2、history age由.3变None；模型、阈值、几何与计数规则未变。四项新增行为测试覆盖顺序全局、局部额外调用、计划图丢失拒绝和不兼容配置预先拒绝。归档中budget_runner仅修改注释，V4原16案的实现与结论不受影响。

协议已明确no_fixed_call_quota=true、variable total neural calls、非等预算优势，9案为4段已暴露开发片各两次加原固定负例一次。严格全局覆盖仍受两包队列和实际算力约束；额外局部工作造成足够积压时仍会缺帧失败，代码没有承诺必然通过或无限积压。

两项解释边界需保持：

1. V5的 `history_selection_requested` 因scheduled而为true，表示强制oldest计划队列；fast/birth adaptive history均关闭。不得把这个日志值解释成阶段自适应历史策略获得了验证。通用clock_contract文案仍沿用latest/history描述，应结合新source_selection与冻结配置解释。
2. V5的 `predecessor_protocol_sha256=beb7…` 实际绑定EQUAL_BUDGET_BATCH_V4_PROTOCOL；直接复制配置的greedy资格协议SHA是 `3467372b11c998439f77d413b6f814c179ff6fa56b21bbae56a51c5624bff403`。这是继承的谱系字段，非执行配置失配；可在说明中明确两条前序记录，不改写已冻结协议或因此重跑实验。

本地保存的greedy资格记录仍是四片11/12/11/12、固定负例预测0；Aug14失配不能用历史八次成功覆盖。V5本次审查未发现新的实质实现问题，但软件通过与预定启动不等于9案资格通过；本节未审其终态，不预先宣称覆盖修复已经改善真实总数或时限。最终报告应保留greedy反例、V4等预算结果以及V5独立版本的全部实际结局。

## V7 birth 几何/分数融合语义复核

只审本地代码、CPU shadow记录、冻结配置及已有软件日志；未连接板卡、USB或启动实验。V7归档SHA独立重算为 `ee44e637d6fb1161a11c3ca2452c184a57e7809cc58a1a2c1d624b5d0c8236e1`，60个源码项对归档/本地/协议全部一致，protocol与launch绑定通过。Slurm133427与ARM保存日志分别为189 tests in12.539s和45.787s、OK；这些是软件行为证据。

### 实现及默认兼容

`BirthRefinement.fuse`复制已接受的局部检测；开关为true时只将前四个坐标换成同图实际global seed的坐标，保留所选局部confidence/class。没有使用tracker预测位置、补插未来图或修改原始seed/selected数组。preserve_global_geometry默认为False且严格要求布尔值；在冻结float32检测输出路径，关闭时保留原局部几何的数值行为。

budget_runner和realtime都调用同一fuse方法，只替换birth seed的一行测量；两者仍在全部global/local融合后对该源图更新一次tracker/counter。Endpoint的选择、几何及全局弱框整合逻辑未变。realtime只在无endpoint提案时做birth，此时seed_index仍对应原base_detections；预算路径也直接使用当前base中的seed，未发现索引错位。

birth日志分别保留原 `accepted_detection`、实际用于关联的 `fused_detection` 和 `fusion_mode`，足以区分原始局部输出与混合测量。后续复算应使用fused_detection重建输入，不能仍把accepted_detection的局部坐标当作实际关联坐标。该分数是局部证据赋给全局几何的融合支持值，不能描述为原global detector输出的高置信度或已经校准的概率；全局框几何更准确也不是由此自动得到证明。

### CPU控制与因果解释

独立核对shadow八案的summary/frames/events输入SHA，均绑定原V4 B账本；26处替换的global seed、selected local和fused值逐项一致，确实只换birth坐标而保留真实局部分数/class。两重复的CPU影子总数均为12、12、11、12。

shadow程序在改后测量上重新执行TrackingSession，但沿用已记录的源帧、提案、局部输出和endpoint测量；没有把新跟踪状态反馈到提案选择。它支持“在这些固定输出流中，birth坐标替换会改变关联和总数”的探索性诊断，不能证明重新运行完整策略必得相同结果，更不是新的硬件精度或时延证据。V7真实闭环可能改变后续提案及global/local分配，必须按其自己的实际终态报告。

### 冻结协议与历史边界

V7实际执行路径回到V4的conditional_local_pair：两包、Q=ceil(F/2)，local占第二个调用slot；它不是V5/V6的“保全global后额外调用”。四段正例配置相对V4只新增preserve_global_geometry=true，原预算、模型、阈值、几何保持一致。前驱V6、受控比较V4和shadow结果三个SHA引用均独立核对正确；九案明确为shadow选择后的开发检验，未把参考总数放入runtime配置。

V6仍为失败批次：只完成前两片，第三案54global+8local后丢计划108，部分4不作整片评分。还应区分时限：V6自身门限是事件/最大观察2s、p95 1.5s、队列4；首案1486.642ms的clock_pass仅对应该V6门限，不代表原1s合同通过。V7协议已恢复事件1s、最大观察1.5s、p95 1s和队列2，不能用V6前两片总数正确消除其时序限制。

本轮语义和同图更新审查未发现实质实现问题。已有四项新增测试覆盖输入不变性、默认/非法配置、预算路径日志、realtime共享融合与一次更新。未见V7九案终态，不能先写通过、等预算优势或普遍零漏计。V4的Aug15不利结果、greedy失配和V5/V6额外调用失败继续保留；本审查不扩数据、分辨率或实验矩阵。

## V7 与 RAM I/O 终态最终交叉核对

已独立重验两原包、112/30文件、2262/625个raw、527个共享调用前缀及18个复制文件，预算/作用域/累计计数一致。V7正例两遍均12/12/11/12，MAE=0；原时限仅7/8通过，最大发布1153.863ms。SD负例202/300调用后缺404→410，partial0不评分，整批仍FAILED。

RAM两案完成：负例300调用输出0但无人工总数参考，Aug15为325调用、计数12，不增加独立样本。预载3.105/11.496s与约.56s回盘排除于流计时，解码/推理/计数仍在板上；不能升级原SD失败或声称持续SD落盘达标。60源码与15资产的前后检查一致。RAM摘要已将本批1个复核视频/12次与历史4/47上下文分开。

未发现影响这些有边界结论的实质证据矛盾。RAM结果支持存储路径敏感性的工程观察，不是新增准确率单位或原SD合同通过。本次仅本地只读核验，无板卡/USB/模型或新任务操作；阶段实验结束，剩余工作为稿件与归档。
