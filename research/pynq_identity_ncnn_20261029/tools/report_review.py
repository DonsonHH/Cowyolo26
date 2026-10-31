from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=load(ROOT/'results/independent_board_verification.json');e=load(ROOT/'results/independent_export_verification.json')
assert b['actual_model_vectors']==e['vectors']==132 and b['all132_runtime_photo_tensor_bytes_exact_to_server']
assert b['retrieval_decisions']==144 and b['all_retrieval_decisions_exact']
report=f'''# PYNQ-Z2身份编码器：实际ARM运行与部署一致性

**现有奶牛身体花纹编码器已在同一块PYNQ-Z2的ARM上完成132张图的真实网络推理。** 归一化特征与服务器Torch参考的最大绝对差异为{b['maximum_normalized_feature_difference']:.8g}，两种图库下共144个查询的第一名及拒识决定保持一致。网络张量输入到576维特征平均{b['model_ms']['mean']:.2f}ms、P95为{b['model_ms']['p95']:.2f}ms；不包含高分辨率抓拍、读取、预处理或与前台并发的耗时。

这证明部署实现与既有编码器相符，**并未新增永久身份识别准确率证据**。接下来实际运行同板前台YOLO和后台编码器，测资源竞争、触发照片和检索队列。

## 固定模型及输入

选用既有`C_letterbox_trained_seed26`，与前台固定seed26对齐，未根据新检索结果挑模型。模型为MobileNetV3-small特征骨干＋平均池化＋Flatten，输出576维，再做L2归一化；阈值保持0.8445389603236383。权重SHA-256：`{b['encoder_checkpoint_sha256']}`。

模型使用FP32导出与FP32权重，ncnn参数图120层，包含卷积、深度卷积、池化、全连接、HardSwish等九类显式算子。ncnn与pnnx固定20261020版本，使用发布方哈希核验；源tag和文件哈希均保留。官方文档提供PyTorch→pnnx→ncnn路径及ARM构建方法，这些是实现选择依据；实机结果来自本目录记录。[官方转换说明](https://github.com/Tencent/ncnn/wiki/use-ncnn-with-pytorch-or-onnx) · [官方ARM构建说明](https://ncnn.readthedocs.io/en/latest/how-to-build/how-to-build.html)

132图包括30张Aug14历史图库、30张Aug19图库、60张既有带标签查询和12张原片真实事件抓拍。Aug14同次通行图库是泄漏控制，不能作为独立评价；以Aug19图库查询Aug14事件属于回顾实验，也不等于真实上线时的注册顺序。12事件查询没有可靠永久身份标签，因此全部保留`identity_reference_available=false`的边界。

## 实际完成的核对

- 服务器分别完成132次Torch和132次ncnn图条件前向；每个向量文件含输入、原始特征和归一化特征，独立重算范数、余弦与144个检索决定。导出追踪／转换工具内部探针单独说明，未混入这264次计数。
- ARM在2次预热后完成132份正式向量，Pillow实时预处理也逐图运行。132张照片生成的输入张量与服务器参考逐字节一致；输出以事先固定的1e-4特征误差、1e-5余弦误差和排序／拒识一致性门限验收。
- 实际ARM图像输入、576维原始特征、归一化特征和运行记录全部取回。独立复算132组特征和144个检索决定，库文件、参数及权重哈希均核对。没有安装Torch或替换板卡全局NumPy／Pillow，也没有改变PL配置。

## 保留的故障与修正

1. 服务器作业130569在转换文件已经生成后，尝试导入带数字属性名的工具生成Python时失败。保留该作业和文件，130572直接复用ncnn参数／权重完成真实132图一致性检查，未重复训练或改变模型。
2. 首次ARM构建默认开启VFPv4。在`NCNN_RUNTIME_CPU=OFF`时，官方CMake追加`-mfpu=neon-vfpv4`，覆盖了Cortex-A9的NEON目标，原生创建阶段报SIGILL。保存初版库、readelf属性和独立子进程-4退出记录；新目录显式`NCNN_VFPV4=OFF`，产物仅需NEON／VFPv3。初次SIGILL发生在网络运行前，没有称为成功推理。
3. 第二次向量任务执行4次正式向量、2次预热后在照片预处理门禁失败。服务器Pillow11.3对等比缩放和补边位置使用round，板上Pillow9.0.1使用int截断；132图中81张输入不同。保留错误结果，使用明确的round几何复现原服务器变换；第三版先核对全部132输入，再进行网络推理，全部输入字节相同，原数值与检索门限未放宽。

成功板端PID2149正常结束；前两轮构建及失败向量均保留。新兼容库SHA-256为`{b['bridge_library_sha256']}`。当前结果只支持这一固定模型、输入集与运行环境的部署一致性，不代表整套ncnn通用兼容性。

## 下一关口

[392时刻5Hz周期与同板后台](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_periodic_joint_20261030/计划与验收.md>)将使用当次实际前台计数事件、同帧原生分辨率物理通道图和当次检测框，真正执行照片裁剪、预处理、身份网络和跨日期图库检索。RFID未应答为模拟条件，摄像头由公开源回放提供；需分别报告前台跳帧、截止时间和后台等待，不能把两个网络各自平均速度相加推断并发达标。
'''
(ROOT/'身份编码器ARM实机部署与一致性.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

固定身份编码器的服务器转换和132图ARM实机向量验收已完成，全部198份板端归档文件哈希核对。132张实时预处理张量与原Torch参考逐字节一致，132份归一化特征和144个检索决定独立复算通过。

自审保留三类失败：pnnx生成Python数字属性名、VFPv4不兼容、Pillow截断／取整差异。原文件和输出未覆盖，既有权重、图库及阈值未重新选择。PYNQ全局包与PL配置保持。成功132＋2次预热、此前失败4＋2次预热、转换内部探针分别计数。

身份端侧部署一致性已有实测证据。实际耳标读失败、永久身份真值、现场高分辨率相机和同板联合5Hz均未由这一阶段证明；联合实机任务另行验收，整体研究目标保持进行中。
''',encoding='utf-8')
docs=[ROOT/r for r in ['部署依据与计划.md','身份编码器ARM实机部署与一致性.md','Review与当前状态.md']]
evidence=['protocol/encoder_v1.json','protocol/board_build_v1.json','protocol/board_build_v2.json','protocol/board_vectors_v1.json','protocol/board_vectors_v2.json','protocol/board_vectors_v3.json',
 'results/independent_export_verification.json','results/independent_board_verification.json','results/export_transfer_verification.json',
 'evidence/source_staging.json','evidence/server_Pillow_sources.json','evidence/board_Pillow_sources_and_diag_progress.json','evidence/board_native_exit_diagnostic.json',
 'board_delivery/build_v2_result.json','board_delivery/vectors_results_v2/record.json','board_delivery/vectors_results_v3/record.json',
 'board_delivery/vectors_results_v3/terminal.json','board_delivery/vectors_results_v3/preprocessing_gate.json','tools/ncnn_encoder_v3.py']
record={'status':'FIXED_BODY_ENCODER132_ACTUAL_ARM_VECTORS132_PHOTO_INPUTS_AND144_RETRIEVAL_DECISIONS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'encoder_checkpoint_sha256':b['encoder_checkpoint_sha256'],'actual_ARM_formal_vectors':132,'warmups':2,
 'prior_failed_formal_vectors':4,'prior_failed_warmups':2,'all_runtime_photo_input_tensors_exact':132,
 'max_normalized_feature_error':b['maximum_normalized_feature_difference'],'retrieval_decisions_exact':144,
 'mean_tensor_to_feature_ms':b['model_ms']['mean'],'FP32_model_and_weights':True,'PL_actions':0,
 'global_Pillow_or_numpy_changed':False,'failed_native_SIGILL_and_Pillow_input_evidence_preserved':True,
 'new_permanent_identity_accuracy_proven':False,'simultaneous_frontend_execution_in_this_record':False,
 'new_training_updates':0,'whole_goal_complete':False,'evidence_hashes':{r:sha(ROOT/r) for r in evidence},
 'documents':[{'path':str(doc.resolve()),'sha256':sha(doc)} for doc in docs]}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ['evidence_hashes','documents']}))
