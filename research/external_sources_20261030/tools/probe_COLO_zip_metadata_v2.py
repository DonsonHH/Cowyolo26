"""Capture only release ZIP directory and annotation text; no image extraction."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import urllib.request,json,hashlib,struct,zlib,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/COLO_zip_metadata_v2';OUT.mkdir(exist_ok=False)
release=json.loads((ROOT/'evidence/data_endpoint_probes/COLO_release.response').read_text(encoding='utf-8'))
asset=next(a for a in release['assets'] if a['name']=='COLO_COCO.zip');URL=asset['browser_download_url'];SIZE=asset['size'];records=[];downloaded=0
def fetch(start,end,label):
 global downloaded
 assert 0<=start<=end<SIZE and end-start+1<=16*1024*1024
 req=urllib.request.Request(URL,headers={'User-Agent':'cow-research-source-audit','Range':f'bytes={start}-{end}'})
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}))
 with opener.open(req,timeout=18) as r:
  expected=f'bytes {start}-{end}/{SIZE}'
  if r.status!=206 or r.headers.get('Content-Range')!=expected:
   prefix=r.read(256);f=OUT/(label+'.unexpected_prefix');f.write_bytes(prefix)
   raise RuntimeError(('Range_not_honored',r.status,r.headers.get('Content-Range'),len(prefix)))
  data=r.read(end-start+2);assert len(data)==end-start+1
  row={'label':label,'offset_start':start,'offset_end_inclusive':end,'HTTP_status':r.status,'content_range':r.headers.get('Content-Range'),
       'etag':r.headers.get('ETag'),'final_host':urllib.request.urlparse(r.url).netloc if hasattr(urllib.request,'urlparse') else r.url.split('/')[2],
       'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 downloaded+=len(data);assert downloaded<=24*1024*1024;file=OUT/(label+'.range');file.write_bytes(data);row['file']=str(file.resolve());records.append(row);return data
result={'created_UTC':datetime.now(timezone.utc).isoformat(),'asset_id':asset['id'],'asset_name':asset['name'],'release_tag':release['tag_name'],'asset_size':SIZE,'source_URL':URL,'image_pixels_decoded':0,'model_forwards':0}
try:
 tail=fetch(max(0,SIZE-65557),SIZE-1,'zip_tail');pos=tail.rfind(b'PK\x05\x06');assert pos>=0
 e=struct.unpack_from('<4s4H2IH',tail,pos);assert e[1]==e[2]==0 and e[3]==e[4] and e[5]!=0xffffffff and e[6]!=0xffffffff
 count=e[4];directory_size=e[5];directory_offset=e[6]
 directory=fetch(directory_offset,directory_offset+directory_size-1,'central_directory');entries=[];cursor=0
 while cursor<len(directory):
  h=struct.unpack_from('<4s6H3I5H2I',directory,cursor);assert h[0]==b'PK\x01\x02';name_bytes=directory[cursor+46:cursor+46+h[10]]
  name=name_bytes.decode('utf-8' if h[3]&0x800 else 'cp437');assert '\x00' not in name
  entries.append({'name':name,'flags':h[3],'method':h[4],'CRC32':h[7],'compressed_bytes':h[8],'uncompressed_bytes':h[9],'local_header_offset':h[16]})
  cursor+=46+h[10]+h[11]+h[12]
 assert cursor==len(directory) and len(entries)==count
 (OUT/'entries.json').write_text(json.dumps(entries,indent=2)+'\n',encoding='utf-8')
 candidates=[x for x in entries if x['name'].lower().endswith('.json')];json_records=[]
 assert len(candidates)<=40
 for i,row in enumerate(candidates):
  assert row['uncompressed_bytes']<=8*1024*1024 and row['method'] in [0,8] and not row['flags']&1
  header=fetch(row['local_header_offset'],row['local_header_offset']+29,'json'+str(i).zfill(2)+'_header');h=struct.unpack('<4s5H3I2H',header);assert h[0]==b'PK\x03\x04' and h[3]==row['method']
  start=row['local_header_offset']+30+h[9]+h[10]
  data=fetch(start,start+row['compressed_bytes']-1,'json'+str(i).zfill(2)+'_data')
  decoded=zlib.decompress(data,-15) if row['method']==8 else data
  assert len(decoded)==row['uncompressed_bytes'] and zlib.crc32(decoded)&0xffffffff==row['CRC32']
  f=OUT/('annotations_'+str(i).zfill(2)+'.json');f.write_bytes(decoded);d=json.loads(decoded)
  json_records.append({'archive_member':row['name'],'file':str(f.resolve()),'sha256':hashlib.sha256(decoded).hexdigest(),'images':len(d.get('images',[])),
   'annotations':len(d.get('annotations',[])),'categories':d.get('categories'),'first_filenames':[r.get('file_name') for r in d.get('images',[])[:3]]})
 result.update({'status':'ZIP_DIRECTORY_AND_ALL_COCO_JSON_READ_CRC_VERIFIED','entries':count,'directory_bytes':directory_size,'json_files':json_records,'downloaded_range_bytes':downloaded})
except Exception as e:result.update({'status':'METADATA_ACCESS_INCOMPLETE','error_type':type(e).__name__,'error':str(e)[:600],'downloaded_range_bytes':downloaded})
result['range_records']=records
f=ROOT/'results/COLO_zip_metadata_probe.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='range_records'}))
