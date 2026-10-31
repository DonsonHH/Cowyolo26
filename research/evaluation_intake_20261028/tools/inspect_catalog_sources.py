from pathlib import Path
import json
PROJECT = Path(__file__).resolve().parents[2]
paths = ['source_demo_20261026/delivery/results/preview/summary.json',
         'detector_training_20261027/delivery/results/inference/summary.json',
         'composition_control_20261027/delivery/results/inference/summary.json',
         'cows2021_adaptation_20261027/delivery/results/inference/summary.json',
         'orientation_video_20261027/delivery/results/inference/summary.json']
for name in paths:
    value = json.loads((PROJECT / name).read_text(encoding='utf-8'))
    records = value.get('conditions', value.get('models', value.get('results', [])))
    print(json.dumps({'path': name, 'keys': list(value), 'records_type': type(records).__name__,
                      'first_record': records[0] if isinstance(records, list) and records else records,
                      'other_small_fields': {k: v for k, v in value.items() if not isinstance(v, (dict, list))}}, ensure_ascii=False))
