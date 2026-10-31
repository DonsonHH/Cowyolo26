"""Resume verified server prefixes via local exact HTTP ranges; preserve all attempts."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,time

ROOT=Path(__file__).resolve().parents[1]
REMOTE='/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    protocol=ROOT/'protocol/sessions_v1.json';p=json.loads(protocol.read_text(encoding='utf-8'))
    stopped=json.loads((ROOT/'evidence/stage_transfer_stop.json').read_text(encoding='utf-8'))
    prefixes={r['sequence']:r for r in stopped['preserved_prefixes']};out=ROOT/'input/resumed_videos';out.mkdir(parents=True,exist_ok=False)
    def fetch(row):
        folder=out/row['sequence'];folder.mkdir();url=row['url'];reads=[];errors=[];began=time.monotonic()
        def get(start,end,name):
            assert 0<end-start<=4*1024*1024
            for attempt in [1,2]:
                t=time.monotonic()
                try:
                    with urlopen(Request(url,headers={'Range':f'bytes={start}-{end-1}','Accept-Encoding':'identity'}),timeout=40) as r:
                        assert r.status==206 and urlparse(r.url).hostname=='data.bris.ac.uk'
                        cr=r.headers['Content-Range'];match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',cr);assert match
                        a,b,total=map(int,match.groups());assert a==start and b==end-1 and total<=p['maximum_each_video_bytes']
                        data=r.read(end-start+1);assert len(data)==end-start
                        record={'file':name,'start':start,'end_exclusive':end,'object_bytes':total,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                                'Content-Range':cr,'ETag':r.headers.get('ETag'),'Last-Modified':r.headers.get('Last-Modified'),
                                'attempt':attempt,'elapsed_s':time.monotonic()-t}
                    (folder/name).write_bytes(data);reads.append(record)
                    (folder/'range_reads.partial.json').write_text(json.dumps(reads,indent=2),encoding='utf-8')
                    return data,total
                except Exception as exc:
                    errors.append({'file':name,'attempt':attempt,'error':repr(exc),'elapsed_s':time.monotonic()-t})
                    (folder/'range_errors.json').write_text(json.dumps(errors,indent=2),encoding='utf-8')
                    print(json.dumps({'sequence':row['sequence'],'range_error':errors[-1]}),flush=True)
                    if attempt==2:raise
        first,total=get(0,1,'size_probe.bin');prefix=b''
        if row['sequence'] in prefixes:
            meta=prefixes[row['sequence']];path=ROOT/'input/prefixes'/(row['sequence']+'.avi.prefix')
            assert sha(path)==meta['sha256'] and path.stat().st_size==meta['bytes'];prefix=path.read_bytes()
            overlap=min(65536,len(prefix));test,total2=get(len(prefix)-overlap,len(prefix),'prefix_overlap.bin')
            assert total==total2 and test==prefix[-overlap:]
        part_paths=[]
        for n,start in enumerate(range(len(prefix),total,4*1024*1024)):
            end=min(total,start+4*1024*1024);name=f'resumed_part_{n:02d}.bin';body,size=get(start,end,name);assert size==total
            part_paths.append(folder/name)
            print(json.dumps({'sequence':row['sequence'],'downloaded_through':end,'total_bytes':total}),flush=True)
        dest=folder/'RGB.avi'
        with dest.open('xb') as f:
            f.write(prefix)
            for path in part_paths:f.write(path.read_bytes())
        assert dest.stat().st_size==total
        record={**row,'status':'DOWNLOADED','path':REMOTE+'/data_resumed_v1/'+row['sequence']+'/RGB.avi','local_path':str(dest),
                'bytes':total,'sha256':sha(dest),'preserved_prefix_bytes':len(prefix),'prefix_overlap_verified':bool(prefix),
                'successful_range_HTTP_bytes':sum(x['bytes'] for x in reads),'range_reads':reads,'errors':errors,'elapsed_s':time.monotonic()-began}
        (folder/'fetch_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in record.items() if k in ['sequence','status','bytes','sha256','elapsed_s']}),flush=True);return record
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(fetch,p['selected']))
    result={'status':'FOUR_SELECTED_VIDEOS_RESUMED_AND_VERIFIED','protocol_sha256':sha(protocol),'files':rows,'successful':len(rows),
            'successful_bytes':sum(r['bytes'] for r in rows),'preserved_server_prefix_bytes':sum(r['preserved_prefix_bytes'] for r in rows),
            'successful_HTTP_range_bytes':sum(r['successful_range_HTTP_bytes'] for r in rows),'original_server_attempt_preserved':True,
            'proxy_or_node_configuration_changed':False,'media_decode_on_login_node':False,'model_run_on_login_node':False}
    assert result['successful']==4 and result['successful_bytes']<=p['maximum_total_video_bytes']
    target=ROOT/'evidence/fetch_manifest_resumed.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}),flush=True)

if __name__=='__main__':main()
