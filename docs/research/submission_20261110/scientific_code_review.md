# 通道计数投稿准备：科学问题与实现复核

复核日期：2026-11-10。代码基点：`7e5e974b46a3874c6d5cd46c9a99e3fec3767f0f`。本报告重新检查完整计数路径，不限于上一轮差异。除本文件外未修改项目文件；未连接远端、加载模型或生成新的动物真值。下述最小复现均为内存中的 `SOFTWARE_FIXTURE`。

## 评价目标和结论边界

按用户最新确认，以**完整视频统计窗口内的通行总数是否正确**为主要任务。用户只需看实际视频并核实总数，不要求提供逐事件时间戳、JSON 或人工轨迹。

可以采用独立冻结视频的逐视频绝对误差、MAE、偏差和总数吻合率开展有效的计数研究。缺少带时间的事件参考只限制事件 precision/recall/F1、逐事件漏计/重复和“零漏计”结论，**不自动阻断所有计数论文设计**。方向参考不完整时，只评已核实方向；不能擅自把另一方向真值补成零。逐视频总数正确也不能证明每次通行都被正确关联。

当前 4 段视频及其 47 次已确认方向总数均已参与开发。20 组实验的计数、调用、终态哈希和时限复算通过；它们支持工程原型和开发集对照。现有材料尚未给出一次冻结后、不再针对结果调参的独立视频总数评价，也没有证明严格相同计算预算下的机制优势。投稿主张应选择以下可完成路线：

1. 计数系统路线：增加独立冻结视频与用户总数复核，报告计数误差和板端运行证据；把“观察预算分配优于基线”保留为待检验问题。
2. 机制路线：在上述基础上完成预先规定的等预算对照，才能主张计算分配造成计数改善。

作者、单位等元数据按用户要求继续待定；这不影响当前技术补齐。不得用模板、人名占位或 AI 自查冒充人工确认。

## BLOCKER：与投稿主张直接相关的证据缺口

### B1. 尚无冻结后的独立逐视频计数评价（数据与复核关口，不是代码错误）

证据：[main.tex:87](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/paper/ieee_sensors_20261109/p0p1/main.tex:87)明确四片已成为开发材料；[main.tex:103](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/paper/ieee_sensors_20261109/p0p1/main.tex:103)说明重复播放不增加独立会话。重复播放的 20 组不能作为 20 个独立准确率样本，47 次不能作为独立动物样本。

行动：先冻结新视频来源、时间窗口、输入映射、几何、模型、阈值、策略、输出位置和失败处置规则，再一次性执行全部条件。保存所有视频的结果，交由用户按视频核实总数。查看新结果后调参的片段转为开发资料，不继续称为独立测试。若只能使用同一牧场/同一数据集的新会话，结论限定为该域；不必等待跨牧场资料才能研究域内计数。

### B2. 现有对照不能支持“相同预算下更可靠”的因果主张（仅对该机制主张构成阻断）

代码：[realtime.py:367](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/realtime.py:367)按墙钟处理后获取下一图；局部调用发生于下一次取图前。因此额外局部工作同时改变后续全局帧时刻。[tracking.py:29](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/tracking.py:29)及 [source_clock.py:89](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/source_clock.py:89)还将名义采样率用于跟踪参数/预测时间；U0 改变目标率不是单因素对照。

实测：L1 总调用 1234，C1 为 1239；二者的实际源帧和局部分配不同。C0/C1 请求旧帧 15 次、实际读取 0 次。因此不能将 C1 的 11/12 解释为历史帧导致漏计，也不能把 L1 的四段总数吻合全部归因于局部补检。[main.tex:137](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/paper/ieee_sensors_20261109/p0p1/main.tex:137)与 [main.tex:139](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/paper/ieee_sensors_20261109/p0p1/main.tex:139)目前已正确披露。

行动：执行后文的等预算方案，或把主张收窄为经过独立计数验证的嵌入式系统。不能因为总数评价无需事件时间戳，就把尚未取得的机制因果证据写成已完成。

## IMPORTANT：可修复的实现与评价问题

### I1. 事件评分没有强制事件 ID 唯一，重复记录可得到虚高 TP（已复现，次要评价路径真实缺陷）

位置：[evaluate.py:24](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/evaluate.py:24)、[event_metrics_v2.py:18](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/maintenance/counting_r1/event_metrics_v2.py:18)。事件只在可选 physical correspondence 路径才检查 ID 唯一性（该文件第 90–97 行）。常规评分把每一行都当成独立事件。

最小复现：参考列表放两份同一个 `event_id=E` 的完整事件；预测列表放两份同一个 `event_id=P` 的预测，视频/会话/运行身份均合法。`evaluate_run` 返回 `SCORED_AGAINST_SUPPLIED_HUMAN_REFERENCE`，TP=2、FP=0、FN=0、F1=1。这个结果完全来自重复行。

修复：在正式评分入口分别要求参考和预测的 `event_id` 为非空字符串且在规定作用域内唯一；重复应报错并保存原记录，不静默去重。两个不同动物可以同帧完成，所以不能把“相同时间/帧”本身作为重复规则。新增测试应覆盖重复参考、重复预测、两个唯一 ID 同时完成及跨会话合法 ID。

现有 frozen20 的逐案复算已检查预测 ID 唯一，未发现该缺陷污染现有计数。该缺陷不是缺少人工标注造成的，也不要求用户新增逐事件标注才能修复。

### I2. 事件参考的帧与时间一致性校验不足（已复现，次要评价路径真实缺陷）

位置：[evaluate.py:28](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/evaluate.py:28)。只检查 `completion_source_frame0` 落入窗口、关键帧列表非空，以及 entry_time 小于 completion time；不检查关键帧范围、不检查 entry frame，也不对帧号和实际源 PTS 做绑定。预测事件也未重新绑定到帧账本。

最小复现：统计区间为帧 0–20，完成帧写 10，参考与预测的 `time_s` 都写 1,000,000，仍得 TP=1。把关键帧列表改成 `[-50,10000]` 也仍然评分成功。有限值/JSON 检查会拒绝 NaN，故本报告不将 NaN 误列为已接受。

修复：依据 `frames.jsonl` 或预先冻结的完整源 PTS 索引验证预测 entry/completion 帧与时间；参考原帧若来自不同帧率，要求可核验映射并分别保存原片与板端输入的哈希，不用一个 SHA 字段混淆两种坐标。关键帧须为合法整数且属于声明窗口；事件 ID、方向、entry/completion 顺序也应一致。对故意位于窗口外的预测，应预先规定拒绝损坏账本或记为窗口外记录，不事后删掉改善分数。

### I3. 缺少符合用户工作方式的正式“总数参考”评分入口（当前需求缺口，可直接补齐）

位置：[evaluate.py:24](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/evaluate.py:24)要求每个参考事件有时间、关键帧和轨迹；[main.tex:97](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/paper/ieee_sensors_20261109/p0p1/main.tex:97)只定义事件集合评分，没有主要计数指标。[main.tex:142](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/paper/ieee_sensors_20261109/p0p1/main.tex:142)及结论仍把独立逐事件标注写成主评价必须条件，应按最新用户授权调整。

行动：新增与事件评分分离的总数评价入口。由系统保存 source/input SHA、窗口、闸线/方向约定、模型/配置/运行 SHA、开发或冻结测试角色、预测总数；人工界面仅要求用户确认视频总数。只有用户明确确认后才写 `reviewed`；系统负责生成结构化记录，不让用户填写 JSON。允许方向总数未知，禁止自动补零。逐视频保存 `prediction-reference`、绝对误差、吻合标志；跨独立视频计算 MAE、平均偏差和吻合率。零通行视频同样有效，避免使用除以参考总数的指标作为主指标。

当前开发数据换算的 MAE 为 U0=1.50、L0=1.25、C0=1.00、L1=0、C1=0.25 次/片；这些只是四段开发片的描述统计，不能替代新冻结测试。帧级时延、uncertain 记录数量和软件测试数均不能充当计数真值或 FN。

### I4. 局部框只裁到整幅源图，未限制在实际可见局部视野（已复现的边界缺口，现有结果未见触发）

位置：[geometry.py:75](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/geometry.py:75)逆变换后只按整幅 source width/height 截断；[backends.py:63](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/backends.py:63)不检查框中心是否来自 letterbox 的实际图像内容；[endpoint_recovery.py:133](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/endpoint_recovery.py:133)只检查物理通道、面积/重叠和置信度。

最小复现：1000×1000 源图，局部 ROI `[200,200,600,600]`，256 输入；输入检测框 `[64,-64,192,320,.9,0]`，decode 接受源框 `[300,100,500,700]`，包含局部输入没有提供的像素区。带 letterbox padding 的非正方形 ROI 也会把 padding 位置映射到 ROI 外。若这种框中心跨端区，当前路径没有独立的“中心确实在本次可见图像内容内”资格检查。

行动：对局部结果保存实际可见内容区域；至少拒绝中心落在裁剪视野外/letterbox padding 的候选，并对端区核验所需身体位置被裁断的情况显式标记。不要简单把局部框再裁到 ROI 后直接计数，那会移动框中心并可能制造过线。用实际现存日志先审计，再在开发片上验证任何资格规则；不能为改善某个新测试总数再调规则。

影响审计：frozen20 共执行 100 次局部调用，71 个结果被接受；逐个检查这 71 个框，没有框超出对应 ROI。因此目前没有证据说明本缺口改变了已报告的任何总数。这里的 71 次“接受”也不是 71 次人工确认正确。

### I5. 超过观察间隔后的 episode 仍保留旧 `emitted` 标志（已复现，影响截断账本完整性）

位置：[counter.py:41](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/counter.py:41)重置 origin/candidate/streak 等字段，却没有重置 `emitted`；[counter.py:70](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/counter.py:70)用该标志抑制 finish/eviction 截断记录。

内存复现：stable_samples=1，同 ID 在 t=0 位于 A、t=.2 位于 B，生成一次完整事件；t=3.1 重新出现在中部、t=3.3 到 B。跨 2 秒间隔后新 episode 无有效 origin→destination 通行，但其 state.emitted 仍为 true，finish 返回空列表。此前的 observation_gap / unanchored 记录仍存在；本报告不将其描述为“完全静默”，也未发现多计完整事件。

行动：把“此 ID 曾经完成过”与“当前 episode 已完成”分离，在观察间隔重置时初始化新 episode 状态。新增“先完成、再超时重现、最后未完成”的记录一致性测试；保留此前完整事件，不回滚总数。此项不单独阻断总数评价，但需要在使用截断账本作可靠性论据前修复。

## 复核后未发现的新缺陷

- [observation_track.py:20](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/observation_track.py:20)只记录当前实际检测；速度分母使用两个实际源时间。`box_at` 只改变关联几何，不修改历史。[source_clock.py:86](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/source_clock.py:86)拒绝非递增源时间，并按源秒清理存活期。本轮未确认新的未来帧泄漏或 dt 单位错误。
- [tracking.py:68](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/tracking.py:68)在当前 observed_velocity 路径输出实际匹配框；Lost 轨迹不直接提供计数位置。一次源图只调用一次 counter update。不能把轨迹外推当作实测过线。
- [realtime.py:392](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/realtime.py:392)收集 tentative/confirmed/lost 的真实观测预测用于竞争归属；[endpoint_recovery.py:163](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/counting/endpoint_recovery.py:163)只移除满足当前类别、低分、重叠和相对所有权条件的全局弱框。未复现新的确定性近邻吞并缺陷。它仍是几何启发式，不能由软件测试推出真实相邻动物已无误关联。
- 事件作用域正常路径严格对照 run/video/session；显式 legacy normalization 不改原日志。匹配器的最大基数、再最小时间误差目标与论文一致。唯一性和时间/帧绑定缺陷见 I1/I2。
- frozen20 的 186 个终态文件哈希全部重验；20 案复算与保存指标逐案一致。原 XSA、内嵌 bit/HWH、manifest 及 20 案冻结指纹已独立复核一致；这不能推导功耗或布局布线资源。

## 可在现有板卡和视频上执行的等预算实验

不改变现有 1280×720、5 Hz 准备输入、S256 权重、O8 固件和物理通道；不改 DNS/网络。先用现有开发片测可持续预算，再冻结整个新测试协议。采集原速继续运行，调度器决定花在哪些模型调用上，不强迫传感器变分辨率或 FPS。

### 主实验：把相同调用预算分配给全局或局部

建议实现一个固定 source-time block 调度器，先在开发资料确认可行。例如每 0.8 源秒允许恰好 2 个非热身调用（2.5 调用/秒，仅为开发候选值，不能未经实测就称已通过）：

| 条件 | block 内第 1 次 | block 内第 2 次 |
|---|---|---|
| A：全局预算基线 | 在固定源时刻 t 的完整视野全局检测 | 在固定源时刻 t+0.4 的完整视野全局检测 |
| B：条件局部预算分配 | 同 A 的 t 全局检测 | 若基于截至 t 的实际观测触发核验，检测 t 的局部；否则使用 t+0.4 的全局检测 |

两条件每个完整 block 都执行 2 次真实模型调用，使用相同的独立视频/窗口和总预算；一次热身单列。跟踪器名义时钟独立固定为同一个值，不能让预算方案顺带改变 lost 秒数、TTL 或关联阈值。局部资格与 fallback 规则在开发阶段冻结。未能在安排期限完成的源帧/调用不能用未来图替代，也不能重跑替换失败；记为 deadline/预算失败并报告。尾部不完整 block 和 EOF 观察需要事先一致定义，不能给某条件额外收尾调用。

这项实验比较“同预算的另一张全局图”与“条件局部图”的分配，使用视频总数 MAE/吻合率评价即可。不会假装两种策略看到同一组图；不同的观察图正是分配策略的处理变量。仍须报告实际完成的全局/局部/热身调用、全部选择源时刻、墙钟时限和失败。

### 机制控制：同一真实调用流上，局部结果使用或屏蔽

在 B 的一次真实执行里，保存全部全局/局部输出，另用两个不共享状态的 counter/tracker 处理同一条已经因果产生的调用流：B-use 使用局部结果，B-mask 只接受全局结果。两者不得影响原采集/核验触发调度，原始输出不改写。这样无需额外模型调用，就能隔离“把局部测量送入关联器”对最终总数的作用。

该 shadow 比较只回答使用局部信息的作用，不能独自证明资源分配优于另一个有效基线，也不能拿双 tracker 的墙钟开销冒充单系统性能。主实验 A 才提供把预算用于额外全局图的有效对照。

历史选帧暂不作为主贡献。只有开发资料中预先构造/发现实际能读旧帧的可达工况，再冻结该策略并进入新测试；不能因为 frozen20 的零实际历史读取就宣称历史模块通过或失败。

### 总数核验与统计

每个新冻结视频生成一张用户可核对的卡片：原片/结果视频、统计窗口、计数规则、预测总数以及待确认总数。用户确认后系统绑定该值到视频 SHA 和窗口。主表逐视频列 A/B 的误差、调用预算和时限，所有失败保留。重复播放先按每视频聚合或单独列运行波动，不把 repeats 当独立样本；统计不确定性以视频/会话为单位。当前缺少跨牧场资料时不报告跨牧场泛化。

## POLISH：论文与交付同步

1. 在主指标中定义逐视频计数误差/MAE/吻合率，事件 F1 移到可选辅助评价；同步修订摘要、讨论第 142 行、结论第 147 行和原研究清单的门禁文字。
2. 每张实验表注明 development/frozen test、独立视频数与 repeat 数。保留 C1 的 11/12、旧时限失败与零历史读取。
3. 保留“从准备帧计划到达开始”的时延边界。缺物理曝光/传输测量不妨碍报告板端原速回放性能，但不得写曝光到决策的端到端延迟；缺功耗/实现报告时删除节能或资源利用率优势主张。
4. 作者与机构继续留待用户提供；独立计数复核的实际人、日期和确认动作由系统记录，不能用作者字段待定阻止技术工作，也不能代用户签名确认。

本报告提出的修改和新实验尚未执行；它本身不升级任何数据或稿件为 submission-ready。
