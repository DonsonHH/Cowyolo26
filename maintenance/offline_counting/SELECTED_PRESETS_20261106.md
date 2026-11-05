# 当前选定配置与板端运行

选择YOLO26n O8，输入256×256，完整视野1280×720 MJPEG以5Hz采集，实际全局模型观察约2.86–2.95Hz。采集率不是模型观察率；局部恢复和热身调用另计。选择基于已有视频的数量与时延，未声称所有摄像头的全局最优值。

| 安装 | 原始实测配置 | 已知方向数量 |
|---|---|---|
| Camera1 | [Aug14 V14](realtime_configs/aug14_hd_s256_birth_v14.json)、[Aug15 V14](realtime_configs/aug15_hd_s256_birth_v14.json) | 下行12、12 |
| Camera2 | [Aug19 V16](realtime_configs/aug19_hd_s256_birth_v16.json)、[Aug20 V16](realtime_configs/aug20_hd_s256_birth_v16.json) | 上行11、12 |

两套使用同一源码/模型/固件，区别是安装区域/方向/范围和恢复窗口。Camera1局部恢复1.5倍、年龄1.5秒；Camera2局部恢复2倍、年龄2秒。年龄也影响起点支持窗口，起点放大仍1.5倍。计数需已确认同一短期轨迹先后在两个相隔端区出现真实位置，不能用预测位置或牛总数预填输出。

实际执行源码包为V13R1，SHA256 `51a87f2eeb830f76d64c42a92844a8c2c078ab72bc636832621dcb9a09107f70`，按[精确源码恢复](qualified_birth_sources/README.md)核对50项，再与各案例冻结中的模型、plan、库和固件指纹对齐。模型与视频按用户要求留本机，仓库不包含这些大文件。当前板端目录：

```text
/home/xilinx/jupyter_notebooks/cow_research_offline_counting_20261031/physical_channel_v4_20261101/realtime_counting_v1_20261102/birth_refinement_v13r1/runtime
```

在该目录并使用已配置LAP依赖的PYNQ环境，回放入口为：

```bash
env XILINX_XRT=/usr OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  PYTHONPATH="$PWD:/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029/source/lap-0.5.13" \
  /usr/local/share/pynq-venv/bin/python -m counting.realtime \
  --source /absolute/path/to/input.avi --source-kind paced-file \
  --config /absolute/path/to/config.json --output /absolute/path/to/NEW_RUN
```

以具备访问现有PYNQ设备权限的环境执行，新输出目录必须不存在。不要与其他模型任务争用加速器。现有实机输入按1倍墙钟到达，板端完成解码、ROI/旋转、模型、跟踪、计数和日志；电脑只做事前采集格式适配和事后核查视频绘制。模型初始化耗时不包含在流水线时间内，详见summary.startup_s。

实体摄像头接口支持`--source 0 --source-kind live`，但**本次没有接入实体摄像头验证**。换视频或摄像头时应新建配置，修改video/session、方向、物理多边形和检测ROI，移除或更新旧`expected_capture_frames`、范围等视频专有字段。新的视角、遮挡和双向混流需要各自核对，不能把当前四段开发结果解释为任意视频准确保证。

输出`events.jsonl`、`frames.jsonl`、`uncertain.jsonl`、`transform.json`和`summary.json`。已知数量吻合、源对AI自查、原冻结服务合同分别记录；Aug19 V16最慢事件1026.627毫秒，原1秒事件合同失败，见[完整报告](REALTIME_DELIVERY_20261106.md)。后续实验由用户决定，本轮不再追加模型运行。
