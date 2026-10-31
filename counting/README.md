# 离线奶牛通道计数

输入视频和通道配置，输出原图坐标下的检测、短期轨迹、IN／OUT／NET、逐事件记录及不确定片段。支持PC ONNX参考和PYNQ-Z2 O8后端。分辨率来自已导出的模型；采样频率可配置或处理所有帧，没有固定FPS验收要求。

当前结果与验收边界见[执行状态](../maintenance/offline_counting/STATUS.md)。模型和数据集保留在用户已有存储中。

## PC运行

```powershell
python -m pip install -r counting/requirements-pc.txt
python -m counting --video ABSOLUTE_VIDEO_PATH --config counting/config.example.json --output NEW_RUN_DIRECTORY
```

先填写[配置示例](config.example.json)中的模型路径、视频／源会话标识和通道。每个输出目录必须是新目录，已有结果不会覆盖。`sample_hz:null`处理每帧；设置采样率时选择接近该采样率的整数源帧间隔，并在summary中报告实际名义频率。离线处理不按墙钟跳过需要处理的帧。

`detection_roi_xyxy`是原视频像素坐标；`rotation_clockwise`支持0／90／180／270。`axis`为通行轴，`perpendicular_roi`为另一坐标的归一化范围。计数A／B区域由`counter.lower/upper`指定；A→中间→A不算完整通行，A→B→A算两个方向的两次通行。单类cow模型用`cow_class_ids:[0]`；通用COCO头应明确改为相应类别编号。

源时间来自解码器PTS，时钟不递增时直接报错。当前跟踪运动模型沿用规则采样的更新tick；较大的源时间间断会截断并重置轨迹，不把预测位置当通行观察。实时不规则dt运动模型仍是后续范围。`lost_seconds`转换为当前名义采样下的Lost保留tick，计数状态按真实源时间检查间隔并回收。

## 输出

| 文件 | 内容 |
|---|---|
| `events.jsonl` | 统计范围内完整通行：事件ID、临时track ID、方向、进入／完成源时间和源帧 |
| `frames.jsonl` | 每个实际处理帧的原图检测框、确认轨迹和当时计数 |
| `uncertain.jsonl` | 轨迹首次在中间出现、断流、终止等不确定／截断记录 |
| `transform.json` | 原图、ROI、旋转、实际resize和padding |
| `summary.json` | 模型／配置／源视频hash、计数、耗时、运行状态、内存和证据范围 |

轨迹ID仅为该次运行的短期标识。日志流式写入；帧图像不全片缓存，计数状态与累计总数分开，时间统计最多保留最近10,000个样本。summary中总elapsed含模型初始化、处理和释放，初始打开、seek及输入hash在其外；选中帧时延与整段吞吐分别解释。

## PYNQ-Z2运行

沿用板上已有O8库、固件、模型program和resident plan；不要在ARM板上安装PC依赖文件。实测环境为Python3.10.4、NumPy1.21.5、OpenCV4.5.4、PYNQ3.1.1、LAP0.5.13。

```powershell
python -m counting.package_board --output NEW_SOURCE_PACKAGE.tar.gz
```

包中含counting、必要的R1模块、冻结NumPy跟踪源文件及逐文件hash；不含模型、视频、库或依赖。展开到板上新目录，按[已运行的板端配置](../maintenance/offline_counting/original_o8_320.json)修改后端资产路径，再用PYNQ venv运行同一个`python -m counting`入口。需具备访问PYNQ设备的权限；R2实机使用授权的sudo环境和现有共享加速器文件锁，未替换原库或固件。完整命令与代码包hash保存在对应launch结果。

## 复核与评分

```powershell
python -m counting.review_server --video ORIGINAL_VIDEO --template REVIEW_TEMPLATE.json --playback OPTIONAL_REMUX.mp4 --port 8780
python -m counting.evaluate --run RUN_DIRECTORY --reference REVIEWED_HUMAN.json --output NEW_SCORE.json
python -m counting.render --video ORIGINAL_VIDEO --run RUN_DIRECTORY --output NEW_REVIEW.mp4
```

复核页面只显示源画面，默认逐帧图像模式，也提供视频模式；草稿保存在本浏览器，导出JSON需人工完成。只处理模板指定范围，拒绝未验证源文件。首次当前原片实际是MPEG容器，虽然后缀是mp4；浏览器播放副本采用无重编码转封装，并核对全部14,009帧解码hash一致。人工参考仍绑定原文件hash。

评分入口拒绝pending／draft记录，核对源hash、视频／会话、统计范围及人工事件字段。集合P/R与物理方向对应分开；没有人工参考时输出COMPLETED_UNSCORED，不把总数吻合当成事件准确率。结果回放的框在未推理的显示帧上短暂保持，并标明原观察帧号；不新增模型前向。

## 验证命令

```powershell
python -m unittest counting.test_counting counting.test_video_integration maintenance.counting_r1.test_r1 -v
```

视频集成用例使用明确标记的软件矩形和像素适配器，只检验15／30FPS、不同尺寸、旋转、完整文件输入输出等接口行为；真实模型效果另由真实视频运行和人工事件评价证明。
