"""Bounded ISO-BMFF video sample-table reader for read-only data auditing."""
from pathlib import Path
import csv, hashlib, importlib.util, json, struct

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('old_probe',ROOT.parent/'counting_reference_candidates_20261027/tools/probe_mootrack_container.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
boxes,child=old.boxes,old.child

def entries(data,body,fmt):
    n=struct.unpack_from('>I',data,body[0]+4)[0];size=struct.calcsize(fmt)
    assert body[0]+8+n*size==body[1]
    return [struct.unpack_from(fmt,data,body[0]+8+i*size) for i in range(n)]

def index(data):
    moov=list(boxes(data));assert len(moov)==1 and moov[0][0]==b'moov'
    found=[]
    for kind,a,b in boxes(data,moov[0][1],moov[0][2]):
        if kind!=b'trak':continue
        mdia=child(data,a,b,b'mdia');hdlr=child(data,*mdia,b'hdlr')
        if data[hdlr[0]+8:hdlr[0]+12]==b'vide':found.append(mdia)
    assert len(found)==1
    mdia=found[0];minf=child(data,*mdia,b'minf');stbl=child(data,*minf,b'stbl')
    table={k:(a,b) for k,a,b in boxes(data,*stbl)}
    stsz=table[b'stsz'];fixed,n=struct.unpack_from('>II',data,stsz[0]+4)
    sizes=[fixed]*n if fixed else list(struct.unpack_from(f'>{n}I',data,stsz[0]+12))
    assert stsz[0]+12+(0 if fixed else 4*n)==stsz[1] and all(x>0 for x in sizes)
    if b'co64' in table:chunks=[v[0] for v in entries(data,table[b'co64'],'>Q')]
    else:chunks=[v[0] for v in entries(data,table[b'stco'],'>I')]
    stsc=entries(data,table[b'stsc'],'>III');assert stsc[0][0]==1
    assert all(v[2]==1 for v in stsc)
    assert all(stsc[i][0]<stsc[i+1][0] for i in range(len(stsc)-1))
    offsets=[];cursor=0;mapping=0
    for c,base in enumerate(chunks,1):
        while mapping+1<len(stsc) and stsc[mapping+1][0]<=c:mapping+=1
        count=stsc[mapping][1];assert cursor+count<=n
        for size in sizes[cursor:cursor+count]:offsets.append(base);base+=size
        cursor+=count
    assert cursor==n and len(offsets)==n
    stts=entries(data,table[b'stts'],'>II');durations=[d for count,d in stts for _ in range(count)]
    assert len(durations)==n
    composition=[0]*n
    if b'ctts' in table:
        t=table[b'ctts'];version=data[t[0]];assert version in [0,1]
        composition=[d for count,d in entries(data,t,'>II' if version==0 else '>Ii') for _ in range(count)]
        assert len(composition)==n
    sync=[v[0]-1 for v in entries(data,table[b'stss'],'>I')] if b'stss' in table else list(range(n))
    assert sync==sorted(set(sync)) and sync[0]==0 and sync[-1]<n
    description=table[b'stsd'];assert struct.unpack_from('>I',data,description[0]+4)[0]==1
    sample=list(boxes(data,description[0]+8,description[1]));assert len(sample)==1 and sample[0][0]==b'avc1'
    body=sample[0][1];width,height=struct.unpack_from('>HH',data,body+24)
    conf=child(data,body+78,sample[0][2],b'avcC');avcc=data[conf[0]:conf[1]];assert avcc[0]==1
    nal_length=(avcc[4]&3)+1;count=avcc[5]&31;pos=6;parameter_sets=[]
    for _ in range(count):
        size=struct.unpack_from('>H',avcc,pos)[0];pos+=2;parameter_sets.append(avcc[pos:pos+size]);pos+=size
    count=avcc[pos];pos+=1
    for _ in range(count):
        size=struct.unpack_from('>H',avcc,pos)[0];pos+=2;parameter_sets.append(avcc[pos:pos+size]);pos+=size
    assert parameter_sets and pos<=len(avcc)
    mdhd=child(data,*mdia,b'mdhd');assert data[mdhd[0]]==0
    timescale=struct.unpack_from('>I',data,mdhd[0]+12)[0]
    samples=[];dts=0
    for i,(off,size,dur,cts) in enumerate(zip(offsets,sizes,durations,composition)):
        samples.append({'decode_index0':i,'offset':off,'size':size,'dts_ticks':dts,'pts_ticks':dts+cts,'duration_ticks':dur,'sync':i in set(sync)})
        dts+=dur
    order=sorted(range(n),key=lambda i:(samples[i]['pts_ticks'],i))
    assert len({s['pts_ticks'] for s in samples})==n
    for rank,i in enumerate(order):samples[i]['display_index0']=rank
    return {'width':width,'height':height,'timescale':timescale,'samples':samples,'sync_indices':sync,
            'nal_length_bytes':nal_length,'parameter_sets_hex':[x.hex() for x in parameter_sets],
            'avcc_hex':avcc.hex(),'ctts_present':b'ctts' in table,'stts':stts,'table_types':[k.decode() for k in table]}

def main():
    out=ROOT/'results/sample_index';out.mkdir(parents=True,exist_ok=False)
    moov=ROOT.parent/'counting_reference_candidates_20261027/results/MooTrack360_container_probe/moov.bin'
    raw=moov.read_bytes();assert hashlib.sha256(raw).hexdigest()=='f060958b4bd3120c0e35070f0532930e41a97e349a8d8e448f8d60031b2e18d3'
    value=index(raw);samples=value.pop('samples')
    with (out/'samples.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(samples[0]));w.writeheader();w.writerows(samples)
    groups=[]
    for target in [0,8991,26973]:
        decoded=next(s['decode_index0'] for s in samples if s['display_index0']==target)
        start=max(s for s in value['sync_indices'] if s<=decoded)
        # End at next keyframe, hence a self-contained GOP including all B-frame references.
        end=next((s for s in value['sync_indices'] if s>start),len(samples))
        chosen=samples[start:end]
        groups.append({'target_display_index0':target,'target_decode_index0':decoded,'start_decode_index0':start,'end_decode_index0_exclusive':end,
                       'display_indices0':sorted(s['display_index0'] for s in chosen),'sum_video_bytes':sum(s['size'] for s in chosen),
                       'range_start':min(s['offset'] for s in chosen),'range_end_exclusive':max(s['offset']+s['size'] for s in chosen)})
    value.update({'status':'PINNED_MOOV_SAMPLE_TABLE_PARSED','moov_sha256':hashlib.sha256(raw).hexdigest(),'sample_count':len(samples),'requested_GOPs':groups,
                  'sum_planned_contiguous_range_bytes':sum(g['range_end_exclusive']-g['range_start'] for g in groups)})
    (out/'index.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in value.items() if k not in ['sync_indices','avcc_hex','parameter_sets_hex','requested_GOPs']}))
    print(json.dumps([{k:v for k,v in g.items() if k!='display_indices0'} for g in groups]))

if __name__=='__main__':main()
