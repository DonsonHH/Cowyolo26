from pathlib import Path
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'tools/smoke.py'
target = ROOT / 'tools/smoke_v2.py'
assert not target.exists()
text = source.read_text(encoding='utf-8')
changes = [("out = ROOT / 'results/smoke'", "out = ROOT / 'results/smoke_v2'"),
           ('folded, _ = fold_batchnorm(teacher)\n        original, _ = insert_quantisers(folded)',
            'folded, _ = fold_batchnorm(teacher)\n        folded.requires_grad_(True)\n        original, _ = insert_quantisers(folded)')]
for before, after in changes:
    assert text.count(before) == 1
    text = text.replace(before, after)
target.write_text(text, encoding='utf-8')
record = {'source': 'tools/smoke.py', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'corrected': 'tools/smoke_v2.py', 'corrected_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
          'failure_job': '129989', 'diagnosis_job': '129990',
          'reason': '34fusedbias parameters hadrequires_gradFalse, producingNonegradients; no nonfinitegradients in all4loss controls.',
          'only_changes': ['enablegrad for allfolded parameters beforequantcalibration/conversion', 'newresultfolder preservingfailedrun'],
          'protocol_values_weights_initial_values_loss_and_tolerances_changed': False}
(ROOT / 'results/retry_v2_provenance.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record))
