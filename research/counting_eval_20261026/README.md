# 奶牛计数参考评价与真实反向样本

本轮从已有开发基线推进到逐事件评价。优先阅读[计数评估与下一步](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/计数评估与下一步.md>)。

已完成：新增外部源视频和发布方轨迹核查、两个真实图像运动方向的覆盖、固定模型/参数的14组外部回放、6次参考通行的量化比较、5条荷斯坦源图标注草案和计数/匹配边界测试。

最关键结果：外部`Toros`参考轨迹导出6次完整B→A事件，官方模型匹配6次，五epoch微调模型匹配2次。样本只有一个片段和一个方向，不能将其写成全场100%准确率或跨场景成熟结论；该差异提示需要检查俯视适配后的侧视表现。

## 1 查看结果

- [源图中的六次参考通行](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/source_review/six_reference_passages.jpg>)
- [参考事件匹配与计数结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/results/metrics.json>)
- [冻结协议](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/annotations/evaluation_protocol_v1.json>)
- [荷斯坦源图草案](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/annotations/multicam_source_events_v1.csv>)及[其覆盖边界](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/annotations/multicam_review_scope.json>)
- [Review与复现状态](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/Review与复现状态.md>)

可直接播放的H.264预览在`previews`，按原始时序播放：

- 真实右→左：[官方模型](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/previews/reverse_generic.mp4>)、[五轮微调模型](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/previews/reverse_pilot.mp4>)。本片有6事件参考。
- 真实左→右：[官方模型](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/previews/forward_generic.mp4>)、[五轮微调模型](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/previews/forward_pilot.mp4>)。本片仅展示预测，尚无完整事件参考。

四个视频均通过全帧解码和帧数检查，反向片段479帧，正向片段606帧。[视频核验记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/results/local_preview_checks.json>)保存编码、时长与哈希。`delivery/counting_evaluation/media`保留经传输校验的MPEG4 Part 2预览，H.264是其另存的兼容副本。服务器保留原始完整推理输出。

交付包`results/counting_evaluation_delivery.tar.gz`为91,718,697字节，SHA256为`eed889d5659e4f66e946b940dba0e58d3254cfcae8265207cb06e9225ea9622a`。本地核验33个清单文件，并用不同实现从原始轨迹重建事件、穷举一对一匹配，结果与服务器评分一致，详见[独立复算记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_eval_20261026/results/local_independent_verification.json>)。

## 2 复现流程

服务器根目录：`/share/home/renly/projects/idcoo_research_20261026/phase2`。每次运行先按use-renly-slurm检查身份、实时分区和已有队列，输入离线可读后再提交计算。

```bash
cd /share/home/renly/projects/idcoo_research_20261026/phase2
sbatch tools/author_gt_audit.slurm
sbatch tools/external_inference.slurm
sbatch tools/score_counting.slurm
```

三个阶段按顺序执行并核对终态与产物；新的实验应先创建独立运行目录，保留本轮冻结结果。评价配置在`annotations`；通用与微调checkpoint、输入尺寸320、confidence0.2、ByteTrack、区域阈值和稳定帧数均固定，没有外部数据再训练。

本轮外部推理129675、测试评分129683、最终导出129690均为COMPLETED/0:0。两次编码失败保留在运行记录中；最终导出改为服务器MPEG4传输、本地H.264转码。临时下载代理已关闭并核实端口不再监听。

`tools/zone_counter.py`实现完整跨区计数；`event_metrics.py`进行最大匹配数量优先、最小时间误差的一对一分配，方向在匹配后评分。两组单元测试检验折返、临界抖动、边界截断、缺失、重复和错误方向，不把合成测试当成真实通行证据。

## 3 状态边界

发布方参考轨迹评价与代理源图草案分别保存。后者仍为`produced_not_user_validated`，且不完全盲标；拥挤区待补标，不能由草案推导全片精度。

真实相反方向来自不同源视频与视角；同一固定俯视通道的双向/相向重叠验收尚未完成。花纹身份、现场RF和PYNQ-Z2推理性能都属于后续阶段。
