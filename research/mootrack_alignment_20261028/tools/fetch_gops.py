"""Retrieve predeclared video GOPs by exact HTTP Range, with a strict byte budget."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
import argparse,csv,hashlib,json,struct,time

ROOT=Path(__file__).resolve().parents[1]
URL='https://zenodo.org/records/20287681/files/1hour_annotated_sequence.mp4?download=1'
SIZE=18890553141
MOOV_SHA='f060958b4bd3120c0e35070f0532930e41a97e349a8d8e448f8d60031b2e18d3'
BUDGET=64*1024*1024

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tail',action='store_true');args=parser.parse_args()
    out=ROOT/('evidence/tail_ranges' if args.tail else 'evidence/video_ranges');out.mkdir(parents=True,exist_ok=False)
    meta=json.loads((ROOT/'results/sample_index/index.json').read_text(encoding='utf-8'))
    samples=list(csv.DictReader((ROOT/'results/sample_index/samples.csv').open(encoding='utf-8')))
    for s in samples:
        for k in ['decode_index0','display_index0','offset','size']:s[k]=int(s[k])
    assert meta['ctts_present'] is False
    assert all(s['decode_index0']==s['display_index0'] for s in samples)
    if args.tail:
        previous=json.loads((ROOT/'evidence/video_ranges/manifest.json').read_text(encoding='utf-8'))
        previous_total=previous['downloaded_bytes'];groups=[]
        for target in [53919,53945]:
            start=max(s for s in meta['sync_indices'] if s<=target)
            end=next((s for s in meta['sync_indices'] if s>start),len(samples));chosen=samples[start:end]
            groups.append({'target_display_index0':target,'target_decode_index0':target,'start_decode_index0':start,'end_decode_index0_exclusive':end,
                           'display_indices0':[s['display_index0'] for s in chosen],'sum_video_bytes':sum(s['size'] for s in chosen),
                           'range_start':min(s['offset'] for s in chosen),'range_end_exclusive':max(s['offset']+s['size'] for s in chosen)})
    else:previous_total=0;groups=meta['requested_GOPs']
    total=0;reads=[]
    def get(start,end,name):
        nonlocal total
        length=end-start;assert 0<length<16*1024*1024 and previous_total+total+length<=BUDGET
        with urlopen(Request(URL,headers={'User-Agent':'CowResearch-bounded-video-audit/1.0','Accept-Encoding':'identity','Range':f'bytes={start}-{end-1}'}),timeout=40) as r:
            assert r.status==206 and r.headers['Content-Range']==f'bytes {start}-{end-1}/{SIZE}'
            assert urlparse(r.url).hostname=='zenodo.org'
            b=r.read(length+1);assert len(b)==length
            row={'file':name,'start':start,'end_exclusive':end,'bytes':length,'sha256':hashlib.sha256(b).hexdigest(),
                 'http_status':r.status,'Content-Range':r.headers['Content-Range'],'ETag':r.headers.get('ETag'),'final_url':r.url}
        (out/name).write_bytes(b);reads.append(row);total+=length
        (out/'partial_reads.json').write_text(json.dumps(reads,indent=2),encoding='utf-8')
        return b
    current=get(24,24+1076007,'moov_recheck.bin');assert hashlib.sha256(current).hexdigest()==MOOV_SHA
    results=[]
    for g in groups:
        tag=f"target_{g['target_display_index0']:05d}"
        start=g['range_start'];b=get(start,g['range_end_exclusive'],tag+'.range.bin')
        elementary=bytearray()
        for h in meta['parameter_sets_hex']:elementary.extend(b'\0\0\0\1'+bytes.fromhex(h))
        nal_counts={};ids=[]
        for s in samples[g['start_decode_index0']:g['end_decode_index0_exclusive']]:
            packet=b[s['offset']-start:s['offset']-start+s['size']];assert len(packet)==s['size']
            pos=0;types=[]
            while pos<len(packet):
                size=int.from_bytes(packet[pos:pos+meta['nal_length_bytes']],'big');pos+=meta['nal_length_bytes']
                assert size>0 and pos+size<=len(packet)
                nal=packet[pos:pos+size];pos+=size;types.append(nal[0]&31)
                nal_counts[str(nal[0]&31)]=nal_counts.get(str(nal[0]&31),0)+1
                elementary.extend(b'\0\0\0\1'+nal)
            assert pos==len(packet)
            if s['decode_index0']==g['start_decode_index0']:assert 5 in types
            ids.append(s['display_index0'])
        p=out/(tag+'.h264');p.write_bytes(elementary)
        results.append({**g,'elementary_file':p.name,'elementary_bytes':len(elementary),'elementary_sha256':hashlib.sha256(elementary).hexdigest(),
                        'nal_counts':nal_counts,'target_local_frame0':g['target_display_index0']-g['start_decode_index0'],
                        'sample_order_is_display_order':True,'native_fps':'30000/2002'})
        print(json.dumps({'tag':tag,'bytes':len(b),'frames':len(ids),'total_bytes':total}),flush=True)
    result={'status':'TAIL_DIAGNOSTIC_GOPS_FETCHED' if args.tail else 'THREE_PREDECLARED_GOPS_FETCHED','source_url':URL,'source_total_bytes':SIZE,'full_source_MD5_not_verified':True,
            'budget_bytes':BUDGET,'downloaded_bytes':total,'source_moov_sha256_reverified':MOOV_SHA,'range_reads':reads,'GOPs':results,
            'previous_phase_range_bytes':previous_total,'cumulative_phase_range_bytes':previous_total+total,
            'author_code_executed':False,'model_prediction_run':False,'GT_alignment_certified':False,'time_unix':time.time()}
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'downloaded_bytes':total}),flush=True)

if __name__=='__main__':main()
