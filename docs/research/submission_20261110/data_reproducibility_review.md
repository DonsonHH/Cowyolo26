# 数据、可复现性与历史身份研究的投稿准备审计

审计日期：2026-11-10。仓库固定为 `C:\Users\Donson\Documents\Codex\exports\Cowyolo26-20261031\repo`，HEAD `7e5e974b46a3874c6d5cd46c9a99e3fec3767f0f`。同时只读检查了 `C:\Users\Donson\Documents\ChatGPT\奶牛\paper_p0_p1_20261109` 与导师汇报目录。以下以 **R/** 指代上述仓库根，以 **W/** 指代 `C:\Users\Donson\Documents\ChatGPT\奶牛`。

本审计按用户最新偏好，把**每段视频中人工接受的通行总数及预测总数是否一致**作为可采用的主终点。不要求用户逐事件打时间、不要求新增人工 JSON，也不要求重新确认已经接受的四段总数。事件 precision/recall/F1、逐次零漏计和永久牛号正确率属于更强的主张，现有总数不能支持；可以直接从本篇计数论文的主张中删去，而无需为保留它们扩大人工工作。

结论：当前资料可以写成有实际板端实现、可复算开发对照和明确失败的**视频回放原型研究**。若要声称“补检提高未见会话上的计数准确性”或提供一个可由外部复核的复现发布版，仍有下面的关口。作者和单位的待补字段不在本次优先项内。

## 已直接检查的覆盖

- 重新读了 20 组本地 `frames.jsonl`、`events.jsonl`、`summary.json` 和终态记录：计数、全局/局部/热身调用、100 个输出文件哈希和全部原回放时限与发布的指标一致；15 次历史请求均被覆盖，捕获统计与处理台账中的历史帧读取均为 0。不是仅采信 `FINAL_REVIEW.json`。
- 重新计算了 V4 源清单中的 51 个文件哈希，当前文件全部匹配；新版论文的 5 个源文件和 PDF 也匹配构建证明。这个结果证明本地源与特定实机版本相符，不证明外部读者已经取得模型、固件或可执行环境。
- 直接从 Cows2021 final20 与 BECA 的各 480 条原始决定重算主工作点。final20 的旧/新模型分别为 C/W/U=10/2/18、3/0/27，未知 FA=3/30、0/30；BECA 为 13/15/2、13/11/6，未知 FA 均 26/30。全部接受决定与记录的分数、阈值相符。这支持“作者标签下的组件结果可复算”，不认证作者身份标签全部正确。
- 从协议的实际 ID 列表重算，Cows2021 的 120 个校准/开发 ID、16 个域适配训练 ID、20 个 final20 ID 两两不交，合计恰为原协议全部 156 个合格 ID。
- 只做本地文件/版本检查，无网络、远程命令、模型前向、训练或板端写入。对 19,865 个不大于 512 KB、排除主要第三方源树的已跟踪文本作有限密钥模式检查，未命中；这不是全仓库安全认证，也没有复核远端当前状态。

## BLOCKER

### B1. 现有“数对”的主证据仍来自开发选择，不能作为新方法的独立准确性证据

四段视频已经用于诊断/参数选择，Aug20 首次 9/12 后也进入开发；V4 八次重复和 P0/P1 二十次运行都复用这些素材。新对照 L1 的四段总数吻合有价值，C1 的 Aug20 11/12 则说明不能将 V4 两次吻合写成每次都正确。它们不是新会话、47 次之外的新独立样本，也不证明哪一次错误被局部补检修复。

证据：R/[P0/P1 正文](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/paper/ieee_sensors_20261109/p0p1/main.tex:87>) 第 87–103、131–142 行；R/[R5 历史验证](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/maintenance/offline_counting/R5_REPORT.md:61>) 第 61–85、118–136 行。

修正：主问题改为“固定计算条件下，每会话的方向总数误差能否降低”，主表按视频列人工接受的总数、两个方向的预测数、绝对误差和实耗调用。新候选确定后，用没有参与本候选选择的会话做固定比较；参考可以是用户看连续视频后确认的简单双向总数，不需事件时间或 JSON。若没有这样的新会话，结果限定为这四段开发片的探索性比较。已有四段无需再次审核。保留 Purdue 6 月 9 日 0/1 等外来源失败，不能仅挑“数齐”的 MultiCam 视频作为整体泛化证据。两个方向分别在不同视频出现，不等于同一通道的双向/相向工况已经验证。

本项阻断的是**独立准确性或方法优越性主张**，不否定四段已接受总数或原型的实现结果。不以“缺逐事件 JSON”阻断较弱的总数论文。

### B2. 当前公开代码树仍有明确未闭合的再分发许可来源

R/`NOTICES.md` 第 7 行明确承认 O8 的 `resident_methods.inc`、`software_fusion.inc` 尚无单独作者和许可来源，并要求上传/合并/再分发前由权利人核实。两个文件实际在 HEAD 的源树中；发布散列一致不解决这个问题。

实际跟踪实现也不能只按 ByteTrack 论文或根 MIT 许可证理解：R/`pynq/cow_research_numpy_tracker_20261029/cow_tracker/byte_tracker.py:1` 标明 **Ultralytics AGPL-3.0**；R/`research/pynq_frontend_port_20261029/NumPy跟踪移植与实机回归.md:7` 说明它从 Ultralytics 8.4.63 保留 AST、只改导入和依赖边界。根 `LICENSE:1–13` 是 MIT，`NOTICES.md:5` 虽正确保留第三方许可，但不是针对实际衍生分发的完整清单。检查名称含 license/copying/notice 的已跟踪文件，没有找到 AGPL 完整许可文本；保留了源文件中的许可链接和标记。

证据：R/[许可待核实说明](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/NOTICES.md:7>)；R/[实际 tracker 来源](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/research/pynq_frontend_port_20261029/NumPy跟踪移植与实机回归.md:7>)；R/[AGPL 文件头](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/pynq/cow_research_numpy_tracker_20261029/cow_tracker/byte_tracker.py:1>)。

修正：由实际权利人完成两个 O8 文件的来源认定和授权；制作逐组件的版权/许可证清单及必要许可文本，写明本项目的修改范围和实际 Ultralytics 来源，核查组合分发、权重及派生图的授权安排。未核实的文件不要继续作为已具备开放再分发权的投稿附包发布。此结论基于本地已捕获材料，是“授权证据未闭合”，不代替对具体许可证义务的法律认定，也不要求删除历史证据。

## IMPORTANT

### I1. 必须统一跨任务的暴露记录；现有标签不能自动构成整个系统的未见测试

最明确的交叉关系如下：

1. Cows2021 的作者身份 Test 裁剪有 7,931 张能对应本项目检测原图，其中 5,998/1,249/684 分别落在检测训练候选/开发验证/开发保留角色。身份 ID 与身份编码器训练隔离，不等于检测器或整条链路没见过原像素。
2. 当前日期/采样规则下的 156 个合格 Cows ID 已全部分配并使用：120 个校准/开发、16 个训练、20 个 final20。不能把 final20 再用于选模型/阈值后继续称它为新方法未见测试。若改变日期或采样规则以启用剩余来源，必须重新定义评价，不是从旧名单中再拿一批相同意义的最终 ID。
3. 早期身份材料的“03-05 至 03-11 像素仍隔离”是当时、特定任务范围的记录；后来的 R5 已明确 3 月 8/9 日原视频用于开发。3 月 10/11 日仍需逐文件核查训练/开发接触关系。不能直接从十月报告复制全项目未见日期的说法。
4. Cows2021、OpenCows 和 MultiCam 的名字、年份或数字 ID 命名空间不同，不能证明不同牧场、不同物理牛。新的数据审计正确限定为文件/日期/训练清单核查，未验证近重复或跨数据集物理身份独立。

证据：R/[来源对应审计](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/research/cows2021_identity_intake_20261030/results/source_relationship_audit.json:18>) 第 18–31 行；R/`research/cows2021_identity_eval_20261030/protocol/run_v1.json:4–136`；R/`research/identity_domain_adapt_20261030/protocol/run_v1.json:7–47`；R/`research/identity_final20_20261030/protocol/run_v1.json:4–29`；R/[后来的日期暴露说明](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/maintenance/offline_counting/R5_REPORT.md:118>)；R/[本轮数据审计局限](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/p0p1_20261110/DATASET_AUDIT.json:145>)。

修正：在下一次预测前创建一个跨检测、校准、身份和计数的追加式 source/exposure 表，至少记录官方对象/文件哈希、相机/日期/视频时间窗、派生父文件、标签类型、梯度训练/阈值选择/开发/固定评价角色和首次预测/人工查看情况。先对照现有记录填表；未知关联保持未知，元数据查看与像素/分数暴露分开。新测试按“对哪一候选、哪一任务未见”声明，不再只有一个笼统 holdout 字段。

### I2. 最新二十组对照的公共复现输入缺失，已有 V4 源哈希不能替代它们

本地可以取到 P0/P1 的 machine protocol、二十份配置/freeze、终态、帧/事件台账和复算工具；公开 R/`docs/research/p0p1_20261110` 实际仅有 README 和五份汇总 JSON。`VERIFIED_METRICS.json` 末尾引用了 `COLLECTION.json`、`batch_protocol.json`、`BATCH_FREEZE_INDEX.json` 的哈希，但这些对象以及 `collect_ablation.py`、`review_ablation.py` 没有作为本轮公共目录内容提供。另一个实际生成输入的 `maintenance/review_20261109/capture_v3/SOURCE_FORMAT_MANIFEST.json` 在工作树存在，但未被 HEAD 跟踪。

公开 V4 的 51 个源文件确实匹配 `SOURCE_VERSION.json`，因此不是“没有源码”。缺口是：外部读者无法仅靠最新汇总恢复本轮每案的完整条件、输入转换和执行证据；模型图/plan/bit/HWH/native 库继续位于私有存储，只有哈希并不提供取得方式。论文构建可复算与实验可重跑是两项不同交付。

证据：R/[公开指标所指的私有证据对象](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/p0p1_20261110/VERIFIED_METRICS.json:1640>)；R/[V4 精确源版本](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/maintenance/review_20261109/age_v4/SOURCE_VERSION.json:1>)；W/`paper_p0_p1_20261109/stage_ablation.py:24–40,73–104`；W/`paper_p0_p1_20261109/PRIVATE_ARCHIVE.json:5–15`。

修正：在许可核实后提供紧凑、可离线核查的研究附包：本轮协议/配置/freeze、原始小台账与独立重算脚本、源哈希、实际环境版本、官方数据的对象和窗口、预转换命令/帧映射、模型训练与导出/归一化/编译配方及必要资产取得方式。受限原视频可由读者从官方来源按清单重建，不必直接再分发。私有资产若只能按合理请求取得，应明确限制和联系人/取得流程；在此之前把状态写成“本地及私有归档可审计，尚非自包含公共复现包”。

### I3. 文件一致性审计的覆盖与训练过程可重建性要分开

本轮 16,760 个图像/标签文件和训练来源校准图的审计有清楚的代码覆盖。它没有重新解码核查 RGB 近重复；复用旧 RGB hash 的检查已在 JSON 中说明。`source_block` 仅为原编号每 100 个分箱，不是会话，不能把 block 相交直接认作泄漏，也不能把 block 解释清楚后反过来认作会话独立。

所用训练 checkpoint 是 recovered **last** 而非 best；其原作业 `130518_9` 保留 `FAILED|1:0`，轮转计划来自冻结的分离 CPU 生成器及观察到的批数重建，逐更新梯度审计数组未恢复。当前图/plan/权重哈希是有用的部署身份，不能单凭它们升级为完整重放了原训练、原更新顺序或原始全部训练验收。

证据：W/[实际执行的数据审计源](<C:/Users/Donson/Documents/ChatGPT/奶牛/paper_p0_p1_20261109/slurm_audit_training_data.py:24>) 第 24–58、76–100 行；R/[训练与归一化记录](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/p0p1_20261110/DATASET_AUDIT.json:124>) 第 124–152 行；R/[block 语义](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/p0p1_20261110/SOURCE_BLOCK_AUDIT.json:6>)。

修正：方法/附包写清实际 last checkpoint、选择规则和恢复原因；保留原失败日志、实际完整训练配置、源码和可复得数据清单。若无原训练逐更新证据，只认领“该冻结权重的部署与有限恢复记录”。数据独立性应从父图/源视频/时段/动物关联审计建立，而非把 16760 文件哈希通过当作无泄漏证明。本次不要求为了补一份更绿的验收报告重训。

### I4. 协议及实验选择历史需要可读登记，避免将局部冻结误写成全研究预注册

本轮 machine protocol、配置和输出字节绑定可核对；原最初 Markdown 冻结副本未找回，当前 Markdown 后补了限制说明。其版本明确承认这一点。Python 可执行文件及所有安装包也没有每案字节冻结，只记录前一 V4 环境，属于共享运行条件。V4 是多轮开发和失败后的选定版本；P0/P1 单案冻结不消除前面的数据选择与调参历史。

证据：W/[协议当前文本](<C:/Users/Donson/Documents/ChatGPT/奶牛/paper_p0_p1_20261109/ABLATION_PROTOCOL.md:1>) 第 1–8、26–38 行；R/[公开补充的协议限制](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/p0p1_20261110/README.md:23>)；R/`paper/ieee_sensors_20261109/p0p1/main.tex:123–139`。

修正：公开一个选择/运行登记表，列明训练候选、计数策略版本、四段的暴露顺序、每轮完整结果、失败及采用决定。当前摘要的 “An initial configuration” 宜改成“a configuration selected during development”，避免被读成首次尝试或独立基线。后续冻结协议保存原始字节和独立时间证据，修订另存；当前资料保持“探索性、分块冻结”，不补造预注册。若只认领总数误差，协议也同步改用该终点，不沿用必须补人工逐事件时间的旧路线。

### I5. 公开归档的实际内容与排除声明不完全一致，需要独立的投稿发布包

HEAD 有 34,096 个跟踪路径；按当前文件尺寸相加约 1,162,294,007 字节，**不是 Git 压缩仓库大小**。索引只有 21,040 个不同 blob，13,056 个路径是已存在 blob 的重复入口；原件、服务器结果、delivery 和可读副本混合，容易把同一数据或运行重复计为证据。

R/`ARCHIVE_CONTENTS.md:19` 与 `README.md:30` 称排除了数据集和依赖缓存，但树中实际有完整作者标注和依赖/缓存副本。例如 Cows2021 的 train/validation/reserved_test annotations 分别有 7,248/1,023/2,131 个图像条目，9,395/1,238/2,532 条标注；不是仅保留文件名索引。`server/deployment_audit/dependencies_offline` 有 3,305 文件、约 49.24 MB；另有 `server/deployment_audit/cache/ultralytics/Ultralytics/settings.json` 等缓存。还存在来自源图的照片面板；“没上传完整原视频”不等于没有任何数据衍生像素。

证据：R/[归档排除声明](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/ARCHIVE_CONTENTS.md:19>)；R/`research/cows2021_labels_20261027/catalog/train_annotations.json:1`、`validation_annotations.json:1`、`reserved_test_annotations.json:1`；R/`HANDOFF.md:62–66` 的实际源照片面板；R/[已承认的衍生图及环境信息公开问题](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/20261109_成果与复审.md:60>) 第 60–64 行。上述路径/数量来自本轮 `git ls-files`/索引对象检查。

修正：保留历史档案，另做内容可审查的版本化投稿附包，只有一个主要结果表和每个运行的唯一 ID；去除不需要的镜像源树、缓存、私人环境定位信息，发布明确的源/派生/复制关系。修改排除声明为实际范围，对已包含标注、衍生面板和第三方代码逐项核对许可及署名。不要未经授权重写公共历史或删除唯一证据。

### I6. 数据和模型许可须按实际发布材料登记，泛称“公开数据”不足以覆盖视频/图像/标注/权重

本地已捕获来源把 Bristol 的 OpenCows2020/Cows2021/MultiCam 数据标为 Non-Commercial Government Licence；BECA 指定 Figshare v1 为 CC BY 4.0；COLO HF 卡片记录为 MIT，但实际 640×640 GitHub COCO 导出 JSON 内 `licenses` 列表为空。作者代码许可证、数据许可、权重及派生量化图的授权不是同一对象。尤其不能仅依论文可以引用或作者图像可下载，就认定可把汇报视频、源图面板、整份标签、训练权重以根 MIT 重新发布。

证据：R/[Bristol 数据许可记录](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/data_audit_20261026/数据集审计与基线进展.md:110>)；R/[BECA 固定来源](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/independent_source_recheck_20261030/BECA身份数据准入与冲突核查.md:7>)；R/[COLO 所用版本区别](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/external_sources_20261030/公开俯视数据来源与准入结论.md:21>)；R/`research/external_sources_20261030/evidence/COLO_zip_metadata_v2/annotations_00.json:1`；W/`导师汇报_奶牛通道计数_20261109/README_请先阅读.md:27` 已提示视频再分发待核实。

修正：按“原始对象/版本—实际获取来源—许可文本及证据—用途—修改—再分发范围—引用/署名”制作清单；投稿图和补充视频逐个关联到该清单。能用官方获取清单和重建命令解决时，不必再分发原数据。许可不明确的派生媒体继续保留在本地汇报范围，等待确认。本次未联网更新条款，不对当前法律效力作超出本地证据的判断。

## 已有独立来源标签与身份工作的可用性清单

这里“作者标签”指标签来源独立于本项目本次预测，不表示已经独立人工认证了真实耳标、全部身份或完整通行覆盖。“独立程序复算”只验证计算与记录，不产生新的 GT。

| 材料/阶段 | 已有标签及实际覆盖 | 现在可用于什么 | 应归档或隔离的主张 |
|---|---|---|---|
| 四段 MultiCam 通道片，V4/P0P1 | 用户已接受方向总数 12/12/11/12；输出/台账真实，均是开发素材 | 本论文的开发总数误差、计算调用及回放计时 | 不作为未见测试；不从总数推事件 F1、逐次零漏计或永久身份 |
| MultiCam 早期 400 图 ImageNet 基线、750 图身份训练 | 作者匿名 ID；基线 20 注册/10 校准未知/10 评价未知；后续 580 训练图，分开的校准与 6 注册+6 未知评价身份 | 组件级已知/未知检索、拒识及覆盖风险；保留全部 seed | 后续已反复分析，归为开发；不是耳标恢复或本篇新计数测试 |
| 原 12 次事件照片、ID009/020、跨日期换图库 | 照片来源可追溯；ID009 与 E010 的同次通行重叠有几何/像素证据，020 无可靠身份对应；换 Aug19 图库后仍无已接受事件身份 | 功能/裁剪域/图库日期诊断、同次通行泄漏反例 | 不能把候选越阈值当“找回牛号”；Aug19 图库检索 Aug14 是回顾诊断，不是当时已登记的部署 |
| Cows2021 540 图跨日期组件评价 | 作者身份标签；120 互斥 ID，先校准后评价；当前旧 C Top-1 65/120，C/W/U=30/21/69，未知 FA20/120 | 真实作者标签下的开放集组件基准、负结果与域适配开发 | 与检测原图有已知来源关系；不等于未见整系统、跨牧场或当前通行真值 |
| Cows 域适配 16 ID/457 图、final20 的 90 图及 ARM 复核 | 训练 ID 与 120 开发、20 final 两两分开；final20 新模型 Top-1 30/30，但主阈值 C3/W0/U27，未知 FA0/30；ARM 是同输入部署复核 | 已冻结模型在保留身份上的组件结果；数值/部署一致性；保留排序与覆盖取舍 | final20 已使用；不能只报 100% 排名，不能称全部 156 合格 ID 里还有同协议未用最终组；ARM 重跑不增加独立身份 |
| BECA 20 ID/90 图迁移及分数诊断 | 作者视觉 ID，隔离 15 个冲突线索 ID 和 3 个 QA ID；实际两组同 JPEG 双 ID 已字节证实；日期叠字与文件名存在不一致；两模型未知 FA26/30 | 按文件名日期划分的外来源组件压力、拒识失败和标签风险 | 未认证耳标/全部 ID/实际时间；看完标签的阈值枚举是乐观诊断上界；20 ID 现已暴露 |
| RF queue、confirmed12 RF stream、实际触发/并行身份任务 | SIM 码表、预声明功能标签；实际 CPU/ARM/NCNN 查询与队列日志 | 软件异常处理、队列完整性、模型部署和同板争用 | 不作为真实 RF 读码/错误率，不产生当前视频的永久身份 GT；同照片多条件不是新牛 |
| Toros 历史片 | 实际保存发布方轨迹原表，由其导出单方向 6 次参考；发布方说明为检测/跟踪后人工修正 | 外来源、侧视的历史轨迹/通行压力；可明确原参考来源；已用于开发 | 不是当前 four-clip 的 GT，不是未见测试，也不补同一俯视通道双向；旧官方/微调结果不是当前 S256 候选结果 |
| Purdue AutoCattlogger 两个单牛片 | 用户预测前确认每片 1 次左→右通行；6/8 校准、6/9 冻结测试 0/1 失败，早期阶段性暴露已披露 | 保留有来源和简单人工总数的独立来源失败；符合无需事件时间的计数端点 | 原 404 访问失败记录不能再写成始终未取到数据；6/9 也不能在继续诊断/选参后当新版本未见测试 |
| COLO Top-View 504 图/3950 框，其中测试 50 图/451 原始框 | 作者检测标注；1 个退化框、15 个轻微越界；已经运行后续三模型/三尺寸外来源评价 | 检测任务的外来源压力与标签口径分析 | 没有通行/永久 ID；早期“测试像素未打开”只属当时状态；不可当计数 GT |
| MooTrack360 | 实际作者 GT 350272 行、8 ID；空间 ×2 和全片帧映射仍未完全确认 | 待准入的跟踪/映射候选 | 抽样对应不足以生成完整通行 GT；不把牛舍任意跨线等同出入口 |
| CattleEyeView | 已保存论文/仓库说明，论文报告人工跟踪计数；本地未取得原片和完整标注 | 现有公开人工 GT 的候选线索 | 不能列成项目已拥有的测试；应先取得实际数据、许可和事件口径 |

关键来源与可追溯对象：

- R/`docs/research/identity_baseline_20261026/身份基线与训练路线.md:13–25`；`identity_training_20261026/训练方案与执行记录.md:15–45`。
- R/[ID009 来源与准入](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/identity_source_provenance_20261029/原视频身份来源核查与评价准入.md:59>) 第 59–68 行；R/[换图库的时间顺序和标签分母](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/crossdate_gallery_20261029/跨日期图库与真实抓拍身份结果.md:35>) 第 35–38、80–105 行。
- R/[Cows 跨日期结果](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/cows2021_identity_eval_20261030/跨日期身份检索与拒识结果.md:7>) 第 7–28、48–54 行；R/[final20 全部结果](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/identity_final20_20261030/保留20身份结果与自动接受限制.md:15>) 第 15–22、73–77 行；实际决定位于对应 `research/.../delivery/results/evaluation/all_decisions.json`，本轮已重新聚合主工作点。
- R/[BECA 标签/日期风险](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/beca_fixed_transfer_20261030/固定模型外来源结果与阈值失配.md:67>) 第 67–90 行；R/`docs/research/beca_score_diagnosis_20261031/单阈值能解决多少问题.md:20,45`。
- R/[RF 模拟边界](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/confirmed12_rf_stream_20261029/计划与验收.md:5>) 第 5–12 行；R/`HANDOFF.md:38–53`。
- R/[Toros 实际参考](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/counting_eval_20261026/README.md:5>) 第 5–24 行；原作者表：`research/counting_eval_20261026/delivery/counting_evaluation/annotations/publisher_gt_original.txt`，对应导出 `publisher_derived_reference_events.csv`；R/[Purdue 后来的成功获取及失败](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/maintenance/offline_counting/R5_REPORT.md:63>) 第 63–85 行。
- R/`docs/research/external_sources_20261030/公开俯视数据来源与准入结论.md:23–40`；后续已用状态见 `docs/research/colo_eval_20261030/COLO三模型三尺寸外来源检测与下一步.md`；R/`docs/research/mootrack_alignment_20261028/Review与当前状态.md:5–19`；R/`docs/research/counting_reference_candidates_20261027/独立计数参考候选核查.md:7–11`。

上述身份路线完整保留在历史归档中。可供独立组件论文或附录取材的真实作者标签主要来自 MultiCam、Cows2021 与 BECA；NCNN/ARM/PL 数值复核、crop/domain/torso、图库与阈值诊断、RF 合成和触发/队列阶段复用这些输入，不新增现场永久身份 GT。主篇若聚焦通行总数和计算取舍，应把身份/RFID路线作为系统背景或另案研究，避免把尚未验证的找回能力加入主贡献。

## POLISH

- R/`README.md:3,32`、`HANDOFF.md:1–3`、`STAGE_INDEX.md:7–9` 仍以 11 月 9 日 V4 为当前入口；新版 P0/P1 在论文子目录已正确标明。更新统一入口即可，历史记录不改写。
- 原报告中“仍待板卡信息”“RF四轮原包尚待恢复”“Purdue未取得”“COLO测试像素未开”“03-05至03-11仍隔离”等句子有明确历史时点。当前状态表应覆盖这些后续变化，不能单凭一句旧报告就认定当前缺失或未暴露。
- 投稿正文应保留与方法判断相关的负结果，缩减阶段日志、重复表、作业号和运维元数据。作者署名等继续待确认；本审计不将其置于数据/证据关口之前。

## 最小可执行的下一步

1. 固定“每视频、每方向总数误差”主终点，已有四段继续使用已接受总数，保留 C1 与外来源失败；删除不打算支持的事件 F1/永久身份正确率主张。
2. 汇总跨任务暴露表和来源关系，圈定对下一候选确实未用于选择的会话；取得简单总数即可，不要求人工时间或 JSON。先固定候选、预算和所有报告条件，再运行。
3. 补齐最新二十组的可审计小附包及取得受限输入的说明；逐对象清理许可和署名问题，再确定公开范围。历史大归档保持可恢复，投稿附包单独版本化。
4. 将身份/RFID真实已有标签、失败、泄漏和数值一致性按本清单归档，主篇聚焦已经能验证的总数与资源取舍。

本轮仅创建本审计文件，没有执行上述下一轮实验或修改其他材料。

## 补充：同一 MultiCam 数据集的 camera2 8 月 17/18 日暴露核查

补查仍只读本地元数据、协议、来源/结果文本，没有下载、解码、观看新视频或运行模型。先用日期、相机路径及八个精确文件名作定向检索，再从已保存的官方 ZIP 中央目录和 `.info.json` 提取对象记录；没有以整个数据集名称或日期相同直接推定像素重复。

### IMPORTANT：可提名 camera2 新文件，但不能认证为未见动物或未见通行

保存的官方目录中，camera2 在 2023Aug17 和 2023Aug18 **各有四个视频**：

| 日期 | 官方目录中的文件，按文件名时间排序 | 本次精确文件名检索结果 |
|---|---|---|
| 2023Aug17 | `2023-08-17T12-49-53.mp4`、`13-13-24.mp4`、`13-34-34.mp4`、`13-55-15.mp4`，后三项同日期前缀 | W 中仅命中保存的官方 `entries.json` 和 `info.json`；本次检索的仓库来源/协议/结果文本未命中 |
| 2023Aug18 | `2023-08-18T12-53-13.mp4`、`13-15-55.mp4`、`13-36-34.mp4`、`13-55-52.mp4`，后三项同日期前缀 | 同上 |

因此，**没有发现这八个 camera2 原视频已用于计数器训练、调参、推理、抽帧或原生内容选择的本地记录**。这是有明确检索范围的“无已知计数暴露”，不是证明私有服务器全部历史、未记录操作或跨相机同次通行均已排除。官方目录的读取本身只暴露元数据，不等于观看了视频。

可按不看内容的规则提名最早文件作为下一计数验证候选，优先提名：

- `MultiCamCows2024Root/videos/camera2/2023Aug17/2023-08-17T12-49-53.mp4`。官方 ZIP 元数据大小 **260,571,176 字节**，CRC32 **2728321474**；发布方 `.info.json` 的 SHA1 为 **c838a48dc2e060f0118c103913700c2e2d6d30c7**。
- 备用：`MultiCamCows2024Root/videos/camera2/2023Aug18/2023-08-18T12-53-13.mp4`。官方大小 **260,538,408 字节**，CRC32 **4160466738**，发布方 SHA1 **7a7ada1070c3fe366e54aa0b426e65dd032263d2**。

以上是发布方元数据值，**本补查没有读取相应视频字节来核验它们，也未得知时长、完整通道范围或是否含完整牛通行**。不得先看多个候选的计数成绩再挑表现较好的片段。可先固定“最早完整文件、全部可解码区间”的取材规则，或明确固定的起止区间；若只抽查/只截取，应保留原因、完整候选清单、无事件和截断情况。若选定区间最终没有完整通行，它只能成为负例，不将其换成有牛片后继续称原先的随机测试。简单视频总数的人工确认足够，不需要用户填写逐事件时间/JSON。

官方对象证据：W/[中央目录 Aug17 对象](<C:/Users/Donson/Documents/ChatGPT/奶牛/identity_source_provenance_20261029/evidence/zip_directory/entries.json:97771>) 与 [Aug18 对象](<C:/Users/Donson/Documents/ChatGPT/奶牛/identity_source_provenance_20261029/evidence/zip_directory/entries.json:97617>)；W/`identity_source_provenance_20261029/evidence/zip_metadata/info.json` 中按上述完整 `id` 唯一匹配的发布方叶记录。目录记录只是出处，尚不是新实验准入或结果。

### 日期/身份交叉暴露必须保留

1. **camera1 Aug17 已经开发使用。** 七个原文件均做过预定字节位置的原生内容抽查；`12-54-41` 完整取得并看过全片稀疏概览，`13-25-38` 完整取得、形成通行参考草案，后续又做四模型回放。不能将 camera1 Aug17 再当新测试，也不能只因 camera2 不同，就推断它拍到的是从未用于方法选择的物理通行。
2. **Aug17/Aug18 身份裁剪也已经用过。** 直接读取 R/`research/crop_domain_20261029/input/new_validation_gallery_selection.json` 的 25 行，全部为 **camera1、Aug17** 的新验证图库；`input/validation_query.json` 的 55 行全部为 **camera1、Aug18**。身份训练的实际 750 图清单中，580 个梯度训练图全部来自 camera1 Aug14–16；Aug18 的 55 图是身份验证查询，并参与 checkpoint/阈值选择，不是这批图的直接梯度训练。这些事实应按“身份组件的模型选择暴露”登记。
3. **计数检测器与身份编码器是不同模型。** 当前 S256 检测器的已审计训练/校准来自 Cows2021 的训练清单，不能把上述 MultiCam 身份验证图自动记成 S256 检测器梯度训练；另一方面，若它们影响了全项目裁剪/预处理或机制选择，也不能宣称全系统完全未见同日期材料。
4. **原来源核查没有给出这两日的 camera2 映射。** `identity_source_provenance` 的几何协议实际只搜索 camera1 Aug14 的 0–10873 源帧。公开身份裁剪文件没有已核实的完整源视频/帧映射，因此不能据身份目录 ID、裁剪朝向或文件名序号，排除与 camera2 Aug17/18 的同牛、同次通行对应。
5. **camera1 Aug18 的 R5 原视频也已使用。** 文件是 `2023-08-18T12-53-40.mp4`，不是 camera2 的 `12-53-13.mp4`；同一天、相差的文件名时刻不证明相机时钟已经同步或两个录像完全独立。

精确证据：R/[camera1 Aug17 筛选记录](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/research/overhead_long_session_20261028/普通俯视长视频筛选与下一步.md:9>) 第 9–38 行；R/`docs/research/long_video_fixed_replay_20261029/普通俯视长片四模型回放与研究决策.md`；R/[裁剪域协议的验证日期](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/research/crop_domain_20261029/protocol/study_v1.json:63>) 第 63–67 行；R/`research/identity_training_20261026/delivery/catalog/image_manifest.json` 的实际 750 行图像对象；R/[来源几何搜索范围](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/research/identity_source_provenance_20261029/protocol/geometry_v1.json:4>) 第 4–13 行；R/[R5 Aug18 实际文件/区间](<C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/maintenance/offline_counting/R5_ADMISSION.json:24>) 第 24–29 行。

推荐的论文用语为：“在同一牧场/数据集内，采用本地记录未发现已有计数预测或调参使用的 camera2 新原文件，作预先冻结的会话计数验证；同牛及跨相机同次通行重叠未知。”在没有进一步源映射前，不称跨牧场、未见动物或已证明完全独立的通行测试。

### 最小复算发布包：避免继续分发许可未闭合的 O8 源，不删除历史

可以先发布一个**计数结果审计附包**，明确它与可重跑硬件实验的完整发行版不同：

| 最小内容 | 要解决的问题 | 发布边界 |
|---|---|---|
| 冻结的总数比较协议、全部候选/运行登记、每视频人工接受总数及其原始确认出处 | 主终点、选择顺序、分母及失败是否可核查 | 保留已接受总数；无需人工事件时间；不以输出框回填新 GT |
| `sources.csv/json`：官方对象、文件大小/哈希、相机日期、确切区间、转换命令、源帧/输出帧映射 | 读者如何取得和重建同一输入 | 原视频从官方取得；不默认再分发受限媒体；发布方哈希与本项目实测哈希分开 |
| 每案配置、机器协议/freeze、原始小型 count/frame/event 台账、全部失败状态 | 是否能从独立原记录重算每视频计数/调用/时间 | 去除非必要运维定位信息；若制作去定位副本，保留副本自己的哈希及变换说明，不能冒充原冻结字节 |
| 不导入 O8、不连接网络/板卡的纯离线复算入口、输入 manifest 和结果比较 | 新机器能否复现本次表格，而非只看到 verifier 的 green JSON | 运行相对路径；输入只读；不触发模型推理；错误输入明确失败 |
| 当前执行源版本、权重/graph/plan/native 库/bit/HWH 指纹和实际版本表；算法可发布部分及第三方许可文本 | 明确原始实验到底用了什么 | O8 作为外部依赖列明固定资产、取得限制及授权恢复途径；本附包不包含未明确授权的两个 native include |
| Data/Code Availability、版权/许可逐对象表与 known limits | 可审计与可重跑的能力边界是否诚实 | 若不能公开必要 O8 执行资产，明确附包只做结果复算，硬件重跑需授权依赖；不声称 fully self-contained reproduction |

现有公共历史可继续留作证据；先不执行删除或历史重写。将新附包另设版本/标签、按实际授权选入文件，可避免继续扩大未核实 O8 源的再分发。**这不自动解决旧公共提交里的版权问题**，B2 仍由实际权利人完成来源/许可核实。其他实际采用的 Ultralytics AGPL 源也不能因为未包含 O8 就被当作纯 MIT 项目；授权范围和必要许可文本仍需逐项处理。
