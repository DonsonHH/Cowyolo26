# 三seed可训练整数前向与准入结果

2026年10月28日。承接[整数参考与图优化定位](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_reference_20261028/图优化残差加法定位与下一步.md>)。

**三个seed的整数前向已接入可训练STE路径，并完成各2次真实更新后的导出检查。六个初始／更新后模型的8个训练回归输入全部通过，2496个逐层累加条件经独立实现核验一致。** 这使原定六轮配对训练具备数值与梯度准入依据。本阶段6次更新用于冒烟检查，正式六轮QAT仍未执行。

## 1. 固定实现与检查对象

使用此前三个身份编码器权重、同64张训练校准图及同8张回归输入。Conv/BN在CPU合并，观察器完成后固定尺度；整数点积用DOUBLE卷积处理整数操作数实现，并检查INT32绝对和上界，再按已规定顺序重建为FP32。非卷积运算保留FP32。[事前计划](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/执行计划.md>)、[冻结协议](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/protocol/trainable_integer_smoke_v1.json>)。

反向定义为截断直通估计STE：输出截断位置的梯度为0，其余位置通过量化后浮点Conv计算输入、权重和偏置梯度，再应用输入／权重截断掩码。采用普通和深度卷积分别在CPU、GPU与显式Autograd代理检查。CPU最大差约1.91×10⁻⁶，GPU两个条件差为0，均小于预设10⁻⁵；截断位置梯度为0。这检验声明的代理梯度公式，不采用离散舍入函数的有限差分作真梯度。[实现](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/tools/integer_trainable.py>)、[梯度控制](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/delivery/results/smoke_v2/gradient_controls.json>)。自定义前向／反向的接口依据[PyTorch2.8扩展文档](https://docs.pytorch.org/docs/2.8/notes/extending.html)。

主门槛保持最大特征差≤0.001、余弦≥0.9999、打包前后差≤10⁻⁶，并增加CPU/GPU前向一致性检查。OFF及ALL禁用QDQ融合均为必过路径，默认ALL作为额外对照保留。

## 2. 首次失败与修复

129989先完成三个seed初始8输入检查，第一次反向后在参数更新前退出。四组损失控制随后发现：104个参数张量中，缺梯度的34个恰好都是Conv/BN合并后仍为`requires_grad=False`的偏置；其余梯度均有限。蒸馏、triplet、组合损失和直接距离triplet条件得到相同结论。

修复只在CPU合并后启用全部参数梯度，并另建结果目录。权重初值、损失、数值规则、协议与门槛不变；新旧初始前向也逐位一致。旧脚本、失败日志和诊断保留。[修复差异记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/results/retry_v2_provenance.json>)、[四损失诊断](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/delivery/results/backward_probe/summary.json>)。

## 3. 全部模型结果

表中OFF、禁融合ALL、默认ALL均为CPU Torch参考与相应ORT输出的比较；CPU/GPU列另作跨设备前向检查。每个单元的分母都是同8张训练回归输入。

| seed | 状态 | CPU/GPU | OFF | ALL禁QDQ融合 | 默认ALL | 该状态的最大Torch/ORT特征差 |
| --- | --- | --- | --- | --- | --- | --- |
| 26 | 初始 | 8/8 | 8/8 | 8/8 | 8/8 | 1.19×10⁻⁷ |
| 26 | 更新2次后 | 8/8 | 8/8 | 8/8 | 8/8 | 7.45×10⁻⁸ |
| 27 | 初始 | 8/8 | 8/8 | 8/8 | 8/8 | 1.04×10⁻⁷ |
| 27 | 更新2次后 | 8/8 | 8/8 | 8/8 | 8/8 | 7.45×10⁻⁸ |
| 28 | 初始 | 8/8 | 8/8 | 8/8 | 8/8 | 1.49×10⁻⁷ |
| 28 | 更新2次后 | 8/8 | 8/8 | 8/8 | 8/8 | 5.96×10⁻⁸ |

各seed的两次更新都产生104个有限梯度张量；每个seed有98个参数张量改变，量化参数／缓冲保持不变。训练批次为P8K4，AdamW学习率3×10⁻⁵，蒸馏加0.25×triplet损失，使用确定性训练预处理。这里验证更新与导出，完整研究训练仍按预先固定的配对增强和120次更新执行。

六图均打包52组权重，912008字节的整数权重常量；图约1.233MB，DOUBLE重建、FP32偏置及其他运算保留。48个打包前后检查通过。[192个前向比较CSV](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/results/forward_metrics192.csv>)、[完整摘要](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/delivery/results/smoke_v2/summary.json>)。

## 4. 与上一轮整数参考的初始化差异

本轮seed26初始特征与上一轮整数参考最大相差0.0286511。补查发现上一轮在GPU合并Conv/BN，本轮在CPU合并。全部52层旧图与GPU合并权重／偏置逐位相同，本轮与CPU合并逐位相同；输入和源checkpoint一致。

两种合并路径有128707个浮点权重元素不同，最大差3.81×10⁻⁶；经过重新观察尺度和量化后有6个权重整数不同、49层存在量化参数差异。这说明后续配对必须固定同一合并设备和初始状态，不能从不同数值初始化分别启动两分支。[实测记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/results/initialization_probe.json>)、[本机核验](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/results/initialization_local_verification.json>)。

本轮默认ALL全部通过，同时保存的六个实际优化图各有2个QLinearAdd。该结果对应新的CPU合并／校准和导出图，不覆盖上一轮GPU合并候选的默认6/8失败。[实际导出图审计](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/delivery/results/export_graph_audit.json>)。仅凭本轮通过，还不能分别量化合并差异与图结构对旧融合失败的贡献。

## 5. 独立核查与交付

独立程序使用NumPy INT64窗口点积替代主程序DOUBLE Conv，检查六模型×8输入×52层，共2496个累加条件、67951488个累加元素，与ORT INT32输出完全一致；并重算最终特征、量化权重编码、固定尺度、参数改变量和输入角色。主程序／服务器独立实现／本机保存张量重算的144组ORT指标一致，另48组CPU/GPU指标、48组打包检查均通过。实际读取216张图，全部属于训练角色且hash对应，验证和留出图未读取。[独立核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/delivery/results/independent_verification.json>)。

作业129989失败、129990诊断完成后，129991修正版冒烟正常结束，48秒；129992独立核查16秒、129993收集8秒、129994初始化核查5秒，均COMPLETED/0:0。GPU为V100S，运行环境Torch2.8.0、ORT1.23.2。主机进程MaxRSS约1.58GiB，属于训练／导出工作负载。[训练与交付终态](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/results/delivery_status_01.txt>)、[初始化终态](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/results/initialization_status_01.txt>)。

82个清单文件和包hash已逐项核对，包57733931字节，SHA-256为`6eb73f945710e67b1cf0421a6f1dd35d497e49d6848fb37f9ce94ab64faf951e`。初始化核查在打包之后，单独保存hash与终态。导出TracerWarning来自Python侧上界断言，实际导出算子由symbolic明确规定；本轮只验收固定batch1和8回归输入，不据此认领动态形状或所有输入通过。序列化图的运行环境提示也保留。[本机交付核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/results/local_verification.json>)。

## 6. 当前决策

后续执行更新：原定[六轮配对训练](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_qat_20261028/六轮配对QAT与身份验证结果.md>)现已完成，QAT360／浮点360更新。本文中的正式0次与6次冒烟更新对应本阶段，原准入结果不变。

三seed冒烟准入通过。下一步从相同CPU合并初值分别启动浮点继续训练与整数前向QAT，各seed固定六轮、每轮20个相同P8K4批次；记录配对增强张量hash，固定末轮模型并保留全部seed。只在既有开发验证图库／查询上标定并比较接收、错配和未知误接收，旧已用测试继续排除。

正式训练权重从初值重新开始，这6次冒烟更新不参与学习结果。当前数值实现仍是DOUBLE整数卷积参考，最终定点映射、板上延迟／内存及检测与身份联合运行另行验收。完整自审见[Review](<C:/Users/Donson/Documents/ChatGPT/奶牛/integer_trainable_20261028/Review与当前状态.md>)。
