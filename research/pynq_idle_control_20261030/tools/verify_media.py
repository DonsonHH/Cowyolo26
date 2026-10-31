from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile,re,xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=load(ROOT/'evidence/media_transfer.json');archive=ROOT/'media_delivery.tar.gz';assert sha(archive)==t['sha256'] and archive.stat().st_size==t['bytes']
out=ROOT/'media_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==t['members']
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  file=(out/m.name).resolve();assert file.is_relative_to(out.resolve()) and not file.exists()
  file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(m).read())
for row in load(out/'results/media/manifest.json'):assert sha(out/row['file'])==row['sha256'] and (out/row['file']).stat().st_size==row['bytes']
media=out/'results/media';data=load(media/'plot_data.json');xml=ET.parse(media/'idle_control_all_runs.svg');ns={'s':'http://www.w3.org/2000/svg'}
current=ROOT/'delivery';prior=PROJECT/'pynq_periodic_joint_20261030/delivery';roots=[prior,prior,current,current]
for index,row in enumerate(data['runs']):
 records=load(roots[index]/'results'/row['case']/'timing_rows.json')
 assert row['slot']==[r['slot'] for r in records] and row['release_to_count_ms']==[r['release_to_count_ms'] for r in records]
 summary=next(r for r in load(roots[index]/'results/record.json')['cases'] if r['case']==row['case'])
 assert [row[k] for k in ['processed','skipped','late']]==[summary[k] for k in ['processed_frames','skipped_slots','deadline_misses']]
jobs=load(current/'results/foreground_idle_identity/background/record.json')['jobs'];bars=0;maxerror=0.
for panel in [1,2]:
 axis=xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]',ns);paths=[]
 for element in axis:
  if element.attrib.get('id','').startswith('patch_'):
   path=element.find('s:path',ns)
   if path is not None and 'clip-path' in path.attrib:paths.append(path)
 rows=[r for r in data['bars'] if r['panel']==panel];assert len(rows)==len(paths)==(8 if panel==1 else 22)
 for row,path in zip(rows,paths):
  value=data['runs'][row['source_index']][{'Skipped':'skipped','Late':'late'}[row['kind']]] if panel==1 else jobs[row['job_index']][row['key']]
  assert value==row['value']
  clip=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1);rect=xml.find('.//s:clipPath[@id="'+clip+'"]/s:rect',ns)
  points=np.asarray([float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]).reshape(-1,2)
  height=np.ptp(points[:,1])/float(rect.attrib['height'])*(145 if panel==1 else 1300)
  xpos=(points[0,0]-float(rect.attrib['x']))/float(rect.attrib['width'])*(2.2 if panel==1 else 11.2)-.6
  error=max(abs(height-value),abs(xpos-row['x']));assert error<3e-5;maxerror=max(maxerror,error);bars+=1
pause=load(current/'results/foreground_idle_identity/worker_pause_intervals.json');summary=next(r for r in load(current/'results/record.json')['cases'] if r['case']=='foreground_idle_identity');t0=summary['clock_start_monotonic_ns']
assert data['worker_pause_windows_s']==[[(r['pause_acknowledged_monotonic_ns']-t0)/1e9,(r['foreground_completed_monotonic_ns']-r['pause_acknowledged_monotonic_ns'])/1e9] for r in pause]
assert len(data['photos'])==11
for row,job in zip(data['photos'],jobs):
 assert row['photo_file']==job['photo_file'] and row['source_frame0']==job['source_frame0'] and row['predicted_id']==job['predicted_id'] and row['accepted']==job['accepted']
 assert sha(current/'results/foreground_idle_identity/background'/job['photo_file'])==row['photo_sha256']
with Image.open(media/'all11_idle_photos.png') as im:im.load();assert im.size==(1600,980)
r={'status':'30_SVG_BARS1564_FULL_TIMING_POINTS392_PAUSE_WINDOWS_AND11_PHOTO_LINKS_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'bars':bars,'maximum_bar_geometry_error':maxerror,'time_series_points':sum(len(r['slot']) for r in data['runs']),
 'pause_windows':len(pause),'photo_links':11,'expected_figures_to_view':2,'expected_panels_to_view':15,'new_model_forwards':0,'whole_goal_complete':False}
file=ROOT/'results/media_verification.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
