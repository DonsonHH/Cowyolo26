from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from threading import Lock
import argparse,hashlib,json,re,time

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--positive',action='store_true');args=parser.parse_args()
    protocol=ROOT/'protocol'/('positive_candidate_v1.json' if args.positive else 'selection_v1.json');p=json.loads(protocol.read_text(encoding='utf-8'));url=p['selected']['url']
    out=ROOT/'input'/('positive_video_ranges' if args.positive else 'video_ranges');out.mkdir(parents=True,exist_ok=True);assert not (out/'manifest.json').exists()
    records=[];errors=[];lock=Lock();reserved=0;budget=p['maximum_source_bytes']+64*1024*1024
    def get(start,end,filename):
        nonlocal reserved
        dest=out/filename;meta=dest.with_suffix(dest.suffix+'.json');length=end-start
        if meta.exists():
            record=json.loads(meta.read_text(encoding='utf-8'));assert sha(dest)==record['sha256'] and dest.stat().st_size==length
            return record
        assert not dest.exists()
        for attempt in [1,2]:
            with lock:reserved+=length;assert reserved<=budget,'Conservative transfer budget exhausted'
            began=time.monotonic();data=bytearray()
            try:
                with urlopen(Request(url,headers={'Range':f'bytes={start}-{end-1}','Accept-Encoding':'identity','User-Agent':'ID-Coo ordinary overhead reference preparation'}),timeout=40) as r:
                    assert r.status==206 and urlparse(r.url).hostname=='data.bris.ac.uk'
                    cr=r.headers['Content-Range'];match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',cr);assert match
                    a,b,total=map(int,match.groups());assert a==start and b==end-1 and total<=p['maximum_source_bytes']
                    while len(data)<length:
                        block=r.read(min(1024*1024,length-len(data)));assert block;data.extend(block)
                    assert not r.read(1)
                    record={'file':filename,'start':start,'end_exclusive':end,'object_bytes':total,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                            'Content-Range':cr,'ETag':r.headers.get('ETag'),'Last-Modified':r.headers.get('Last-Modified'),'attempt':attempt,'elapsed_s':time.monotonic()-began}
                dest.write_bytes(data);meta.write_text(json.dumps(record,indent=2),encoding='utf-8');return record
            except Exception as exc:
                with lock:
                    errors.append({'file':filename,'attempt':attempt,'received_bytes':len(data),'error':repr(exc)})
                    (out/'errors.json').write_text(json.dumps(errors,indent=2),encoding='utf-8')
                print(json.dumps({'range_error':errors[-1]}),flush=True)
                if attempt==2:raise
    probe=get(0,1,'size_probe.bin');total=probe['object_bytes'];assert total>0
    print(json.dumps({'source_bytes':total,'source':p['selected']['filename'],'maximum_bytes':p['maximum_source_bytes']}),flush=True)
    jobs=[(at,min(total,at+p['range_chunk_bytes']),f'part_{i:03d}.bin') for i,at in enumerate(range(0,total,p['range_chunk_bytes']))]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(get,*job) for job in jobs]
        for future in as_completed(futures):
            record=future.result();records.append(record)
            print(json.dumps({'completed_part':record['file'],'parts_done':len(records),'parts_total':len(jobs)}),flush=True)
    records.sort(key=lambda r:r['start']);dest=ROOT/'input'/p['selected']['filename'];assert not dest.exists()
    with dest.open('xb') as f:
        for r in records:f.write((out/r['file']).read_bytes())
    assert dest.stat().st_size==total
    result={'status':'ONE_FROZEN_ORDINARY_OVERHEAD_LONG_VIDEO_DOWNLOADED','source_url':url,'source_filename':dest.name,'local_path':str(dest),
            'source_bytes':total,'source_sha256':sha(dest),'protocol_sha256':sha(protocol),'range_reads':[probe,*records],
            'errors':errors,'successful_HTTP_bytes':sum(r['bytes'] for r in records)+1,
            'conservative_attempt_bytes_reserved_this_run':reserved,'source_budget_bytes':p['maximum_source_bytes'],
            'new_model_predictions':False,'GT_available':False,'whole_goal_complete':False}
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['range_reads','errors']}),flush=True)

if __name__=='__main__':main()
