# 奶牛通道计数：离线与板端实时

2026-11-06：当前板上实时结果、选择的安装配置与证据边界见[实机交付报告](../maintenance/offline_counting/REALTIME_DELIVERY_20261106.md)。实时入口为 `python -m counting.realtime --source INPUT --config CONFIG --output NEW_DIRECTORY`；本轮测试为按1倍墙钟到达的视频回放，全部在线处理在PYNQ-Z2执行。实体摄像头输入尚未验证。

实时候选使用已确认的同一轨迹在相隔端区各一次真实位置，至少两张不同源图像，预测不能计数。下文两次/三次确认示例和旧离线成绩属于历史策略，未改写为新的实时成绩。源码精确版本见[恢复说明](../maintenance/offline_counting/qualified_birth_sources/README.md)，使用当前文件前应对齐案例源指纹。

输入视频和通道配置，输出原图坐标下的检测、短期轨迹、IN／OUT／NET、逐事件记录及不确定片段。支持PC ONNX参考和PYNQ-Z2 O8后端。分辨率来自已导出的模型；采样频率可配置或处理所有帧，没有固定FPS验收要求。

当前结果与验收边界见[执行状态](../maintenance/offline_counting/STATUS.md)。模型和数据集保留在用户已有存储中。

当前示例使用两次连续真实观察确认，来源是[快速通行单因素对照](../maintenance/offline_counting/FAST_PASSAGE_FIX.md)：三次确认会漏掉出口区仅有两次观察的快速牛。原冻结配置和库的默认参数保留；这不是任意观察率下的准确性保证。新会话仍须单独验证，预测位置不构成真实观察。

`track_only_in_channel:true`把原图坐标下、中心位于`perpendicular_roi`之外的检测框在跟踪关联前排除，避免栏杆等通道外误检争抢通道内轨迹。旧配置缺省为false以保留既有行为；计数仍会检查通道范围。相机标定所得的关联参数单独放在配置中，新建轨迹门限与已有轨迹关联门限分开。

## PC运行

```powershell
python -m pip install -r counting/requirements-pc.txt
python -m counting --video ABSOLUTE_VIDEO_PATH --config counting/config.example.json --output NEW_RUN_DIRECTORY
```

先填写[配置示例](config.example.json)中的模型路径、视频／源会话标识和通道。每个输出目录必须是新目录，已有结果不会覆盖。`sample_hz:null`处理每帧；设置采样率时，按源PTS选择达到下一个采样时刻的首个源帧。VFR不按名义FPS固定跳帧；源频率不足时不会伪造观察，并记录无法提供的采样槽。离线处理不按墙钟跳过需要处理的帧。

`detection_roi_xyxy`是原视频像素坐标；`rotation_clockwise`支持0／90／180／270。`axis`为通行轴，`perpendicular_roi`为另一坐标的归一化范围。计数A／B区域由`counter.lower/upper`指定；A→中间→A不算完整通行，A→B→A算两个方向的两次通行。单类cow模型用`cow_class_ids:[0]`；通用COCO头应明确改为相应类别编号。

源时间来自解码器PTS，时钟不递增时直接报错。运动矩阵、过程噪声和Lost过期均按实际源时间处理；单位步长保留冻结Kalman行为，非单位间隔的噪声扩展见source_clock.py。`lost_seconds`是真实源秒，计数状态也按源秒检查间隔和回收。预测位置不构成通行观察；本节描述离线处理，实时采集与调度由独立 `counting.realtime` 入口负责。

非零解码起点默认从文件头顺序定位，避免VFR的名义FPS跳转误标帧。可选`source_index_file`为同一原视频顺序解码生成的唯一PTS索引：先核对原文件hash，再核对跳转后实际PTS，匹配才使用快速定位；不匹配回退顺序解码。该索引没有检测／跟踪结果，不恢复旧实验状态。

## 输出

| 文件 | 内容 |
|---|---|
| `events.jsonl` | 统计范围内完整通行：事件ID、临时track ID、方向、进入／完成源时间和源帧 |
| `frames.jsonl` | 每个实际处理帧的原图检测框、确认轨迹和当时计数 |
| `uncertain.jsonl` | 轨迹首次在中间出现、断流、终止等不确定／截断记录 |
| `transform.json` | 原图、ROI、旋转、实际resize和padding |
| `summary.json` | 模型／配置／源视频hash、计数、耗时、运行状态、内存和证据范围 |

轨迹ID仅为该次运行的短期标识；`run_id`区分重启／重复运行，`session_id`标识源会话。日志流式写入；帧图像不全片缓存，计数状态与累计总数分开，时间统计最多保留最近10,000个样本。`elapsed_s`含模型初始化、处理和释放，`overall_elapsed_s`还包含初始打开、源索引／顺序定位与输入hash；选中帧时延与整段吞吐分别解释。

## PYNQ-Z2运行

沿用板上已有O8库、固件、模型program和resident plan；不要在ARM板上安装PC依赖文件。实测环境为Python3.10.4、NumPy1.21.5、OpenCV4.5.4、PYNQ3.1.1、LAP0.5.13。

```powershell
python -m counting.package_board --output NEW_SOURCE_PACKAGE.tar.gz
```

包中含counting、必要的R1模块、冻结NumPy跟踪源文件及逐文件hash；不含模型、视频、库或依赖。展开到板上新目录，按[已运行的板端配置](../maintenance/offline_counting/original_o8_320.json)修改后端资产路径，再用PYNQ venv运行同一个`python -m counting`入口。需具备访问PYNQ设备的权限；R2实机使用授权的sudo环境和现有共享加速器文件锁，未替换原库或固件。完整命令与代码包hash保存在对应launch结果。

## 复核与评分

原片8912–10873已由用户审阅标注视频并确认通过，不再要求8780页面或逐事件JSON。下面的源画面标注工具仍可用于建立独立事件评分参考；用户视频验收与独立事件P/R评分分别记录。新日期的冻结验证见[R5报告](../maintenance/offline_counting/R5_REPORT.md)。

```powershell
python -m counting.review_server --video ORIGINAL_VIDEO --template REVIEW_TEMPLATE.json --playback OPTIONAL_REMUX.mp4 --port 8780
python -m counting.evaluate --run RUN_DIRECTORY --reference REVIEWED_HUMAN.json --output NEW_SCORE.json
python -m counting.render --video ORIGINAL_VIDEO --run RUN_DIRECTORY --output NEW_REVIEW.mp4
```

复核页面只显示源画面，默认逐帧图像模式；有帧时间索引时可切换视频模式。通道由模板review_gate提供，导出时需标记可见躯干中心。草稿按源文件、会话、范围、通道与标注协议分开；兼容旧草稿可显式复制，原内容保留。原图帧与源时间由解码器提供，跳帧未就绪时不能标记。当前原片实际是MPEG容器，虽然后缀是mp4；浏览器播放副本采用无重编码转封装，并核对全部14,009帧解码hash一致。人工参考仍绑定原文件hash。

评分入口拒绝pending／draft记录，核对源hash、视频／会话、统计范围及人工事件字段。集合P/R与物理方向对应分开；没有人工参考时输出COMPLETED_UNSCORED，不把总数吻合当成事件准确率。结果回放的框在未推理的显示帧上短暂保持，并标明原观察帧号；不新增模型前向。

## 验证命令

```powershell
python -m unittest counting.test_counting counting.test_video_integration maintenance.counting_r1.test_r1 -v
```

视频集成用例使用明确标记的软件矩形和像素适配器，只检验15／30FPS、不同尺寸、旋转、完整文件输入输出等接口行为；真实模型效果另由真实视频运行和人工事件评价证明。

### 透视通道边界

可用`channel_polygon`给出原图归一化[x,y]顶点（3–64点、简单无孔多边形），此时`perpendicular_roi`设为[0,1]。`axis`及`counter.lower/upper`仍定义源坐标中的两条门线；两线都要穿过区域内部。点在边界上不纳入。设置`track_only_in_channel:true`可在关联前排除区域外检测，计数和复核使用同一区域。裁剪/旋转/letterbox后的框先还原到原图再判区域。

例如透视变宽的竖向通道：`"channel_polygon":[[0.2,0],[0.4,0],[0.8,1],[0.2,1]]`。该数值仅演示格式，需要按实际无预测画面标定。旧配置不含该字段时继续使用原侧带；不能将多边形草稿用于另一形状的人工参考。
