# IEEE Sensors Journal 投稿条件与现成数据核查

核查日期：2026-11-10。对象：YOLO26n + PYNQ-Z2 奶牛通行计数稿件。本轮仅查公开第一手资料和已有本地小型来源记录；没有训练、推理、下载新视频、提交表单、联系作者或投稿。最新用户范围：作者信息全部待补；用户只核对原视频牛/通行总数及预测计数，不承担事件时间戳或 JSON 标注。

## 1. 对实验路线的直接结论

**可把逐视频、逐方向的通行计数误差作为主终点，不必把人工时间戳和事件 F1 设为本项目的必交材料。** 本次读到的 Sensors Journal 作者指南及审稿指南没有规定必须有 timed ground truth、事件 F1、某个视频/牛只数量，或必须自行采集新视频。审稿指南实际明确的是新颖性，以及稿件完整、适合本刊。这些原则不能被改写成编辑部从未规定的定量门槛。[官方审稿指南，2025-02](https://ieee-sensors.org/wp-content/uploads/2025/03/Guide-for-SJ-Reviewers.docx.pdf)

这一评价设计有直接领域先例：CattleEyeView 的计数实验采用 MAE，其轨迹任务另报 MOT 指标。采用总数终点不等于充分证明当前方法有效；仍需在事先冻结、未参与选择方法的会话上，比较相同板卡、模型和资源条件下的计数误差与代价。是否达到新颖性及证据质量由完整结果决定。[CattleEyeView 原文 IV 节、表 III](https://arxiv.org/html/2312.08764v1)

因此，补全顺序应为：**先审核已有原片的使用历史，冻结留出会话和计数口径；用户确认原片总数；在全部既定条件下评价；补齐资源与计时证据；按最后结果写贡献。** 现成轨迹标签只作为有条件的次要验证来源。无需为了事件 F1 而让用户补造时间标签。

## 2. 官方要求、建议与本项目科学判断分别是什么

| 项目 | 经官方材料确认的性质 | 本稿处理 |
|---|---|---|
| 新颖性及主题匹配 | 接收推荐的必要条件；稿件需自足完整 | 贡献要落在视觉传感系统的观测/验证资源权衡，并用对照证明实际改善；“新型号 YOLO 移植到板卡”本身不是已证贡献。[审稿指南](https://ieee-sensors.org/wp-content/uploads/2025/03/Guide-for-SJ-Reviewers.docx.pdf) |
| 传感器方向 | 当前作者页链接的关键词包括 SYST、DATP、OPTO、APPL，其中含机器学习、基于传感数据的检测及成像传感器 | 选择与视觉传感系统相符的类别。该关键词 PDF 文件路径年份为 2017，应表述为“当前作者页仍链接的分类”，不冒称 2026 新版范围文件。[官方关键词](https://ieee-sensors.org/wp-content/uploads/2017/02/IEEE-Sensors-Journal-Editorial-Keywords.pdf) |
| 稿件与入口 | IEEE 双栏；常规稿通常不超过 8 页；图形摘要为必需；通过作者门户提交 | 完稿 PDF、可编辑源文件及图形摘要一并预备；不把工作稿框图占位当成已完成图形摘要。[作者指南](https://ieee-sensors.org/ieee-sensors-journal/for-authors/) |
| 收费 | 当前页：OA 可选 US$2,800；非 OA 的 US$110/页为自愿；常规稿超过 8 个出版页为强制 US$175/页 | 目前按约 8 页准备。费用是提交前再核的行政项，不依据本轮工作代作者作支付选择。[作者指南](https://ieee-sensors.org/ieee-sensors-journal/for-authors/) |
| 作者及 ORCID | IEEE 作者工具页要求所有作者具备 ORCID | 所有姓名、单位、排序、通信作者、邮箱、ORCID、贡献和经费保持待作者提供；不能从已有文件名推断。[IEEE 作者工具](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/) |
| AI 披露 | AI 产生的文章文本、图、代码等须在 Acknowledgments 识别系统、涉及章节和使用程度；纯语法编辑通常不在强制范围 | 据真实用途准备披露记录。已有架构、分析、代码和正文起草辅助不能统称为只润色语法。[IEEE 投稿政策](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/) |
| 动物研究说明 | 报告涉及动物的研究须说明伦理监督机构，或解释为何未进行相应审查 | 本研究若只二次使用公开既有影像，就如实交代该事实及未重新接触动物；具体无需新审批的依据仍由作者/所在机构确认。不能编造豁免编号。[IEEE 投稿政策](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/) |
| 数据与代码开放 | IEEE 明确鼓励共享方法、数据和代码以促进可重复性 | 本次未找到 Sensors Journal 明定所有稿件必须公开全部视频或必须含 DAS 的规则。建议仍写明确的 Data/Code Availability，列第三方 DOI、受许可限制的原片和本项目可公开的配置/结果/脚本。[IEEE Research Reproducibility](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/) |
| 补充材料 | IEEE 提供分文件上传、图形摘要、视频和数据 README 规范；图形摘要须随文送审 | 可交紧凑复现材料与演示；主文自身仍需能理解贡献、协议和结果。[IEEE 补充材料指南](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/prepare-supplementary-materials/) |
| 时间标注、样本数、功耗、实拍 | 本次官方文本未把这些列成所有稿件统一的硬要求 | 是否必须取得取决于主张。声称物理摄像头系统、功耗优势或真实通行延迟，就需要对应实测；仅有文件回放则限定为相应边界。这是研究设计判断。 |

作者资格本身需要真实知识贡献、参与撰写/实质修改及批准最终稿；应由作者确认。引用和结果必须准确，失败结果不能省去后再声称全数达标。[IEEE Ethical Requirements](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/ethical-requirements/)

## 3. 用户只核对总数时，可完成怎样的论文评价

以下是**本项目建议协议，不是期刊规定**。

1. 以视频/连续会话为独立数据单元。先冻结相机、日期、文件 hash、完整评价时窗、几何区域、方向、截断规则及方法版本。固定时窗不因预测好坏而改变。同一片重放只增加系统重复性证据，不增加独立会话数。
2. 用户观看不含模型框、轨迹或预测数字的源视频，确认本时窗内完整通行总数，能分方向时分别确认两个方向。可用自然语言逐行确认，代理据此填写计数表；无需用户制作时间戳/JSON。若用户先看过预测，按实际记录复核方式，不能写成盲标。
3. 保存每片原始参考数和每种方法预测数。主报逐片误差、方向分开的绝对误差、MAE、RMSE、signed bias、完全一致的视频数/分母；若使用百分比误差，事先规定参考数为零时的处理。先逐片取绝对值再汇总，避免不同片的正负误差相消。
4. 比较 latest-frame、局部验证及候选组合方法时，在相同输入/模型下同时报告全局调用、局部调用、实际观测率、板端时间及队列。既有“不同 nominal Hz”对照不能自动解释成同调用预算的算法增益。若历史选择实际从未被采用，就不声称已验证其收益。
5. 对相同会话的配对误差给出差值；区分相机、日期和拥挤工况。不要把相关帧或重复板测当作独立样本抬高显著性。没有必要预先编造一个“期刊要求 N 头”的门槛；测试集规模及覆盖应与最后主张一起公开。

这能支持“在所测留出视频上的方向性总数误差及资源权衡”。**不能仅凭总数推出事件 precision/recall/F1、漏计概率、每头牛均正确关联，或已经证明零漏计/零重计。** 漏一次与重计一次可以得到正确总数；该识别能力边界应在讨论中说明。若未取得独立 timed GT，事件匹配公式可以留作工具说明或删去，不必保留一张无法填实的主结果表。

同样，运行日志可测“触发输出的源图到达至发布的年龄”、采集迟到、排队及处理时间；这不依赖人工事件时间。**真实动物完成通行到输出的延迟**则需要独立通行时刻，不能由触发图的时间代替。物理摄像头输运与原生 H.264 解码是否纳入，还须按实际板测边界写清。

## 4. 已有公开数据的标签与可用边界

### 4.1 CattleEyeView：场景最接近，访问与标签文件仍未取得

原文描述人工标注、资深人员复核的 14 段顶视装载通道视频，含框、track ID、计数等；按视频划训练/测试，计数以穿越区域数量和 MAE 评价。它确实比仅有静态框的数据更接近通行任务，但论文未给出本项目双区域、双向事件的逐事件表结构。[原文 III–IV 节](https://arxiv.org/html/2312.08764v1)

**旧记录须修正：该工作已是 2023 IEEE VCIP 会议论文**，作者仓库给 DOI `10.1109/VCIP59821.2023.10402676`。仓库实际仅列 README、LICENSE，Dataset and Codes 指向 Google Form。本轮没有提交表单，未取得视频或标注路径。仓库 Apache-2.0 不足以确认表单发放数据的独立条款，论文的 CC BY 也不自动覆盖数据。[作者仓库](https://github.com/AnimalEyeQ/CattleEyeView)

决定：保留作最相关文献及后备来源；本轮不要让投稿准备依赖尚未取得的文件。只有取得实际数据及条件后，才核对每视频计数定义、轨迹 ID、帧号、折返与截断规则。

### 4.2 Counting cattle / Toros：有已取得的作者修正轨迹，已经是开发资料

这是 Mendeley 数据集 `10.17632/dk54zg67dd.1`，**与 MooTrack360 是不同数据集**。发布页标 CC BY 4.0，称有 10 个视频；仅对其中一个约 15 秒视频构造逐帧 MOT 真值。标签最初经 YOLOv8/DeepSORT 辅助，随后人工修框、补漏及重分 ID，因此是发布方人工修正参考，不应称为纯算法伪标签。[官方记录及制作说明](https://data.mendeley.com/datasets/dk54zg67dd/1)

已知真实成员路径为 `Ground Truth/gt.txt` 与 `Ground Truth/Toros.mp4`；CSV 列为帧号、ID、左上角 x/y、宽/高、置信度。官方说明的“视频牛数”也不等同于本稿完整穿越的数量。[作者数据说明](https://data.mendeley.com/public-files/datasets/dk54zg67dd/files/10f85eea-c352-4e28-aee8-0f209e09f05e/file_downloaded)

已有本地证据记录 479 视频帧、1,775 行、9 个 ID 值，与发布说明的 478/1,774/8 不完全相同；按既定区域导出了 6 个完整 B→A 事件。它已多次进入模型评价和后续诊断，不可重新称为最终未见测试。`Vacas1` 已有水印来源疑问，不应因平台统一 CC BY 标记就纳入主要评价。

可复用的小文件入口：[来源与帧号约定](../counting_eval_20261026/annotations/external_sources_frozen.json)、[既有协议](../counting_eval_20261026/annotations/evaluation_protocol_v1.json)、[作者 GT 路径与转换程序](../counting_eval_20261026/tools/author_gt_audit.py)、[已有核查报告](../counting_eval_20261026/计数评估与下一步.md)。这些是当前读取的项目历史记录，本轮未重新运行旧结果。

决定：适合继续做已暴露的外部侧视压力对照，也能核查事件评分程序；不再增加最终独立会话分母，不以新标签下载作为当前主线。

### 4.3 MooTrack360：GT 可定位，但源时间、干净输入及通行任务均待准入

官方 Zenodo v1.1 列出 `TrackEval_evaluation_code.zip`（23.4 MB，MD5 `907533e4bc6398c7761b073be3fb4019`）及 `1hour_annotated_sequence.mp4`（18.9 GB）。ZIP 预览能直接辨别 `data/gt/mot_challenge/1hour/gt/gt.txt` 和同级 `seqinfo.ini`；`data/trackers/.../1hour.txt` 是已发表跟踪器输出，不能拿来充当 GT。[记录](https://zenodo.org/records/20287681)、[ZIP 目录预览](https://zenodo.org/records/20287681/preview/TrackEval_evaluation_code.zip?include_deleted=0)

项目已有这一个小型轨迹包的取得记录（SHA256 `26800ea3b6e653e4e9d7c54a2587060bd2a920b4e862f0b84afef624234b6478`），无需重复下载。此前审计记录：GT 帧 1–53,920、8 个 ID；seqinfo 标 10 fps；视频容器为 53,946 样本、约 14.985 fps。这里只重新读历史报告，未重新验远端大视频。[已有核查与风险](../counting_reference_candidates_20261027/独立计数参考候选核查.md)、[取得记录](../counting_reference_candidates_20261027/catalog/MooTrack360_TrackEval_evaluation_code.record.json)

新增冲突：WACV 2026 原文 §5 称评价序列有 59,321 帧，开始 3 头，后来 5 次入场增至 8 头，且不会离开再进入。它不能直接支持同通道双向完整穿越；不应把 8 个身份当作 8 个通行事件。本文访问 PDF 全文返回 403，以上限定为该官方 PDF 的可检索正文，未声称做过本轮视觉对齐。[WACV 原文](https://openaccess.thecvf.com/content/WACV2026/papers/Christiansen_MooTrack360_A_Novel_Fisheye_Camera_Dataset_for_Robust_Multi_Diary_WACV_2026_paper.pdf)

作者仓库声明项目使用 CC BY-NC-SA 4.0；TrackEval 工具本身的许可不自动替换数据许可。[作者仓库许可声明](https://github.com/SDU-Robotics/MooTrack360#ℹ️-license)

决定：暂不用于最终通行成绩。先解决原片/标注帧映射、帧率和版本差、是否烧录框及同源干净输入；即使解决，也主要是室内长时跟踪或入场检测的外部压力材料。

### 4.4 Cows2021：手工静态框与身份，不是独立通行标签

官方数据记录列 Detection and localisation、Identification、Weights，包含原始 `Sub-levels/Identification/Videos`，数据许可是 Non-Commercial Government Licence。作者代码说明 Identification 的训练 crop 可由原片经检测器及 `make_data` 流程生成；不能把这些生成的 tracklets 当成独立人工逐帧轨迹。[数据记录](https://data.bris.ac.uk/data/dataset/4vnrca7qw1642qlwxjadp87h7)、[原视频目录](https://data.bris.ac.uk/data/dataset/14c0b7eaafdaba4bf694eec88ba4cba2)、[作者代码说明](https://github.com/Wormgit/Cows2021)

当前稿件已用其中 6,809 张训练、1,571 张开发验证；因此“视频没跑过”不足以证明与训练来源独立。已有 source-role 日期/像素 hash 检查不能替代原片、会话和近重复审查。

决定：继续用于已经声明的检测训练/验证。没有必要为了总数主终点改用这些短片，更不能把现有图像 bin 当作独立会话标签。

### 4.5 MultiCamCows2024：本轮主线最省改动，但不能从清洗后 crop 还原完整真值

官方记录和 README 提供 7 日、3 摄像头的 137 段原始监控视频，日期为 2023-08-14 至 20；目录明确是 `MultiCamCows2024Root/videos/camera{1,2,3}/2023Aug{14..20}`。另有 101,329 张按日/身份组织的 crop。数据记录当前许可是 Non-Commercial Government Licence。[官方数据记录](https://data.bris.ac.uk/data/dataset/2inu67jru7a6821kkgehxg3cv2)、[官方小型 README](https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/readme.txt)

原文明确：先以检测器生成 5 Hz 躯干 tracklets，再人工检查完整性、去除不足 80% 可见躯干或重叠 crop，并部分手调裁剪。这对 Re-ID 有效，却**会主动删除通行评价最关心的遮挡/截断样本**；身份 crop 目录不构成全原片的完整轨迹真值。本轮未定位到独立公开的逐事件表或逐帧完整 MOT 标注。[原文 §3.2](https://arxiv.org/html/2410.12695v1)

决定：优先复用已经下载而确实未用于参数/模型选择的原片。由用户确认每片总数即可完成主参考，读取 crop 不必扩张为本轮标注任务。仍需谨慎区分“新会话”“新相机”和“新农场”；这批数据无法自称跨农场最终泛化试验。

## 5. 已有 MultiCam 原片的具体暴露边界

稿件已明确把 camera1 Aug14、camera1 Aug15、camera2 Aug19、camera2 Aug20 四片列为开发材料；不能将另一次板端重复运行当作独立测试。

当前读取的另外两个 `source_info.json` 如下，均曾用于源画面/几何检查：

| 文件 | 记录内的实际元数据 | 当前可称谓 |
|---|---|---|
| `2023-08-18T12-53-40.mp4` | 2560×1440；25 fps；11,160 解码帧；末 PTS 446.365 s；260,538,408 B；SHA256 `a31cb079cd2423ccaa0265d599d6d6201cb14f7646aadd4c1ce17dafbd0cda9d` | `SOURCE_CALIBRATION_ONLY`，model forwards=0；不是完全未见 |
| `2023-08-16T12-52-13.mp4` | 2560×1440；25 fps；17,107 解码帧；末 PTS 684.248 s；260,833,320 B；SHA256 `92eca11ad61c0d1a2797fc3a87d85942bb893ba4f30592968a6e52629920bc12` | `SOURCE_CALIBRATION_ONLY`，model forwards=0；已有 dense source review 的部分另有暴露 |

元数据直接来自 [Aug18 source_info](../offline_counting_20261031/r5/calibration/source_2023-08-18T12-53-40/source_info.json) 与 [Aug16 source_info](../offline_counting_20261031/r5/calibration/source_2023-08-16T12-52-13/source_info.json)。它们可以诚实作为“未跑模型但已做场景校准的前瞻性比较/新会话检查”，不应贴“完全未见、独立最终测试”的标签。若后续冻结后对其评价，再把结果用于改配置，它们也将进入开发资料。

**截至本文件落盘，尚未仅凭本地记录确认某一个具体 MP4 是“已经下载且完全未暴露”。** 官方确有 camera1/2 的 Aug17、其他时段等候选目录，但目录存在不证明本项目未读过、未跑过或已经下载。主流程正在核对服务器实际库存和暴露清单，精确候选应由该现状审计产生；本文件不凭日期猜一个测试集。

## 6. 最接近的其他公开标签来源及为何不扩张本轮

| 来源 | 可核查的现成标注/路径 | 对当前实验的决定 |
|---|---|---|
| AutoCattlogger，Purdue | 原论文介绍人工记录过镜牛 ID 顺序；作者代码使用 `sampleVideos1/sampleVideos1_gtLabels_inOrder.csv`、`sampleVideos2/sampleVideos2_gtLabels_inOrder.csv`，列名 `CowID`。[论文](https://doi.org/10.1016/j.atech.2025.101561)、[作者代码](https://github.com/VADL-Purdue/AutoCattlogger) | 公开 data/readme 实际提供的是两个日期的**每段通常只有一头牛的 cut-videos**，不是论文全部连续小时原片；并提示边缘可能有额外牛。本轮未下载 tar、未读取 CSV 实物，也未确认数据独立许可，不能把代码 Apache-2.0 当成数据条款。可作后备，不能当成已经取得的拥挤通道留出。[数据 README](https://github.com/VADL-Purdue/AutoCattlogger/blob/main/data/readme.md) |
| MmCows，Purdue | `visual_data.zip`（约 20 GB）含 7/25 的 15 秒采样图/ID 框；格式 `[cow_id,x,y,w,h]`，标准化至 4480×2800；有 Unix 时间及相机目录。原始 VIA JSON 需另请求。[作者仓库](https://github.com/neis-lab/mmcows) | 手工身份框确实存在，但稀疏静态标注、牛舍运动与当前完整通道任务不同；1 秒原始视觉资料又大得多。本轮无需再下载；不以 15 秒间隔的跨线次数当作完整通行真值。数据和代码许可仍要分别核，不沿用仓库 MIT 推定数据。 |

没有将合成 MOO 多视角身份图、仅身份 crop 或网络模型输出加入“现成独立通行真值”的清单。

## 7. 数据许可、图像再用和可复现交付

- Cows2021 与 MultiCamCows2024 的官方记录都链接 NCGL v2.0。应保留各自数据 DOI、提供者、原始许可链接及来源文件名。该许可限制为非商业使用并要求来源署名等条件；不能将它们随本项目代码改标 MIT/AGPL，也不能将文章 OA 许可当成原片再授权。[NCGL v2.0 官方文本](https://www.nationalarchives.gov.uk/doc/non-commercial-government-licence/version/2/)
- Toros 为发布平台 CC BY 4.0，但 `Vacas1` 的源画面水印问题仍是项目已经发现的具体来源异常，暂不纳入主要实验和论文再用图。MooTrack 为作者仓库声明 CC BY-NC-SA；CattleEyeView 发放数据条款尚未取得。
- 可公开本项目的总数确认表、预测计数表、来源/hash 清单、固定配置、计时及调用日志、统计与重算脚本，原视频继续指向原发布方。示例帧、视频片段和可能的衍生标注应逐项注明来源与许可；是否可直接放入论文/补充包，需按实际再用方式核对，不能一律认定公开下载即允许任意再分发。IEEE 要求作者在必要时于投稿前取得第三方同意。[IEEE Recycling Content 政策](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/)
- 建议可用性声明明确分三类：第三方公开原数据及其限制；本项目可公开的小型复现材料及位置；尚未发布的板端原始 payload。正式上传位置/DOI 尚未形成时保留待补，不写“all data are publicly available”。[IEEE 可重复性指导](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/)

## 8. 投稿前的最小证据门槛

这些是**针对当前稿件主张的项目门槛**，不伪称编辑部的硬性清单。

| 门槛 | 可以具体交付的结果 | 不能用什么代替 |
|---|---|---|
| 原创问题可检验 | 冻结主比较及其资源限制；把条件局部验证与 latest-frame 等对照写清 | 仅有模型版本、板端跑通或总数开发调参 |
| 总数参考可追溯 | 用户确认的原片/时窗/方向总数，含复核方式和争议状态 | 用算法轨迹反推原片真值；只数完全看得见的容易片段 |
| 数据角色诚实 | 训练、校准、开发、前瞻性会话、最终留出来源账本；不隐去 Aug20 已进入开发 | 将新运行编号当作新独立样本；把已做几何校准片称完全未见 |
| 计数主结果闭合 | 各片参考/预测、绝对误差、MAE 等，与固定控制条件和失败一起报告 | 用累计总数一致代替逐片误差；只保留成功重复 |
| 资源/时序主张有实测 | 同模型输入条件下的调用、队列、板端分阶段/端到端计时；真实观测率和所有越限 | 目标 Hz、桌面 FPS、软件测试数、FPGA 规格或静态配置 |
| 附件和来源完整 | 原始来源、许可证、方法代码、图表可重算和最终 PDF/图形摘要核查 | 私有 payload 存在或脚本退出码就称公开可复现 |
| 行政信息就绪 | 作者、单位、ORCID、贡献/经费/利益冲突、伦理说明、AI 披露、真实通信作者确认 | 自动猜测；用户未提供时继续保留待补 |

当前可直接推进的是计数终点的留出方案和完整稿件的证据映射。逐事件 JSON 不再是当前范围内的必需条件。最终结果若不能支持最初机制假设，应改写为真实得到的比较结论；不通过增加免责声明或隐去失败把未证贡献包装成成功。

## 9. 本次访问和证据边界

官方作者页、审稿指南、IEEE AI/伦理/作者资格/可重复性/补充材料页面均已重新读取。Bristol 的 `data.bristol.ac.uk` 入口出现超时，出版方正式链接的 `data.bris.ac.uk` 记录、README 与相应子目录可读。CattleEyeView 仓库和 arXiv 原文可读，未执行 Form。MooTrack Zenodo 记录/ZIP 预览可读，WACV PDF 全文请求为 403，帧数及入场描述来自官方文档的检索索引；本轮未下载或视觉核对该大视频。NCGL v2.0 官方正文直接访问为 403，许可条款核查来自同一官方页面的可检索文本。

项目历史报告和小型 JSON 均按记录本身的证据等级使用；没有把本轮阅读旧审计变成重新实测。未使用相关旧个人记忆作为当前来源。本次仅新增此 Markdown 文件。

## 10. 补充：同一数据集 camera2 / Aug17 的具体留出候选

补充核查时间：2026-11-10 15:14（Asia/Shanghai）。主流程已实查服务器库存：R5 的三个 camera1 原片（Aug15、16、18）及核心四片均已暴露。以下内容更新第 5 节“精确候选尚未确认”的状态：**可以在既有 MultiCamCows2024 数据集内，按文件时间顺序预先指定 camera2 的 Aug17 最早原片作为新的候选；本轮仍未下载视频。**

### 10.1 官方直链与文件头

[官方 camera2 / 2023Aug17 目录](https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera2/2023Aug17/) 的常规 HTTP GET 返回 200，实际读取 1,760 字节 HTML，列出以下 4 个文件。网页读取工具访问该目录失败后，使用标准 Python `urllib` 读取同一个公开目录成功，未登录、未使用凭据。随后仅作 HTTP HEAD，4 个文件均返回 200、`Content-Type: video/mp4`、`Accept-Ranges: bytes`；**没有读取任何视频响应体、MP4 容器索引或图像帧**。

| 原片及官方直链 | 官方目录与 HEAD 一致的大小 / bytes | HTTP Last-Modified（UTC） | HEAD ETag |
|---|---:|---|---|
| **[2023-08-17T12-49-53.mp4](https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera2/2023Aug17/2023-08-17T12-49-53.mp4)** | **260,571,176** | 2023-08-17 18:37:24 | `64de68e4-f880028` |
| [2023-08-17T13-13-24.mp4](https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera2/2023Aug17/2023-08-17T13-13-24.mp4) | 260,456,488 | 2023-08-17 18:38:12 | `64de6914-f864028` |
| [2023-08-17T13-34-34.mp4](https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera2/2023Aug17/2023-08-17T13-34-34.mp4) | 260,620,328 | 2023-08-17 18:39:04 | `64de6948-f88c028` |
| [2023-08-17T13-55-15.mp4](https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera2/2023Aug17/2023-08-17T13-55-15.mp4) | 260,112,424 | 2023-08-17 18:39:51 | `64de6977-f810028` |

**建议固定第一行的 `12-49-53`，理由仅为 camera2/Aug17 的最早文件，未查看牛数或任何预测。** 其余三行是目录完整性记录和事先可规定的后备顺序，不建议看到模型表现后才择优换片。

官方原文对这一批监控资料声明原生采集为 HikVision DS-2CD5546G0-IZHS、25 FPS、2560×1440、机内 MP4 编码；这属于**数据集层面的采集说明**，尚未在上述具体 MP4 上由容器/解码实查确认。目录/HEAD 不提供每片真实时长、帧数、PTS、视频 codec 或 SHA256；不能据相邻文件名间隔推定视频时长，也不能把 ETag 当成内容 hash。文件名时间没有在此次目录中附时区，不能与 HTTP 修改时间混为采集时间。[原文 §3.1](https://arxiv.org/html/2410.12695v1)

### 10.2 本地暴露核查：看过目录，未找到此原片内容或计数调参记录

本轮用 `rg` 检索 `C:\Users\Donson\Documents\ChatGPT\奶牛` 和本地 Cowyolo26 仓库内的 JSON/JSONL、CSV、Markdown、Python、YAML、TXT、HTML、LOG（每文件不超过 4 MiB，排除 .git、node_modules、vendor 和本轮新增审查目录）。检索四个完整 MP4 basename，以及 `camera2/2023Aug17`、`camera2_aug17` 等路径/标识写法。结果如下：

- **四个完整 MP4 basename 均无命中**；没有找到对应预测计数、运行 summary、人工总数、源图抽样或下载 manifest。
- `camera2/2023Aug17/` 只命中以前抓取的 **camera2 根目录链接**，以及完整数据归档中央目录内该日期的 `.header.html` / `.footer.html` 元数据项。`initial_sources.json` 中对应记录名为 `mc_camera2`，指向 camera2 根目录，200、2,167 字节；这是目录抓取，不是原片内容读取。[既有目录抓取记录](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/server/phase2/catalog/initial_sources.json)、[归档目录元数据](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/research/identity_source_provenance_20261029/evidence/zip_directory/non_image_video_members.json)
- 已有 `aug17_input_functional_only`、普通俯视长视频筛选及后续四模型回放，对应的是 **camera1** 的 `2023-08-17T12-54-41.mp4`、`13-25-38` 等。旧报告明确 camera1 的最早片已完整取得并概览，其他文件亦做过源图筛选；不能仅因“Aug17”字样就误认 camera2 的这四片已被跑过。[既有 camera1 选择说明](C:/Users/Donson/Documents/Codex/exports/Cowyolo26-20261031/repo/docs/research/overhead_long_session_20261028/普通俯视长视频筛选与下一步.md)、[功能运行 summary](../offline_counting_20261031/runs/other_video_functional/summary.json)

因此，合适的来源角色描述是：**“此前已编入公开目录，当前本地记录未发现内容读取、计数核对或模型/阈值选择暴露的 camera2 Aug17 视频候选。”** 本地文本无命中不构成对所有远端历史的绝对证明；主流程的实机/服务器库存与任务日志审查应一并保留。它来自同一牧场、同一牛群与已知 camera2；而同日 camera1 已被观察，故不可声称新农场、完全未见日期或完全独立的动物群体。当前检测器使用 Cows2021 的训练来源和任何辅助身份模型的数据使用仍分别记录，不能以这个新视频留出暗示整个系统从未接触该场景。

### 10.3 与“用户只确认总数”相容的冻结方式

可以在任何新预测前保存：上面首个原片的 URL/文件身份、相机和日期、固定原生相对 PTS 时窗 `0 ≤ t < 120 s`、**现有 camera2 几何及计数规则**、候选权重/程序/config hash、比较条件及资源预算。后续取得文件再校验实际字节和 SHA256，核查容器时基与解码完整性；这个技术准入不需要用户提供额外标注。

用户只需对冻结的这 120 秒原片确认完整通行总数，能分方向则分别确认；代理记录确认文字与审核方式即可。不要在此要求事件 JSON、事件时间戳或新采集。若几何不适用而必须改变，明确转为几何校准/开发材料，再另冻结评价。若该时窗无完整通行，仍保留零通行结果作为阴性输入检查，不把它解释为非零通行泛化证据；如需继续覆盖，先规定后续原片/时窗选择规则，再查看预测。

这一材料选择仅扩展**同一公开数据集内的新视频会话比较**。最终可报告的主结果仍是逐片/方向总数误差、实际调用与板端计时；不增添事件级准确率、独立农场泛化或真实传感器端到端延迟主张。
