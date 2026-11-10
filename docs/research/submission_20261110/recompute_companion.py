"""Verify the delivered file set and re-score reviewed totals without a model or video."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
args=parser.parse_args();root=args.root.resolve()
manifest=json.loads((root/'PUBLIC_MANIFEST.json').read_bytes())
for relative,binding in manifest['files'].items():
    path=(root/relative).resolve()
    assert path.is_relative_to(root),relative
    data=path.read_bytes()
    assert len(data)==binding['bytes'] and hashlib.sha256(data).hexdigest()==binding['sha256'],relative
sys.path.insert(0,str(root/'runtime'))
from counting.count_metrics import score_totals,aggregate_totals
def read(path):
    data=path.read_bytes()
    return gzip.decompress(data) if path.suffix=='.gz' else data
index=json.loads((root/'EVIDENCE_INDEX.json').read_bytes())
groups=defaultdict(list);cases=[]
for item in index['cases']:
    if item['output'] is None:
        cases.append({**item,'score_status':'NOT_STARTED'});continue
    folder=root/item['output']
    summary=json.loads(read(folder/'summary.json'))
    event_path=folder/'events.jsonl.gz'
    events=[json.loads(line) for line in read(event_path).splitlines() if line.strip()]
    if summary['status']!='COMPLETED_UNSCORED':
        cases.append({**item,'runtime_status':summary['status'],'score_status':'FAILED_NOT_FULL_VIDEO_SCORE'});continue
    if not item.get('reference'):
        cases.append({**item,'runtime_status':summary['status'],'score_status':'NO_ACCEPTED_HUMAN_TOTAL','prediction':summary['counts']});continue
    reference=json.loads((root/item['reference']).read_bytes())
    score=score_totals(summary,events,reference)
    groups[(item['study'],item['policy'],item['repeat'])].append(score)
    cases.append({**item,'score_status':score['status'],'absolute_error':score['absolute_error_over_reviewed_directions'],
                  'prediction':score['predicted_directional_totals'],'reference_totals':score['reference_totals']})
aggregates={}
for key,group in groups.items():
    # Only the four-video development benchmark is aggregated as that benchmark.
    if len(group)==4:aggregates['/'.join(map(str,key))]=aggregate_totals(group)
print(json.dumps({'status':'DELIVERED_FILES_AND_REVIEWED_TOTALS_RECOMPUTED',
 'files_verified':len(manifest['files']),'aggregates':aggregates,'cases':cases,
 'new_model_forwards':0,'event_f1':None,'raw_tensor_payloads_included':False},indent=2))
