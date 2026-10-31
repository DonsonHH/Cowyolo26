from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
REMOTE = '/share/home/renly/projects/idcoo_research_20261026'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
base = json.loads((PROJECT / 'integer_trainable_20261028/protocol/trainable_integer_smoke_v1.json').read_text())
smoke = PROJECT / 'integer_trainable_20261028/delivery/results/smoke_v2'
target = ROOT / 'protocol/paired_integer_qat_v1.json'
assert not target.exists()
sources = []
for source in base['source_models']:
    state = smoke / f'seed{source["seed"]}_initial/state.pt'
    sources.append({**source, 'integer_initial_state': REMOTE + f'/integer_trainable_20261028/results/smoke_v2/seed{source["seed"]}_initial/state.pt',
                    'integer_initial_state_sha256': sha(state)})
protocol = {'name': 'Fixed CPU-fold sixepoch paired integerforward QAT and float continuation v1',
    'created_UTC': datetime.now(timezone.utc).isoformat(), 'source_models': sources,
    'scope': 'Existing training and reused developmentvalidation only; no oldevaluation/newholdout, sourcevideo orboard inference.',
    'admitted_smoke_summary_sha256': sha(smoke / 'summary.json'),
    'admitted_independent_verification_sha256': sha(PROJECT / 'integer_trainable_20261028/delivery/results/independent_verification.json'),
    'source_manifest_sha256': base['manifest_sha256'], 'calibration_manifest_sha256': base['calibration_manifest_sha256'],
    'code_freeze': [{'remote_path': REMOTE + '/integer_trainable_20261028/tools/' + name,
                     'sha256': sha(PROJECT / 'integer_trainable_20261028/tools' / name)} for name in ['integer_trainable.py', 'export_integer.py', 'smoke.py']],
    'training': base['training'], 'seeds': [26, 27, 28],
    'initialization': 'CPU ConvBNfold from sourcecheckpoint for bothbranches. Integerbranch restore exact admittedinitialstate; assert FP32masterweights/biases identical to pairedfloat. Discarded2update smoke states neverused.',
    'calibration': 'Use exact stored64traincalibration manifest and fixed admitted qparams, no recalc/calibration onvalidation.',
    'paired_control': 'Reset seedperbranch; identical120P8K4indices, augmented image tensor SHA256 and optimizer/loss/stepbudget. All104weights/bias parameter tensors enabled.',
    'conditions': ['source_folded_fp32', 'initial_integer', 'paired_float_continuation', 'integer_forward_qat'],
    'export_gate': {'vectors': 8, 'maximum_absolute_error': .001, 'minimum_cosine': .9999, 'maximum_packing_error': 1e-6},
    'adopted_validation_runtime': 'CPU ORT1.23.2 ALL withsession.disable_quant_qdq=1; OFF anddefaultALL reported in numericgate. Float graph usesOFFreference.',
    'validation': 'Existing25gallery55queries, maximagecosinescoreperidentity; empiricalunknownFAR<=.05 threshold maxC/minW/higherthreshold tie rule. Exploratory calibration andvalidation on reusedqueries, not independenttestperformance.',
    'checkpoint': 'Fixedlast epoch6, allseedsreported, no checkpoint/seed selection.',
    'formal_QAT_target_updates': 360, 'paired_float_target_updates': 360,
    'smoke_updates_carried_into_training': 0, 'FPGA_execution': False, 'whole_goal_complete': False}
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
(ROOT / 'results').mkdir(exist_ok=True)
(ROOT / '执行计划.md').write_text('''# 六轮配对整数前向QAT计划

2026年10月28日。三seed可训练数值／梯度／更新后导出准入完成后执行。

1. 固定CPU合并初值；整数分支恢复已验初始状态，与浮点分支逐项比较master权重和偏置。冒烟更新权重排除。
2. 每seed每分支6轮×20批P8K4，同样本、同增强张量、同优化器和损失，末轮固定；保留全部seed。
3. 每个导出用8训练回归向量检查数值和打包，再在既有开发图库／查询评价闭集、C/W/U和未知误接收。
4. 训练图访问角色、120步配对hash、冻结模型／阈值、完整不利结果和Slurm终态独立复核。

开发验证重复使用，阈值与成绩均为开发校准结果；最终独立身份和真实事件评价另补。实际板上执行仍待连接／工具信息及定点映射。
''', encoding='utf-8')
print(json.dumps({'protocol_sha256': sha(target), 'target_updates_per_branch': 360}))
