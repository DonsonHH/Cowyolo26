# Review与复现状态

2026年10月27日。已逐项回查本次范围协议、原始轨迹、源帧端点、媒体、页面和报告。

| 等级 | 核查项与结论 |
| --- | --- |
| 已核查 | 范围8912–10873，含两端1962帧；四个导出视频均78.48秒、25fps并完整解码 |
| 已核查 | 两组预测事件由独立状态机重算，逐项等于服务器结果：官方0、五轮模型7次向下 |
| 已核查 | 浏览器同步播放，两路WebM均readyState4且媒体时间相同；源帧9420跳转显示实际检测框 |
| 已核查 | 既有标注localStorage键、事件格式、原片hash保持原样；独立QA中的2条旧事件在聚焦切换后保留 |
| IMPORTANT | FFmpeg与OpenCV端点RGB不是逐位相同；顺序解码的同号帧比相邻帧更接近，保留全部差异数字 |
| IMPORTANT | 本次重放此前实际推理，没有新的模型训练；7是预测，不是准确率或已确认档案身份 |
| IMPORTANT | 旧Toros 6/6与2/6、当前俯视0与7分别按原范围保留，未用新演示覆盖旧结果 |
| BLOCKER | 最终独立计数评分仍缺人工JSON；此项不阻止使用公开牛体框继续训练和源片效果演示 |
| BLOCKER | 最终硬件验收缺PYNQ连接、镜像及工具版本；当前预览为服务器离线推理输出 |

服务页面：[模型对照](http://127.0.0.1:8779/annotation_workbench/model_preview.html)。服务关闭后可直接打开[训练模型MP4](<C:/Users/Donson/Documents/ChatGPT/奶牛/source_demo_20261026/previews/pilot_f8912-10873.mp4>)。

复核命令：本地媒体生成脚本`tools/prepare_local_preview.py`保存了严格解码与独立事件算法。其输出不覆盖现有文件；复跑前应使用新的输出目录保留本轮产物。源帧核对使用顺序解码`select`的帧编号，第一次时间快速seek失败文件保留为诊断证据。

报告与证据：[主要报告](<C:/Users/Donson/Documents/ChatGPT/奶牛/source_demo_20261026/指定源视频范围与训练路线.md>)、[全部媒体核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/source_demo_20261026/results/local_preview_verification.json>)、[交付清单校验](<C:/Users/Donson/Documents/ChatGPT/奶牛/source_demo_20261026/results/local_delivery_check.json>)、[浏览器截图](<C:/Users/Donson/Documents/ChatGPT/奶牛/source_demo_20261026/results/browser_preview.png>)。
