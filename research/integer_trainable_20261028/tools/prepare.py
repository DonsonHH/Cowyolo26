from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
base = json.loads((PROJECT / 'qat_study_20261026/protocol/qat_v2.json').read_text(encoding='utf-8'))
target = ROOT / 'protocol/trainable_integer_smoke_v1.json'
assert not target.exists()
protocol = {'name': 'Three seed trainable integer-forward STE pre/postupdate gate v1',
    'created_UTC': datetime.now(timezone.utc).isoformat(),
    'scope': 'Trainingrole only. Numerical/gradient smoke, no validation, test, identityaccuracy or board claim.',
    'source_models': base['source_models'], 'manifest_sha256': base['manifest_sha256'],
    'calibration_manifest_sha256': base['calibration_manifest_sha256'],
    'prior_protocol_sha256': hashlib.sha256((PROJECT / 'qat_study_20261026/protocol/qat_v2.json').read_bytes()).hexdigest(),
    'calibration': 'Same64trainimages, floatobserver calibration then freeze; first8deterministictrainingvectors regression.',
    'numerical_contract': 'Integerdot products via exact bounded DOUBLEconv of integer operands, INT32bound checked; DOUBLEinputscale thenweightscale thenbias, FP32cast and explicitdivision/nearest-even outputquant. NonConvFP32retained.',
    'weight_contract': 'TrainableFP32masterweights, explicitdivide/nearest-even INT8then UINT8offset128 at export; all52arrays packed afterexport.',
    'gradient_contract': 'Declared clipped STE: exactforward outputclippingmask times quantizedFloatConv gradients; input/weight clippingmasks applied. Compared against explicitAutograd surrogate, not finitedifference derivative of roundedforward; no doublebackward.',
    'runtime_conditions': ['OFF', 'ALL_disable_quant_qdq', 'ALL_default_diagnostic'],
    'seeds': [26, 27, 28], 'actual_discarded_smoke_updates_each': 2,
    'training': base['training'],
    'gradient_controls': ['CPUordinary/depthwise', 'GPUordinary/depthwise', 'finite allmodel gradients', 'actualparameterschange', 'qparamsunchanged'],
    'gates': {'vectors': 8, 'maximum_absolute_embedding_difference': .001, 'minimum_cosine': .9999,
              'maximum_packing_error': 1e-6, 'maximum_STE_control_gradient_error': 1e-5,
              'GPU_CPU_forward_same_embedding_tolerance_required': True},
    'sequencing': 'Checkall3initialseedgates beforeanyupdates. Ifany fails, preserveallinitials and stopbeforeupdates. After2discardedupdatesperseed, re-export andreporteveryseed evenifpostgatefails. Noformal6epochQATinthisstage.',
    'formal_QAT_updates': 0, 'holdout_or_validation_allowed': False, 'FPGA_execution': False,
    'whole_goal_complete': False}
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
(ROOT / 'results').mkdir(exist_ok=True)
(ROOT / '执行计划.md').write_text('''# 可训练整数前向：三seed准入计划

2026年10月28日。先完成原数值规则的可训练实现，不直接进入正式六轮QAT。

1. 冻结同三源权重、同64训练校准图、原8向量和原特征/打包容差。
2. CPU/GPU普通与深度卷积比较声明的STE梯度公式，检查截断位置为零；这不是离散前向的数值微分。
3. 三seed分别校准、固定尺度，比较CPU/GPU前向和OFF/ALL禁用QDQ融合，默认ALL不利结果另报。全部初始seed通过后才更新。
4. 每seed仅做2次丢弃的真实训练更新，保存梯度、输入、参数/尺度摘要；重导出并检查全部8向量。正式QAT更新仍0。
5. 独立检查源hash、输入角色、全部条件与作业终态。若未通过，保留失败，不放宽容差或跳过seed。

INTEGER累加使用DOUBLE整数卷积作数值实现，重建保留DOUBLE、非卷积保留FP32，不等于最终定点硬件。三seed和更新后导出通过，也还需要完整配对训练、身份评价和PYNQ-Z2联合测量。
''', encoding='utf-8')
print(json.dumps({'protocol_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                  'seeds': protocol['seeds'], 'formal_QAT_updates': 0}))
