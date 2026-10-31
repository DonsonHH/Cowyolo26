from pathlib import Path
from datetime import datetime,timezone
import json,gzip,hashlib,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
frames=[9545,9550,9555]
p={'created_UTC':datetime.now(timezone.utc).isoformat(),'development_reference_track':103,'reference_is_independent_GT':False,
    'frames':frames,'selection':'threeconsecutiverawAobservationsaround9550failedconfirmation;notselectedforvisualsuccess',
    'source_sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1','new_model_forwards':0,'whole_goal_complete':False}
file=ROOT/'protocol/visual_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
out=ROOT/'results/native_frames';out.mkdir(exist_ok=False)
source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';assert sha(source)==p['source_sha256']
filter='+'.join('eq(n\\,'+str(f)+')' for f in frames)
subprocess.run(['ffmpeg','-v','error','-i',str(source),'-vf','select='+filter,'-frames:v','3','-fps_mode','passthrough',str(out/'anchor_%02d.png')],capture_output=True,check=True)
references={r['frame0']:r for r in load(ROOT/'input/reference_boxes.json') if r['reference_track_id']==103}
caches=load(ROOT/'protocol/audit_v1.json')['caches'];data={}
for c in caches:
    raw={r['frame0']:r['predictions'] for r in gz(c['raw_file'])};trace=gz(c['trace_file']);post={f:[r for r in trace['post_tracker'] if r['frame0']==f] for f in frames}
    obs={r['frame0']:r for r in trace['observations']};data[c['condition']]={'raw':raw,'post':post,'obs':obs}
fontpath='C:/Windows/Fonts/arial.ttf';font=ImageFont.truetype(fontpath,22);small=ImageFont.truetype(fontpath,17)
canvas=Image.new('RGB',(1540,1690),'#f2f5f7');draw=ImageDraw.Draw(canvas)
draw.text((14,12),'New-vs-old actual O8: entry observations around the confirmation failure',font=font,fill='#193844')
draw.text((14,43),'Blue=old640 development reference; orange=raw boxes; green=confirmed tracker output. No permanent-ID or independent GT.',font=small,fill='#48616c')
for x,label in [(12,'Old O8 native lane'),(372,'New O8 native lane'),(735,'Exact shared192 input'),(1145,'Frozen trace facts')]:draw.text((x,77),label,font=font,fill='#193844')
records=[]
for i,frame in enumerate(frames):
    nativefile=out/('anchor_'+str(i+1).zfill(2)+'.png')
    with Image.open(nativefile) as im:im.load();native=im.convert('RGB')
    assert native.size==(2560,1440);y=114+i*505
    for ci,name in enumerate(['old_O8','new_O8']):
        panel=native.crop((870,0,1920,1440)).resize((342,469),Image.Resampling.BILINEAR);pd=ImageDraw.Draw(panel)
        def rect(box,color,width):
            x1,y1,x2,y2=box;pd.rectangle(((x1-870)*342/1050,y1*469/1440,(x2-870)*342/1050,y2*469/1440),outline=color,width=width)
        rect(references[frame]['xyxy'],'#3574d8',3)
        for row in data[name]['raw'][frame]:rect(row['xyxy'],'#d58930',1)
        for row in data[name]['post'][frame]:
            if row['track_id'] is None:continue
            rect(row['xyxy'],'#26ab68',2)
            a,b,c,d=row['xyxy'];pd.text((max(0,min(280,(a-870)*342/1050)),max(0,min(440,b*469/1440))),str(row['track_id']),font=small,fill='#148345',stroke_width=1,stroke_fill='#eff5f4')
        canvas.paste(panel,(12+ci*360,y))
    new_input=PROJECT/'pynq_mosaic192_eval_20261030/delivery/results/quality/board_inputs/original'/('f'+str(frame).zfill(5)+'.png')
    old_input=PROJECT/'pynq_rot192_eval_20261029/delivery/results/quality_v2/board_inputs/original'/new_input.name
    with Image.open(new_input) as im:im.load();pixels=im.convert('RGB')
    with Image.open(old_input) as im:im.load();assert im.convert('RGB').tobytes()==pixels.tobytes()
    canvas.paste(pixels.resize((384,384),Image.Resampling.NEAREST),(735,y+40))
    o=data['new_O8']['obs'][frame]
    ledger=gz(ROOT/'results/new_O8/iou03/frame_correspondence.json.gz');entry=next(r for r in ledger if r['reference_track_id']==103 and r['frame0']==frame)
    lines=['source f'+str(frame),'reference103 y='+format(references[frame]['axis_position'],'.3f'),
        'raw score='+format(entry['raw_confidence'],'.6f'),'raw center y='+format(entry['raw_axis_position'],'.3f'),
        'confirmed ID='+str(entry['post_track_id']),'tentative IDs='+str(sorted(o['tentative_positions'])),
        'admitted priors='+str(len(o['accepted_history'])),'fixed conf0.2; stable3',
        'At9550: fused minimum','1-score=0.711417 >0.7',
        'Input pixels unchanged.','Reference IDs are model','tracks, not cow identities.']
    for li,line in enumerate(lines):draw.text((1145,y+16+li*30),line,font=small,fill='#294653')
    draw.text((16,y+473),'Source f'+str(frame),font=small,fill='#294653')
    records.append({'frame0':frame,'native_file':str(nativefile.resolve()),'native_sha256':sha(nativefile),
        'new_input_path':str(new_input.resolve()),'new_input_sha256':sha(new_input),'old_input_path':str(old_input.resolve()),
        'shared_decoded_input_pixels_exact':True,'raw_predictions':{n:data[n]['raw'][frame] for n in data},
        'post_tracker':{n:data[n]['post'][frame] for n in data},'new_observation':o})
draw.text((14,1645),'Actual old count11; new10; human total12. This contact sheet diagnoses confirmed-track evidence, not event-level accuracy.',font=small,fill='#48616c')
f=ROOT/'results/reference103_entry_confirmation.png';canvas.save(f)
record={'status':'THREE_NATIVE_FRAME_OLD_NEW_TRACKER_AND_SHARED_INPUT_PANELS_RENDERED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'file':str(f.resolve()),'sha256':sha(f),'panels':9,'source_records':records,'new_model_forwards':0,'reference_is_independent_GT':False,'whole_goal_complete':False}
f=ROOT/'results/visual_manifest.json';assert not f.exists();f.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='source_records'}))
