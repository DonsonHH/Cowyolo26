# Cows2021数据准入完成与三seed训练

更新：2026年10月27日。数据准入已完成；截至北京时间21:55（日志13:55 UTC），正式训练作业129918仍在运行，seed26/27各完成10轮，seed28到第8轮。全部模型尚未共同冻结，回放与计数效果尚未产生。

## 1. 数据用途与实际准入

本阶段承接[完整来源与日期分组核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_labels_20261027/原始标注准入与来源恢复.md>)，实际取得8380张原图，完成完整解码、官方归档逐图CRC/大小核对、重复筛查及真实标签加载，再通过CUDA短跑进入正式训练。

| 用途 | 日期 | 图像数 | 当前使用 |
| --- | --- | --- | --- |
| 训练 | 2020-02-05至02-27 | 6809 | 原图/标签准入，正式训练 |
| 验证开发 | 2020-02-28至03-04 | 1571 | 原图/标签准入，训练期间开发验证 |
| 开发保留 | 2020-03-05至03-09 | 1400 | 本阶段未取得像素 |
| 最终日期留出候选 | 2020-03-10至03-11 | 622 | 本阶段未取得像素，最终独立性未确认 |

按发布方目录看，8380张包括Train/train的7248张、Train/val的1023张及Test/val的109张。109张拍摄于3月4日，依模型运行前固定的日期规则进入本项目验证开发角色，不声称重现发布方原split成绩。3月8/9日原视频已用于开发，继续排除在新最终日期留出之外。

[固定图像清单](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/input/image_fetch_manifest.json>)、[准入协议](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/protocol/data_admission_v1.json>)。

## 2. 原图完整性与重复检查

补取轮次正常结束，工具返回退出码0。8380张合计2,747,795,477字节，与官方ZIP中对应成员的解压后大小合计一致。Slurm129914完整执行Pillow验证/解码及OpenCV解码；旧OpenCows归档也在同作业内重新校验，并对11779张旧图用同一解码器重算指纹后比较。

| 检查项 | 实际结果 |
| --- | --- |
| 新图像完整解码 | 8380/8380，错误0，尺寸均1280×720 |
| 新批完全字节重复组 | 0 |
| 新批完全RGB像素重复组 | 0 |
| 跨训练/验证的完全重复隔离成员 | 0 |
| 与旧OpenCows完全字节/RGB重用图像 | 0 |
| 跨角色dHash距离≤2的复核线索 | 0 |
| 旧图Windows/Linux指纹差异 | 0 |

该结果限于本次完全重复和相似线索筛查，不证明不同农场、不同牛群或全部潜在时间邻近关系独立。最终日期留出和跨场泛化仍待分别验收。[图像审计](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/image_audit_01/summary.json>)、[重复明细](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/image_audit_01/overlap.json>)。

独立Slurm129915将每张原图CRC和大小与官方ZIP中央目录逐项比对，8380张全部一致，并重算下载SHA256。CRC在此用于字节完整性检查，不作为密码学签名。[逐图CRC结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/source_archive_CRC_audit.json>)。

## 3. 标签与真实加载器

标签定义为可见旋转奶牛躯干多边形的轴对齐包围框，映射到检测类别0。只使用发布方cow标注，不把head对象、annotation编号或临时track ID当作个体身份。

Slurm129916从发布JSON重算全部13165个元数据包围框，与原派生结果最大差约2.27×10^-13像素，再建立独立图像别名与九位小数YOLO文本。Ultralytics8.4.63真实加载器的全部成员、类别和逐行float32框均与预期一致：

| 角色 | 图像 | 实际加载框 |
| --- | --- | --- |
| train | 6809 | 8888 |
| val | 1571 | 1864 |

加载后又重算全部原图/标签hash，确认加载器未修改源字节。本机另核对下载清单、逐图CRC、来源URL、角色框数、图像/loader摘要和短跑记录的hash关联。[loader结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/labels_v1/summary.json>)、[源字节不变](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/source_immutability_after_loader.json>)、[本机交叉复核](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/data_admission_independent_reconciliation.json>)。

## 4. 训练规则与CUDA短跑

[训练协议v1](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/protocol/detector_v1.json>)在新模型运行前写定：

- 官方YOLO26n COCO权重重新初始化每个seed，不继续旧牛体模型。
- seed26/27/28各10轮，320输入、batch32、显式AdamW、初始学习率0.002、AMP关闭。
- 每个seed统一取末轮last.pt，best.pt仅存档；三个模型共同冻结后才回放源片和Toros。
- 保留全部seed，不按视频计数或开发AP挑选一个作为最终模型。

该实验与此前OpenCows运行的数据来源、标签和验证集不同，是适配模型的开发比较，不将结果变化归为纯数据量或合成比例效应。CSV末轮指标与框架返回的best指标分别存放。

Slurm129917完成两次真实CUDA前向、反向及AdamW更新，损失与梯度有限，366个参数张量发生变化。短跑权重不保存用于正式训练；新作业重新读取官方源权重。[短跑结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/preflight.json>)。

## 5. 已核实作业状态

| 作业 | 工作 | 状态 |
| --- | --- | --- |
| 129903 | 实际模块/环境与13165个元数据几何预检 | COMPLETED / 0:0 |
| 129907 | 固定前64训练图与99标签的小范围真实loader | COMPLETED / 0:0 |
| 129914 | 全8380图解码、旧11779图同解码器比较与重复筛查 | COMPLETED / 0:0，5分29秒 |
| 129915 | 全8380图官方归档逐图CRC/大小核对 | COMPLETED / 0:0，10秒 |
| 129916 | 派生标签与全量实际loader | COMPLETED / 0:0，23秒 |
| 129917 | 两次CUDA短跑，权重丢弃 | COMPLETED / 0:0，7秒 |
| 129918 | 三个seed各10轮正式训练 | 21:55实查RUNNING，seed28到第8轮 |
| 129919 | 三模型源片与Toros回放 | 成功依赖129918，21:55仍等待 |
| 129920 | 结果与复现材料打包 | 成功依赖129919，21:55仍等待 |

截至该快照，没有确认全部正式训练成功，也没有新模型视频计数成绩。短作业的Slurm内存采样不代表实际峰值，服务器结果不填入PYNQ-Z2性能表。[状态快照](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/pipeline_observation_02.json>)、[训练提交](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/training_submission.txt>)、[回放依赖](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/replay_collection_submission.txt>)。

## 6. 传输与失败记录

第一轮保留11项失败：10次连接重置、1次读取超时。确认原进程退出后，先重算8369张成功文件的hash，再只补缺图。旧失败清单和部分manifest没有删除或覆盖，TLS证书与域名校验保持开启。[补取决策与记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/transfer_resume_01_to_02.json>)、[完整下载摘要](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/download_attempt_02/summary.json>)。

主进程使用6线程；末尾300张另采用3线程缓存，最多合计9个请求工作线程。300张均经JPEG字节检查、SHA256及不覆盖已有文件的原子硬链接提交，供主清单写入者复用。调整只改变传输顺序与缓存，不增加样本或改变训练配置。[缓存协议](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/protocol/tail_cache_transport_v1.json>)、[缓存终态](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/tail_cache_summary_01.json>)。

原作者身份pkl和检测h5的公共入口也已核实，但内容没有下载/加载，训练继续使用本项目指定的YOLO26n初始化。[归档与作者权重核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/官方归档与作者权重核查.md>)。

## 7. 回放与后续验收

源片只导出8912–10873帧，共1962帧/78.48秒；仍从原始frame0顺序解码，每5帧推理一次，保留相同跟踪历史、ROI、区域阈值、稳定样本数和间隔规则。实际计数模块与本地已核验代码的字节/AST一致。[计数模块快照](<C:/Users/Donson/Documents/ChatGPT/奶牛/cows2021_adaptation_20261027/results/counter_source_snapshot.json>)。

Toros继续是已用过的6事件诊断，保留躯干训练框与整牛参考的范围差异。原片数量是预测，独立人工JSON到位前不填写准确率。回放完成后须独立复算事件、完整解码媒体并检查浏览器，再展示实际新结果。

最终日期候选622张、同一固定通道独立双向事件、原片身份对应、未知风险、整数数值及PYNQ-Z2联合实测仍分别待验。新参考素材核查尚未形成合格新测试集。[参考候选报告](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_reference_candidates_20261027/独立计数参考候选核查.md>)。
