# 第一阶段纯IoU候选：多seed与反向回归、采用决策

2026年10月29日。**本轮不把第一阶段纯IoU设为全场景默认算法。** 它恢复了新普通俯视长片seed26的一次事件，原片三seed总数也保持；但在已使用的Toros真实反向片中，官方YOLO26n从6次正确匹配降到5次、漏1次，并出现原轨迹转而跟随邻牛的病例。全部条件已保留，不以局部总数增加替代回归验收。

用户人工确认的原片8912–10873帧橙框内12头仍有效，原seed26达标组合保持。本轮候选、原算法、模型权重与两版新片参考分别保存，原成果没有被覆盖。

## 1 从上一轮结果提出的检验

[上一轮单因素实验](<C:/Users/Donson/Documents/ChatGPT/奶牛/long_video_track_gap_20261029/新片轨迹分段定位与单因素对照.md>)表明：相同检测框及相同中断前状态下，去掉第一阶段代价中的分数融合，可恢复ID19并使新片seed26预测11→12。这个结果不能单独证明整套算法更可靠，因此先冻结以下全部配对条件。

| 资料 | 固定模型 | 跟踪更新时钟及计数轴 | 评价依据 |
| --- | --- | --- | --- |
| 新普通俯视长片 | 官方、Cows2021十轮seed26／27／28 | 5Hz，原生y轴；从源帧0至10120，每5帧更新 | 模型前助理草案尚待独立接受，只报告预测 |
| 原人工12头开发片 | Cows2021十轮seed26／27／28 | 5Hz，原生y轴；从源帧0至10870，每5帧更新 | 指定8912–10873帧总数12已人工接受；没有新逐事件真值 |
| 已用Toros反向片 | 官方、旧OpenCows五轮模型 | 30Hz，原生x轴；479源帧全部更新 | 已使用的发布方轨迹派生6事件，保持2秒匹配规则 |

9份缓存分别运行原算法与候选，合计18次完整跟踪、31166次更新、36条计数路径。所有9个原算法条件先通过旧输出精确回归，之后才运行候选。新长片与Toros核查全图框；原片核查全部ROI框、历史、全图输出ID、确认／待确认观察及计数。原片没有历史的全部通道外坐标参考，未声称这一部分也做了逐坐标旧值回归。

候选代码与上一轮方法的语法树一致：只把**第一阶段**代价`1−IoU×score`改为`1−IoU`，保留0.8门槛。第二阶段、未确认轨迹匹配、去重、3次稳定观察、2秒中断、ROI及检测框均保持。3次观察在5Hz下跨度0.4秒，在30Hz下为2/30秒；本轮沿各自历史协议回归，没有将它们混写成统一稳定时长，也没有重新训练或运行检测器。

冻结条件与所有缓存哈希见[回归协议](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/protocol/regression_v1.json>)。

## 2 全部9组主要结果

下表“当前计数路径”指确认时交接紧邻一次待确认观察的固定方法。俯视片显示向下A→B，Toros显示反向B→A；另一个方向的预测均为0。

| 资料与模型 | 原算法预测 | 候选预测 | 可支持的解释 |
| --- | ---: | ---: | --- |
| 新长片，官方 | 0 | 0 | 固定检测缓存稀疏，改关联未产生事件 |
| 新长片，seed26 | 11 | 12 | 重现上一轮恢复结果，仍待独立逐事件接受 |
| 新长片，seed27 | 12 | 12 | 总数保持；不等于全部轨迹不变 |
| 新长片，seed28 | 12 | 12 | 总数保持，有事件时间变化 |
| 原片，seed26 | 12 | 12 | 对人工总数12，绝对总数误差均0；原成功版本保持 |
| 原片，seed27 | 11 | 11 | 对人工总数12，绝对总数误差均1 |
| 原片，seed28 | 11 | 11 | 对人工总数12，绝对总数误差均1，有事件时间变化 |
| Toros，官方 | 6 | 5 | 参考正确匹配6→5，漏计0→1，误计均0 |
| Toros，旧五轮模型 | 2 | 4 | 参考正确匹配2→4，漏计4→2，误计均0 |

新长片群体／单牛／人员三个窗口中，候选输出分别为官方0／0／0，seed26、27、28均11／1／0。人员窗口无事件只说明本段局部对照没有触发通行，不是完整背景误报率，也不是牛的真实反向覆盖。

“仅确认后观察”的另一条路径同样全部保留：新长片原算法合计0／11／11／12，候选0／12／11／12；原片两算法均11／10／11；Toros两种计数器各自得到同样的6→5和2→4。完整36路径、窗口内全部事件和指标见[原始结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/delivery/results/summary.json>)。

### 2.1 Toros的参考评分范围

按原2秒容差做时间最优配对，再检查方向，官方候选未匹配的是发布方ID14的193帧事件（约6.433秒）。旧五轮候选仍漏发布方ID16和ID22对应的两次事件。两模型在这次参考下FP均为0，但下面的轨迹证据说明，事件FP为0不能推出轨迹关联正确。

这份6事件参考已经被此前多轮诊断使用，本轮是受控回归，不是新的未见测试；Toros也不作为后续普通正上方数据训练主线。独立从1775条发布方轨迹重新导出6事件，并用穷举配对复核8条允许评分的路径。新长片没有因此获得正式准确率或F1。

### 2.2 总数相同时，也要保留变化

| 条件 | 事件帧／方向多重集合的变化 |
| --- | --- |
| 新长片seed26 | 新增2675；另一个事件3845→3840，提前0.2秒 |
| 新长片seed27 | 两计数路径的事件帧和方向均保持 |
| 新长片seed28 | 3390→3385，提前0.2秒 |
| 原片seed26／27 | 各自两计数路径的事件帧和方向均保持 |
| 原片seed28 | 9705→9690，提前0.6秒 |
| Toros官方 | 原199事件消失，另一个291→289，提前2/30秒 |
| Toros旧五轮模型 | 新增134和215两个B→A事件，其余事件时间保持 |

这些比较使用帧与方向的多重集合，不用相同数字ID跨算法硬配。多个临时ID重新编号，轨迹坐标和输出行数也可能变化。

## 3 为什么官方反向片会退化

按发布方框检查本轮退化病例，候选中的临时ID5发生了如下对应变化：

| 源帧 | 原算法ID5的主要发布方框支持 | 候选ID5的主要发布方框支持 |
| --- | --- | --- |
| 150 | ID14，IoU约0.855 | ID14，IoU约0.854 |
| 153 | ID14，IoU约0.777 | ID14，IoU约0.776 |
| 162 | ID5无当前确认输出 | ID7，IoU约0.881 |
| 167 | ID14，IoU约0.929 | ID7，IoU约0.904；ID14由新ID15覆盖 |
| 199 | ID14，IoU约0.961，已产生对应通行事件 | ID7，IoU约0.917；新ID15缺少原ID5的B区起点 |
| 245 | ID14，IoU约0.902 | ID7，IoU约0.882，ID5在此产生了另一次事件 |

在源图与发布方框支持下，这说明候选将原有ID历史接到了邻牛，原牛随后被新ID覆盖；“轨迹活得更久”可以让总数变差。该检查是看到退化后进行的病例诊断，完整保留各框对全部发布方ID的IoU，不把最大IoU直接当全视频ID切换率或独立人工身份验收。

175个病例IoU另用向量化实现独立复核，数值一致。[病例坐标、参考支持与计数状态](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/results/reference_case.json>)及[独立病例复算](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/results/reference_case_verification.json>)可查。为避免全图缩小时ID标签重叠，另提供[四面板放大说明图](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/results/failure_focus/official_ID5_before_after.png>)，相同源帧153／167、蓝色发布方14、粉色发布方7、绿色只显示预测ID5，原生裁剪和坐标保存在配套记录中。

## 4 同步检查重叠双ID风险

在18组全部原生ROI输出中枚举6367对框，用预先固定的IoU≥0.5记录高重叠候选。该阈值用于筛查，**不是物理重复判定或身份合并规则**。

| 条件 | 有高重叠候选的采样时点：原→候选 |
| --- | ---: |
| 新长片4模型 | 各自0→0 |
| 原片seed26 | 2→4 |
| 原片seed27 | 0→0 |
| 原片seed28 | 1→1 |
| Toros官方 | 1→6 |
| Toros旧五轮模型 | 22→29 |

总计69条“ID对×采样时点”候选全部独立复算；同一时点可能多对，不能把该数当牛数或独立样本量。原片seed26候选10415帧有IoU约0.982的双ID，Toros旧五轮候选130帧约0.946；这些是进一步核对的具体位置。原片计数维持12也不能掩盖轨迹冗余，另一方面并排牛的框本来就可能重叠，不能看到高IoU就直接合并ID。

## 5 看全部成对视频

左侧是原融合第一阶段，右侧是纯IoU候选；视频展示当前交接计数路径。原片25帧/秒显示，在5Hz更新间保留最近一次预测；新长片使用5Hz源采样按原时间播放；Toros逐源帧30Hz。视频没有叠加新片助理参考。

| 资料 | 模型与回放 |
| --- | --- |
| 新长片群体80秒 | [官方](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/long_official_paired.mp4>) · [seed26](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/long_seed26_paired.mp4>) · [seed27](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/long_seed27_paired.mp4>) · [seed28](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/long_seed28_paired.mp4>) |
| 原片8912–10873，78.48秒 | [seed26](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/original_seed26_paired.mp4>) · [seed27](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/original_seed27_paired.mp4>) · [seed28](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/original_seed28_paired.mp4>) |
| Toros反向全片，479帧 | [官方：6→5的退化](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/toros_generic_paired.mp4>) · [旧五轮：2→4](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/videos/toros_pilot_paired.mp4>) |

静态病例：[缺口前153](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/cases/toros_generic_f00153.jpg>)、[重现162](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/cases/toros_generic_f00162.jpg>)、[新ID覆盖原牛167](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/cases/toros_generic_f00167.jpg>)、[参考事件附近199](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/cases/toros_generic_f00199.jpg>)、[原片高重叠10415](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/media_delivery/results/media/cases/original_seed26_f10415.jpg>)。Toros静态图额外显示发布方ID14蓝框、ID7粉框，绿色是预测框；预测视频只显示预测。

22张图来自运行前预设锚点；退化与最大重叠病例另增加9张事后诊断图，选择依据在媒体协议中注明。所有来源和标注层分别保留，不把事后挑图当盲测。

## 6 采用决策与后续顺序

1. **保持当前基线，不作全局替换。** 本轮候选在局部有价值，但已用参考回归出现官方6→5的退化，且部分高重叠候选增加。原片人工12头的成功模型和配置继续作为开发可用版本。候选保存为机制研究分支，不根据本轮结果临时增加视频、seed或牛个体特判来避开不利条件。
2. **若继续改关联，正反病例必须一起约束。** 新长片ID19恢复是正例，Toros ID5转跟邻牛是反例。应先固定能同时检验二者的动作／几何与竞争证据，再做单因素实验；单看更便宜的IoU或延长轨迹不足以证明正确关联。该方向还需要更多普通俯视新会话，避免只拟合两个病例。
3. **继续补可信评价。** 原片总数已验收；新片逐事件参考由独立人员接受后，再对全部冻结条件统一匹配。后续留出按日期、会话和相机在调参前冻结；真实双向仍需同一普通俯视通道中的牛通行，人员反向不充当证据。鱼眼分支保持归档。
4. **并行推进完整身份辅助链路。** 用保留的计数基线触发原图抓拍，缺码／延迟读码情形触发后台花纹编码、图库检索与未知拒识。评价应覆盖正确找回、错误找回、未解决、漏事件及队列延迟；模型track ID不能代替登记牛身份。已有公开身份实验要与真实事件裁剪建立对应后，才能作为系统结果。
5. **保持单板部署目标。** 服务器承担训练和离线验证，最终前台检测及后台身份推理均在PYNQ-Z2执行。板卡连接与镜像／工具版本到位后，核对模型映射、实际联合延迟、队列、丢帧、资源和能量。本轮CPU跟踪耗时不代替板上推理性能。

论文证据中，本轮应作为“局部恢复与跨条件退化的消融及失败分析”。去掉一处分数融合属于已知关联组件的配置控制，不能单独认领算法新颖性；可发表的贡献仍需独立评价、完整身份触发链路和实际资源受限联合运行支持。研究总线见[从想法到论文](<C:/Users/Donson/Documents/ChatGPT/奶牛/研究总览_从想法到论文.md>)。

## 7 交付、复现与自审

回归CPU作业130351已`COMPLETED / 0:0`，22秒，2 CPU／8 GiB，无GPU、无检测前向或训练；[终态记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/evidence/status_01.txt>)及全部输出保留。141归档条目均安全解包和逐项校验。媒体作业130352同样`COMPLETED / 0:0`，3分59秒、4 CPU／8 GiB；[媒体终态](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/evidence/render_status_03.txt>)、69条目媒体包和完整日志均已取回。

独立复算覆盖36条完整计数路径、31166观察时点、9027个ROI中心、6367对框IoU、69条重叠候选及反向片8组参考评分。9视频8444帧在服务端及本机均完整解码；31张成对图与1张四面板病例说明图共66面板实际目视，48个栅格文件均校验。全部模型、确认前后两条计数路径、不利结果和失败病例均保留。[独立复算记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/results/independent_verification.json>)、[采用决策记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/results/adoption_decision.json>)、[实际回放代码](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/tools/replay.py>)与[本轮Review](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/Review与当前状态.md>)可查。媒体的终态、哈希、完整解码及目视范围另由本目录results/media_verification.json和evidence/visual_review.json记录；没有声称全部视频逐帧人工播放或新独立标注完成。
