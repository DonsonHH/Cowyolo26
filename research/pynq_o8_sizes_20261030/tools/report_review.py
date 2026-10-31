from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=load(ROOT/'results/s256_board_verification.json');b=load(ROOT/'results/s320_board_verification.json');c=load(ROOT/'results/ordered_reference_verification.json')
old=load(PROJECT/'pynq_rot192_compile_20261029/results/independent_implementation_verification.json')
assert a['actual_board_qualification_vectors']==b['actual_board_qualification_vectors']==8 and a['full_raw_bytes_exact'] and b['full_raw_bytes_exact_to_ordered_reference_and_native']
report=f'''# 192／256／320统一到用户O8引擎的真实板端检查

三尺寸现已都在同一块PYNQ-Z2的`yolo26_optimization_8`固件上实际执行奶牛单类模型。此前320用O6得到约1056ms的历史结果保持；它与本轮O8的结果分开，不能把混合引擎比较当作纯分辨率效应。

## 本次受控向量结果

| 输入 | 固定权重 | 正式向量／预热 | 张量至raw平均ms | 本表平均耗时倒数FPS | 本次已覆盖范围 |
| --- | --- | --- | --- | --- | --- |
| 192 | S192_rot90_seed26 | 8／2 | {old['mean_training_vector_tensor_to_raw_ms']:.2f} | {1000/old['mean_training_vector_tensor_to_raw_ms']:.2f} | 另已完成真实完整视频与同板后台回放 |
| 256 | S256_rot90_seed26 | 8／2 | {a['tensor_to_raw_ms']['mean']:.2f} | {1000/a['tensor_to_raw_ms']['mean']:.2f} | 仅训练校准向量资格与受控耗时 |
| 320 | S320_rot90_seed26 | 8／2 | {b['tensor_to_raw_ms']['mean']:.2f} | {1000/b['tensor_to_raw_ms']['mean']:.2f} | 仅训练校准向量资格与受控耗时 |

不同尺寸使用各自预先训练并冻结的seed26权重，因此这仍不是“同一权重只改输入尺寸”的消融。三者结构、单类头、128张训练校准图及方向日程、编译源码、94PL＋8ARM深度卷积、O8固件及运行选项保持相同。

256与320的8个正式向量均超过200ms，只是受控张量模型执行已超出5Hz单帧预算；没有把平均耗时倒数冒充包含相机、预处理、跟踪和身份后台的系统吞吐。本轮不扩充256／320完整视频或后台计数结果，也不据这8张训练图推断最终精度。

## 320的严格数值差异与参考口径

初始CPU资格作业130593_1为FAILED／2:0：8张中7张完整raw与旧NumPy参考一致，第5张产生低置信候选差异；当前conf0.2保留的两个检测框仍逐字节一致。这个失败及原始数组、协议和日志保持。

一次固定失败向量的实际探针在关闭／开启软件融合时都复现差异。按输出依赖筛去未执行的死张量后，首个有效浮点差异出现在注意力MatMul；后续一个量化元素跨过半整数边界：

| 项目 | 旧NumPy参考 | 原生C++ |
| --- | --- | --- |
| 注意力加法FP32值 | -1.7367326021 | -1.7367330790 |
| 除以量化尺度后 | -31.4999981 | -31.5000076 |
| 加zero-point -18后INT8 | -49 | -50 |

只在诊断参考中替换这一元素，完整raw立即等于原生结果，支持该单点数值原因；这不是部署时使用参照修补输出。没有改卷积、权重、校准、编译产物或固件。

随后在新协议中明确非卷积浮点口径：MatMul按K依次做FP32乘法／加法、不融合FMA；Softmax为FP32减最大、C99 expf、FP32顺序求和与除法。Python参考独立实现相同运算顺序，标量expf使用主机libm，未调用原生执行器。它消除了原先未明确的BLAS求和顺序差异；这是**参考合同的明确化，不是模型改进**。原误差门限没有放宽。

192／256／320共24个固定向量，在明确顺序的参考下都与既有原生CPU完整raw逐字节相同；旧NumPy参考仍为23/24。320实际板端8向量继而与明确顺序参考和原生CPU逐字节一致。该结果只覆盖固定向量，不能证明所有未来输入在不同数学库上均逐位一致。

## 实机与自审

256实际PID8572、320成功PID10501均完成2预热＋8正式向量，安全释放且进程退出，已知O8固件保持。未重新编程或改写用户O8目录。320第一次板端PID10019因尺寸文本替换误改SHA256函数名，在图实例化／推理前失败；脚本、日志、空结果保留，新脚本只修改尺寸与新输出路径，哈希函数回归检查后执行，失败未记作网络前向。

8个256、8个320实际raw均取回独立核查；24参考数组、INT8单点干预数组、编译graph／plan及每个传输包哈希已复核。320原完整NumPy门禁失败没有被后来的参考口径覆盖。细节见[数值独立核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_o8_sizes_20261030/results/ordered_reference_verification.json>)、[256板端](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_o8_sizes_20261030/results/s256_board_verification.json>)和[320板端](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_o8_sizes_20261030/results/s320_board_verification.json>)。

继续保持192为接近用户约5FPS条件的主候选；它已有实际前后台回放，但计数11／人工12、反向跨来源1/6仍未达成最终效果。提高分辨率与速度需要进一步方法／硬件权衡，不能仅由256／320在服务器上的计数更好就建议直接替换板端配置。
'''
(ROOT/'同O8三尺寸实机与320数值口径.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

补齐256和320的同O8实机资格及受控延迟，8＋8正式向量全部取回；192既有结果保留。表格区分张量执行、完整视频和同板后台，未将训练向量用作精度或整链FPS证明。

320初始NumPy完整raw差异保留为失败，三实际探针／单点INT8干预定位浮点累加边界。新协议明确MatMul和Softmax算术顺序，24固定向量与独立顺序参考一致；不是改权重、原生程序或放宽误差门限。320原NumPy失败仍为1/8，未改历史结论。

两尺寸实际板端输出与参考／原生CPU逐字节核对，固件保持，PID8572和10501已退出。首个320脚本SHA命名错误在推理前失败，原证据保留。后续仍需独立真实数据与普通俯视计数效果，整体科研目标进行中。
''',encoding='utf-8')
evidence=['protocol/sizes_v1.json','protocol/ordered_float_reference_v1.json','protocol/ordered_float_reference_v2.json','protocol/board_s256_v1.json','protocol/board_s320_v1.json','protocol/board_s320_v2.json',
 'results/compile_transfer_verification.json','results/failed320_parity_diagnostic.json','results/ordered_reference_verification.json',
 'results/s256_board_verification.json','results/s320_board_verification.json','numeric_delivery/results/probe320_causal/summary.json',
 'numeric_delivery/results/ordered_reference/summary.json','s256_board_delivery/results/record.json','s256_board_delivery/results/terminal.json',
 's320_board_delivery/results_v2/record.json','s320_board_delivery/results_v2/terminal.json',
 'evidence/status01.txt','evidence/s320_board_status01.json','tools/ordered_float_reference.py','tools/ordered_hybrid_executor.py','tools/board_s320_vectors_v2.py']
docs=[ROOT/f for f in ['计划与验收.md','同O8三尺寸实机与320数值口径.md','Review与当前状态.md']]
r={'status':'SAME_O8_S256_AND_S320_ACTUAL_BOARD_VECTORS_AND_ORDERED_FLOAT_REFERENCE_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_new_board_qualification_vectors':16,'actual_new_board_warmups':4,
 'same_O8_firmware_as192':True,'s256_mean_tensor_to_raw_ms':a['tensor_to_raw_ms']['mean'],'s320_mean_tensor_to_raw_ms':b['tensor_to_raw_ms']['mean'],
 's256_all8_over200ms':True,'s320_all8_over200ms':True,'all16_actual_raw_bytes_exact_to_native_and_qualified_reference':True,
 'ordered_reference_vectors_exact':24,'original_numpy_reference_vectors_exact':23,'original320_full_raw_failure_preserved':True,
 'reference_nonconv_float_order_explicitly_revised':True,'native_engine_weights_calibration_or_firmware_changed':False,
 'single_INT8_boundary_intervention_causally_restores_full_raw':True,'s320_first_failed_board_forward_count':0,
 'both_actual_board_processes_terminal_and_absent':True,'new_training_updates':0,'full_video_count_or_joint5FPS_at_256_or320_proven':False,
 'whole_goal_complete':False,'evidence_hashes':{f:sha(ROOT/f) for f in evidence},'documents':[{'path':str(f.resolve()),'sha256':sha(f)} for f in docs]}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['evidence_hashes','documents']}))
