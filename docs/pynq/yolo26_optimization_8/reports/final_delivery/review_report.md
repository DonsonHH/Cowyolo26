# Optimization 8 完整操作审议与自审报告

日期2026-10-19。审查者为实施者本人，不冒称独立第三方审计。最终验收以原始证据及发布完整性记录为准。

## 1. 范围与方法

逐条核对完整O8任务书（SHA7325641dab9b75e3e18d761b44e63f3f9fccc5f2f7389abf9acf3eef35e6ec5d）、AGENTS/experience、冻结O7、逐文件源差异、硬件工程/仿真、实际PL/整网/COCO/相机原始记录、授权与文件SHA。`source_review/source_change_index.json`及unified diff可供复核。

| 工作包 | 审议结论 | 主要证据 |
|---|---|---|
| O8-00 |独立目录、工具和基线通过|同轮A三轮/初始冻结/本地Vivado2026.1|
| O8-01 |低频多帧profile通过|TXsync/submit/poll/RXsync+copy/LUT/fill/repeat，正式关闭细采样|
| O8-02 |精确融合通过，负收益开关未默认|PC/板端100图三档411tensor/全部实验|
| O8-03 |计划、格式、单消费者/容量/bank/DAG检查通过|六计划字节重建、六畸形计划拒绝、额外显式fan-out拒绝|
| O8-04 |实际cache/reader/路由与clean timing通过|完整及扩展RTL、原始Vivado/DRC/源清单|
| O8-05 |真实PL跨层与中间数值通过|32实际向量+镜像+282块独立Golden+3072实际极值字节|
| O8-06 |17→25组合收益通过|三档C/D短测及正式三轮、每对节点诊断；未称穷举最优|
| O8-07 |速度、精度、稳定性及正常入口通过|A/D、C/D各3×100；3×PC5000；1000fixed；192/224各100camera|

## 2. 问题、修复和失败保留

| 发现 | 处置 | 复核结果 |
|---|---|---|
| P1 初版元数据长连乘−8.807ns |分级有界检查；失败工程不导出/下载 |重跑完整RTL及综合，最终+.040ns|
| P1 第二次route原PE路径−.424ns |独立physopt工程复用同一DCP，未改RTL/时钟/任意例外 |WNS/WHS/TNS/THS、route、DRC全通过|
| P1 恢复测试将写入start bit0误读为busy |按RTL使用busy bit2；预复位、错误清理先halt再free |原失败保留；实际abort、错误802和合法pair恢复通过|
| P2 PYNQ因同名XSA误选bit解析器 |XSA原样保留在O8 exports；不补丁系统库 |HWH解析、Overlay下载/附着均通过|
| P2 SSH断管导致打印BrokenPipe |独立冻结板端作业，stdout落盘，从140图断点续跑 |旧日志不改；三档各100唯一图最终0diff|
| P2 新PC重建入口缺静态依赖及gomp链接顺序 |保留两次失败DLL；修正静态库并放于目标文件后 |新DLL9图全部逻辑边界0diff，未替换正式评估DLL|
| P2 正常入口清单误纳PC参考raw |旧v1清单保留；原文件hash不改，正确列为重建依赖 |24运行文件闭合，三档+camera正常CLI通过|
| P2 导入O7的说明/PC默认库/TB引用 |在独立O8修复文档、DLL与本地模板；原历史不变 |完整清单逐文件SHA，三档graph/plan实际重建一致|
| P3 DRC初稿无负载网归因不准 |按rpt纠正33条FIFO状态网，旧稿保留 |40393可路由网完整，12项约束检查均0|
| P3 收尾审计误以为校准池只有128张 |核对512张池，固定配方取前128，未改模型/数据 |整池与val5000不交叉，113模型文件与O7相同|
| P2 一次性建设生成器可误覆盖接受版 |10个建设脚本加封存保护，原始版本单独保留 |正常原生/图/仿真/硬件新输出入口仍可用，运行源SHA未变|
| P2 对照A仍引用外部旧目录，首份封包源码数量表述滞后 |保留首份已验证归档；补齐逐字节相同的13文件O7运行参考，最终报告改为读取当前源索引 |原正式数据不变；最终新归档重新校验CRC/SHA及解包运行|

没有删慢帧、改hash掩盖错误、降低精度或改变计时口径来满足门槛。所有失败构建/原始日志/输出仍可审查。

## 3. 代码与协议审查重点

- 算术PE、requant和权重语义保持；controller仅增加local loader观察信号。mode2保存真实LUT后字节，halo使用消费者输入零点。
- 层内sink_fire与外部out_fire分离，外部TLAST只对应实际RX结束；internal/external remaining独立。cache只在完整提交后valid，frame/tensor身份匹配，reset/error/start/finish失效。
- 地址生成无通用除法关键路径；FIFO保留任意背压下的数据，缓存边界/容量/metadata检查不会读旧帧。满128KiB和Co80尾组实际通过。
- 原graph不改，DAG调度保留每逻辑节点一次，FP32残差边界未消除。JSON及binary图SHA均检查；畸形计划在CMA/提交前拒绝。
- 残差65536表保持原FloatLookup/DQ、加法舍入与quantize，ffp-contract=off；debug私有FP32中间值重建的限制明确。PL中间值来自真实S2MM，未用PC冒充。
- 持久小BO/独占锁/有界等待/停机再free保持。页对齐占用与实测一致；CmaFree波动不冒称泄漏，memstat仅解释本安装已验证的首字低/高32位。
- C API只跨opaque、标量及数组，不跨C++ vector对象。GCC同编译器ABI提示原样保留，源码与编译flags有快照；未加fast-math。

## 4. 授权、范围与保存

先核对资源/时序/仿真，再获用户明确许可下载本次O8和为A/D切换旧基线；旧基线许可未挪用于新构建。仅易失性PL，无SD启动、QSPI/Flash、kernel/device-tree/systemPython、电源跳线改动。当前许可不扩展到未来任意编程。

PC网口恢复仅ActiveStore，PersistentStore未变。O4–O7 PC14264、板端1762文件的集合/大小/SHA完全保持，无Git init/reset/清理；旧根文档先备份。原StageC/D两个P2不通过改写历史关闭。

## 5. 结果与实用限制

主A/D1.137999×、三轮同向，驻留同固件独立1.036506×；三档AP变化0pp。1000fixed及两档100camera无意外DMA error/hang，BO关闭回0/0。真实camera10张无损PNG与PC raw/boxes0diff；有person框供人工检查，有框率不等于准确率。

初始化约12–14秒、冷首帧、慢帧、采集/绘制/保存均分列。没有测功耗、Fmax、frame age/driver drops、逐轮温度轨迹或干净VM全新Vivado安装重建，不把这些未测主张写入PASS。终态core80001/100MHz、DMA1002/1002、core2/error0、BO0/0。

## 6. 交付审议

交付源/模型/固件/计划、正常入口、原生/图/硬件重建脚本、全部计时/AP/失败数据和中文复现说明。归档CRC/成员SHA在封存后单独记录，避免自引用。`completion_audit.json`逐项给出证据和结论；有任何未证实必需项时不宣布任务整体完成。停止于本轮，不自动进入O9。
