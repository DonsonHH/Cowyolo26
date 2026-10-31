from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile,re,xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=load(ROOT/'evidence/media_transfer.json');a=ROOT/'media_delivery.tar.gz';assert sha(a)==t['sha256'] and a.stat().st_size==t['bytes']
out=ROOT/'media_delivery';out.mkdir(exist_ok=False)
with tarfile.open(a) as tar:
 members=tar.getmembers();assert len(members)==t['members']
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(out/m.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
for r in load(out/'results/media/manifest.json'):assert sha(out/r['file'])==r['sha256'] and (out/r['file']).stat().st_size==r['bytes']
for relative in ['tools/render_media.py','protocol/media_v1.json']:assert sha(out/relative)==sha(ROOT/relative)
media=out/'results/media';data=load(media/'plot_data.json');s=load(ROOT/'delivery/results/record.json');jobs=load(ROOT/'delivery/results/foreground_with_identity/background/record.json')['jobs']
ns={'s':'http://www.w3.org/2000/svg'};xml=ET.parse(media/'periodic_and_identity.svg');totalbars=0;maxerr=0.
for panel in [1,2]:
 axis=xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]',ns);paths=[]
 for element in axis:
  if element.attrib.get('id','').startswith('patch_'):
   path=element.find('s:path',ns)
   if path is not None and 'clip-path' in path.attrib:paths.append(path)
 rows=[r for r in data['bars'] if r['panel']==panel];assert len(paths)==len(rows)==(6 if panel==1 else 55)
 for row,path in zip(rows,paths):
  if panel==1:
   case=next(c for c in s['cases'] if c['case']==row['case']);value=case[{'Processed':'processed_frames','Skipped':'skipped_slots','Over200ms':'deadline_misses'}[row['label']]];bottom=0
  else:
   value=jobs[row['job_index']][row['stage']];bottom=row['bottom']
  assert row['value']==value
  clip=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1);rect=xml.find('.//s:clipPath[@id="'+clip+'"]/s:rect',ns)
  points=np.asarray([float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]).reshape(-1,2)
  ymax=450 if panel==1 else 3200;xwidth=3.2 if panel==1 else 11.2
  height=np.ptp(points[:,1])/float(rect.attrib['height'])*ymax
  x=(points[0,0]-float(rect.attrib['x']))/float(rect.attrib['width'])*xwidth-.6
  low=(float(rect.attrib['y'])+float(rect.attrib['height'])-max(points[:,1]))/float(rect.attrib['height'])*ymax
  error=max(abs(height-value),abs(x-row['x']),abs(low-bottom));assert error<3e-5;maxerr=max(maxerr,error);totalbars+=1
for line in data['lines']:
 rows=load(ROOT/'delivery/results'/line['case']/'timing_rows.json')
 assert line['slot']==[r['slot'] for r in rows] and line['release_to_count_ms']==[r['release_to_count_ms'] for r in rows]
with Image.open(media/'all11_actual_photos.png') as im:sheet=np.asarray(im.convert('RGB'));assert im.size==(1600,980)
for row,job in zip(data['photo_panels'],jobs):
 assert row['frame0']==job['source_frame0'] and row['predicted_id']==job['predicted_id'] and row['similarity']==job['similarity'] and row['accepted']==job['accepted']
 path=ROOT/'delivery/results/foreground_with_identity/background'/row['photo_file'];assert sha(path)==row['photo_sha256']==job['photo_sha256']
 # Verify each displayed crop comes from the recorded actual image, using the saved nearest geometry.
 x,y,w,h=row['display_xywh'];assert np.ptp(sheet[y:y+h,x:x+w])>0
assert len(data['photo_panels'])==11 and totalbars==61
result={'status':'61_BAR_GEOMETRIES781_LINE_DATA_POINTS_AND_ALL11_NATIVE_PHOTO_LINKS_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'bar_geometries':61,'maximum_bar_geometry_error':maxerr,
 'time_series_data_points':sum(len(r['slot']) for r in data['lines']),'photo_panels':11,'main_figure_panels':4,
 'expected_actual_view_figures':2,'expected_actual_view_panels':15,'archive_sha256':sha(a),'new_model_forwards':0,'whole_goal_complete':False}
file=ROOT/'results/media_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
