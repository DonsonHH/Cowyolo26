from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,random,os,csv
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');SRC=ROOT/'data/opencows2020/extracted/detection_and_localisation';OUT=ROOT/'data/opencows2020/derived_detection';OUT.mkdir(parents=True,exist_ok=True)
groups=defaultdict(list);manifest=[]
for p in sorted((SRC/'images').glob('*.jpg')):
 sha=hashlib.sha256(p.read_bytes()).hexdigest();groups[sha].append(p)
real_groups=[(h,ps) for h,ps in groups.items() if any(int(p.stem)<=3707 for p in ps)];rng=random.Random(20261026);rng.shuffle(real_groups)
# Development split only. Same-event augmentation/source overlap is not resolved by this grouping.
test_hash={h for h,_ in real_groups[:len(real_groups)//5]};val_hash={h for h,_ in real_groups[len(real_groups)//5:len(real_groups)*3//10]}
edits=Counter();samples=[]
for sha,paths in sorted(groups.items()):
 for p in paths:
  real=int(p.stem)<=3707
  split='dev_test' if real and sha in test_hash else ('val' if real and sha in val_hash else 'train')
  if not real and sha in test_hash|val_hash:split='quarantine_duplicate_of_holdout'
  label=SRC/'labels-darknet'/(p.stem+'.txt');lines=[];clipped=0;removed=0
  for line in label.read_text().splitlines():
   if not line.strip():continue
   cls,cx,cy,w,h=map(float,line.split());x1=max(0,min(1,cx-w/2));y1=max(0,min(1,cy-h/2));x2=max(0,min(1,cx+w/2));y2=max(0,min(1,cy+h/2))
   if x2<=x1 or y2<=y1:removed+=1;continue
   clipped+=int(any(abs(a-b)>1e-7 for a,b in zip((x1,y1,x2,y2),(cx-w/2,cy-h/2,cx+w/2,cy+h/2))))
   lines.append(f'0 {(x1+x2)/2:.9f} {(y1+y2)/2:.9f} {x2-x1:.9f} {y2-y1:.9f}')
  target=OUT/'labels'/split/(p.stem+'.txt');target.parent.mkdir(parents=True,exist_ok=True);target.write_text('\n'.join(lines)+'\n')
  dest=OUT/'images'/split/p.name;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():dest.symlink_to(p)
  edits['clipped_boxes']+=clipped;edits['removed_zero_area_boxes']+=removed
  manifest.append({'image':str(p),'sha256':sha,'synthetic_by_readme':not real,'split':split,'clipped_boxes':clipped,'removed_boxes':removed,'derived_label':str(target)})
summary={'job_id':os.environ['SLURM_JOB_ID'],'split_counts':dict(Counter(r['split'] for r in manifest)),'edits':dict(edits),'scope':'development-only hash-group split; cross-source/time/augmentation lineage is not verified; final generalization protocol must be constructed separately','seed':20261026,'original_files_changed':False}
(OUT/'data.yaml').write_text(f'path: {OUT}\ntrain: images/train\nval: images/val\ntest: images/dev_test\nnames:\n  0: cow\n')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
