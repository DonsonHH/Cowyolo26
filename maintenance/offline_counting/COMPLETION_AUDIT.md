# 完成审计：原片通过，新会话尚未验收

2026-11-01。按用户授权的R1–R5规划逐项检查当前文件、日志和结果，不把阶段交付替换为整体验收。原片用户视频验收已保留；本次核对不重跑训练或模型。

| 要求 | 当前判断 | 直接证据与边界 |
|---|---|---|
| R1.1 恢复两份.inc及归档筛选 | 已完成 | [来源及release hash](../counting_r1/results/source_recovery.json)、[25项回归及修改范围](../counting_r1/results/regression_initial.json)。[后续干净编译和实际库加载](results/native_reproducible_build.json)通过；早期失败仍保留，在用库未替换 |
| R1.2 评分v2 | 软件功能已完成 | [评分代码](../counting_r1/event_metrics_v2.py)、[独立穷举/重排/重复/错方向/边界用例](../counting_r1/test_r1.py)、[CLI核对](../counting_r1/results/scorer_cli_smoke.json)。未把同方向匹配当物理方向正确的证明；缺独立对应仍输出不可判定 |
| R1.3 低分二次关联及阈值合同 | 逻辑修复已完成 | [25项回归](../counting_r1/results/regression_initial.json)证明只去掉第二阶段score融合，其他阶段继承；[阈值合同](../counting_r1/THRESHOLDS.md)区分0.1/0.2/0.25。未宣称精度上升 |
| R1.4 一条已有缓存的有界对照 | 已完成，数量无改善 | [缓存对照](../counting_r1/results/cache_comparison.json)：2175个同视频tick，两个版本各一次，原事件复现，11→11；无新增检测前向 |
| R1.5 复核模板、环境及资产清单 | 交付完成，独立事件真值不齐 | [空事件模板](../counting_r1/manual_event_template.json)、[资产清单](../counting_r1/results/environment_assets.json)。原片已按用户视频确认免除JSON；模板没有伪造12行GT。后续实际使用的320资产另有板上hash，其他历史路径不能据此视为全部在线核实 |
| R2 通用视频、坐标、源时间、空状态及有界日志 | 功能核对通过 | [入口及合同](../../counting/README.md)、[62项PC日志](results/review_fixes_final_pc.log)、[37项ARM日志](results/review_fixes_board.log)、[审阅修正](REVIEW.md)。不同文件/FPS/尺寸的接口夹具不充当真实牛精度 |
| R3 一次候选选择及冻结 | 320候选已选定并冻结 | [冻结记录](FROZEN_CANDIDATE.json)与原片用户验收；历史不同权重/ROI/量化的结果只作系统候选参考，未证明五候选公平排名或分辨率因果关系 |
| R4 板上完整视频和可回看演示 | 原片已通过用户验收 | [三轮结果索引](results/verification_summary.json)、[v3终态](results/board320_v3_summary.json)、[用户确认](results/user_video_acceptance.json)。原尺寸解码到计数均在板上；12次事件、内存和耗时分别记录。当前允许离线，实时和身份找回不在本次验收范围 |
| R5 冻结后的独立新会话执行 | 执行完成 | [入组协议](R5_ADMISSION.json)、[三段终态](results/r5_batch_status.json)、[hash/帧数/事件核对](results/r5_verification_summary.json)、[三段视频校验](results/r5_render_verification.json)。全部正常退出、4836源帧、969前向；结束后[四个相关PID均不存在](results/r5_final_process_check.json) |
| R5 新会话计数准确性 | 尚未通过 | 8月15日模型11次、助手源画面暂点12次；8月16日6次、空通道0次。助手暂点不是独立人工GT，事件P/R/F1未评分；同一相机、两段正例和一段负例不能证明真实反向或跨牧场泛化 |
| 发布、保留历史及排除大资产 | 已执行，当前补充同一PR | [GitHub草稿PR](https://github.com/DonsonHH/Cowyolo26/pull/1)。代码、配置、报告和小结果发布；模型、数据集及视频留在原位置，历史失败记录保留 |

结论：原片演示已经验收，完整目标尚未达到。当前需要用户核对新增8月15日的完整通行情况；若确认12次，则仍有计数差异需要修复，并需另留新会话评价。已经查看并用于修正的片段不能继续冒充未见测试。

已提供[约4.6秒疑点短片的清单](results/r5_fast_passage_excerpt.json)，帮助定位快速轨迹只有2个出口区观察而未满足3次确认的情况。该短片只辅助核对，不代替全片总数或独立事件对应。原片8780/JSON不再是阻塞项；不以再次运行相同实验、自动加数或扩大训练来代替这项新片确认。
