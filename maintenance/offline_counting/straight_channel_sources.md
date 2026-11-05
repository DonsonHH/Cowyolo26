# 直通道来源核查：CattleEyeView

核查日期：2026-11-01（Asia/Shanghai）。本次为第一方资料、论文原图和小范围标签元数据核查；没有训练、模型推理、连接 PYNQ-Z2、提交表单或联系作者。核查开始时本地仓库为干净的 `667b652c`。本文件只评估来源准入，不调整已经冻结失败的 Purdue 6/9。

**结论：CattleEyeView 的实体栏道符合“笔直、狭窄、顶部相机”的候选几何，但当前不能作为已取得的完整通行计数测试集。** 已实看论文原图，不能把标题当几何证据；已找到同作者公开的图像标签子集，但仍未取得可配对的原始连续视频、FPS、完整轨迹和事件参考。状态为 `geometry_promising / original_video_not_obtained / full_event_gt_pending_verification`。

## 1. 实际视角与通道几何

| 项目 | 本次证据 | 判断与边界 |
| --- | --- | --- |
| 相机 | 论文 III-A 明示顶部 RGB CCTV、安装高度 3.7 m；Fig.1 展示安装实物。[论文 III-A](https://arxiv.org/html/2312.08764v1) · [Fig.1 原图](https://arxiv.org/html/2312.08764v1/image/camera.png) | **作者事实**：普通 RGB 视频来源，属于顶部视角；不是深度或热成像数据。相机内参、焦距及标定未取得。 |
| 实体栏道 | Fig.1 标注长 3.0 m、宽 0.81 m；Fig.2 实拍中牛沿两侧栏杆间的直段移动。[Fig.1](https://arxiv.org/html/2312.08764v1/image/camera.png) · [Fig.2](https://arxiv.org/html/2312.08764v1/image/scenes.png) | **图示事实与观察**：实体装载通道为直、窄的单列通道。这些是图中所标通道段尺寸，不能自动当整个牧场动线或精确可用视野尺寸。 |
| 镜头几何 | Fig.2/5 的栏杆在画面上下边缘明显弯曲。[Fig.2](https://arxiv.org/html/2312.08764v1/image/scenes.png) · [Fig.5](https://arxiv.org/html/2312.08764v1/image/tracking.png) | **视觉观察**：存在明显广角/桶形表现。不能称为无畸变正射相机，也不能仅据图确认具体镜头类型；实体栏道直与图像中栏杆弯曲需分开。 |
| 完整身体与遮挡 | Fig.2 同时显示整牛及左右边缘的半身牛；Fig.5 后部示例有贴靠/骑跨重叠。[Fig.2](https://arxiv.org/html/2312.08764v1/image/scenes.png) · [Fig.5](https://arxiv.org/html/2312.08764v1/image/tracking.png) | **视觉观察**：适合研究通道通行，但不是没有遮挡的理想单牛画面。不能由静态示例认领任一条完整通行或确定序列端点。 |

因此，它值得保留为直栏道候选。是否比既有数据更容易检测、跟踪或计数，尚没有本项目实测证据；也不能从几何适配推导板端速度、输入分辨率或准确率。

## 2. 连续性、帧号与标注口径

| 必查项 | 已确认 | 尚缺证据 |
| --- | --- | --- |
| 视频还是独立图像 | 作者称 14 个视频序列、30,703 帧、753 个不同牛实例，并按视频划分训练/测试。[作者 README](https://github.com/AnimalEyeQ/CattleEyeView/blob/main/README.md) · [论文 III-IV](https://arxiv.org/html/2312.08764v1) | 未取得原视频或帧清单，不能确认发布包是否保留全部相邻原帧、是否重编码/抽帧、是否存在剪切与缺帧。 |
| FPS 与原始编号 | 同作者 mtYOLO 配置写 `imgsz: [1920, 1080]`，公开标签文件名含 `10_00142.txt` 等数字后缀。[固定版本配置](https://github.com/AnimalEyeQ/mtYOLO/blob/bb52cfa7ab5f2e040949886950812b4ce3312ef0/config/dataset/cattleeyeview_multitask.yaml) | 这是作者配置和文件命名，不能冒充实际视频容器尺寸、FPS 或时间戳映射。论文正文、已读配置和标签目录未给出可核验 FPS；没有 `seqinfo.ini` 或原片映射表。 |
| 人工框与 MOT ID | 论文说明人工标注并由更资深标注员复核，包含身体/头部框、tracking ID 以及通过 ramp 的牛数。[论文 III-A/C](https://arxiv.org/html/2312.08764v1) | 论文声明不等于实际文件覆盖检查。原始轨迹文件、ID 生命周期、遮挡/画外续接、逐帧覆盖以及 MOTChallenge 文件格式均未取得。 |
| 完整通行计数 | 作者定义为越过预设区域的牛数，并指出来回跨线会重复计数。[论文 III-C、IV](https://arxiv.org/html/2312.08764v1) | 未取得作者区域、逐事件起止帧、方向、回头去重和视频首尾截断规则。不能直接与本项目“完整 A→B / B→A 通行”等同。 |

**753 是作者称的不同牛实例数，不是已经核实的 753 次完整通行。** 总实例数、逐视频动物数、越区次数和有方向的完整通行事件必须分别记录；本次没有产生新的事件分母或计数成绩。

## 3. 下载入口：原始数据仍未取得

通过 GitHub connector 重新读取作者仓库完整树，`truncated=false`，树 SHA 为 `32e8008e328567d644306a408d3d18ce73f960a4`，只有 `LICENSE` 和 `README.md`；公开 releases 和 issues 列表均为空。README 的两处 Dataset and Codes 链接都指向同一 Google 表单。[完整树 API](https://api.github.com/repos/AnimalEyeQ/CattleEyeView/git/trees/main?recursive=1) · [releases API](https://api.github.com/repos/AnimalEyeQ/CattleEyeView/releases) · [README](https://github.com/AnimalEyeQ/CattleEyeView/blob/main/README.md)

本轮实查：短链可重定向到下列完整表单地址，但本机 Python 对 `docs.google.com` 连接超时；网页读取工具也未能打开。没有读取表单字段或提交后页面，所以**不能断言它必需人工审批、填写即可立即下载，或数据已永久下线**。可确认的当前状态是：已检查的公开第一方入口没有提供本轮可直接取得的原视频/原始 MOT/计数包。

- [作者表单短链](https://forms.gle/KGf3dmEjPX9qwVz49)
- [短链实际重定向的表单](https://docs.google.com/forms/d/e/1FAIpQLSdLffqnj7sC7qXHMUpcu_E7GZLDYGaEMutCHbr3v_kghlmP3w/viewform?usp=send_form)

原视频整包字节数、单序列大小、原视频/GT 是否可分别下载、是否支持 Range、原数据使用条件：均为 `pending_verification`。作者代码仓库的 Apache-2.0 标识不单独证明未取得的视频包具有相同授权。

这一访问缺口已在本仓库 [2026-10-27 核查](../../docs/research/counting_reference_candidates_20261027/独立计数参考候选核查.md) 和 [2026-10-30 来源准入](../../docs/research/external_sources_20261030/公开俯视数据来源与准入结论.md) 中记录。旧理由主要是实际数据与事件口径未取得，并非已经证明实体通道不够直；本次补充了原图几何证据和下节公开标签发现。

## 4. 新发现：同作者 mtYOLO 有公开标签，但不能替代连续计数 GT

同一作者团队的 [mtYOLO README](https://github.com/AnimalEyeQ/mtYOLO/blob/bb52cfa7ab5f2e040949886950812b4ce3312ef0/README.md) 将 CattleEyeView 图像下载继续指向原仓库，同时公开了三份标签 ZIP。下列大小来自 [作者目录 API](https://api.github.com/repos/AnimalEyeQ/mtYOLO/contents/data/CattleEyeView?ref=bb52cfa7ab5f2e040949886950812b4ce3312ef0)。固定核查版本为 `bb52cfa7ab5f2e040949886950812b4ce3312ef0`。

| 作者标签包 | 字节数 | 本轮读取范围 |
| --- | ---: | --- |
| `labels_cattleeyeview_multitask.zip` | 30,026,434 | HTTP Range 实读 ZIP 尾部、完整中央目录和 3 个 TXT，不下载整包 |
| `labels_cattleeyeview_pose.zip` | 3,018,998 | 只读 GitHub 文件元数据，未读取 ZIP 内容 |
| `labels_cattleeyeview_segment.zip` | 27,988,444 | 只读 GitHub 文件元数据，未读取 ZIP 内容 |

对 multitask ZIP 的独立目录复算结果：6,294 个目录项，其中 3 个目录、**6,291 个 TXT**，`train=5,056`、`val=1,235`，没有视频、图片、轨迹表、计数表或序列配置文件。文件名编号存在大量空洞，不能作为已经连续标注的原片序列。

| split | 文件名前缀 | TXT 数 | 数字后缀最小-最大 |
| --- | ---: | ---: | --- |
| train | 01 | 477 | 28-1159 |
| train | 02 | 609 | 50-2320 |
| train | 03 | 465 | 76-1748 |
| train | 04 | 553 | 26-4123 |
| train | 05 | 444 | 59-1721 |
| train | 06 | 1270 | 6-2962 |
| train | 08 | 1 | 739-739 |
| train | 09 | 1 | 127-127 |
| train | 14 | 1236 | 120-4339 |
| val | 10 | 259 | 142-1433 |
| val | 11 | 257 | 1308-3354 |
| val | 12 | 229 | 87-896 |
| val | 13 | 490 | 105-1326 |

这只是**该公开 multitask ZIP**的目录事实，不据此推断原始 CattleEyeView 数据漏标。数字后缀是否对应原视频从 0/1 开始的帧号仍待映射证据。例如 `10_00148` 后接 `10_00153`，不能把文件顺序压成无缺口视频。

已实际解压 `labels/train/01_00051.txt`、`labels/val/10_00142.txt`、`labels/val/10_00143.txt`，均核对 ZIP CRC32。前者 2 行，后两者各 1 行。结合 [作者标签解析器 L105-L150](https://github.com/AnimalEyeQ/mtYOLO/blob/bb52cfa7ab5f2e040949886950812b4ce3312ef0/ultralytics/ultralytics/data/utils.py#L105-L150) 和 `kpt_shape: [24, 3]` 配置，可确认该格式为：

`class, bbox(cx,cy,w,h), 24×(x,y,visibility), segmentation polygon(x,y,...)`

这里首列 `0` 是配置中的 `cow` 类别，**不是牛的 tracking ID**。该格式没有单独的跨帧 ID、时间戳、方向或完整通行事件列。三个样本也不能证明所有 TXT 的人工覆盖质量。它可以作为进一步核查图像检测/姿态/分割标注的入口，当前不能独立承担通行计数验证。

### 小范围读取的可复查信息

- 已核对 HTTP `206` 及精确 `Content-Range`，文件总长为 `30026434`。
- 固定版本中央目录：`bytes=29380644-30026411`，645,768 字节，SHA-256 `b414bee13ba5d126c3321d4b762104d741a885309375ccca8fef170763167d19`。
- 固定版本复核（目录、3 份 TXT 的本地头和压缩载荷）合计读取 657,838 字节；此前 main 分支探测另读 714,555 字节。未请求视频像素。
- 样本解压内容 SHA-256：`01_00051.txt` 为 `8ae1e56f6df8dfe6abffcffa356c1cc06fa142724e0b45f6487ace4bae0c39ee`；`10_00142.txt` 为 `f5f32d908966a5d5564927bc2226e395c6e88daf6091aff238235d284be17a7e`；`10_00143.txt` 为 `b18e40f6380b236e1fd17d2b488a991088772f14f751b259bb44615b0d104a30`。
- 几何视觉核查读取的是作者论文 Fig.1/2/3/5 原图，保存在系统临时目录用于查看；没有把论文示例当原始连续视频。

## 5. 公开、非签名原始 URL

以下链接可以直接 GET 论文图或标签 ZIP，**其中没有可直接使用的原始连续视频地址**。本轮只实读 multitask ZIP 的小范围；pose/segment 仅核实官方目录列有对应公开 URL。

- [论文 Fig.1 相机与栏道尺寸 PNG](https://arxiv.org/html/2312.08764v1/image/camera.png)
- [论文 Fig.2 顶部通道样例 PNG](https://arxiv.org/html/2312.08764v1/image/scenes.png)
- [论文 Fig.3 人工标注示例 PNG](https://arxiv.org/html/2312.08764v1/image/annot.png)
- [论文 Fig.5 时序示例 PNG](https://arxiv.org/html/2312.08764v1/image/tracking.png)
- [固定版本 multitask 标签 ZIP，30,026,434 B](https://raw.githubusercontent.com/AnimalEyeQ/mtYOLO/bb52cfa7ab5f2e040949886950812b4ce3312ef0/data/CattleEyeView/labels_cattleeyeview_multitask.zip)
- [固定版本 pose 标签 ZIP，3,018,998 B](https://raw.githubusercontent.com/AnimalEyeQ/mtYOLO/bb52cfa7ab5f2e040949886950812b4ce3312ef0/data/CattleEyeView/labels_cattleeyeview_pose.zip)
- [固定版本 segment 标签 ZIP，27,988,444 B](https://raw.githubusercontent.com/AnimalEyeQ/mtYOLO/bb52cfa7ab5f2e040949886950812b4ce3312ef0/data/CattleEyeView/labels_cattleeyeview_segment.zip)

**本项目当前准入决定：保留候选，暂不用于新的完整通行主测试。** 若以后取得原片，应先核容器 FPS/帧数、实际帧映射、完整 GT 与许可，再固定区域、方向、折返和首尾截断规则；这一步完成前，不把 753、6,291 或 30,703 当作通行事件数。

## 6. 补查 Arazo 等（2022）跛行视频：明确私有，未找到原始 top RGB 公开下载

核查对象仅限 *Segmentation Enhanced Lameness Detection in Dairy Cows from RGB and Depth Video*，arXiv `2206.04449`；没有扩展到其他跛行数据集。**当前排除为可直接取得的替代测试源：作者原文在引言和结论均明确称其为 “proprietary dataset”，本轮未找到公开原始 top-view RGB 视频、单片直链或计数 GT。** 这比“搜索没有结果”有更直接的私有数据证据。[论文引言与结论](https://arxiv.org/html/2206.04449)

| 核查项 | 一手证据与结论 |
| --- | --- |
| 数据性质 | 原文采集说明在 **Section 3（Dataset and task）**；Section 4.1 是划分协议。D435 + Raspberry Pi 4b、30 fps、640×480，RFID 触发前 7 秒/后 3 秒记录；标注部分含 864 个 top 片段、116 头不同牛，并过滤多牛/农场人员片段。这些是作者报告，未获容器文件复核。[原文 Section 3、Table 1](https://arxiv.org/html/2206.04449) |
| 原视频公开性 | 已读完整原文、作者本人主页的该论文条目、DCU 官方机构托管记录。主页仅链论文；DCU Documents 只列 PDF，没有视频或数据附件。GitHub connector 对 `lameness user:EricArazo` 和精确短标题检索均无匹配仓库，未取得该论文的作者数据发布库。[作者主页条目源码](https://github.com/EricArazo/EricArazo.github.io/blob/master/index.html) · [DCU 官方记录](https://doras.dcu.ie/27302/) |
| 单片下载与大小 | **没有可核实的原始 top RGB 单片或整包 URL**，因而单片字节数、整包体量、Range/分片能力和许可均未核实。公开论文 PDF 或示例 PNG 不能计入已取得视频数量。未申请、联系作者或尝试登录私人托管。 |
| 直窄通道与裁切 | 已实际查看 Fig.3 原始 PNG：下排左侧 top RGB 是窄直栏道，但该帧的牛后躯在左边缘截断。静态例图不能证明任一原始片段完整展示头尾通过区域，也不能证明比 Cows2021 更适合完整事件。[Fig.3 原图](https://arxiv.org/html/2206.04449v1/inputs.png) |
| 标注是否支持计数 | 作者标的是片段级跛行分数；分割训练另用每视角 250 张图的半自动掩膜。未见可用的完整轨迹 ID/逐事件计数发布包。[原文 Section 3、4.2](https://arxiv.org/html/2206.04449) **推断**：RFID 固定时间窗和单牛清洗不保证完整通行，更不保留相邻牛、多牛、漏触发或连续流量的完整分母；864 不能直接当作 864 次合格通行。 |

本轮可公开直接读取的第一方 URL：

- [arXiv 原文 HTML](https://arxiv.org/html/2206.04449)
- [DCU 官方论文 PDF 直链（不是视频）](https://doras.dcu.ie/27302/1/2022_CV4Animals_CVPRw_Lameness_detection.pdf)
- [论文 Fig.3 原始输入示例 PNG（不是视频）](https://arxiv.org/html/2206.04449v1/inputs.png)，本次 GET 为 HTTP 200，619,698 B；SHA-256 `805894525cd1bce47fcb32c919725e7192d7d2a9dac014dfeb4afc56c076a844`。

状态：`author_declared_proprietary / no_public_original_video_url_found / no_counting_gt_obtained`。私有性质是原文事实；“未找到公开原视频”限定为本轮已检查的第一方入口，不扩大成对未来发布的断言。本轮新增模型执行数为 0。

## 7. 补查 Winkler/Boucheron Criollo RGB-D：原始 bag 公开，连续多头主验收未准入

核查对象为 [Dryad DOI `10.5061/dryad.tqjq2bw4s`](https://datadryad.org/dataset/doi:10.5061/dryad.tqjq2bw4s) 及其 [Zenodo 官方记录 `8108223`](https://zenodo.org/records/8108223)。本轮只读官方 README、网页/目录和 ZIP 元数据；没有下载 34 GB 包、bag 载荷或 DGE 图包，也未安装依赖、解码视频或运行模型。

**决定：可公开取得原始 RGB-D bag，但当前只保留辅助候选，不准入“30–120 秒连续真实画面、多头完整通过、直窄通道”的主验收。** 现有证据是按牛保存的记录，部分为站立、部分为行走；未证明任何单 bag 含符合新门槛的连续多头完整通行。不能拼接多个单牛记录凑主验收长度，也不能用字节数猜时长。

### 官方说明与尚缺证据

| 项目 | 已核实事实 | 适用范围与缺口 |
| --- | --- | --- |
| 是否原始 RGB | 官方 Methods 称 D435i 采集的未过滤/未处理 rosbag，含 RGB 和 depth；多数 640×480，少数 848×480。[Dryad Methods](https://datadryad.org/dataset/doi:10.5061/dryad.tqjq2bw4s) | 可以寻找真实 RGB 输入。`Total_sorted_DGE_images.zip` 是处理后的 depth/grayscale/edge 图，不能代替原始 RGB 视频。 |
| 站立还是行走 | 官方 Methods 称约 1/3 站在 lane，其余无阻碍地走过 lane；并说明站立与行走文件命名。[Dryad Methods](https://datadryad.org/dataset/doi:10.5061/dryad.tqjq2bw4s) | 行走不自动等于完整头尾通行，更不保证连续多头或某个时长。 |
| 分段与身份命名 | README 按 class、cow sequence/eartag 保存；同日重复记录另有单数字 take 后缀，提取成图后身份信息会丢失。[官方 README](https://zenodo.org/records/8108223/files/README.md?download=1) | 文件名中的编号需按作者口径解读，不能直接当跨序列永久 ID；不同 take 也不能拼成连续事件。 |
| 正上方、直窄与全身视野 | README/Methods 写 lane，但本轮论文采集示意未完成视觉核查：出版社全文请求 403、原图请求遇到 DNS 失败。作者论文的 [第一方出版记录](https://www.ars.usda.gov/research/publications/publication/?seqNo115=413126) 确认论文与数据团队对应。 | **待核实**：RGB 是否严格正上方、具体栏道几何、整牛及首尾边界。未拿 lane 一词当视角/几何实证，也未据此宣称比 Cows2021 更好。 |
| 时长、FPS与事件 GT | 已读 README/发布页和 ZIP 目录没有每 bag 时长、可复核 FPS、完整通行区或事件表；标签为 BCS 分类。[官方 README](https://zenodo.org/records/8108223/files/README.md?download=1) · [作者项目说明](https://github.com/zwinkler/Automated-BCS/blob/main/README.md) | 原始 bag 内时间与帧信息尚未读取。尚无独立计数参考，不能将文件数当通过牛数；当前主验收证据不足。 |

### 整包与单成员获取：已实读元数据，不需先下 34 GB

公开的原始 ZIP 文件地址为 [Unfiltered_bag_files.zip](https://zenodo.org/records/8108223/files/Unfiltered_bag_files.zip?download=1)。本轮正常 GET 的 `Range: bytes=-65536` 返回 HTTP `206`，`Content-Range: bytes 34337635812-34337701347/34337701348`；因此已实证总长 **34,337,701,348 B** 且支持小范围读取。发布页列出的整包 MD5 为 `63eaa613ee8fd5e78ddc8d3d0c6baafb`，本轮未下载整包，**没有验证这个整包 MD5**。

本轮另以 `bytes=34337680606-34337701249` 成功读取 20,644 B 完整 ZIP64 中央目录。两次成功 ZIP 元数据响应合计 **86,180 B**；中间一次 DNS 失败未读文件内容。目录 SHA-256 为 `ae8528274097733fbcf0f2a9f389c6dd7fa0a02beb453a382e12652ffca3a733`。

独立目录复算：162 项 = 6 个目录 + **156 个 bag**；BCS 目录 `2/3/4/5/6` 分别有 `6/20/54/51/25` 个 bag。155 个使用 DEFLATE（ZIP method 8），一个空 bag 为 method 0；目录中没有独立 GT/事件表。该文件数是档案成员数，不是事件数。

| 可供以后单成员检查的候选 | 解压后 B | ZIP 压缩载荷 B | 本地 ZIP 头偏移 | CRC32（目录记录，未验载荷） |
| --- | ---: | ---: | ---: | --- |
| `Unfiltered_bag_files/5/Cow_24_7022.bag` | 88,700,999 | 72,964,492 | 23,498,921,504 | `ed9e3b63` |
| `Unfiltered_bag_files/4/Cow_35_1044.bag` | 92,893,771 | 76,076,906 | 13,101,334,652 | `addc865c` |
| `Unfiltered_bag_files/3/Cow_33_3008.bag` | 96,406,851 | 79,188,957 | 4,598,559,124 | `9a3ff5da` |

这三份文件名符合官方行走文件的四位标识样式，但**未观察其画面、时长或完整通行**。根据已验证 Range 和 ZIP 目录，可以以后只取一个成员的压缩数据并解压/核 CRC，无需传输整包；约 73 MB 的第一个候选仍不是本轮授权的小元数据读取，因此没有获取。

最小文件不能自动当预览样本：目录还存在 `Unfiltered_bag_files/6/Cow_40.bag`（0 B）和 `Unfiltered_bag_files/4/Cow_1_8025.bag`（解压后仅 27,076 B）。本轮不把它们当成功视频或合格事件。

Zenodo 的 [ZIP 在线目录](https://zenodo.org/records/8108223/preview/Unfiltered_bag_files.zip?include_deleted=0) 可直接查看 bag 名与大小，但其 bag 项没有单独下载超链接。本轮没有发现现成的单 bag 独立 URL；“可按 ZIP 成员 Range 获取”与“提供单 bag 下载按钮”是两件事。Dryad 数据页可读，但 [README 下载端点](https://datadryad.org/downloads/file_stream/2391630) 本轮网页工具返回 403；这不改变 Zenodo 公开文件已经实读成功的事实。

可复用的公开非签名地址：

- [原始 bag 整包（支持 Range，本轮只读元数据）](https://zenodo.org/records/8108223/files/Unfiltered_bag_files.zip?download=1)
- [官方 README](https://zenodo.org/records/8108223/files/README.md?download=1)
- [ZIP 目录预览](https://zenodo.org/records/8108223/preview/Unfiltered_bag_files.zip?include_deleted=0)
- [作者原始/处理数据说明与工具仓库](https://github.com/zwinkler/Automated-BCS)

状态：`public_original_rgbd_bags / range_metadata_verified / auxiliary_candidate_only / full_passage_and_duration_pending_verification`。到目前为止，三个新增核查来源都未形成满足新门槛的主验收素材；这不是模型失败或计数成绩。
