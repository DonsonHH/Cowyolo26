# IEEE Sensors Journal工作稿

更新（2026-11-10）：优先阅读 [P0/P1 修订稿](p0p1/README.md)，已纳入 20 组消融、数据审计与 C1 反例。下文及原 PDF 保留为原 V4 阶段记录。

主投目标：IEEE Sensors Journal，出版商IEEE。论文主线保持PYNQ-Z2与YOLO26n，研究资源受限视觉传感器如何通过因果图像选择、真实局部补检和可审计事件输出，改善通道计数可靠性。

- [期刊选择与官方要求](../../docs/research/journal_20261109/期刊选择与官方投稿要求.md)
- [论文架构与实验合同](研究架构与证据清单.md)
- [英文正文](main.tex)
- [参考文献](references.bib)
- [官方通用模板原文](vendor/ieee_official_bare_jrnl.tex)与[来源/许可](vendor/SOURCE.json)

当前是未投稿的研究工作稿。作者、单位、通信信息、资助、伦理判断与最终AI披露由实际作者确认，未填入样例姓名或审批号。工作稿明确区分历史失败、2026-11-09修复与最终V4的8轮上板通过，以及尚待完成的独立事件参考、预算匹配消融和真实相机实验。最终源包为33f2a957…，云端与目标ARM各141项软件检查通过。

采用已安装`research`核对第一手来源、`anti-defensive-writing`组织学术表达；采用IEEE/Overleaf官方标记的通用期刊模板起稿。Sensors专用最新ZIP未取得，最终版式还需与当时作者指南核对。

编译和绘图在私有服务器Slurm执行，不在本机训练、推理或大型构建。全量结果和源数据留在私有存储，恢复索引不上传公开仓库。

当前可阅读稿：[PDF](output/pdf/Cowyolo26_IEEE_Sensors_Working_Draft.pdf)。构建证明和逐页视觉检查记录与PDF同目录保留。本文仍是研究工作稿，不能将4段开发片和重复播放表述为独立泛化验证。
