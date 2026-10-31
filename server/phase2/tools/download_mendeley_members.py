from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,struct,time,shutil
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2');OUT=ROOT/'data/mendeley_counting/selected_compressed';OUT.mkdir(parents=True,exist_ok=True)
URL='https://data.mendeley.com/public-files/datasets/dk54zg67dd/files/447679ea-783a-4702-bdd8-285dab542906/file_downloaded'
selected={'Ground Truth/gt.txt','Ground Truth/Toros.mp4','Videos/Toros2.mp4','Videos/Toros4.mp4','Videos/Toros5.mp4','Videos/Toros6.mp4','Videos/Toros7.mp4','Videos/Vacas1.mp4'}
rows=[r for r in json.loads((ROOT/'catalog/mendeley_zip_members.json').read_text()) if r['name'] in selected]
def request_range(start,end):
 for attempt in range(3):
  try:
   op=build_opener(ProxyHandler({}))
   with op.open(Request(URL,headers={'Range':f'bytes={start}-{end}','User-Agent':'Mozilla/5.0'}),timeout=40) as r:
    if r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):raise ValueError('Range not honored')
    data=r.read(end-start+2)
   if len(data)!=end-start+1:raise ValueError('short payload')
   return data
  except Exception:
   if attempt==2:raise
   time.sleep(1+attempt)
tasks=[]
for r in rows:
 header=request_range(r['header_offset'],r['header_offset']+29)
 if header[:4]!=b'PK\x03\x04':raise ValueError('bad local ZIP header')
 namelen,extra=struct.unpack_from('<HH',header,26);start=r['header_offset']+30+namelen+extra;r['compressed_data_offset']=start
 safe=r['name'].replace('/','__').replace(' ','_');r['compressed_path']=str(OUT/(safe+'.deflate'));chunks=OUT/(safe+'.chunks');chunks.mkdir(exist_ok=True)
 for offset in range(0,r['compressed'],1024*1024):
  count=min(1024*1024,r['compressed']-offset);p=chunks/f'{offset:012d}.bin'
  if not p.exists() or p.stat().st_size!=count:tasks.append((start+offset,start+offset+count-1,p))
print(json.dumps({'selected_members':len(rows),'bytes_to_transfer':sum(r['compressed'] for r in rows),'chunks_pending':len(tasks),'route':'direct range download; US3 endpoint returned403'}),flush=True)
t=time.time()
def get(task):
 start,end,p=task;p.write_bytes(request_range(start,end));return p
with ThreadPoolExecutor(max_workers=12) as pool:
 for i,f in enumerate(as_completed([pool.submit(get,task) for task in tasks]),1):
  f.result()
  if i%10==0:print(json.dumps({'chunks_done':i,'chunks_total':len(tasks),'elapsed_s':round(time.time()-t,1)}),flush=True)
for r in rows:
 safe=r['name'].replace('/','__').replace(' ','_');chunks=OUT/(safe+'.chunks');p=Path(r['compressed_path'])
 with p.open('wb') as f:
  for offset in range(0,r['compressed'],1024*1024):
   with (chunks/f'{offset:012d}.bin').open('rb') as s:shutil.copyfileobj(s,f)
 if p.stat().st_size!=r['compressed']:raise ValueError('assembled compressed length mismatch')
(OUT/'members_manifest.json').write_text(json.dumps({'archive_url':URL,'archive_expected_sha256':'1fcb101ac83eb917f492e00f10b8b67d912fbb1bc881e40b11713a078868e01b','archive_fully_downloaded':False,'members':rows},indent=2))
print(json.dumps({'completed_members':len(rows),'elapsed_s':round(time.time()-t,1)}),flush=True)
