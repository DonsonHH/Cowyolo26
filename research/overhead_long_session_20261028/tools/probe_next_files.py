"""Bounded native-data discovery of the six remaining files, without any model."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from threading import Lock
import hashlib,json,re,time
ROOT=Path(__file__).resolve().parents[1]
def main():
    listing=ROOT/'evidence/camera1_2023Aug17_listing.json';data=json.loads(listing.read_text(encoding='utf-8'));files=data['videos'][1:];assert len(files)==6
    p={'name':'All six remaining day17 camera1 files, fixed byte-fraction native probes','files':files,'fractions':[.25,.5,.75],
       'header_bytes':1024*1024,'fragment_bytes':4*1024*1024,'budget_bytes':96*1024*1024,
       'selected_after_first_native_file_showed_no_cows_in_overview':True,'based_on_model_results':False,
       'bounded_probes_do_not_validate_whole_video':True,'content_selection_not_random_final_test':True}
    protocol=ROOT/'protocol/next_file_probe_v1.json'
    if protocol.exists():assert json.loads(protocol.read_text(encoding='utf-8'))==p
    else:protocol.write_text(json.dumps(p,indent=2),encoding='utf-8')
    out=ROOT/'input/next_file_probes';out.mkdir(exist_ok=True);assert not (out/'manifest.json').exists()
    rows=[];lock=Lock()
    initial_files=[f for folder in out.iterdir() if folder.is_dir() for f in folder.iterdir() if f.name in ['header.bin','size_probe.bin']]
    initial_bytes=sum(f.stat().st_size for f in initial_files);bytes_read=initial_bytes
    (out/'initial_guard_attempt.json').write_text(json.dumps({'reason':'First attempt assumed MPEG pack code at byte0; actual sources share IMKH camera private header before MPEG-PS packets.',
            'initial_successful_response_bytes':initial_bytes,'files':[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in initial_files]},indent=2),encoding='utf-8')
    def get(url,start,end,path):
        nonlocal bytes_read
        with lock:bytes_read+=end-start;assert bytes_read<=p['budget_bytes']
        with urlopen(Request(url,headers={'Range':f'bytes={start}-{end-1}','Accept-Encoding':'identity'}),timeout=40) as r:
            assert r.status==206 and urlparse(r.url).hostname=='data.bris.ac.uk'
            cr=r.headers['Content-Range'];m=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',cr);assert m
            a,b,total=map(int,m.groups());assert a==start and b==end-1
            body=r.read(end-start+1);assert len(body)==end-start
        assert not path.exists();path.write_bytes(body)
        row={'file':path.relative_to(ROOT).as_posix(),'start':start,'end_exclusive':end,'object_bytes':total,
             'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'Content-Range':cr}
        path.with_suffix(path.suffix+'.json').write_text(json.dumps(row,indent=2),encoding='utf-8');return row
    def fetch(item):
        folder=out/item['filename'];folder.mkdir(exist_ok=True);records=[]
        suffix='_retry' if (folder/'header.bin').exists() else ''
        probe=get(item['url'],0,1,folder/('size_probe'+suffix+'.bin'));records.append(probe);size=probe['object_bytes'];assert size>16*1024*1024
        header=folder/('header'+suffix+'.bin');records.append(get(item['url'],0,p['header_bytes'],header))
        body=header.read_bytes();magic=body[:4].hex()
        assert body[:16].hex()=='494d4b48010200000200000100000000' and b'\0\0\1\xba' in body,'Camera header or MPEG-PS signature differs'
        if suffix:assert body==(folder/'header.bin').read_bytes(),'Original preserved header differs on repeat'
        for fraction in p['fractions']:
            start=max(0,int(size*fraction)-p['fragment_bytes']//2);end=min(size,start+p['fragment_bytes'])
            records.append({**get(item['url'],start,end,folder/f'fraction_{int(fraction*100):02d}.ps'),'fraction':fraction})
        result={**item,'source_object_bytes':size,'magic_first4_hex':magic,'range_reads':records,'whole_video_downloaded':False}
        (folder/'record.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'completed_probe_file':item['filename'],'source_bytes':size}),flush=True);return result
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(fetch,f) for f in files]
        for future in as_completed(futures):rows.append(future.result())
    rows.sort(key=lambda r:r['filename']);result={'status':'SIX_FILES_THREE_NATIVE_FRACTIONS_EACH_FETCHED','protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
       'files':rows,'successful_HTTP_bytes':bytes_read,'initial_guard_attempt_response_bytes':initial_bytes,
       'budget_bytes':p['budget_bytes'],'model_predictions':0,'whole_goal_complete':False}
    assert len(rows)==6 and bytes_read<96*1024*1024
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    import tarfile
    archive=ROOT/'next_probes_input.tar'
    with tarfile.open(archive,'w') as t:
        for f in out.rglob('*'):
            if f.is_file():t.add(f,arcname=f.relative_to(ROOT))
    print(json.dumps({'status':result['status'],'HTTP_bytes':bytes_read,'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}),flush=True)
if __name__=='__main__':main()
