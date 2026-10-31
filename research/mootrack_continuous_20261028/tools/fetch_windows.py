"""Bounded, resumable exact-range retrieval of the five frozen video windows."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from threading import Lock
import csv,hashlib,json,time,traceback

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    protocol_path=ROOT/'protocol/continuous_births_v1.json';p=json.loads(protocol_path.read_text(encoding='utf-8'))
    out=ROOT/'evidence/video_ranges';out.mkdir(parents=True,exist_ok=True);assert not (out/'manifest.json').exists()
    idx=PROJECT/'mootrack_alignment_20261028/results/sample_index'
    assert sha(idx/'samples.csv')==p['sample_rows_sha256'] and sha(idx/'index.json')==p['sample_index_sha256']
    meta=json.loads((idx/'index.json').read_text(encoding='utf-8'));samples=[]
    with (idx/'samples.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):samples.append({k:int(v) for k,v in r.items() if k!='sync'})
    lock=Lock();attempt_bytes=0;response_rows=[];failures=[];completed=[]
    def get(start,end,filename):
        nonlocal attempt_bytes
        length=end-start;assert 0<length<=8*1024*1024
        dest=out/filename;record=dest.with_suffix(dest.suffix+'.json')
        if record.exists():
            row=json.loads(record.read_text(encoding='utf-8'));assert row['start']==start and row['end_exclusive']==end and row['bytes']==length
            assert dest.stat().st_size==length and sha(dest)==row['sha256']
            with lock:response_rows.append(row)
            return dest.read_bytes()
        assert not dest.exists(),f'Unrecorded partial destination: {dest}'
        for attempt in range(1,3):
            data=bytearray();began=time.time()
            with lock:
                assert attempt_bytes+length<=p['HTTP_budget_bytes'],'Actual network budget exhausted'
                attempt_bytes+=length  # reserve entire attempt conservatively, including failed requests
            try:
                headers={'User-Agent':'CowResearch-continuous-data-audit/1.0','Accept-Encoding':'identity','Range':f'bytes={start}-{end-1}'}
                with urlopen(Request(p['source_url'],headers=headers),timeout=35) as r:
                    assert r.status==206 and r.headers['Content-Range']==f"bytes {start}-{end-1}/{p['source_total_bytes']}"
                    assert urlparse(r.url).hostname=='zenodo.org'
                    while len(data)<length:
                        block=r.read(min(1024*1024,length-len(data)));assert block,'Incomplete range response';data.extend(block)
                    assert not r.read(1)
                    row={'file':filename,'start':start,'end_exclusive':end,'bytes':length,'sha256':hashlib.sha256(data).hexdigest(),
                         'http_status':r.status,'Content-Range':r.headers['Content-Range'],'ETag':r.headers.get('ETag'),'final_url':r.url,
                         'attempt':attempt,'elapsed_s':time.time()-began}
                dest.write_bytes(data);record.write_text(json.dumps(row,indent=2),encoding='utf-8')
                with lock:response_rows.append(row)
                return bytes(data)
            except Exception as exc:
                failure={'file':filename,'attempt':attempt,'received_bytes':len(data),'error':repr(exc),'time_unix':time.time()}
                with lock:
                    failures.append(failure);(out/'failures.json').write_text(json.dumps(failures,indent=2),encoding='utf-8')
                print(json.dumps({'range_failure':failure}),flush=True)
                if attempt==2:raise
    moov=get(24,24+1076007,'moov_recheck.bin');assert hashlib.sha256(moov).hexdigest()==p['moov_sha256']
    def fetch(w):
        name=w['name'];start=w['range_start'];end=w['range_end_exclusive'];parts=[]
        for n,at in enumerate(range(start,end,8*1024*1024)):
            stop=min(end,at+8*1024*1024);filename=f'{name}.part{n:02d}.bin';parts.append((at,stop,filename));get(at,stop,filename)
        joined=b''.join((out/name).read_bytes() for _,_,name in parts);assert len(joined)==end-start
        elementary=bytearray()
        for h in meta['parameter_sets_hex']:elementary.extend(b'\0\0\0\1'+bytes.fromhex(h))
        nal_counts={}
        for s in samples[w['decode_start_video0']:w['decode_end_video0_exclusive']]:
            packet=joined[s['offset']-start:s['offset']-start+s['size']];assert len(packet)==s['size'];pos=0;types=[]
            while pos<len(packet):
                n=int.from_bytes(packet[pos:pos+4],'big');pos+=4;assert 0<n<=len(packet)-pos
                nal=packet[pos:pos+n];pos+=n;kind=nal[0]&31;types.append(kind);nal_counts[kind]=nal_counts.get(kind,0)+1
                elementary.extend(b'\0\0\0\1'+nal)
            assert pos==len(packet)
            if s['decode_index0']==w['decode_start_video0']:assert 5 in types
        output=out/(name+'.h264');assert not output.exists();output.write_bytes(elementary)
        result={**w,'elementary_file':output.name,'elementary_bytes':len(elementary),'elementary_sha256':sha(output),
                'parts':[{'start':a,'end_exclusive':b,'file':f} for a,b,f in parts],'nal_counts':nal_counts}
        (out/(name+'.complete.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({'completed_window':name,'source_bytes':len(joined),'decode_frames':w['decode_frames']}),flush=True)
        return result
    # Each window is independent; only two bounded network requests run simultaneously.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(fetch,w) for w in p['windows']]
        for future in as_completed(futures):completed.append(future.result())
    completed.sort(key=lambda w:w['publisher_ID']);response_rows.sort(key=lambda r:r['start'])
    result={'status':'ALL_FIVE_FROZEN_CONTINUOUS_WINDOWS_FETCHED','protocol_sha256':sha(protocol_path),
            'source_total_bytes':p['source_total_bytes'],'successful_HTTP_bytes':sum(r['bytes'] for r in response_rows),
            'conservative_attempt_bytes_reserved':attempt_bytes,'HTTP_budget_bytes':p['HTTP_budget_bytes'],
            'range_reads':response_rows,'windows':completed,'failures':failures,'full_video_MD5_verified':False,
            'model_predictions_or_training':False,'GT_alignment_certified':False,'whole_goal_complete':False}
    assert result['successful_HTTP_bytes']==p['planned_HTTP_bytes'] and len(completed)==5
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['range_reads','windows','failures']}),flush=True)

if __name__=='__main__':main()
