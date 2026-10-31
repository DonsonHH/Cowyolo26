# Review与复现状态

2026年10月27日。已回查作者标注定义、实际图像、元数据、重合度算术与报告结论。

| 等级 | 核查与结论 |
| --- | --- |
| 已核查 | 作者论文3.1定义躯干框；实际查看的Toros参考框包含头/腿，与训练框范围有差异 |
| 已核查 | 第27帧五轮原始框IoU0.48409、交集/预测面积0.97816、面积比0.50031，独立重算一致 |
| 已核查 | 训练组成2596真实＋3317synthetic，占比56.10%；12张视觉样本均为训练角色 |
| 已核查 | 全7043份XML及当前分发10折JSON已读取；filename无异名指向，22份额外source/path记录不提供完整母图映射 |
| 已核查 | 作者分发JSON每折8–18组完全相同字节图片跨train/test；没有把它推断为所有论文实验的实际划分 |
| 已核查 | 当前开发划分的完全重复hash隔离规则继续保留，未更改模型、标签、checkpoint或冻结事件成绩 |
| 已核查 | 81个交付文件hash、5模型几何描述、首个查看标记选择、63JPEG解码及原ZIP完整hash复核完成 |
| IMPORTANT | 几何标记是逐参考行查看候选，不是一对一检测TP，也不证明同一牛的正确躯干框 |
| IMPORTANT | 修正此前“新模型检测覆盖成为限制”的解释：已知框配对观察不足，但标注口径也参与其中；纯召回/关联归因仍需一致参考 |
| IMPORTANT | 合成占比和外观变化不足以确定因果，暂未启动真实/混合数据训练对照 |
| BLOCKER | 完整的母图/会话映射、独立计数JSON、原片身份对应及PYNQ信息继续待完成；总体目标仍在进行 |

本地核查命令：

```powershell
python data_definition_20261027/tools/verify_audit.py
```

该命令重新计算重合度、数据组成、当前分发折的完全重复交叉和原ZIP hash，并检查训练角色样本。它不改变任何冻结成绩或制造新的人工标注。

主要报告：[标注口径与训练数据审计](<C:/Users/Donson/Documents/ChatGPT/奶牛/data_definition_20261027/标注口径与训练数据审计.md>)。当前统一定义：[bounding_box_spec_v1.json](<C:/Users/Donson/Documents/ChatGPT/奶牛/data_definition_20261027/protocol/bounding_box_spec_v1.json>)。
