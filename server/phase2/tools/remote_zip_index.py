from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
import io,zipfile,json
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2');OUT=ROOT/'catalog'
URL='https://data.mendeley.com/public-files/datasets/dk54zg67dd/files/447679ea-783a-4702-bdd8-285dab542906/file_downloaded'
class HTTPFile(io.RawIOBase):
 def __init__(self):
  self.op=build_opener(ProxyHandler({}));self.pos=0;self.size=275216868;self.fetched=0
 def seekable(self):return True
 def readable(self):return True
 def seek(self,off,whence=0):self.pos=off if whence==0 else (self.pos+off if whence==1 else self.size+off);return self.pos
 def tell(self):return self.pos
 def read(self,n=-1):
  if n<0:n=self.size-self.pos
  n=min(n,self.size-self.pos)
  if n<=0:return b''
  start=self.pos;end=start+n-1
  with self.op.open(Request(URL,headers={'Range':f'bytes={start}-{end}','User-Agent':'Mozilla/5.0'}),timeout=35) as r:
   if r.status!=206:raise ValueError('Range unavailable')
   data=r.read()
  if len(data)!=n:raise ValueError('Range length mismatch')
  self.pos+=n;self.fetched+=n;return data
f=HTTPFile()
with zipfile.ZipFile(f) as z:
 rows=[{'name':x.filename,'bytes':x.file_size,'compressed':x.compress_size,'header_offset':x.header_offset,'compression':x.compress_type,'crc32':f'{x.CRC:08x}'} for x in z.infolist() if not x.is_dir()]
(OUT/'mendeley_zip_members.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps({'archive_bytes':f.size,'index_bytes_fetched':f.fetched,'files':rows}),flush=True)
