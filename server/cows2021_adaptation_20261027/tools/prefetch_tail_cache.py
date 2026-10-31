"""Bounded transport-only cache for the fixed final300 development JPEGs.

The existing downloader keeps its six workers. Three cache workers fetch a
disjoint future tail, commit complete verified JPEG byte streams atomically,
and let the original manifest writer reuse them. No role or label is changed.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from urllib.parse import urlparse
import concurrent.futures,hashlib,json,os,socket,threading,time
import requests

ROOT=Path(__file__).resolve().parents[1]
SOURCE_MANIFEST_SHA='a0483f65e57c7f45bb329d0515ef19aff76e66f47c92e39ce19f5b84af6eaa4b'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def save(path,value):
    partial=path.with_name(path.name+'.partial')
    partial.write_text(json.dumps(value,indent=2));partial.replace(path)


def main():
    assert socket.gethostname()=='mu01' and os.environ['HOME']=='/share/home/renly'
    assert ROOT==Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
    source=ROOT/'input/image_fetch_manifest.json';assert sha(source)==SOURCE_MANIFEST_SHA
    all_items=json.loads(source.read_text())['items']
    items=sorted(all_items,key=lambda r:r['file_name'])[-300:]
    assert [r['file_name'] for r in items]==[f'{i:05d}.jpg' for i in range(8080,8380)]
    assert all(r['capture_date']<='2020-03-04' and r['development_role']=='validation' for r in items)
    primary=Path('/proc/2794954')
    assert primary.exists() and primary.stat().st_uid==os.getuid()
    command=(primary/'cmdline').read_bytes().replace(b'\0',b' ').decode()
    assert str(ROOT/'tools/fetch_images.py') in command and '--attempt 01' in command
    out=ROOT/'results/tail_cache_01';out.mkdir(exist_ok=False)
    cache=out/'JPEGs';cache.mkdir()
    started=time.perf_counter();local=threading.local()
    save(out/'process.json',{'PID':os.getpid(),'created_UTC':datetime.now(timezone.utc).isoformat(),
         'verified_existing_primary_PID':2794954,'source_manifest_sha256':sha(source),
         'selection':'fixed300 largest basenames from existing development manifest',
         'workers':3,'maximum_new_connections_with_primary':9,
         'dataset_or_training_protocol_modified':False,'new_model_forward':False})
    def task(row):
        target=ROOT/row['relative_image_path']
        assert target.resolve().is_relative_to(ROOT/'raw_images')
        if target.exists():
            return {'file_name':row['file_name'],'status':'ALREADY_PRESENT','bytes':target.stat().st_size,'sha256':sha(target)}
        if not hasattr(local,'session'):
            local.session=requests.Session();local.session.trust_env=False
            local.session.headers['User-Agent']='CattleResearch-fixed-development-tail-cache/1.0'
        cached=cache/row['file_name'];temporary=cached.with_name(cached.name+'.partial')
        error=None
        for attempt in range(2):
            try:
                with local.session.get(row['url'],timeout=(10,30),stream=True) as response:
                    response.raise_for_status();endpoint=urlparse(response.url)
                    assert endpoint.scheme=='https' and endpoint.hostname=='data.bris.ac.uk'
                    size=0
                    with temporary.open('wb') as file:
                        for block in response.iter_content(128*1024):
                            size+=len(block);assert size<=8*1024*1024;file.write(block)
                assert 0<size<=8*1024*1024
                with temporary.open('rb') as file:assert file.read(2)==b'\xff\xd8'
                actual_sha=sha(temporary)
                assert row['previous_train_sample_sha256'] is None or actual_sha==row['previous_train_sample_sha256']
                temporary.replace(cached)
                try:
                    os.link(cached,target)
                    status='VERIFIED_BYTES_COMMITTED_FOR_PRIMARY_REUSE'
                except FileExistsError:
                    assert sha(target)==actual_sha,'Concurrent native response differs; preserve cache and stop this member'
                    status='PRIMARY_ALREADY_COMMITTED_IDENTICAL_BYTES'
                return {'file_name':row['file_name'],'development_role':row['development_role'],
                        'source_url':row['url'],'bytes':size,'sha256':actual_sha,'status':status,
                        'cache_file':str(cached),'target_image':str(target),'image_pixels_decoded':False}
            except Exception as exc:
                error={'type':type(exc).__name__,'message':str(exc)}
                if attempt==0:time.sleep(3)
        return {'file_name':row['file_name'],'source_url':row['url'],'error':error}
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(task,row) for row in items]
        for future in concurrent.futures.as_completed(futures):
            records.append(future.result())
            if len(records)%25==0 or len(records)==len(items):
                progress={'complete_members':len(records),'selected_members':300,
                          'failed_members':sum('error' in r for r in records),'elapsed_s':time.perf_counter()-started}
                save(out/'progress.json',progress);print(json.dumps(progress),flush=True)
    records.sort(key=lambda r:r['file_name']);save(out/'member_manifest.json',records)
    failed=sum('error' in r for r in records)
    summary={'status':'FIXED_TAIL_TRANSPORT_CACHE_TERMINAL','selected_members':300,'failed_members':failed,
             'member_status_counts':dict(Counter(r.get('status','FAILED') for r in records)),
             'member_manifest_sha256':sha(out/'member_manifest.json'),'elapsed_s':time.perf_counter()-started,
             'primary_download_restarted':False,'selection_manifest_or_training_protocol_changed':False,
             'candidate_final_pixels_accessed':False,'new_model_training_or_forward':False}
    save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    raise SystemExit(0 if failed==0 else 2)


if __name__=='__main__':main()
