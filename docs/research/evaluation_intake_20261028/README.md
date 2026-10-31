# 独立评价接收与当前验收关口

当前入口已扩展为[29组预测与9个明确配对](<../lost_recovery_20261028/Lost低分恢复与完整事件结果.md>)，保留原17组、后续23／26组及本文件的历史检查。新索引覆盖交接12／11／11与两个事件不变的关联控制；使用接收命令时以`--catalog`选择[当前v4索引](<../../../research/lost_recovery_20261028/results/frozen_prediction_catalog_v4.json>)。[原接收框架与28项检查](<../paired_event_intake_20261028/评价入口与下一步.md>)继续复用，29条件／58方向行贯通已验证。以下内容记录早期准备阶段，独立人工JSON和板卡信息仍未收到。

2026年10月28日。**标注页修复、复核JSON接收检查和17组冻结预测索引已完成。下一步的源片独立评分与PYNQ-Z2实测，分别需要复核JSON和板卡连接／版本信息。** 当前没有新增通行真值或板上成绩。

## 1. 标注页修复与保留内容

已实际复现：播放时输入10873，时钟刷新把它改成10253，点击后跳到10253。修复为输入帧号时暂停播放，且不刷新正在编辑的输入框。QA模式新增明确测试提示，主模式保持正常标注视图。

浏览器9项回归覆盖编辑暂停、末帧10873、上下界、源帧步进、全片／聚焦切换、倍速和取帧；原有2条QA事件、复核者声明和覆盖内容在修复前后相同。未打开或操作主草稿，没有新增／删除事件，没有改动JSON模式、存储键或事件定义。[失败与实际跳转](<../../../research/evaluation_intake_20261028/results/annotation_jump_before_fix.json>)、[修复与hash](<../../../research/evaluation_intake_20261028/results/annotation_jump_fix.json>)、[浏览器回归](<../../../research/evaluation_intake_20261028/results/annotation_browser_retest.json>)。

[修复后的隔离QA页面，2条测试事件不是真值](<../../../ARCHIVE_CONTENTS.md#omitted>)

[正常标注页](http://127.0.0.1:8779/annotation_workbench/index.html) · [本地HTML](<../../../research/phase3_diagnosis_20261026/annotation_workbench/index.html>)。服务关闭时，可在`phase3_diagnosis_20261026`目录运行`python tools/annotation_server.py --port 8779`，只监听本机。

## 2. 复核JSON接收入口

保留原JSON并计算文件hash，复用现有结构检查，再核对原视频身份、区域／事件定义、8912–10873帧的完整覆盖、疑难／截断、末帧质量和已知QA样例。未知完整帧段不按零通行处理，同帧两头牛不自动去重。已看过预测的声明保留，不能由程序改称盲标。

页面导出的状态始终是`draft_pending_independent_review`。**检查通过只表示可继续做原始源帧和来源核验，程序不自动认证独立真值，也不计算准确率。** 真正复核完成后，收到用户提供的文件和说明，就按原计划继续核查与评分，无需再次申请训练或评分权限。

接收命令示例，把“导出的JSON完整路径”替换成真实文件；输出路径须是新文件：

```powershell
& 'C:\Users\Donson\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 `
  'C:\Users\Donson\Documents\ChatGPT\奶牛\evaluation_intake_20261028\tools\inspect_annotation.py' `
  '导出的JSON完整路径' `
  --output 'C:\Users\Donson\Documents\ChatGPT\奶牛\evaluation_intake_20261028\results\received_review_inspection.json'
```

16项检查通过，包含错误源视频／区域、单帧覆盖缺口、疑难、坏末帧、NaN、错误时间、已知QA改名、同帧双牛、输入不变及CLI禁止覆盖。首次CLI测试被Windows子进程输出编码打断，增加子进程UTF8选项后通过；原失败和旧测试脚本保留。[16项结果](<../../../research/evaluation_intake_20261028/results/intake_test_results_v2.json>)、[QA被拦下的实跑](<../../../research/evaluation_intake_20261028/results/known_QA_intake_check.json>)。

页面的3帧稳定观察指25fps原视频帧；模型是5Hz检测下的3个稳定采样。这两种时间标记口径分别保留，不能混写。接收后要核对关键源帧及短通行争议，使用既有2秒事件配对规则，不根据结果调整容差。

## 3. 17组预测已就绪

索引包含同源片、同8912–10873范围的全部5组检测回放、6组数据组成条件和6组方向条件，共17组。每组绑定原事件文件、摘要、协议和checkpoint hash；计数历史均从源帧0开始。旧Cows原朝向三组与新原朝向事件一致，作为历史别名只计一次；官方／五轮旧预览的归一化事件也核对一致，但不据此宣称所有旧运行细节相同。

[完整预测索引](<../../../research/evaluation_intake_20261028/results/frozen_prediction_catalog.json>) · [CSV](<../../../research/evaluation_intake_20261028/results/frozen_prediction_catalog.csv>)。这些是已冻结预测，尚未与新独立参考评分；Toros的既有6事件和仅在Toros运行的参数条件继续另列。

## 4. 两项当前必要输入

| 输入 | 需要提供什么 | 收到后的下一项实际工作 |
| --- | --- | --- |
| 独立复核JSON | 从标注页导出的文件，保留覆盖、疑难及是否看过预测的说明 | 来源／结构检查→关键原帧与争议核查→冻结参考→同规则匹配17组预测，分别报告漏计、重计、方向错误 |
| PYNQ-Z2连接与版本 | SSH地址、用户名、端口，PYNQ镜像版本，Vivado及HLS版本（如有） | 只读环境／ABI／内存／已有overlay检查→小网络数值→检测／身份单模型→联合队列、时延、内存与功率 |

本对话尚未收到这两项新输入。未从其他课程工程推断板卡版本或猜测连接地址。真实身份／RF对应与论文主要机制的证据也继续按原范围验收。

原源视频260096040字节及SHA已重新核对，近期研究作业已由实时`sacct`确认全部终止且成功；当前不是在等计算完成。[必要输入审计](<../../../research/evaluation_intake_20261028/results/required_input_audit.json>)、[实时作业核查](<../../../research/evaluation_intake_20261028/results/live_compute_audit.txt>)。

## 5. 当前状态

本阶段准备已完成。独立真值与实际板卡信息是主线外部输入，更多已见开发集训练不能替代它们。整个研究目标未完成，不能把准备通过写成最终计数准确或PYNQ-Z2已运行。[完整Review](<Review与当前状态.md>)。
