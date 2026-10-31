from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'results/local_delivery_verification.json'
record = json.loads(path.read_text(encoding='utf-8'))
assert record['manual_visual_QA'] == 'pending'
render = json.loads((ROOT / 'delivery/results/render_record.json').read_text(encoding='utf-8'))
for row in render['files']:
    actual = ROOT / 'delivery' / row['path']
    assert hashlib.sha256(actual.read_bytes()).hexdigest() == row['sha256']
backup = ROOT / 'results/local_delivery_before_visual_QA.json'
assert not backup.exists()
backup.write_bytes(path.read_bytes())
record.update(manual_visual_QA='PASS', visual_review_UTC=datetime.now(timezone.utc).isoformat(),
    visual_review_scope={'score_plot': 'All6panels visible, samecosineaxes, readablelegend, thresholds andcategories',
                         'contact_sheet': 'All5QATacceptederrorcases and12sourcepanels visible, query/gallery labels andscores readable',
                         'independent_animal_identity_or_label_truth_verified': False})
path.write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps({'status': record['status'], 'manual_visual_QA': 'PASS', 'whole_goal_complete': False}))
