"""Decode selected public crops and verify provenance and split integrity."""
from pathlib import Path
from collections import defaultdict,Counter
from PIL import Image,ImageOps,ImageDraw
import hashlib,json,os
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline')
OUT=ROOT/'results/image_audit';OUT.mkdir(parents=True,exist_ok=False)
protocol_path=ROOT/'protocol/identity_pilot_v1.json';protocol=json.loads(protocol_path.read_text())
manifest_path=ROOT/'catalog/image_manifest.json';manifest=json.loads(manifest_path.read_text())
stage=json.loads((ROOT/'catalog/stage_complete.json').read_text());selection=json.loads((ROOT/'catalog/selection.json').read_text())
assert hashlib.sha256(protocol_path.read_bytes()).hexdigest()==stage['protocol_sha256']
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==stage['manifest_sha256']
assert not(set(protocol['validation_unknown_ids'])&set(protocol['evaluation_unknown_ids']))
rows=[];pixels=defaultdict(list);bytegroups=defaultdict(list);images={}
def dhash(image):
    v=list(image.convert('L').resize((9,8)).getdata());value=0
    for y in range(8):
        for x in range(8):value=(value<<1)|int(v[y*9+x]>v[y*9+x+1])
    return value
for entry in manifest:
    p=ROOT/entry['relative_path'];data=p.read_bytes()
    assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
    with Image.open(p) as im:
        im.load();im=im.convert('RGB');w,h=im.size
        pix=hashlib.sha256(w.to_bytes(4,'big')+h.to_bytes(4,'big')+im.tobytes()).hexdigest();d=dhash(im)
        images[entry['relative_path']]=im.copy()
    assert entry['source_filename'].endswith('_1.jpg') and entry['camera']==1
    assert entry['split']=={'2023Aug14':'gallery','2023Aug19':'calibration','2023Aug20':'evaluation'}[entry['day']]
    assert entry['split']!='gallery' or entry['cohort']=='known'
    row={**entry,'width':w,'height':h,'pixel_sha256':pix,'dhash64':f'{d:016x}'}
    rows.append(row);pixels[pix].append(row);bytegroups[entry['sha256']].append(row)
exact=[{'pixel_sha256':key,'files':[r['relative_path'] for r in group],'splits':sorted({r['split'] for r in group})} for key,group in pixels.items() if len({r['split'] for r in group})>1]
near=[]
for i,a in enumerate(rows):
    for b in rows[i+1:]:
        if a['identity']==b['identity'] and a['split']!=b['split']:
            distance=(int(a['dhash64'],16)^int(b['dhash64'],16)).bit_count()
            if distance<=2:near.append({'identity':a['identity'],'left':a['relative_path'],'right':b['relative_path'],'dhash_hamming':distance})
counts=Counter((r['identity'],r['split']) for r in rows)
assert all(n==5 for n in counts.values())
known=sorted({r['identity'] for r in rows if r['cohort']=='known'})
for page in range((len(known)+4)//5):
    sheet=Image.new('RGB',(960,5*180),'white');draw=ImageDraw.Draw(sheet)
    for y,identity in enumerate(known[page*5:(page+1)*5]):
        for x,split in enumerate(['gallery','calibration','evaluation']):
            group=sorted([r for r in rows if r['identity']==identity and r['split']==split],key=lambda r:r['relative_path'])
            r=group[len(group)//2];im=images[r['relative_path']]
            sheet.paste(ImageOps.contain(im,(315,145)),(x*320,y*180+20))
            draw.text((x*320+4,y*180+3),f'ID {identity} {r["day"]} {split}',fill='black')
    sheet.save(OUT/f'cross_day_known_{page+1}.jpg',quality=92)
summary={'job_id':os.environ['SLURM_JOB_ID'],'status':'PASS' if not exact else 'REVIEW_REQUIRED_EXACT_CROSS_SPLIT_DUPLICATES',
         'images':len(rows),'cohort_id_counts':{cohort:len({r['identity'] for r in rows if r['cohort']==cohort}) for cohort in ['known','validation_unknown','evaluation_unknown']},
         'images_by_split':dict(Counter(r['split'] for r in rows)),
         'all_images_fully_decoded':True,'same_identity_split_sizes':sorted(set(counts.values())),
         'min_side_lt128':sum(min(r['width'],r['height'])<128 for r in rows),'minimum_dimensions':[min(r['width'] for r in rows),min(r['height'] for r in rows)],
         'exact_pixel_cross_split_duplicates':exact,'near_same_identity_cross_day_candidates':near,
         'near_candidate_interpretation':'Perceptual similarity of the same cow across dates is expected; dHash is a screening signal, not proof of duplicated source passage',
         'protocol_sha256':stage['protocol_sha256'],'manifest_sha256':stage['manifest_sha256'],
         'independent_annotation_status':'Uses public author identity labels, no new independent human verification by this project'}
(OUT/'audited_manifest.json').write_text(json.dumps(rows,indent=2))
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ['near_same_identity_cross_day_candidates']},indent=2),flush=True)
assert not exact,'Freeze evaluation until exact duplicate findings are handled'
