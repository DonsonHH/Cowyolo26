from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
REMOTE = '/share/home/renly/projects/idcoo_research_20261026'
study = PROJECT / 'integer_qat_20261028/delivery/results/study'
summary = json.loads((study / 'summary.json').read_text())
previous = json.loads((PROJECT / 'integer_qat_20261028/protocol/paired_integer_qat_v1.json').read_text())
target = ROOT / 'protocol/activation_range_v1.json'
assert not target.exists()
models = []
for row in summary['conditions']:
    local = study / f'seed{row["seed"]}_{row["condition"]}/state.pt'
    assert hashlib.sha256(local.read_bytes()).hexdigest() == row['state_sha256']
    models.append({'seed': row['seed'], 'condition': row['condition'], 'quantized': row['quantized'],
                   'remote_path': REMOTE + f'/integer_qat_20261028/results/study/seed{row["seed"]}_{row["condition"]}/state.pt',
                   'sha256': row['state_sha256']})
protocol = {'name': 'Train-only fixed range clipping and fixed-weight controls v1',
    'created_UTC': datetime.now(timezone.utc).isoformat(), 'source_models': previous['source_models'], 'models': models,
    'formal_QAT_summary_sha256': hashlib.sha256((study / 'summary.json').read_bytes()).hexdigest(),
    'calibration_manifest_sha256': previous['calibration_manifest_sha256'],
    'manifest_sha256': previous['source_manifest_sha256'],
    'code_freeze': previous['code_freeze'],
    'images': 'Same64existingcalibration trainingimages, deterministicBodyTransform and onefixedaugmentedversioneach. Nevervalidation/query/test images.',
    'augmentation_seed_base': 84028, 'batch_size': 4,
    'conditions': ['source_folded_fp32', 'paired_float_continuation', 'initial_integer', 'integer_forward_qat',
                   'QAT_no_activation_clipping', 'QAT_no_weight_clipping'],
    'measurements': '52Convinput/output roundedcode below/above representablerange, endpointcounts anddenominators; weightcode clippedcounts; normalizedfeatureteacher cosine pertrainingimage.',
    'hypotheses': [
        'Fixedfloatcalibrationranges may encounter moreout-of-rangecodes afterQAT oraugmentation; compare sameimages acrossstages.',
        'Ifactivationclipping explains a substantialteacherfeaturedeviation, removingonlyactivationclipping withsameweights may reduce it.',
        'Ifweightclipping explains deviation, removingonlyweightclipping shouldchange teacherfeatureerror. Report noimprovement aswell.'],
    'controls': 'Noactivationclip leaves quantizationsteps butunbounded input/outputintegercodes; noweightclip leavesactivationclipping butunboundedweightcodes. Theseare nondeployable diagnosticinterventions, notnewlowbitmodels.',
    'gates': {'frozen8vector_baseline_max_absolute_error': .001, 'minimum_cosine': .9999,
              'all_actual_accumulator_bounds_fit_INT32': True, 'alloutputs_finite': True},
    'fixtures': 'Quantizedbranches, firsttrainingimage ofeachview, preselectedConvindices0,20,51; saveactualcodeinputs/weights/accumulators/raw/output forindependentarithmetic.',
    'float_clipping_interpretation': 'Potentialrange violations under sameinitialqparams, monitoredwithoutchangingfloatforward.',
    'metric_scope': 'Teacherfeatureagreement andclipping only, noidentityaccuracy/FAR/test orFPGAclaim.',
    'new_training_updates': 0, 'validation_or_test_access_allowed': False, 'whole_goal_complete': False}
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
(ROOT / 'results').mkdir(exist_ok=True)
print(json.dumps({'protocol_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'frozen_model_states': len(models)}))
