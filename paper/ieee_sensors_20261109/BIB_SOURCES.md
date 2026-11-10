# BibTeX原始来源核验

主流程后续补充（同日）：已增加`multicamcows2024`，依据[Bristol官方数据记录](https://data.bris.ac.uk/data/dataset/2inu67jru7a6821kkgehxg3cv2)与[官方readme](https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/readme.txt)，采用数据页建议的作者顺序Campbell、Burghardt、Yu、Dowsey、2024年及DOI `10.5523/bris.2inu67jru7a6821kkgehxg3cv2`。视频实际拍摄于2023年8月，数据发布于2024-11-13；本条为数据记录，不伪作某篇论文的会议/期刊条目。详见`docs/research/journal_20261109/数据来源补充核验.md`。

核查日期：2026-11-09（Asia/Shanghai）。本次仅新增本文件及`references.bib`，未改`main.tex`，未连接服务器/板卡，未运行模型或编译。参考文献键固定为`cattleeyeview`、`cattle_id_2024`、`black_cattle_2025`、`bytetrack`、`zynq_yolo_2024`、`pynqz2`、`yolo26`。

## 已核实的题名、作者和出版字段

| 引用键 | 原始来源 | 已核实字段及本条目的处理 |
|---|---|---|
| `cattleeyeview` | [arXiv:2312.08764](https://arxiv.org/abs/2312.08764)；[arXiv DOI](https://doi.org/10.48550/arXiv.2312.08764) | 题名为*CattleEyeView: A Multi-task Top-down View Cattle Dataset for Smarter Precision Livestock Farming*；作者**Kian Eng Ong、Sivaji Retta、Ramarajulu Srinivasan、Shawn Tan、Jun Liu**；首次提交2023-12-14。条目明确引用arXiv 2023版本，不填未经本次出版商核实的会议页码。arXiv Comments现明确写“Published at VCIP 2023”，因此“只能确认其是未发表预印本”并不准确；本条目仍选择引用实际读到的arXiv记录。 |
| `cattle_id_2024` | [出版商DOI](https://doi.org/10.1038/s41598-024-68418-3)；[Crossref原记录](https://api.crossref.org/works/10.1038/s41598-024-68418-3) | 题名为*AI-enhanced real-time cattle identification system through tracking across various environments*。完整作者**Su Larb Mon、Tsubasa Onizuka、Pyke Tin、Masaru Aikawa、Ikuo Kobayashi、Thi Thi Zin**；Scientific Reports，14(1)，2024-08-01，article-number **17779**。Crossref的`page`为空，因此17779写为Art. no.，不伪造为页码范围。 |
| `black_cattle_2025` | [出版商DOI](https://doi.org/10.1038/s41598-025-91553-4)；[Crossref原记录](https://api.crossref.org/works/10.1038/s41598-025-91553-4) | 题名为*Optimizing black cattle tracking in complex open ranch environments using YOLOv8 embedded multi-camera system*。完整作者**Su Myat Noe、Thi Thi Zin、Ikuo Kobayashi、Pyke Tin**；Scientific Reports，15(1)，2025-02-25，article-number **6820**。Crossref将首作者拆为given=`Su`、family=`Myat Noe`，BibTeX保留其登记拆分；不擅自截成family=`Noe`。`page`为空，6820作为Art. no.。 |
| `bytetrack` | [arXiv:2110.06864](https://arxiv.org/abs/2110.06864)；[正式出版DOI](https://doi.org/10.1007/978-3-031-20047-2_1)；[Crossref原记录](https://api.crossref.org/works/10.1007/978-3-031-20047-2_1) | 作者**Yifu Zhang、Peize Sun、Yi Jiang、Dongdong Yu、Fucheng Weng、Zehuan Yuan、Ping Luo、Wenyu Liu、Xinggang Wang**，两记录一致。arXiv首次提交2021-10-13，v3修订2022-04-07；本BibTeX采用正式*Computer Vision – ECCV 2022*出版版本，年**2022**，已登记页码**1–21**，出版社Springer Nature Switzerland，在线出版日2022-10-23，并保留arXiv eprint/URL。2021预印本年与2022正式出版年分别说明，不混用。 |
| `zynq_yolo_2024` | [IEEE DOI](https://doi.org/10.1109/EIT63098.2024.10762700)；[Crossref原记录](https://api.crossref.org/works/10.1109/EIT63098.2024.10762700) | 题名为*Design and Implementation of the High-performance YOLO Accelerator based on Zynq FPGA*。作者**Gaomiao Xu、Wei Zhao、Zhouqi Ren、Zhenjia Chen、Jiabao Gao**；会议确切名称是**2024 3rd International Conference on Electronics and Information Technology (EIT)**；年2024、登记日2024-09-20、页246–250、出版社IEEE。不能仅凭EIT缩写改写成另一场Electro/Information Technology会议。无登记卷号/期号，不补填。 |
| `pynqz2` | [TUL厂家产品规格PDF](https://www.tul.com.tw/images/PYNQ-Z2_PA_v2_pp_20201209_STD.pdf)；[AMD官方AUP PYNQ-Z2页](https://www.amd.com/en/corporate/university-program/aup-boards/pynq-z2.html)作为交叉核对 | PDF正文品牌为TUL / Technology Un-Limited，并有*TUL PYNQ-Z2 / Product Specification*。本条目为厂商说明书，团体作者TUL。**正文未核实明确出版日期，故不填year**；文件名中的20201209不自动当作出版日期。旧产品落地页`https://www.tul.com.tw/ProductsPYNQ-Z2.html`本次返回404，因此改用实际可读的官方规格PDF，不把失效页写为已核实。 |
| `yolo26` | [Ultralytics官方模型文档](https://docs.ultralytics.com/models/yolo26/)；[官方2026-01-14发布公告](https://www.ultralytics.com/news/ultralytics-redefines-state-of-the-art-vision-ai-with-yolo26) | 团体作者Ultralytics，文档标题*Ultralytics YOLO26*。官方资料确认模型于2026年1月发布，但当前在线文档会更新，**本次没有取得该文档独立且固定的发表日期，故BibTeX不把模型发布日假装为文档出版日**，只记访问日2026-11-09。实验另锁定实际软件版本/commit及导出配置。 |

所有学术论文作者本次均取得完整名单，没有使用猜测姓名，也没有需要`and others`兜底的作者缺项。技术文档使用经来源确认的团体作者。题名中的普通空白、排版破折号转换成可编译的BibTeX空白/`--`，关键专有名词用花括号保护；没有改写题名含义。

## 访问方式与证据范围

arXiv元数据页可以直接读取。两个Nature页面本次被Nature身份服务重定向阻断，未绕过；作者、题名、日期、卷期及文章编号通过出版商向Crossref登记的原始元数据核实。IEEE Xplore此前访问受限，本次使用明确指定的Crossref登记记录核查EIT元数据，没有换访问方式绕行IEEE拒绝。

Crossref网页工具没有解析JSON响应，随后直接读取公开Crossref API的小型元数据响应（无登录、无作者付费正文），取得上述字段。此处属于独立的注册元数据来源，不是获取受限论文正文。Crossref可以核实出版字段，不能单凭登记条目证明论文中的性能数字、量化细节或实验因果解释。

| 引用键 | 本稿可据已取证材料使用的事实 | 尚不能由此来源核查替代的事实 |
|---|---|---|
| `cattleeyeview` | 顶视奶牛多任务数据、计数/检测/姿态/跟踪/分割任务；原摘要给753个cow instances、30,703帧、14视频。 | 753不直接等于跨视频永久身份数；本项目没有因此自动取得独立事件GT或证明与训练集无重叠。 |
| `cattle_id_2024` | 已有跨环境奶牛身份/跟踪研究；出版元数据准确。 | 本次BibTeX核查不重新验证其全部性能表；不把其永久身份能力赋予本项目的短期轨迹ID。 |
| `black_cattle_2025` | 已有YOLOv8多相机黑牛跟踪研究；出版元数据准确。 | 不将不同平台/视频的FPS或MOTA直接与本项目相比，也不复制其数值作为本项目实测。 |
| `bytetrack` | 原文的低分检测关联思想及正式出版来源。 | 本项目修改的关联、源时间和计数逻辑必须另描述；不能称所有自定义行为均为原版ByteTrack。 |
| `zynq_yolo_2024` | Zynq上YOLO加速已有原始研究；准确作者/会议/页码。 | 当前仅核实元数据及可检索摘要，不把未读全的实现/测量数字作为硬件优劣结论。 |
| `pynqz2` | 厂商标称SoC、存储及接口规格。 | 厂商规格不证明本次资源利用率、实际时钟、功耗、端到端时延或无漏计。 |
| `yolo26` | 官方模型与导出/推理头说明。当前文档指出默认one-to-many路径使用NMS；`nms=False`选可免NMS的one-to-one头，DFL-free为其特征。 | 文档中的Intel CPU / GPU基准不是PYNQ-Z2测值；本项目实际导出头、算子和量化格式须由执行资产核对。 |

本轮未生成或修改任何实验结果，亦未声称论文已经投稿就绪。未填的技术文档出版年是明确的取证范围，不能在排版时用访问年、URL日期或文件名日期自动补成发表年。新增可引用事实时，先补原始来源核查，再修改相关正文。
