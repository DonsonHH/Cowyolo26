# Standards 轴最终复核

2026-11-10。固定点为 fef77d37，HEAD 为 7e5e974b；检查两者差异及本轮未提交的计数、预算、评分源码和测试。未发现适用于这些项目文件的额外 AGENTS／CONTRIBUTING／CODING_STANDARDS；第三方树规范不外推。只读复算的58项源码哈希全部匹配8d867877冻结包，未重跑测试、模型或连接设备。

## 硬规则

未发现本轮新的硬规范违反。count_metrics保留未复核方向及事件F1为空，拒绝把重复源区间当作新增视频；用户提供总数即可由代理建档。所查新模块没有串口、JTAG、DNS修改操作，视频夹具仅打开文件。

NOTICES、README、ARCHIVE_CONTENTS已更正历史“无数据／无缓存”声明。Ultralytics派生头与完整AGPL文本保留，后者SHA256为0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0；根MIT未被用来替换第三方许可。两个旧O8 include的来源待核实状态仍保留，不能据此宣布整仓发行许可已闭合。新附包是否落实排除范围，仍以实际清单为准。

## 文案问题

P2：counting/budget_runner.py:222写“Local eligibility was fixed BEFORE its image became available”。首个推理可能超过0.4s，下一图已到达。实际可保证的是仅使用primary和历史状态，并在消费secondary前选择。应更正注释；无需改写8d867877实验冻结源或重跑模型。

## 风格判断

可能的Duplicated Code：budget_runner.py:49起与realtime.py中的“competitors={} … superseded_global_indices(…)”重复融合逻辑，后续维护可能只修一处。属于P3判断，不是当前结果缺陷；不建议为消除风格重复扰动已冻结实验。

本轴：硬违反0；文案问题1（P2）；风格判断1（P3）。Spec和原始结果由另一轴单独复核。

## V7 定点补审

原P2注释已关闭；README明确总数JSON由代理建档。新开关默认False且校验布尔值；fuse复制输入，启用时以实测global seed坐标配合被选local分数／类别。两入口共用方法，accepted_detection与fused_detection分列，fusion_mode说明混合来源，未发现新增硬规则问题；融合值不应称为单次原始检测输出。60项源码及归档匹配ee44e637冻结包，现有cloud／ARM日志均为189项通过。此为软件证据，尚未核验V7实机终态，不能预言成功。未重跑测试、模型或连接设备；旧失败保留，原P3仅为维护判断。
