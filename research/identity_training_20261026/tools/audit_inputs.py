from pathlib import Path
from collections import defaultdict,Counter
from PIL import Image
import hashlib,json,os
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_training');OUT=ROOT/'results/input_audit'
OUT.mkdir(parents=True,exist_ok=False)
p=json.loads((ROOT/'protocol/identity_training_v1.json').read_text());s=json.loads((ROOT/'catalog/stage_complete.json').read_text());rows=json.loads((ROOT/'catalog/image_manifest.json').read_text())
assert hashlib.sha256((ROOT/'protocol/identity_training_v1.json').read_bytes()).hexdigest()==s['protocol_sha256']
assert hashlib.sha256((ROOT/'catalog/image_manifest.json').read_bytes()).hexdigest()==s['manifest_sha256']
roles=s['eligible_roles'];all_ids=[identity for group in roles.values() for identity in group]
assert len(all_ids)==len(set(all_ids))
assert all(len(roles[k])>=3 for k in roles if k!='training_ids') and len(roles['training_ids'])>=10
pixels=defaultdict(list);audited=[]
for row in rows:
    path=ROOT/row['relative_path'];data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes']
    with Image.open(path) as im:
        im.load();im=im.convert('RGB');w,h=im.size
        pixel=hashlib.sha256(w.to_bytes(4,'big')+h.to_bytes(4,'big')+im.tobytes()).hexdigest()
    assert row['identity'] in roles[row['role']] and row['source_filename'].endswith('_1.jpg')
    assert row['split']!='train' or row['role']=='training_ids'
    record={**row,'width':w,'height':h,'pixel_sha256':pixel};audited.append(record);pixels[pixel].append(record)
duplicates=[{'hash':key,'files':[r['relative_path'] for r in group],'splits':sorted({r['split'] for r in group})} for key,group in pixels.items() if len(group)>1]
cross=[r for r in duplicates if len(r['splits'])>1]
for identity in roles['training_ids']:
    group=[r for r in audited if r['identity']==identity]
    assert len(group)>=10 and len({r['day'] for r in group})>=2 and len({r['relative_path'] for r in group})>=4
summary={'job_id':os.environ['SLURM_JOB_ID'],'status':'PASS' if not cross else 'REVIEW_REQUIRED',
         'images':len(rows),'images_by_split':dict(Counter(r['split'] for r in rows)),'identities_by_role':{k:len(v) for k,v in roles.items()},
         'eligible_roles':roles,'excluded':s['excluded'],'all_decoded':True,'exact_duplicates':duplicates,'cross_split_exact_duplicates':cross,
         'minimum_side':min(min(r['width'],r['height']) for r in audited),'protocol_sha256':s['protocol_sha256'],
         'manifest_sha256':s['manifest_sha256'],'scope':'New identity-disjoint public crop study; label truth inherited from dataset author'}
(OUT/'manifest.json').write_text(json.dumps(audited,indent=2));(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True);assert not cross
