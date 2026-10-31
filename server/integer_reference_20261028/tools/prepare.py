"""Freeze a bounded train-vector arithmetic experiment before computation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
REMOTE = '/share/home/renly/projects/idcoo_research_20261026'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = ROOT / 'protocol/integer_conv_v1.json'
    assert not target.exists()
    sources = [
        ('qat_study_20261026/delivery/results/smoke/initial_qat_unpacked.onnx', 'qat_study/results/smoke/initial_qat_unpacked.onnx'),
        ('qat_study_20261026/delivery/results/smoke/initial_qat_packed.onnx', 'qat_study/results/smoke/initial_qat_packed.onnx'),
        ('qat_study_20261026/delivery/results/smoke/export_parity_vectors.npz', 'qat_study/results/smoke/export_parity_vectors.npz'),
        ('qat_study_20261026/protocol/qat_v2.json', 'qat_study/protocol/qat_v2.json'),
        ('qat_study_20261026/tools/qat_components.py', 'qat_study/tools/qat_components.py')
    ]
    protocol = {
        'name': 'Explicit integer Conv accumulation with fixed floating boundary v1',
        'created_UTC': datetime.now(timezone.utc).isoformat(),
        'scope': 'Eight already-used calibration training vectors, seed26 fixed graph. Numerical diagnostic only; no accuracy, training, validation, test or FPGA claim.',
        'inputs': [{'local_source': l, 'remote_source': REMOTE + '/' + r,
                    'bytes': (PROJECT / l).stat().st_size, 'sha256': sha(PROJECT / l)} for l, r in sources],
        'preserved_baseline': 'Original QDQ + FP32 Conv; restore same52foldedConvweights/qparams and reproduce old7of8pass and failingindex3 before changing arithmetic.',
        'candidate_change': 'New numerical reference candidate, not a claim that old standardQDQ has been fixed.',
        'arithmetic': {
            'activation_quantisation': 'FP32 division by stored scale, nearest-even round, addUINT8zero-point and saturate0..255',
            'weight': 'Use exact existing52packedINT8arrays, encode asUINT8(w+128) withzero-point128 for ConvInteger kernel compatibility; no new calibration or weight quantisation',
            'accumulation': 'Subtract zero-points and exact INT64 reference dot products, assert worst-case absolute sum bound fits signedINT32; exported standardConvInteger returnsINT32',
            'reconstruction': 'CastINT32toDOUBLE, multiply input scaleDOUBLE then per-output-channel weight scaleDOUBLE, add originalFP32bias castDOUBLE, castresultFP32',
            'output_quantisation': 'Original scale/zero/range, explicitFP32divide/nearest-even thenFP32dequantise',
            'non_conv_operations': 'OriginalFP32Torch/ONNX operations retained; not an all-integer network or fixed-point hardware design'
        },
        'gates': {'vectors': 8, 'maximum_absolute_embedding_difference': .001,
                  'minimum_cosine': .9999, 'unchanged_packing_tolerance': 1e-6,
                  'integer_accumulator_difference': 0,
                  'original_baseline_failure_must_remain_visible': True},
        'comparisons': ['originalTorch_vs_originalORTdisabled', 'integerReference_vs_ConvIntegerORTdisabled',
                        'integerReference_vs_ConvIntegerORTdefault', 'all52accumulators_pervector',
                        'independentFP64integerConvolution_recalculation'],
        'decisions': 'Report everyvector and preserve failures; no formalQAT until same gate and actual-gradient smoke pass on every trainingseed under a separately approved/frozen numerical implementation.',
        'new_training_updates': 0, 'new_calibration_image_reads': 0,
        'new_independent_accuracy_claim': False, 'board_execution': False,
        'whole_goal_complete': False
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(protocol, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'results').mkdir(exist_ok=True)
    plan = ROOT / '执行计划.md'
    plan.write_text('''# 整数卷积参考：执行计划

2026年10月28日。承接QAT导出检查剩余的1/8失败，先建立明确的累加与重定标参考。本阶段不新增训练或身份准确率。

1. 冻结旧图、权重打包、8个已用训练向量、数值实现和原容差；重现旧7/8与index3失败。
2. 对相同整数激活/权重，用INT64参考累加并检查INT32安全界；以标准ONNX ConvInteger作独立运行路径。
3. 明确逐步DOUBLE重建、FP32边界与nearest-even舍入；这是新数值候选，原QDQ失败保留。
4. 比较全部8向量与52层累加，默认优化另报；独立复算后再判断下一步，未通过不启动正式QAT。
5. 回查输入角色、源hash、Slurm终态及交付文件，完整Review。板上工具版本与独立通行参考继续待用户提供。

若新候选通过，只证明这些训练回归向量下的数值互操作；还需要三seed、真实梯度、训练后导出、身份风险和实际板上执行。DOUBLE重建不直接等于可部署定点重定标。
''', encoding='utf-8')
    print(json.dumps({'protocol_sha256': sha(target), 'frozen_inputs': len(sources),
                      'new_training_updates': 0, 'whole_goal_complete': False}))


if __name__ == '__main__':
    main()
