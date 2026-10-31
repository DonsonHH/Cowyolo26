from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import numpy as np
import json,hashlib,tarfile,gzip,subprocess,xml.etree.ElementTree as ET,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
transfer=load(ROOT/'evidence/media_transfer.json');archive=ROOT/'media_delivery.tar.gz'
assert sha(archive)==transfer['sha256'] and archive.stat().st_size==transfer['bytes']
OUT=ROOT/'media_delivery';OUT.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==transfer['members']
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(OUT/m.name).resolve();assert p.is_relative_to(OUT.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
for row in load(OUT/'results/media/manifest.json'):
 p=OUT/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
for rel in ['tools/render_media.py','protocol/media_v1.json','tools/media.slurm']:assert sha(OUT/rel)==sha(ROOT/rel)
media=OUT/'results/media';meta=load(media/'media_metadata.json');data=load(media/'plot_data.json');board=load(ROOT/'board_delivery/results/record.json');quality=load(ROOT/'delivery/results/quality/summary.json')
xml=ET.parse(media/'quality_and_actual_board.svg');ns={'s':'http://www.w3.org/2000/svg'}
count=0;maxerror=0.
for panel in range(4):
 axis=xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]',ns);paths=[]
 for element in axis:
  if element.attrib.get('id','').startswith('patch_'):
   path=element.find('s:path',ns)
   if path is not None and 'clip-path' in path.attrib:paths.append(path)
 rows=[r for r in data['bars'] if r['panel']==panel];assert len(rows)==len(paths)==[3,6,3,7][panel]
 for row,path in zip(rows,paths):
  if panel==0:
   if row['label']=='O8 actual':value=next(m['down'] for scene in board['scenes'] if scene['scene']=='original' for m in scene['metrics'] if m['counter']=='handoff_events')
   else:value=next(m['down'] for m in quality['video_metrics'] if m['scene']=='original' and m['mode']==row['label'] and m['counter']=='handoff_events')
  elif panel==1:
   if row['label'].startswith('O8 actual'):
    stride=6 if row['label'].endswith('5Hz') else 1
    value=next(r['TP'] for r in load(ROOT/'results/independent_board_verification.json')['publisher_event_scores'] if r['stride']==stride and r['counter']=='handoff_events')
   else:
    mode='FP32' if row['label'].startswith('FP32') else 'QDQ';stride=6 if row['label'].endswith('5Hz') else 1
    value=next(r['formal_event_metrics']['TP'] for r in quality['video_metrics'] if r['scene']=='toros' and r['mode']==mode and r['stride']==stride and r['counter']=='handoff_events')
  elif panel==2:
   a=np.asarray([r['PNG_to_counter_with_raw_save_ms'] for r in board['rows']]);value={'Mean':a.mean(),'P95':np.quantile(a,.95),'Maximum':a.max()}[row['label']]
  else:value=np.mean([r[row['label']] for r in board['rows']])
  assert abs(row['value']-value)<1e-9
  clip=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1);rect=xml.find('.//s:clipPath[@id="'+clip+'"]/s:rect',ns)
  coords=np.asarray([float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]).reshape(-1,2)
  if panel==3:
   plotted=np.ptp(coords[:,0])/float(rect.attrib['width'])*175
   y=(coords[0,1]-float(rect.attrib['y']))/float(rect.attrib['height'])*7.2-.6
   error=max(abs(plotted-value),abs(y-row['bar_y']))
  else:
   maximum=[14,7,data['timing_ymax']][panel];width=[3.2,2.2,3.2][panel]
   plotted=np.ptp(coords[:,1])/float(rect.attrib['height'])*maximum
   x=(coords[0,0]-float(rect.attrib['x']))/float(rect.attrib['width'])*width-.6
   error=max(abs(plotted-value),abs(x-row['bar_x']))
  assert error<2e-5;maxerror=max(maxerror,error);count+=1
assert count==19
movie=OUT/meta['movie_file'];assert sha(movie)==meta['movie_sha256'] and meta['frames']==1962
probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames','-of','json',str(movie)],capture_output=True,text=True,check=True)
stream=json.loads(probe.stdout)['streams'][0];assert [stream['width'],stream['height']]==[1920,450] and stream['avg_frame_rate']=='25/1' and int(stream['nb_read_frames'])==1962
decode=subprocess.run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',str(movie),'-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True);assert not decode.stderr
frames=ROOT/'results/decoded_media_anchors';frames.mkdir(exist_ok=False);checks=[]
folders=[ROOT/'delivery/results/quality/original/FP32',ROOT/'delivery/results/quality/original/QDQ',ROOT/'board_delivery/results/original']
for row in meta['previews']:
 index=row['source_frame0']-8912;assert index==row['video_index0'];png=OUT/row['file'];assert sha(png)==row['sha256']
 file=frames/('f'+str(row['source_frame0'])+'.png')
 subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vf','select=eq(n\\,'+str(index)+')','-frames:v','1','-fps_mode','vfr',str(file)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
 with Image.open(file) as im:a=np.asarray(im.convert('RGB'),np.int16)
 with Image.open(png) as im:b=np.asarray(im.convert('RGB'),np.int16)
 assert a.shape==b.shape==(450,1920,3);delta=np.abs(a-b);mean=float(delta.mean());p95=float(np.quantile(delta,.95));assert mean<6 and p95<20
 for panel in row['panels']:
  trace=gz(folders[panel['mode_index']]/'stride5_counter_trace.json.gz');events=[e for e in trace['handoff_events'] if 8912<=e['frame0']<=10873]
  assert panel['down']==sum(e['frame0']<=row['source_frame0'] and e['direction']=='A->B' for e in events)
  assert panel['up']==sum(e['frame0']<=row['source_frame0'] and e['direction']=='B->A' for e in events)
  assert panel['sample_frame0']==row['source_frame0']-row['source_frame0']%5
  assert panel['post_tracker_boxes']==sum(r['frame0']==panel['sample_frame0'] for r in trace['post_tracker'])
 checks.append({'source_frame0':row['source_frame0'],'path':str(file.resolve()),'sha256':sha(file),'mean_RGB_delta':mean,'p95_RGB_delta':p95,'panels':3})
result={'status':'19_FIGURE_BARS1962_VIDEO_FRAMES_AND12_ACTUAL_ANCHOR_PANELS_INDEPENDENTLY_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'SVG_bar_geometries':count,'max_SVG_geometry_error':maxerror,
 'strict_decoded_video_frames':1962,'source_scope_frame0_inclusive':[8912,10873],'movie_dimensions_WH':[1920,450],
 'anchor_checks':checks,'expected_figures_actually_to_view':5,'expected_total_panels_to_view':16,
 'archive_sha256':sha(archive),'archive_members':len(members),'new_model_forwards':0,'whole_goal_complete':False}
file=ROOT/'results/media_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='anchor_checks'}))
