"""Fixed first-frame vs five-frame aggregation on curated daily-tracklet proxies."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
import hashlib,json,os,csv
import numpy as np
from identity_metrics import calibrate_threshold,summarise,cluster_intervals

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline');BASE=ROOT/'results/embedding_baseline';OUT=ROOT/'results/group_aggregation'
OUT.mkdir(parents=True,exist_ok=False)
protocol_path=ROOT/'protocol/aggregation_v1.json';protocol=json.loads(protocol_path.read_text())
summary=json.loads((BASE/'summary.json').read_text())
assert hashlib.sha256(protocol_path.read_bytes()).hexdigest()==summary['predeclared_companion_protocol_sha256']
vectors=np.load(BASE/'embeddings.npz');index=json.loads((BASE/'embedding_index.json').read_text())
g=vectors['gallery'].astype(np.float64);identities=index['gallery_identity_order'];gallery_ids=[r['identity'] for r in index['gallery']]
indices={identity:[i for i,x in enumerate(gallery_ids) if x==identity] for identity in identities}
def group(split,method):
    groups=defaultdict(list)
    for i,r in enumerate(index[split]):groups[r['identity']].append((r['relative_path'],i,r))
    entries=[];features=[]
    for identity,rows in sorted(groups.items()):
        rows.sort();assert len(rows)==5
        v=vectors[split][rows[0][1]].astype(np.float64) if method=='single_first' else vectors[split][[r[1] for r in rows]].astype(np.float64).mean(0)
        v=v/max(np.linalg.norm(v),1e-12);features.append(v)
        r=rows[0][2];entries.append({'relative_path':f'{r["day"]}/{identity}/camera1_group','identity':identity,'cohort':r['cohort'],'split':split,'day':r['day'],'is_known':r['cohort']=='known','source_images':[r[0] for r in rows]})
    features=np.array(features);similarity=features@g.T;values=np.stack([similarity[:,indices[i]].max(1) for i in identities],axis=1)
    for row,scores in zip(entries,values):
        j=int(np.argmax(scores));row.update(predicted_id=identities[j],similarity=float(scores[j]))
    return entries

results=[]
for method in protocol['methods']:
    name=method['name'];cal=group('calibration',name)
    threshold=calibrate_threshold([r['similarity'] for r in cal],[r['predicted_id'] for r in cal],[r['identity'] for r in cal],[r['is_known'] for r in cal])
    threshold.update(frozen_before_group_evaluation_scoring=True,frozen_at_utc=datetime.now(timezone.utc).isoformat())
    (OUT/f'{name}_threshold.json').write_text(json.dumps(threshold,indent=2))
    evaluation=group('evaluation',name)
    for row in cal+evaluation:row['accepted']=row['similarity']>=threshold['threshold']
    calresult=summarise(cal);evaluated=summarise(evaluation)
    row={'method':name,'threshold':threshold,'calibration':calresult,'evaluation':evaluated,
         'evaluation_identity_cluster_intervals':cluster_intervals(evaluated['per_identity']),
         'unit':'One anonymous cow/date/camera group from five fixed curated crops; complete source passage not independently established'}
    (OUT/f'{name}_calibration_predictions.json').write_text(json.dumps(cal,indent=2))
    (OUT/f'{name}_evaluation_predictions.json').write_text(json.dumps(evaluation,indent=2))
    results.append(row)
result={'job_id':os.environ['SLURM_JOB_ID'],'protocol':protocol,'conditions':results,'board_measurements':None,'scope':protocol['scope']}
(OUT/'summary.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'job_id':os.environ['SLURM_JOB_ID'],'conditions':[{'method':r['method'],'threshold':r['threshold']['threshold'],**{k:v for k,v in r['evaluation'].items() if k!='per_identity'}} for r in results]},indent=2),flush=True)
