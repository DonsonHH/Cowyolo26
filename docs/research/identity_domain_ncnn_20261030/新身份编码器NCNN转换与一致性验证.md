# 新身份编码器的NCNN转换与一致性验证

2026年10月30日。保留域适配阶段预先指定的`C_domain_seed26`末轮模型，FP32 NCNN转换通过。630张图的输入逐图一致，1260条开发决定与Torch一致。校准端点有1条接受状态变化，原阈值继续冻结。这里验证实现一致性；新域的识别质量和低覆盖率结论仍由[配对训练报告](<../identity_domain_adapt_20261030/身份域适配配对训练与开发结果.md>)解释。

## 固定输入和工具

模型checkpoint SHA-256为`b435fb4599d307c0dd8bf3adccb42a466c271a3fdf23ab91d585d463b70cc912`。图库、查询、预处理及阈值均未改变，也没有读取保留的最终20个身份或后续日期图像。正式[运行协议](<../../../research/identity_domain_ncnn_20261030/protocol/run_v1.json>)先于执行冻结，SHA为`c597c8aa116cc9d8fcfba2c1f876691aef9b14931c890ef1a1137100c3085a57`。

图像为已用的Cows2021 540张及MultiCam保留90张，共630张；所有224输入均与上阶段逐字节hash相符。[独立输入核验](<../../../research/identity_domain_ncnn_20261030/results/input_hash_independent_verification.json>)同时核对原JPEG和10份完整张量锚点。文字计划曾写7份锚点，正式运行协议在执行前固定的是7份Cows加3份MultiCam，共10份；本次按正式协议执行。

在Slurm CPU作业`130863`运行，节点`cu03`，最终`COMPLETED / 0:0`，耗时23秒。直接运行既有pnnx可执行文件：`pnnx encoder.pt inputshape=[1,3,224,224] fp16=0 device=cpu`。转换器SHA为`4db234cb90a27dc15e04e0d0edf5706c7a488ab8e6235cf8c146c6ec80fd9355`。转换命令、返回码、原始日志和所有中间文件均取回；生成的Python包装文件仅保留，未执行。

Torch和NCNN各测量630次单图前向；NCNN单线程，FP16/BF16关闭。另观测到1次Python追踪前向，转换器内部TorchScript探针未计量，属于未知额外前向。因此1260是明确的测量前向数，不能当作整个转换流程的精确总数。本阶段没有训练更新，也没有板卡模型前向。

## 数值和决定

| 核查项 | 结果 |
|---|---:|
| Torch与此前存储归一化特征的最大绝对差 | 4.172325134277344e-7 |
| NCNN与本次Torch归一化特征的最大绝对差 | 2.4512410163879395e-6 |
| 两个20ID开发组、40ID压力及6ID保留的决定 | 1260条全部一致 |
| 校准组两个固定阈值的决定 | 240条中1条接受状态变化 |
| 原JPEG与实际224输入复核 | 630/630一致 |

转换门限沿用预先规定的归一化最大绝对差和余弦差，没有因结果修改。图库和查询都使用新NCNN特征重新计算，独立核验逐个身份的最高参考相似度、Top-1和接受／拒绝状态，记录见[独立复算](<../../../research/identity_domain_ncnn_20261030/results/independent_verification.json>)。

唯一校准差异位于全局图像索引89：Top-1始终为`Cows2021_IdentificationTest:035`，Torch拒绝、NCNN接受，最大注册身份分数差约1.066e-6。该图处于校准阈值端点，差异已经[完整保留](<../../../research/identity_domain_ncnn_20261030/delivery/results/export/calibration_endpoint_differences.json>)；未用NCNN重新校准，也未移动阈值隐藏差异。开发决定的完全一致与校准端点的变化分别报告。

## 产物和接下来的边界

新param SHA为`dd1a5af7c7f33b273508665f8332d3b48e847898981fc55989b2278022a98fe7`，新bin SHA为`2a587d0fe293d244eb5632feb0e3665cf6091243198612b59363a6a7bb173252`。param结构与旧模型一致，权重内容已经改变。运行使用的算子列表和逐图误差均保留在[原始结果](<../../../research/identity_domain_ncnn_20261030/delivery/results/export/summary.json>)及其同目录文件。

完整归档`new_encoder_ncnn_delivery_v1.tar.gz`为20,140,230字节，SHA为`488ead95ceac27a1b63fb23733de8d3e2bfdb927e1e2f19e6ced75c4d910bd28`，含33个成员、32个manifest文件；逐项hash核验完成。630份Torch／NCNN raw和归一化向量全部取回，复算不增加模型前向。

下一阶段把同一固定param／bin放入PYNQ-Z2独立目录，复用已验证的ARM库；先验证90张保留图与7张Cows锚点的真实输入、特征及耗时。该小样本实现检查不等于完整Cows身份评价，更不能推出与检测并发时稳定5FPS。板上默认encoder及O8继续保留，后续部署选择仍需按完整识别、拒识和并发实验决定。

自查已核对：模型及协议绑定、630输入、1260开发／240校准决定、校准端点、前向计数限制、完整归档与独立复算。当前没有由本阶段产生的论文发表或部署达标结论。
