"""Recover all public XML source timestamps/blocks; preserve held-out image pixels."""
from pathlib import Path
from collections import Counter,defaultdict
import concurrent.futures,csv,hashlib,json,re,shutil,time
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]


def save(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value,indent=2),encoding='utf-8');temporary.replace(path)


def parse_source(path,role,name,url):
    data=path.read_bytes();root=ET.fromstring(data)
    original=root.findtext('filename') or ''
    match=re.search(r'image_(\d+)_(\d{4}-\d{2}-\d{2})_(\d{1,2})-(\d{1,2})-(\d{1,2})',original)
    capture=None
    if match:capture=f'{match[2]}T{int(match[3]):02d}:{int(match[4]):02d}:{int(match[5]):02d}'
    return {'role':role,'file_name':name,'XML_url':url,'XML_bytes':len(data),'XML_sha256':hashlib.sha256(data).hexdigest(),
            'original_filename':original,'original_frame_index':int(match[1]) if match else None,
            'capture_timestamp':capture,'capture_date':match[2] if match else None,'source_block':root.findtext('folder'),
            'width':int(root.findtext('size/width')),'height':int(root.findtext('size/height')),
            'object_types':dict(Counter((r.findtext('type') or 'unspecified')+':'+(r.findtext('name') or '') for r in root.findall('object'))),
            'session_ID_verified':False}


def main():
    specs=[]
    for role,annotation,listing in [('train','train_annotations.json','train_train_image_listing.html.record.json'),
                                     ('validation','validation_annotations.json','train_val_image_listing.html.record.json'),
                                     ('reserved_test','reserved_test_annotations.json','reserved_test_image_listing.html.record.json')]:
        data=json.loads((ROOT/'catalog'/annotation).read_text(encoding='utf-8'))
        urls=json.loads((ROOT/'catalog'/listing).read_text(encoding='utf-8'))['links']
        byname={u.rsplit('/',1)[-1]:u for u in urls if u.endswith('.xml')}
        for row in data['images']:
            name=row['file_name'];xml_name=Path(name).with_suffix('.xml').name;assert xml_name in byname
            specs.append((role,name,byname[xml_name]))
    assert len(specs)==10402 and len({s[1] for s in specs})==10402
    destination=ROOT/'source_XML';destination.mkdir(exist_ok=True)
    progress=ROOT/'results/source_recovery_progress.json';start=time.perf_counter();records=[];errors=[]
    def task(item):
        role,name,url=item;path=destination/role/Path(name).with_suffix('.xml');path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():return parse_source(path,role,name,url)
        sample=ROOT/'catalog/train_audit'/Path(name).with_suffix('.xml')
        if role=='train' and sample.exists():shutil.copyfile(sample,path);return parse_source(path,role,name,url)
        error=None
        for attempt in range(3):
            try:
                with urlopen(Request(url,headers={'User-Agent':'CattleResearch-public-source-metadata/1.0'}),timeout=20) as response:
                    data=response.read(256*1024+1);assert response.status==200 and len(data)<=256*1024
                ET.fromstring(data)
                temporary=path.with_name(path.name+'.partial');temporary.write_bytes(data);temporary.replace(path)
                return parse_source(path,role,name,url)
            except Exception as exc:
                error=str(exc)
                if attempt<2:time.sleep(.5*(attempt+1))
        return {'role':role,'file_name':name,'url':url,'error':error}
    # Reuse already fetched samples, then fill published boundaries early; the
    # complete inventory, rather than a boundary sample, establishes overlap.
    specs.sort(key=lambda r:(r[1] not in ['00000.jpg','07247.jpg','07248.jpg','08270.jpg','08271.jpg','10401.jpg'],r[1]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures=[pool.submit(task,s) for s in specs]
        for future in concurrent.futures.as_completed(futures):
            value=future.result()
            (errors if 'error' in value else records).append(value)
            done=len(records)+len(errors)
            if done%200==0 or done==10402:
                value={'status':'RUNNING_SOURCE_XML_RECOVERY' if done<10402 else 'XML_TRANSFERS_FINISHED',
                       'total':10402,'complete_XML':len(records),'failed_XML':len(errors),'elapsed_s':time.perf_counter()-start,
                       'validation_or_test_image_pixels_downloaded':False}
                save(progress,value);print(json.dumps(value),flush=True)
    records.sort(key=lambda r:r['file_name']);save(ROOT/'results/source_metadata_all.json',records)
    if errors:
        save(ROOT/'results/source_recovery_errors.json',errors);raise SystemExit(2)
    assert len(records)==10402
    dates=defaultdict(Counter);blocks=defaultdict(Counter)
    for row in records:
        dates[row['capture_date']][row['role']]+=1;blocks[row['source_block']][row['role']]+=1
    overlap_dates={d:dict(v) for d,v in dates.items() if len(v)>1}
    overlap_blocks={b:dict(v) for b,v in blocks.items() if len(v)>1}
    result={'status':'ALL_10402_PUBLIC_XML_SOURCE_METADATA_RECOVERED','complete_XML':len(records),
            'roles':dict(Counter(r['role'] for r in records)),'missing_timestamps':sum(r['capture_timestamp'] is None for r in records),
            'dates':{k:dict(v) for k,v in sorted(dates.items(),key=lambda r:str(r[0]))},'blocks':{k:dict(v) for k,v in sorted(blocks.items(),key=lambda r:str(r[0]))},
            'dates_shared_across_published_roles':overlap_dates,'blocks_shared_across_published_roles':overlap_blocks,
            'original_filename_shared_across_roles':len(records)-len({r['original_filename'] for r in records}),
            'elapsed_s':time.perf_counter()-start,'validation_or_test_image_pixels_downloaded':False,
            'source_block_is_verified_video_session':False,'model_forward_or_training':False,
            'scope':'Published XML timestamp/block metadata only. Block and filename timestamps are source provenance, not independently verified recording session IDs.'}
    save(ROOT/'results/source_recovery_summary.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['blocks','dates']}),flush=True)


if __name__=='__main__':main()
