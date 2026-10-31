"""Read only official ZIP directory/end records, never image/video payloads."""
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from collections import Counter
from datetime import datetime,timezone
import hashlib,io,json,zipfile,time
ROOT=Path(__file__).resolve().parents[1]
URL='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/2inu67jru7a6821kkgehxg3cv2.zip'
class RangeFile(io.RawIOBase):
    def __init__(self,out):
        self.op=build_opener(ProxyHandler({}));self.pos=0;self.out=out;self.calls=[];self.total=0
        with self.op.open(Request(URL,method='HEAD',headers={'User-Agent':'cow-published-index-audit/1.0','Accept-Encoding':'identity'}),timeout=35) as r:
            self.size=int(r.headers['Content-Length']);self.etag=r.headers.get('ETag');self.modified=r.headers.get('Last-Modified')
        assert self.size==39270266920
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,off,whence=0):
        self.pos=off if whence==0 else self.pos+off if whence==1 else self.size+off
        assert 0<=self.pos<=self.size;return self.pos
    def read(self,n=-1):
        if n<0:n=self.size-self.pos
        n=min(n,self.size-self.pos);assert 0<=n<=32*1024*1024 and self.total+n<=40*1024*1024
        if not n:return b''
        a,b=self.pos,self.pos+n-1;headers={'User-Agent':'cow-published-index-audit/1.0','Accept-Encoding':'identity','Range':f'bytes={a}-{b}'}
        if self.etag:headers['If-Match']=self.etag
        start=time.perf_counter()
        with self.op.open(Request(URL,headers=headers),timeout=50) as r:
            assert r.status==206 and r.headers['Content-Range']==f'bytes {a}-{b}/{self.size}'
            if self.etag:assert r.headers.get('ETag')==self.etag
            data=r.read(n+1);assert len(data)==n
        path=self.out/f'part_{len(self.calls):02d}.bin';assert not path.exists();path.write_bytes(data)
        self.calls.append({'start':a,'end':b,'bytes':n,'file':path.relative_to(ROOT).as_posix(),
            'sha256':hashlib.sha256(data).hexdigest(),'elapsed_s':time.perf_counter()-start})
        self.total+=n;self.pos+=n;return data
def main():
    out=ROOT/'evidence/zip_directory';out.mkdir(exist_ok=False);rf=RangeFile(out)
    with zipfile.ZipFile(rf) as archive:
        entries=[{'name':r.filename,'bytes':r.file_size,'compressed':r.compress_size,'CRC32':r.CRC,
                  'method':r.compress_type,'header_offset':r.header_offset,'directory':r.is_dir(),'extra_bytes':len(r.extra),'comment_bytes':len(r.comment)} for r in archive.infolist()]
        central=archive.start_dir
    assert all(r['start']>=central for r in rf.calls)
    for name,value in [('entries.json',entries),('non_image_video_members.json',[r for r in entries if not r['directory'] and Path(r['name']).suffix.lower() not in ['.jpg','.jpeg','.png','.mp4','.avi']])]:
        path=out/name;assert not path.exists();path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    summary={'status':'OFFICIAL_MULTI_CAM_ZIP_CENTRAL_DIRECTORY_COMPLETE_NO_MEMBER_PAYLOAD_READ',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'url':URL,'object_bytes':rf.size,'etag':rf.etag,'last_modified':rf.modified,
        'directory_start':central,'entries':len(entries),'files':sum(not r['directory'] for r in entries),
        'file_suffix_counts':dict(Counter(Path(r['name']).suffix.lower() for r in entries if not r['directory'])),
        'explicit_timestamp_or_mapping_filename_candidates':[r for r in entries if not r['directory'] and any(x in r['name'].lower() for x in ['timestamp','.csv','.json','.xml','annotat','mapping','readme'])],
        'range_bytes':rf.total,'range_requests':rf.calls,'image_video_member_pixels_read':False,
        'source_identity_mapping_certified':False,'whole_goal_complete':False}
    p=out/'summary.json';p.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['range_requests','explicit_timestamp_or_mapping_filename_candidates']}),flush=True)
    print(json.dumps(summary['explicit_timestamp_or_mapping_filename_candidates']))
if __name__=='__main__':main()
