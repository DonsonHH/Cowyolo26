# 本轮Review与复现状态

2026年10月26日。审阅范围是阶段计划、漏计复现、原始检测与跟踪后边界、参考辅助干预、独立复算、源视频标注工具及数据质量。**D1/D2的证据可交付；正常算法仍保留原2/6结果，关联改进和独立人工参考继续待完成。**

## 1 结论与证据对应

| 事项 | 已检查证据 | 当前判断 |
| --- | --- | --- |
| 原漏计可重复 | 实际冻结计数器＋真实保存轨迹，微调两次2事件，官方6事件；事件逐项相等 | 已复现，不把诊断过程称为修复 |
| 捕获原始检测层 | 回调模块及先后顺序、每帧无跟踪ID、479次捕获、原事件完全相等 | 检测前后层次已分清 |
| 参考辅助分层 | 固定权重与规则，IoU 0.5主检查、0.3预声明敏感性；两模型共16条件 | 解释诊断，不升级为普通可运行算法成绩 |
| 独立复算 | 不导入原counter/scorer、不使用NumPy/SciPy；穷举几何配对，再按连续区域分组构造事件 | 4份捕获CSV哈希及16条件的完整事件列表一致 |
| 空ID歧义 | 去掉尚无实际跟踪ID的输出框，再赋参考ID | 官方仍6、微调仍5；恢复不能仅归因于补空ID |
| ID14具体缺口 | 主匹配阈值下原始框B区连续最长5帧，跟踪后2帧 | 未满足原3帧起始区要求；尚未确定跟踪器内部哪项策略导致筛选 |
| 源视频工具 | 真实浏览器跳9000帧、再进1帧、两牛同帧、刷新保存、真实JSON下载、清除后导入、坏末帧拒绝完整状态 | 核心流程通过；独立人工标签尚未产生 |
| 标注结构检查 | 10项场景检查，含同帧多牛、时帧对应、重复UUID、覆盖缺口、截断、坏帧及拒绝自动冻结 | 通过；结构检查不认证标注真实性 |
| 原视频质量 | 原文件哈希一致；严格FFmpeg在末尾报错，正常模式可隐藏该损坏；VP9副本14009帧、25fps并完整解码 | 末帧14008暂排除，原文件保留 |
| 阶段范围 | 总计划列出人工参考、关联改进、身份、RF及板上测量的具体门槛 | 完整科研/板上目标继续推进 |

## 2 作业和产物

服务器目录：`/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis`。

| Job ID | 内容 | 终态 |
| --- | --- | --- |
| 129691 | 首次原始/跟踪后插桩 | FAILED/1:0；断言混淆了默认空回调与跟踪回调的同名函数 |
| 129692 | 修正模块识别后的插桩 | COMPLETED/0:0，18秒；两个模型各479帧，成功运行stderr为空 |
| 129693 | 分层干预、逐帧匹配及位置图 | COMPLETED/0:0，3秒；stderr为空 |

失败目录保留在`results/capture_failed_129691`，没有删除或冒充成功结果。修正后核对回调模块`ultralytics.trackers.track`及函数名，并逐帧捕获实际输出。最终重新读取sacct、队列和代码/协议哈希，见[服务器终态](<C:/Users/Donson/Documents/ChatGPT/奶牛/phase3_diagnosis_20261026/results/server_final_status.txt>)。

主要文件：`results/capture/{generic,pilot}/`为原始及跟踪后框；`results/layers/`为条件结果、逐事件详情、完整逐帧配对和图；`results/independent_diagnosis_verification.json`为独立复算；`annotations/diagnosis_protocol_v1.json`为预先声明的诊断方法。

## 3 复现命令

先按use-renly-slurm完成实时身份、拓扑和队列检查。GPU/CPU脚本使用本次读取的4gpu/V100S及cu分区。输入、依赖和权重已离线可读，再依次提交capture.slurm和layers.slurm；它们拒绝覆盖已有结果目录，新实验应先用独立目录并调整脚本根路径。

本地独立复算及标注检查：

```powershell
python phase3_diagnosis_20261026/tools/verify_diagnosis.py
python phase3_diagnosis_20261026/tools/additional_controls.py
python phase3_diagnosis_20261026/tools/test_annotation_contract.py
python phase3_diagnosis_20261026/tools/validate_annotations.py 待检查的复核JSON
```

QA导出示例`results/qa_fixture_annotation.json`明确标有QA-fixture-not-human-truth，且缺少审阅覆盖；校验结果保持待独立复核。这两个同帧测试事件不会进入科研参考集。

## 4 源视频与兼容副本

原视频260,096,040字节，SHA256为`5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1`。原始文件保留。严格检查命令含`-xerror`，退出码-1094995529，进度记录输出到第14008个帧后终止。按零起始源帧约定，对末帧14008保守隔离，尚未声称完成发布源端包级核查。

浏览器兼容副本使用VP9、1280×720、25fps，完整解码为14009帧、560.36秒；它可能包含解码器对源损坏的掩盖，不能把副本可播放视为修复原证据。关键事件仍须回查源帧，详情见annotations/source_quality_findings.json。

界面验证截图：[实际源视频标注页面](<C:/Users/Donson/Documents/ChatGPT/奶牛/phase3_diagnosis_20261026/results/annotation_workbench.png>)。当前保留本机8779端口的标注服务，便于继续复核；仅监听127.0.0.1，旧8778测试服务已关闭。HTML和视频也可直接使用。需结束服务时运行tools/stop_annotation_server.ps1，它核对任务进程及端口归属后关闭。

## 5 仍需完成的研究步骤

独立人工参考和新留出数据先行，随后测试普通可运行的关联改进。身份图库、未知拒识、受控RF和后台队列继续按总计划实施。用户确认PYNQ-Z2可连接，连接与版本信息稍后提供，板上性能仍为未测。

流程继续采用ask-matt路由与diagnosing-bugs的复现—干预方式，远程执行遵循use-renly-slurm；报告以anti-defensive-writing整理，保留影响解释的真实范围。没有对外发消息、投稿、发布或使用参考辅助结果替代系统成绩。
