from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from datetime import datetime,timezone
import hashlib,json,struct,zlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    prior=load(ROOT/'evidence/zip_directory/summary.json');entries=load(ROOT/'evidence/zip_directory/entries.json')
    selected=[r for r in entries if not r['directory'] and Path(r['name']).name in ['.info.json','.info.rdf','readme.txt']]
    assert any(r['name'].endswith('/.info.json') for r in selected)
    out=ROOT/'evidence/zip_metadata';out.mkdir(exist_ok=False);op=build_opener(ProxyHandler({}));calls=[]
    def request_range(a,b):
        n=b-a+1;assert 0<n<5*1024*1024
        headers={'User-Agent':'cow-source-metadata-member-audit/1.0','Accept-Encoding':'identity','Range':f'bytes={a}-{b}','If-Match':prior['etag']}
        with op.open(Request(prior['url'],headers=headers),timeout=50) as response:
            assert response.status==206 and response.headers['Content-Range']==f'bytes {a}-{b}/{prior["object_bytes"]}' and response.headers.get('ETag')==prior['etag']
            data=response.read(n+1);assert len(data)==n
        path=out/f'range_{len(calls):02d}.bin';path.write_bytes(data)
        calls.append({'start':a,'end':b,'file':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()});return data
    records=[]
    for r in selected:
        a=r['header_offset'];head=request_range(a,a+29);fields=struct.unpack('<4s5H3I2H',head)
        assert fields[0]==b'PK\x03\x04';namesize,extrasize=fields[-2:]
        begin=a+30+namesize+extrasize;compressed=request_range(begin,begin+r['compressed']-1)
        data=zlib.decompress(compressed,-15) if r['method']==8 else compressed
        assert len(data)==r['bytes'] and zlib.crc32(data)&0xffffffff==r['CRC32']
        name=Path(r['name']).name.lstrip('.');target=out/name;assert not target.exists();target.write_bytes(data)
        records.append({'member_name':r['name'],'file':target.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'CRC32_verified':True})
    info=load(out/'info.json');keys=list(info) if isinstance(info,dict) else None
    summary={'status':'PUBLISHED_ZIP_METADATA_MEMBERS_READ_WITH_CRC_AND_SIZE_CHECK','created_UTC':datetime.now(timezone.utc).isoformat(),
       'selected_members':records,'range_requests':calls,'info_json_top_level_type':type(info).__name__,'info_json_top_level_keys':keys,
       'image_or_video_member_payload_read':False,'source_identity_mapping_certified':False}
    target=out/'summary.json';target.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='range_requests'}))
if __name__=='__main__':main()
