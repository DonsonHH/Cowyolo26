from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from geometry import reference
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'input/images_and_references.json').read_text())
previous=json.loads((ROOT.parent/'orientation_validation_20261027/input/selected_validation.json').read_text());previous={r['file_name']:r for r in previous}
maximum=0.;counts={};geometry=[]
for split,rows in manifest.items():
    c=Counter()
    for row in rows:
        references=[reference(a) for a in row['reference_annotations']]
        c.update({'images':1,'references':len(references),'complete':sum(r['reference_complete'] for r in references),'clipped':sum(not r['reference_complete'] for r in references)})
        if split=='val':
            p=previous[row['file_name']];assert p['sha256']==row['sha256']
            for ref,values in zip(references,p['expected_float32_rows']):
                _,cx,cy,w,h=values;box=[(cx-w/2)*1280,(cy-h/2)*720,(cx+w/2)*1280,(cy+h/2)*720]
                error=max(abs(a-b) for a,b in zip(box,ref['visible_reference_AABB']));maximum=max(maximum,error);assert error<.001
        geometry.append({'split':split,'file_name':row['file_name'],'reference_keys':[r['annotation_key'] for r in references]})
    counts[split]=dict(c)
out=ROOT/'results/geometry_preflight.json';assert not out.exists();out.parent.mkdir(exist_ok=True)
result={'status':'ALL10752_ROTATED_REFERENCES_PREPARED_WITH1864_PRIOR_VISIBLE_AABB_REGRESSION','created_UTC':datetime.now(timezone.utc).isoformat(),
'counts':counts,'previous_validation_float32_AABB_max_native_pixel_delta':maximum,'source_manifest_sha256':sha(ROOT/'input/images_and_references.json'),
'geometry_module_sha256':sha(ROOT/'tools/geometry.py'),'model_forwards':0,'identity_labels_generated':False,'whole_goal_complete':False}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
