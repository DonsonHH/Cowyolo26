from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=load(ROOT/'delivery/results/qualification/summary.json');v=load(ROOT/'results/independent_implementation_verification.json')
strict=load(ROOT/'results/strict_raw_bytes_verification.json');board=load(ROOT/'board_delivery/results/record.json');terminal=load(ROOT/'board_delivery/results/terminal.json')
assert q['primary_ordered_vectors_byte_exact']==q['legacy_numpy_vectors_byte_exact']==8 and len(strict['arrays'])==8
assert v['actual_board_raw_arrays_byte_exact'] and v['mean_training_vector_tensor_to_raw_ms']==140.31615075
assert terminal['close_error'] is None and terminal['vectors']==8 and terminal['warmups']==2
report='''# mosaic0.5主候选：同O8实机向量准入完成

2026年10月30日。固定mosaic050_seed26已完成训练图PTQ、同O8程序编译及8张真实PYNQ向量。独立有序整数参考、旧NumPy参考、原生CPU和实际板端的完整raw逐字节一致；未运行新的完整源视频或后台身份负载，因此暂不替换部署候选。

模型SHA为`628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb`。校准沿用旧128张训练图、顺序与直角朝向，128份输入张量hash均与旧记录相同；没有源片、Toros、开发验证或保留日期图进入校准。编译器60个原文件保持，使用原O8固件及ARM运行器。

| 已实际核查 | 结果 |
| --- | --- |
| 模型结构 | 单类cow，102个卷积；94个PL整数卷积、8个ARM整数深度卷积 |
| 图／驻留计划 | 2132个张量、383个程序节点、25对驻留；二进制完整独立解析 |
| Sigmoid类别查表 | 3个头共768个有符号INT8码与标量参考核对；80类仅检查元数据合同，未运行80类网络 |
| 软件训练向量 | 8张；有序参考、旧NumPy与原生CPU完整raw均逐字节一致 |
| 真实PYNQ执行 | 8张正式向量＋2次预热；完整raw与上述参考逐字节一致，含signed zero |
| 控制向量张量→raw | 正式8次平均140.32ms；不含相机、图像读取、计数或身份后台 |
| 设备终态 | PID26423正常结束且已不存在，安全关闭无错误，原O8 bit SHA保持 |

有序参考沿用此前明确的FP32 MatMul逐项乘加、标量C99 expf Softmax顺序。主合同在本候选结果之前固定，旧NumPy结果另存；本候选8向量恰好两者也一致，没有抹去旧320候选的历史差异。

板端8张向量中conf0.2以上预测数为1／3／1／1／3／2／1／1，这是实现控制向量的预测，不是视频通行真值或身份正确率。140.32ms是一次短测平均值，不能由它直接推断新模型完整系统约5FPS，也不能将新FP32反向3／6与旧实机速度拼接。

Slurm130634完成／0:0，用时32秒。量化库日志包含CPU亲和性设置失败后的回退提示，完整输入／输出门禁与主进程均完成；不把这段服务器时间作为板端速度。板上模型程序写入新的cow_research_o8_mosaic192_qual_20261030目录，未重新烧写bit，也未改运行器代码。

主机第一次打包在class_exact／classes_exact字段名映射检查处停止，未上传或执行板端网络；旧局部payload保留，新包只修字段名，数值门限不变。第一次读取板端归档早于归档完成，文件不存在记录保留；之后确认原归档进程已终态再取回，没有重跑向量。

编译结果包45,374,600字节，SHA `abff4bfac778ef5487e1ce8ff7ccd7e38fe42b06f404a7425e50f49a88de1d90`；板端结果包45,862字节，SHA `8fe4085714c8044514b2db75e87a6229139169ddd541fc31f1b9be415ba5b8f5`，均已下载并按逐文件清单校验。

下一步固定本权重，统一评价1571开发验证图、原片／Toros的FP32与QDQ，以及全部2654次真实O8视频推理和板端计数；之后再用新模型历史状态重测5Hz周期前台与实际身份后台。旧模型、计数规则和独立参考缺口保持，整体目标继续。
'''
f=ROOT/'新主候选量化与O8实机准入.md';assert not f.exists();f.write_text(report,encoding='utf-8')
f=ROOT/'Review与当前状态.md';assert not f.exists();f.write_text('''# 本轮Review与当前状态

量化、软件参考与真实8向量准入完成；完整视频质量与前后台约5FPS尚未为新权重证明，不能将这一阶段写成最终部署验收。

- 已核对固定checkpoint、60编译器原文件及128训练校准输入；无源片／验证／Toros校准泄漏。
- 2132张量／383程序节点、768查表码与8份真实板端raw独立复核，逐字节比较包含signed zero。
- 原程序、参考和固件保持，旧NumPy结果另存；两处主机准备／取回问题未触发重跑或阈值改变。
- 板端进程终态且消失，O8 bit不变；140.32ms只代表8张张量输入短测。
- IMPORTANT：量化库CPU亲和性回退提示保留，不伪称日志全部无提示。
- BLOCKER：新权重完整视频与周期负载未验，独立逐事件／永久身份参考仍待补。
''',encoding='utf-8')
evidence=['protocol/compile_v1.json','protocol/board_vectors_v2.json','results/transfer_verification.json',
    'results/independent_implementation_verification.json','results/strict_raw_bytes_verification.json',
    'delivery/results/qualification/summary.json','delivery/results/qualification/actual_calibration_inputs.json',
    'board_delivery/results/record.json','board_delivery/results/terminal.json','board_delivery/final_state.json',
    'evidence/board_precheck.json','evidence/board_collection.json','evidence/board_get.json','evidence/board_get_v2.json',
    'evidence/board_transfer.json','evidence/payload_preparation_v1_failure.json','tools/compile_mosaic192.py',
    'tools/board_cow_vectors.py','reference/ordered_float_reference.py','reference/ordered_hybrid_executor.py']
documents=[]
for name in ['计划与验收.md','新主候选量化与O8实机准入.md','Review与当前状态.md']:
    path=ROOT/name;text=path.read_text(encoding='utf-8');assert '\ufffd' not in text;documents.append({'path':str(path.resolve()),'sha256':sha(path)})
r={'status':'FIXED_MOSAIC050192_PTQ_COMPILE_AND8_REAL_O8_TRAIN_VECTORS_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'checkpoint_sha256':q['checkpoint_sha256'],'actual_train_calibration_images':128,'all_calibration_tensor_hashes_exact_to_old':True,
    'compiler_workspace_original_files_unchanged':60,'primary_ordered_native_legacy_vectors_byte_exact':8,
    'actual_board_formal_vectors':8,'actual_board_warmups':2,'actual_board_raw_arrays_byte_exact':8,
    'mean_training_vector_tensor_to_raw_ms':v['mean_training_vector_tensor_to_raw_ms'],
    'class_LUT_codes_scalar_checked':768,'static_tensor_entries_parsed':2132,'static_program_nodes_parsed':383,
    'board_worker_terminal_and_absent':True,'new_bitstream_programming':False,'new_training_updates':0,
    'new_model_full_video_or_joint5FPS_proven':False,'whole_goal_complete':False,
    'evidence_hashes':{name:sha(ROOT/name) for name in evidence},'documents':documents}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ['evidence_hashes','documents']}))
