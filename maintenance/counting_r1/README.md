# R1维护入口

本目录实现一轮有界维护：恢复O8必要小型源码、评分v2、仅低分第二阶段关联修复和一条已有缓存对照。结果及限制见[STATUS.md](STATUS.md)。权重、数据集、视频、编译库与依赖缓存留在原存储位置。

## 环境与回归

在仓库根目录使用Python 3.12；跟踪／缓存依赖见[requirements-pc.txt](requirements-pc.txt)。评分v2本身只用Python标准库。

```powershell
python -m pip install -r maintenance/counting_r1/requirements-pc.txt
python -m maintenance.counting_r1.run_checks --output maintenance/counting_r1/results/regression_local.json
```

结果路径必须不存在，原验证记录不覆盖。当前已运行25项回归，结果是软件行为检查，不是奶牛精度测试。

## 评分v2

输入可为事件列表，或含`events`的对象。每事件至少有`time_s`和`direction`，建议填`event_id`、`video_id`、`session_id`。时间采用冻结规则下的完成通行源时间。指标定义、阈值边界和歧义解释见[THRESHOLDS.md](THRESHOLDS.md)。

```powershell
python -m maintenance.counting_r1.event_metrics_v2 reference.json predictions.json --tolerance-s 2
```

stdout为JSON。独立物理对应可另用`--physical-pairs links.json`；每条link包含`reference_event_id`、`prediction_event_id`、`independently_verified:true`、`evidence_type`与具体`evidence`。证据类型为`video_review`、`spatial_correspondence`或`trajectory_correspondence`。程序验证格式和一对一性，不自动认证人工证据。

[人工复核模板](manual_event_template.json)尚未填写，CLI会拒绝pending／draft状态。请独立回看原视频再填事件，不依据模型结果构造GT。截断与歧义记录单列并报告，容差和时间口径在比较模型前确定。

## 跟踪修复与有限缓存回放

导入`maintenance.counting_r1.tracker.SecondStageIoUTracker`可使用维护类。它复用冻结NumPy版本及LAP 0.5.13；若已加载另一路径的cow_tracker会拒绝混用。R1只移除第二阶段score融合，第一阶段、未确认阶段及阈值保持原规则。历史入口未替换。

```powershell
python -m maintenance.counting_r1.replay_cache --cache raw_predictions.json.gz --protocol board_protocol.json --reference-trace stride5_counter_trace.json.gz --scene original --stride 5 --output comparison.json
```

这是一次已有检测流的新旧跟踪对照，不能直接读取视频，不运行模型。当前结果11→11，见[结果文件](results/cache_comparison.json)。该记录给出缓存路径及hash；大载荷未提交。

## 原生运行库源码

两个`.inc`文件补回`pynq/yolo26_optimization_8/native_sources/`；归档策略已接收`.inc`。发布清单hash与恢复来源见[源码恢复记录](results/source_recovery.json)。

兼容PC或ARM环境下，现有脚本会在新目录中复制五个源文件并编译：

```powershell
python pynq/yolo26_optimization_8/recompile_native.py --output ABSOLUTE_NEW_BUILD_DIRECTORY --compiler ABSOLUTE_COMPILER_PATH
```

本轮本机MinGW未构建成功，详见[失败记录](results/native_build.json)。该命令在此环境尚未验收，编译结果不得用于替换在用库。后续兼容环境验证需单列记录，不必重新做硬件设计。
