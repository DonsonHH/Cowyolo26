# Review与复现状态

2026年10月27日。已逐项核对协议、真实采集、独立事件复算、参考身份、图像与结论。

后续口径核查修正了原因解释：OpenCows躯干框与已审阅的Toros参考框范围不同，低IoU不能单独当作真实漏检。原始条件和数值复算继续有效，见[标注口径审计](<C:/Users/Donson/Documents/ChatGPT/奶牛/data_definition_20261027/标注口径与训练数据审计.md>)。

| 等级 | 核查与结论 |
| --- | --- |
| 已核查 | 冻结漏计在实际计数器重放两次，均为1/2/1，诊断退出码2稳定 |
| 已核查 | raw回调位于跟踪回调前，三模型各479帧；插桩未改变原事件 |
| 已核查 | 24条件经独立标准库穷举配对、分组区域算法逐事件复算一致 |
| 已核查 | 只保留实际非空跟踪ID的控制按原ROI补算，6条件结果与归档未过滤版本相同，两份记录保留 |
| 已核查 | 158份交付文件逐项hash一致；20张原片衍生图、80张模型叠框图完整解码且与实际轨迹一致 |
| IMPORTANT | 原始框＋参考ID仍为1/1/2事件；此结果同时受框范围差异影响，不能直接用于纯检测召回或关联归因 |
| IMPORTANT | 相同事件数量可能属于不同参考牛，报告保留参考ID和事件帧；时间配对不自动等于逐牛空间确认 |
| IMPORTANT | 稳定区最长帧数还要结合区域顺序、观察间隔和ID连续性，补充记录了超过2秒的匹配间隔 |
| IMPORTANT | 原片同帧双事件保留；代理非盲画面观察未升级为独立人工参考，也未自动去重或宣布识别准确率 |
| 已补验 | 初次交付时浏览器工具无法启动；2026年10月27日恢复后，四组图像均加载，源帧选择、前后张按钮及首帧禁用实际通过，证据见results/browser_qa.json及browser_event_review.png |
| BLOCKER | 独立计数JSON、实际原片身份映射和PYNQ连接/工具信息仍待补充，整套目标未完成 |

本地复算：

```powershell
python event_diagnosis_20261027/tools/reproduce_new_misses.py
python event_diagnosis_20261027/tools/verify_new_diagnosis.py
```

第一条在当前冻结模型上预期退出码2，表示复现漏计；第二条应为PASS。`review_controls.py`生成严格ROI与空间描述，输出拒绝覆盖现有结果；如需复跑应使用新的输出位置保留当前证据。

主要报告：[新模型漏计与原片事件差异](<C:/Users/Donson/Documents/ChatGPT/奶牛/event_diagnosis_20261027/新模型漏计与原片事件差异.md>)。原始条件：[诊断摘要](<C:/Users/Donson/Documents/ChatGPT/奶牛/event_diagnosis_20261027/delivery/results/layers/diagnostic_summary.json>)。
