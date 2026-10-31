from pathlib import Path,PurePosixPath
from collections import Counter,defaultdict
import zipfile,io,json,csv,hashlib,time,xml.etree.ElementTree as ET
from PIL import Image
import numpy as np

SRC=Path(r'C:\Users\Donson\Downloads\10m32xl88x2b61zlkkgz3fml17.zip\10m32xl88x2b61zlkkgz3fml17.zip')
OUT=Path(__file__).resolve().parent.parent/'local_opencows';OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rows=[];bad=[];yolo_errors=[];boundary=[];xml_errors=[];hashes=defaultdict(list);id_stats=Counter();dimensions=defaultdict(Counter);dhashes=defaultdict(list)
with zipfile.ZipFile(SRC) as z:
 names=[x.filename for x in z.infolist() if not x.is_dir()];files=set(names)
 for k,n in enumerate(names):
  if not n.lower().endswith('.jpg'):continue
  try:
   data=z.read(n);sha=hashlib.sha256(data).hexdigest();hashes[sha].append(n)
   with Image.open(io.BytesIO(data)) as im:
    im.load();w,h=im.size;group='detection' if '/detection_and_localisation/' in n else 'identification';dimensions[group][(w,h)]+=1
    row={'name':n,'group':group,'width':w,'height':h,'bytes':len(data),'sha256':sha}
    if group=='identification':
     ps=PurePosixPath(n).parts;split=ps[-3];cow=ps[-2];row.update(split=split,cow_id=cow);id_stats[(split,cow)]+=1
     a=np.asarray(im.convert('L').resize((9,8)),dtype=np.int16);bits=(a[:,1:]>a[:,:-1]).ravel();dh=sum(int(v)<<i for i,v in enumerate(bits));dhashes[cow].append((split,n,dh))
    else:
     stem=PurePosixPath(n).stem;row['synthetic_by_readme']=int(stem)>3707
   rows.append(row)
  except Exception as e:bad.append({'name':n,'error':str(e)})
  if len(rows)%2000==0:print(json.dumps({'decoded':len(rows),'elapsed_s':round(time.time()-t,1)}),flush=True)
 for n in names:
  if '/labels-darknet/' not in n or not n.endswith('.txt'):continue
  text=z.read(n).decode('utf8');stem=PurePosixPath(n).stem
  for i,line in enumerate(text.splitlines(),1):
   if not line.strip():continue
   try:
    a=[float(v) for v in line.split()]
    if len(a)!=5 or a[0]!=0 or not all(np.isfinite(a)) or a[3]<=0 or a[4]<=0:raise ValueError('invalid format/class/size')
    x,y,w,h=a[1:];corners=[x-w/2,y-h/2,x+w/2,y+h/2]
    if min(corners)<-1e-6 or max(corners)>1+1e-6:boundary.append({'label':n,'line':i,'values':a,'corners':corners})
   except Exception as e:yolo_errors.append({'name':n,'line':i,'error':str(e)})
 for n in names:
  if '/labels-xml/' in n and n.endswith('.xml'):
   try:ET.fromstring(z.read(n))
   except Exception as e:xml_errors.append({'name':n,'error':str(e)})
 # Read remaining archive members, checking their CRC as well.
 for n in names:
  if not n.lower().endswith('.jpg') and '/labels-darknet/' not in n and '/labels-xml/' not in n:
   try:z.read(n)
   except Exception as e:bad.append({'name':n,'error':str(e)})

exact=[v for v in hashes.values() if len(v)>1];cross=[]
for group in exact:
 splits={r.split('/identification/images/')[1].split('/')[0] for r in group if '/identification/images/' in r}
 if len(splits)>1:cross.append(group)
near=[]
for cow,items in dhashes.items():
 tr=[x for x in items if x[0]=='train'];te=[x for x in items if x[0]=='test']
 for _,n,h in te:
  if not tr:continue
  best=min(tr,key=lambda q:(h^q[2]).bit_count());dist=(h^best[2]).bit_count()
  if dist<=2:near.append({'cow':cow,'query':n,'train':best[1],'dhash_hamming':dist})
det=[r for r in rows if r['group']=='detection'];ident=[r for r in rows if r['group']=='identification']
det_stems={PurePosixPath(r['name']).stem for r in det};lab_stems={PurePosixPath(n).stem for n in names if '/labels-darknet/' in n and n.endswith('.txt')}
quantiles={}
for group in ('detection','identification'):
 a=np.array([[r['width'],r['height']] for r in rows if r['group']==group]);quantiles[group]={'width':np.quantile(a[:,0],[0,.1,.5,.9,1]).tolist(),'height':np.quantile(a[:,1],[0,.1,.5,.9,1]).tolist(),'min_side_lt128':int((a.min(axis=1)<128).sum()),'min_side_lt224':int((a.min(axis=1)<224).sum())}
report={'archive':str(SRC),'archive_bytes':SRC.stat().st_size,'jpg_images':len(rows),'detection_images':len(det),'detection_real_by_readme':sum(not r['synthetic_by_readme'] for r in det),'detection_synthetic_by_readme':sum(r['synthetic_by_readme'] for r in det),'identity_images':len(ident),'identity_count':len(dhashes),'identity_splits':dict(Counter(r['split'] for r in ident)),'identity_images_per_split':{s:{c:n for (ss,c),n in sorted(id_stats.items()) if ss==s} for s in ('train','test')},'dimension_quantiles':quantiles,'common_dimensions':{g:[{'width':s[0],'height':s[1],'count':v} for s,v in cs.most_common(8)] for g,cs in dimensions.items()},'missing_yolo':sorted(det_stems-lab_stems),'orphan_yolo':sorted(lab_stems-det_stems),'unreadable_or_crc_errors':bad,'invalid_yolo_lines':yolo_errors,'xml_parse_errors':xml_errors,'boxes_extending_beyond_image':len(boundary),'images_with_outside_boxes':len({r['label'] for r in boundary}),'exact_duplicate_groups':len(exact),'exact_train_test_identity_duplicate_groups':len(cross),'near_duplicate_train_test_dhash_le2':len(near),'near_duplicate_note':'dHash screening candidates, not proof of duplicated source event; manual review needed','video_files':sum(PurePosixPath(n).suffix.lower() in ('.avi','.mp4','.mov','.mkv') for n in names),'elapsed_s':round(time.time()-t,1)}
(OUT/'full_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
for name,obj in [('boundary_labels.json',boundary),('exact_duplicates.json',exact),('near_train_test_candidates.json',near)]: (OUT/name).write_text(json.dumps(obj,indent=2),encoding='utf8')
with (OUT/'image_manifest.csv').open('w',encoding='utf8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['name','group','width','height','bytes','sha256','split','cow_id','synthetic_by_readme']);w.writeheader();w.writerows(rows)
sha=hashlib.sha256()
with SRC.open('rb') as f:
 for b in iter(lambda:f.read(8*1024*1024),b''):sha.update(b)
report['archive_sha256']=sha.hexdigest();(OUT/'full_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('identity_images_per_split','common_dimensions')},indent=2),flush=True)
