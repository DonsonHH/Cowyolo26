# MooTrack360：原片可抽查，评价映射仍需确认

2026-10-28。**本轮找到一个会直接影响评价结果的问题：GT坐标与视频原生尺寸不在同一尺度。** 作者配置和四个时刻的叠图支持“GT乘2、视频0起算帧n对应GT1起算帧n+1”的候选映射；全片时间对应尚未证明，因此没有新增计数成绩，也没有修改当前模型。

此前只有标注文本和视频容器信息，未读取像素，见[原候选审计](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_reference_candidates_20261027/独立计数参考候选核查.md>)。本轮按[先行计划及追加诊断](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/计划与验收.md>)取得了实际原生帧，更新这一判断。

## 1. 实际取得了什么

数据来自[官方Zenodo v1.1记录](https://zenodo.org/records/20287681)。本轮未下载整个18.9GB视频，而是解析已绑定SHA256的MP4样本目录，准确读取五个关键帧组及两次目录复核，共44,740,482个HTTP响应体字节，约42.67MiB，低于事先限制的64MiB。没有核验整片发布方MD5；范围请求、响应长度和每段SHA256已保留。[首轮范围证据](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/evidence/video_ranges/manifest.json>)、[片尾证据](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/evidence/tail_ranges/manifest.json>)

五段合计126帧经过解码计数和尺寸检查，实际目视的是其中5张2944×2944原生帧，不能把126帧解码通过写成126帧人工看过。首三个时刻在看像素前已固定；片尾两处和两倍尺度属于后续诊断。

| 视频帧（0起算） | 原片时间 | 用作核查的GT帧（1起算） | GT框数 | 用途 |
| --- | --- | --- | --- | --- |
| 0 | 0秒 | 1 | 3 | 开头映射 |
| 8991 | 599.9994秒 | 8992 | 6 | 约10分钟 |
| 26973 | 1799.9982秒 | 26974 | 7 | 约30分钟 |
| 53919 | 3598.1946秒 | 53920 | 8 | 标注末端假设 |
| 53945 | 3599.9297秒 | 无 | 无 | 原片最后一帧；只作上下文展示 |

第五张附加叠图使用了最后一个已存在的GT，并醒目标为“CONTEXT ONLY”；没有生成53921–53946的假GT。原始像素与附加图层分别保存。

## 2. 空间尺度：直接使用seqinfo会出错

包内`seqinfo.ini`声明2944×2944，但前三张原坐标叠图明显偏小并向左上方错位。作者仓库固定提交`9782faa9ca2702f29298f0a5af58046a83a79f8d`的[README执行配置](https://github.com/SDU-Robotics/MooTrack360/blob/9782faa9ca2702f29298f0a5af58046a83a79f8d/README.md)明确列出`img_resize: 0.5`，并说明配置针对一小时标注序列。由这一线索，仅新增乘2、零平移的空间对照，未搜索最优缩放或偏移。

对350272行GT独立检查，原始框的总体xyxy边界为(350, 281, 1166, 1199)，全部位于1472×1472范围内；乘2也全部位于2944×2944内。**边界落在半分辨率内本身不能证明尺度正确；作者配置和实际叠图才提供额外支持。** 开头、10分钟、30分钟、标注末端共24个发布方框，在乘2后大致对应可见奶牛；没有独立人工框IoU测量，不将其写为定量标注精度。[坐标检查](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/results/scale_control/summary.json>)、[目视记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/evidence/visual_review.json>)

![原片与两倍GT诊断，右图为额外绘制的参考层](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/results/scale_control/native_and_GT_x2_diagnostic.jpg>)

后续若验证通过，应把该映射写入本项目的适配器与固定协议，保留原始发布包；不要直接改原始标签或只改seqinfo后忽略尺度。

## 3. 时间：10fps不能直接当真，26帧差异尚未归因

实际视频样本表为53946帧、每帧2002/30000秒，即约14.985fps；包内GT到53920帧，seqinfo写10fps。只将帧号除以10会将约一小时错算为约90分钟。取样使用视频真实样本时钟，不采用seqinfo的10fps。

样本表解析器在另一现有MP4上与ffprobe逐个核对606个包，字节位置、大小、持续时间、关键帧标志和时间顺序全部一致；ffprobe时间相对原始媒体表有统一-2000 ticks平移，记录为可能涉及edit list的时间原点差异，不据此声称绝对墙钟对应。[解析器控制](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/results/index_control.json>)

抽样支持帧序号对应假设，但仍不能排除中间局部掉帧或其他偏移。按“GT是前53920帧”假设，原片末尾有26帧、约1.7351秒未标注；标注末端与原片最后一帧的画面都可正常解码且布局近似。这个观察**不能区分末尾截断、重复画面或标注导出差异，也没有证明26帧差异只出现在片尾**。[片尾核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/results/tail_review/summary.json>)

![GT末端与视频最后一帧，末图叠层仅作上下文](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/results/tail_review/endpoint_and_final_native_GT_context.jpg>)

## 4. 输入与场景能支撑哪些研究

五张原生抽样图中未见跟踪框或轨迹ID烧录；画面左上仍有模糊的时间样文字，外围有模糊处理，不称为完全无文字或未经处理的传感器原始流。当前可继续核查其作为干净检测输入的条件；没有检查全片所有像素。

画面是小型牛舍围栏、饲喂区、休息区和混凝土通行区域。它有潜力支持鱼眼、遮挡、尺度差异下的跟踪诊断，但这五张静态图没有确认完整牧场出入口或同一通道双向完整事件。**不能把牛舍内任意跨线结果改称牧场进出计数。** 参考轨迹ID也不等于已注册的永久牛只身份，更不提供真实RFID漏读或掉标证据。

当前准入决定：

| 用途 | 本轮决定 | 还需完成 |
| --- | --- | --- |
| 原片格式与GT坐标适配诊断 | 可以继续 | 固定候选映射，保留原始来源 |
| 全片检测／跟踪定量测试 | 尚未准入 | 在标注起始、活动变化与末端检查连续片段，确认帧号／尺度／有效区 |
| 独立通道双向事件测试 | 尚未准入 | 核实真实通道和完整事件，先固定参考与截断规则，再运行冻结模型 |
| 耳标异常身份找回／PYNQ-Z2实测 | 不能据本轮证明 | 另需身份注册、读码与真实硬件证据 |

作者仓库的30个相关文本文件以Git blob和SHA256绑定，包含README和LICENSE；未安装或执行作者代码。仓库标示CC BY-NC-SA 4.0，本轮来源范围见[固定文本清单](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/evidence/author/manifest.json>)与[作者LICENSE](https://github.com/SDU-Robotics/MooTrack360/blob/9782faa9ca2702f29298f0a5af58046a83a79f8d/LICENSE)。不将仓库说明自动扩展为所有数据包用途的完整许可核验。

## 5. 对现有项目的影响与下一步

当前源片范围仍是用户确认的8912–10873帧橙框内完整通行，候选预测12／11／11不变，29条件索引不变。独立人工复核JSON尚未收到，准确计数和F1继续待验；不以“十几头”作为训练标签。板卡连接和版本继续等用户稍后提供，不改变两项推理最终均在PYNQ-Z2运行的目标。

下一阶段先做MooTrack连续片段的时间对应核验，优先选择发布GT中已有身份首次进入及运动明显的边界，图像先于模型预测核查；确认可用后才冻结有效范围与事件规则。若只能支持牛舍跟踪诊断，就按该用途报告，继续寻找符合通道条件的新会话。原片人工事件JSON收到后，优先用既有固定评分器给29条件逐事件配对，再决定是否需要新训练。

本轮上一阶段属于实际进展（六组双ID审计）；本阶段也产生了新的原片和空间映射证据。整体研究目标保持进行中。[完整自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/mootrack_alignment_20261028/Review与当前状态.md>)
