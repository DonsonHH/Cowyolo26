from pathlib import Path
from datetime import datetime,timezone
import json,urllib.request,struct,zlib,hashlib,concurrent.futures
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];plan=json.loads((ROOT/'protocol/COLO_train8_pixel_admission_v1.json').read_text(encoding='utf-8'))
OUT=ROOT/'input/COLO_train8_QA';OUT.mkdir(parents=True,exist_ok=False);URL='https://github.com/Niche-Lab/COLO/releases/download/v1.0.0/COLO_COCO.zip';SIZE=420543072
def get_range(start,end):
 op=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}))
 with op.open(urllib.request.Request(URL,headers={'Range':f'bytes={start}-{end}','User-Agent':'cow-research-source-audit'}),timeout=18) as r:
  assert r.status==206 and r.headers.get('Content-Range')==f'bytes {start}-{end}/{SIZE}'
  data=r.read(end-start+2);assert len(data)==end-start+1;return data
def acquire(item):
 index,row=item;e=row['zip_entry'];rec={'index':index,'archive_member':row['archive_member'],'role':row['role'],'lighting':row['lighting']}
 try:
  header=get_range(e['local_header_offset'],e['local_header_offset']+29);h=struct.unpack('<4s5H3I2H',header);assert h[0]==b'PK\x03\x04' and h[3]==e['method']
  start=e['local_header_offset']+30+h[9]+h[10];payload=get_range(start,start+e['compressed_bytes']-1)
  raw=zlib.decompress(payload,-15) if e['method']==8 else payload;assert len(raw)==e['uncompressed_bytes'] and zlib.crc32(raw)&0xffffffff==e['CRC32']
  f=OUT/row['file_name'];f.write_bytes(raw)
  with Image.open(f) as im:im.load();image=im.convert('RGB')
  assert image.size==(row['image']['width'],row['image']['height'])
  rec.update({'status':'SOURCE_JPEG_CRC_AND_DIMENSIONS_VERIFIED','file':str(f.resolve()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
   'decoded_RGB_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'WH':list(image.size),'annotations':row['annotations'],'downloaded_bytes':len(header)+len(payload)})
 except Exception as error:rec.update({'status':'FAILED_SOURCE_ADMISSION','error':str(error)[:350]})
 return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(acquire,enumerate(plan['selected_rows'])))
manifest={'status':'TRAIN8_PIXEL_QA_ACQUISITION_FINISHED','created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,
 'test50_pixels_requested':False,'new_model_forwards':0,'proxy_or_node_configuration_changed':False,'whole_goal_complete':False}
file=ROOT/'results/COLO_train8_acquisition.json';assert not file.exists();file.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
assert all(r['status']=='SOURCE_JPEG_CRC_AND_DIMENSIONS_VERIFIED' for r in records)
dest=ROOT/'results/COLO_train8_panels';dest.mkdir(exist_ok=False);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13);sheets=[]
for page in range(2):
 for mode in ['raw','publisher_GT']:
  canvas=Image.new('RGB',(1000,1120),'#f4f6f7');draw=ImageDraw.Draw(canvas)
  draw.text((15,12),'COLO Top-View TRAIN ONLY | admission QA | '+mode+' | page'+str(page+1),font=font,fill='#203c42')
  draw.text((15,40),'Author640px export; no model predictions. Official test50 remains unopened.',font=small,fill='#4d6268');panels=[]
  for j,row in enumerate(records[page*4:page*4+4]):
   with Image.open(row['file']) as im:im.load();image=im.convert('RGB')
   if mode=='publisher_GT':
    idraw=ImageDraw.Draw(image)
    for a in row['annotations']:
     x,y,w,h=a['bbox'];color='#ffbc42' if min(w,h)>0 else '#ff4040';idraw.rectangle((x,y,x+w,y+h),outline=color,width=2)
   image.thumbnail((480,480),Image.Resampling.BILINEAR);x=15+(j%2)*495;y=83+(j//2)*510;canvas.paste(image,(x,y))
   draw.text((x,y+484),'QA'+str(row['index'])+' '+row['lighting']+' | boxes '+str(len(row['annotations'])),font=small,fill='#203c42')
   panels.append({'source_file':row['file'],'source_sha256':row['sha256'],'index':row['index'],'rect':[x,y,image.width,image.height],'overlay_mode':mode})
  f=dest/(mode+'_page'+str(page+1)+'.png');canvas.save(f);sheets.append({'file':str(f.resolve()),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'panels':panels})
f=ROOT/'results/COLO_train8_visual_manifest.json';assert not f.exists();f.write_text(json.dumps({'files':sheets,'new_source_images':8,'panels':16,'actually_viewed':False,'new_model_forwards':0},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_QA_images':8,'native_dimensions_match':True,'visual_sheets':4,'test_images_opened':0,'model_forwards':0}))
