"""Red-capable replay of actual periodic throughput, not a fabricated fixture."""
from pathlib import Path
import json,hashlib,sys
PROJECT=Path(__file__).resolve().parents[2]
path=PROJECT/'causal_photo_20261030/results/independent_verification.json'
final=json.loads((PROJECT/'causal_photo_20261030/results/final_review.json').read_text(encoding='utf-8'))
assert hashlib.sha256(path.read_bytes()).hexdigest()==final['evidence_hashes']['results/independent_verification.json']
v=json.loads(path.read_text(encoding='utf-8'));cases=[r for r in v['cases'] if r['case']=='causal_ring']
result={'status':'PERIODIC_TARGET_RED' if any(r['processed_per_second_over_offered_duration']<5 for r in cases) else 'PERIODIC_TARGET_GREEN',
 'actual_board_trace_not_synthetic':True,'target_FPS':5.,'cases':[{'run':r['run'],'FPS':r['processed_per_second_over_offered_duration'],'skips':r['skipped_slots'],'late_frames':r['deadline_misses']} for r in cases],
 'source_verification_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'Replay of original full periodic failure; isolated microbenchmarks cannot turn this green.'}
print(json.dumps(result));sys.exit(1 if result['status'].endswith('RED') else 0)
