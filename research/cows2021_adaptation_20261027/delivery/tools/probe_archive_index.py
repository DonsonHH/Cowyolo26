"""Bounded official ZIP directory-only range probe; no member payload reads."""
from pathlib import Path
import io,json,os,socket,time,zipfile
import requests

ROOT=Path(__file__).resolve().parents[1]
URL='https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/4vnrca7qw1642qlwxjadp87h7.zip'


class RangeFile(io.RawIOBase):
    def __init__(self,session,size,etag,record_dir):
        self.session=session;self.size=size;self.etag=etag;self.pos=0
        self.requests=[];self.record_dir=record_dir
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        target=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        if target<0:raise ValueError('Negative seek')
        self.pos=target;return target
    def read(self,size=-1):
        if size<0:size=self.size-self.pos
        size=min(size,self.size-self.pos)
        assert 0<=size<=32*1024*1024,'Refuse a large whole-archive read'
        if size==0:return b''
        start=self.pos;end=start+size-1;began=time.perf_counter()
        with self.session.get(URL,headers={'Range':f'bytes={start}-{end}','If-Match':self.etag,
                                           'Accept-Encoding':'identity'},timeout=(10,40),stream=True) as r:
            assert r.status_code==206 and r.headers['Content-Range']==f'bytes {start}-{end}/{self.size}'
            assert r.headers.get('ETag')==self.etag
            data=r.raw.read(size+1);assert len(data)==size
        name=f'index_part_{len(self.requests):02d}.bin'
        (self.record_dir/name).write_bytes(data)
        self.requests.append({'start':start,'end':end,'bytes':size,'elapsed_s':time.perf_counter()-began,'file':name})
        self.pos+=size
        return data


def main():
    assert socket.gethostname()=='mu01' and os.environ['HOME']=='/share/home/renly'
    out=ROOT/'results/archive_index_probe';out.mkdir(exist_ok=False)
    session=requests.Session();session.trust_env=False
    session.headers['User-Agent']='CattleResearch-official-archive-index/1.0'
    with session.head(URL,timeout=(10,20)) as response:
        response.raise_for_status();size=int(response.headers['Content-Length']);etag=response.headers['ETag']
    rf=RangeFile(session,size,etag,out)
    with zipfile.ZipFile(rf) as archive:
        infos=archive.infolist()
        items=[]
        for row in infos:
            items.append({'name':row.filename,'header_offset':row.header_offset,'compressed_size':row.compress_size,
                          'uncompressed_size':row.file_size,'CRC32':row.CRC,'method':row.compress_type,
                          'flags':row.flag_bits,'date_time':list(row.date_time),'directory':row.is_dir()})
    # The fetched bytes must all lie in the central directory / end records.
    # Every local member record begins before the start_dir found by zipfile.
    central_start=archive.start_dir
    assert all(r['start']>=central_start for r in rf.requests)
    manifest=json.loads((ROOT/'input/image_fetch_manifest.json').read_text())['items']
    matches=[]
    for selected in manifest:
        suffix=selected['url'].split('/4vnrca7qw1642qlwxjadp87h7/',1)[1]
        found=[row for row in items if row['name']==suffix or row['name'].endswith('/'+suffix)]
        assert len(found)==1,(selected['file_name'],len(found))
        matches.append({'file_name':selected['file_name'],'development_role':selected['development_role'],**found[0]})
    summary={'status':'CENTRAL_DIRECTORY_ONLY_READ_ALL_SELECTED_MEMBERS_FOUND','archive_url':URL,
             'archive_bytes':size,'archive_ETag':etag,'entries':len(items),'selected_images':len(matches),
             'selected_compressed_bytes':sum(r['compressed_size'] for r in matches),
             'selected_uncompressed_bytes':sum(r['uncompressed_size'] for r in matches),
             'compression_methods':sorted({r['method'] for r in matches}),
             'directory_start':central_start,'range_requests':rf.requests,
             'member_payload_or_image_pixels_read':False,'new_training_or_forward':False}
    (out/'entries.json').write_text(json.dumps(items,indent=2))
    (out/'selected_members.json').write_text(json.dumps(matches,indent=2))
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
