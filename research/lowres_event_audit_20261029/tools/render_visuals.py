from pathlib import Path
from datetime import datetime,timezone
import json,gzip,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protocol=load(ROOT/'protocol/visual_v1.json');manifest=load(ROOT/'results/native_frame_manifest.json');p=load(ROOT/'protocol/audit_v1.json')
cache=next(r for r in p['caches'] if r['condition']=='S192_rot90_seed26');raw={r['frame0']:r['predictions'] for r in json.loads(gzip.decompress(Path(cache['raw_file']).read_bytes()))}
references={(r['frame0'],r['reference_track_id']):r for r in load(ROOT/'input/reference_boxes.json')}
frames={r['source_frame0']:r for r in manifest['frames']};out=ROOT/'media/panels';out.mkdir(exist_ok=False)
fontpath='C:/Windows/Fonts/msyh.ttc';font=ImageFont.truetype(fontpath,24);small=ImageFont.truetype(fontpath,19);tiny=ImageFont.truetype(fontpath,16)
pages=[]
for choice in protocol['choices']:
    tid=choice['reference_track_id'];page=Image.new('RGB',(1920,900),'#15202d');draw=ImageDraw.Draw(page)
    draw.text((18,8),'192直角seed26：参照轨迹'+str(tid)+'，'+choice['zone']+'区连续观察诊断',font=font,fill='white')
    draw.text((18,43),'蓝框=640开发参照；绿框=192原始检测(conf≥0.2)。参照为模型轨迹，未当作人工框真值。',font=small,fill='#dce4ed')
    panelrecords=[]
    for column,frame in enumerate(choice['frames']):
        row=frames[frame];source=Image.open(row['file']).convert('RGB');source.load();assert source.size==(2560,1440) and sha(Path(row['file']))==row['sha256']
        reference=references[(frame,tid)]['xyxy'];detections=raw[frame];large=source.copy();d=ImageDraw.Draw(large)
        for pred in detections:d.rectangle(tuple(pred['xyxy']),outline='#77e5a3',width=4)
        d.rectangle(tuple(reference),outline='#56baff',width=6)
        for x in [.34,.75]:d.line([(round(x*2560),0),(round(x*2560),1439)],fill='#ffb74b',width=3)
        for y in [.4,.6]:d.line([(round(.34*2560),round(y*1440)),(round(.75*2560),round(y*1440))],fill='#ffb74b',width=3)
        thumb=large.resize((640,360),Image.Resampling.LANCZOS);page.paste(thumb,(column*640,110))
        x0=max(0,int(reference[0])-80);y0=max(0,int(reference[1])-80);x1=min(2560,int(np.ceil(reference[2]))+80);y1=min(1440,int(np.ceil(reference[3]))+80)
        crop=large.crop((x0,y0,x1,y1));scale=min(620/crop.width,340/crop.height);dimensions=(round(crop.width*scale),round(crop.height*scale))
        crop=crop.resize(dimensions,Image.Resampling.LANCZOS);page.paste(crop,(column*640+(640-dimensions[0])//2,525+(340-dimensions[1])//2))
        draw.text((column*640+12,78),'源帧 '+str(frame)+' / '+format(frame/25,'.2f')+'秒',font=small,fill='white')
        draw.text((column*640+12,480),'原生像素细节（固定参照框外扩80px，仅展示用）',font=tiny,fill='#dce4ed')
        panelrecords.append({'source_frame0':frame,'source_file_sha256':row['sha256'],'reference_box':reference,'raw_boxes':[r['xyxy'] for r in detections],
                             'detail_crop_box':[x0,y0,x1,y1],'detail_display_dimensions':list(dimensions),'panels':2})
    draw.text((18,873),'入口/出口计数规则保持A<0.4、B>0.6、各3个连续采样；5Hz采样。此页不新增标注或改模型。',font=tiny,fill='#dce4ed')
    file=out/('reference_'+str(tid)+'_'+choice['zone']+'.png');page.save(file)
    pages.append({'path':str(file.resolve()),'sha256':sha(file),'reference_track_id':tid,'zone':choice['zone'],'image_panels':6,'columns':panelrecords})
result={'status':'SIX_FIXED_PRIMARY_MODEL_REFERENCE_CASE_PAGES_COMPLETE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'pages':pages,'total_figures':6,'total_image_panels':36,'all_export_frames_within_user_scope':True,
 'visual_protocol_sha256':sha(ROOT/'protocol/visual_v1.json'),'new_network_forwards':0,'new_reference_labels':0,'whole_goal_complete':False}
file=ROOT/'results/media_manifest.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pages':6,'panels':36}))
