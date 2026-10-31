from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
import json,gzip,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frames=[9310,9345,9360];protocol={'status':'FROZEN_BEFORE_MISSING94_SOURCE_PIXELS_RENDER','created_UTC':datetime.now(timezone.utc).isoformat(),
 'reference_model_track_id':94,'frame0_anchors':frames,'selection':'Entry/mid/exitforremainingreference94;noIoU/confidencesearch.',
 'source_sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1','reference_is_independent_GT':False,
 'actual_network_input_pngs_from_previous_verified_board_preparation':True,'new_model_forwards':0,'whole_goal_complete':False}
file=ROOT/'protocol/visual_v1.json';assert not file.exists();file.write_text(json.dumps(protocol,indent=2)+'\n')
source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';assert sha(source)==protocol['source_sha256']
out=ROOT/'results/native_frames';out.mkdir(exist_ok=False)
subprocess.run(['ffmpeg','-v','error','-i',str(source),'-vf','select='+ '+'.join('eq(n\\,'+str(f)+')' for f in frames),'-frames:v','3','-fps_mode','vfr',str(out/'anchor_%02d.png')],check=True,capture_output=True)
reference={r['frame0']:r for r in load(ROOT/'input/reference_boxes.json') if r['reference_track_id']==94}
actual=gz(PROJECT/'pynq_rot192_eval_20261029/board_delivery/results_v2/original/raw_predictions.json.gz');actual={r['frame0']:r['predictions'] for r in actual}
page=Image.new('RGB',(1920,1320),'#f2f4f7');draw=ImageDraw.Draw(page)
fontfile='C:/Windows/Fonts/arial.ttf';font=ImageFont.truetype(fontfile,23);small=ImageFont.truetype(fontfile,18)
draw.text((14,9),'Remaining unmatched development reference94: source context / native lane detail / actual192 input',font=font,fill='#1f334a')
draw.text((14,39),'Blue=640 model reference; green=actual O8 detections. Reference is not independent annotation or permanent cow identity.',font=small,fill='#33445a')
records=[]
for i,frame in enumerate(frames):
 file=out/('anchor_'+str(i+1).zfill(2)+'.png')
 with Image.open(file) as im:native=im.convert('RGB')
 assert native.size==(2560,1440)
 sourcepanel=native.resize((800,450),Image.Resampling.BILINEAR);painter=ImageDraw.Draw(sourcepanel)
 boxes=[('reference',reference[frame]['xyxy'])]+[('actual',r['xyxy']) for r in actual[frame]]
 for kind,box in boxes:
  color='#347deb' if kind=='reference' else '#25a55c';painter.rectangle(tuple(v*800/2560 for v in box),outline=color,width=2)
 y=75+i*405;page.paste(sourcepanel.resize((704,396),Image.Resampling.BILINEAR),(0,y))
 detail=native.crop((870,0,1920,1440)).resize((289,396),Image.Resampling.BILINEAR);painter=ImageDraw.Draw(detail)
 for kind,box in boxes:
  x1,y1,x2,y2=box;color='#347deb' if kind=='reference' else '#25a55c';painter.rectangle(((x1-870)*289/1050,y1*396/1440,(x2-870)*289/1050,y2*396/1440),outline=color,width=2)
 page.paste(detail,(730,y))
 tensorfile=PROJECT/'pynq_rot192_eval_20261029/delivery/results/quality_v2/board_inputs/original'/('f'+str(frame).zfill(5)+'.png')
 with Image.open(tensorfile) as im:inputimage=im.convert('RGB')
 assert inputimage.size==(192,192);page.paste(inputimage.resize((384,384),Image.Resampling.NEAREST),(1060,y+6))
 draw.text((1460,y+30),'Source f'+str(frame),font=font,fill='#243954')
 draw.text((1460,y+73),'Reference94 y='+format(reference[frame]['axis_position'],'.3f'),font=small,fill='#347deb')
 draw.text((1460,y+110),'Actual cow boxes: '+str(len(actual[frame])),font=small,fill='#188046')
 draw.text((1460,y+147),'192 input shown2x nearest',font=small,fill='#33445a')
 draw.text((1460,y+184),'All predictions retained',font=small,fill='#33445a')
 records.append({'frame0':frame,'source_native_png':str(file.resolve()),'source_native_png_sha256':sha(file),
  'actual192_input_file':str(tensorfile.resolve()),'actual192_input_sha256':sha(tensorfile),'reference_box':reference[frame]['xyxy'],'actual_predictions':actual[frame]})
draw.text((14,1301),'No new inference; full model scope0..10873 retained. Human12 is total only. Candidate94 raw coverage:2/15 at both IoU0.5 and0.3.',font=small,fill='#33445a')
file=ROOT/'results/remaining94_source_and_actual_input.png';page.save(file)
record={'status':'THREE_NATIVE_SOURCE_ANCHORS_AND_VERIFIED192_INPUTS_RENDERED','file':str(file.resolve()),'sha256':sha(file),'panels':9,'records':records,
 'new_model_forwards':0,'reference_is_independent_GT':False,'whole_goal_complete':False}
(ROOT/'results/visual_manifest.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='records'}))
