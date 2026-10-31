"""Read MP4 top-level headers and moov metadata only, never mdat pixels."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
import hashlib,json,struct,time

ROOT=Path(__file__).resolve().parents[1]
URL='https://zenodo.org/records/20287681/files/1hour_annotated_sequence.mp4?download=1'


def boxes(data,start=0,end=None):
    end=len(data) if end is None else end
    pos=start
    while pos+8<=end:
        size,kind=struct.unpack_from('>I4s',data,pos);header=8
        if size==1:size=struct.unpack_from('>Q',data,pos+8)[0];header=16
        elif size==0:size=end-pos
        assert size>=header and pos+size<=end
        yield kind,pos+header,pos+size
        pos+=size
    assert pos==end


def child(data,start,end,kind):
    found=[(a,b) for k,a,b in boxes(data,start,end) if k==kind]
    assert len(found)==1,(kind,len(found))
    return found[0]


def parse_moov(data):
    top=list(boxes(data));assert len(top)==1 and top[0][0]==b'moov'
    streams=[]
    for kind,a,b in boxes(data,top[0][1],top[0][2]):
        if kind!=b'trak':continue
        mdia=child(data,a,b,b'mdia')
        hdlr=child(data,*mdia,b'hdlr');handler=data[hdlr[0]+8:hdlr[0]+12].decode('ascii')
        mdhd=child(data,*mdia,b'mdhd');version=data[mdhd[0]]
        if version==0:
            scale,duration=struct.unpack_from('>II',data,mdhd[0]+12)
        else:
            assert version==1
            scale=struct.unpack_from('>I',data,mdhd[0]+20)[0]
            duration=struct.unpack_from('>Q',data,mdhd[0]+24)[0]
        value={'handler':handler,'media_timescale':scale,'media_duration_ticks':duration,'media_duration_s':duration/scale}
        if handler=='vide':
            minf=child(data,*mdia,b'minf');stbl=child(data,*minf,b'stbl')
            stts=child(data,*stbl,b'stts');n=struct.unpack_from('>I',data,stts[0]+4)[0]
            counts=[struct.unpack_from('>II',data,stts[0]+8+i*8) for i in range(n)]
            samples=sum(c for c,d in counts);ticks=sum(c*d for c,d in counts)
            assert ticks>0 and samples>0
            description=child(data,*stbl,b'stsd');count=struct.unpack_from('>I',data,description[0]+4)[0]
            assert count==1
            sample=list(boxes(data,description[0]+8,description[1]));assert len(sample)==1
            codec,body,limit=sample[0]
            width,height=struct.unpack_from('>HH',data,body+24)
            value.update({'codec':codec.decode('ascii'),'width':width,'height':height,'sample_count':samples,
                          'frame_duration_entries':counts,'sample_duration_ticks':ticks,
                          'duration_from_sample_table_s':ticks/scale,'average_fps_from_sample_table':samples*scale/ticks})
        streams.append(value)
    return streams


def main():
    destination=ROOT/'results/MooTrack360_container_probe';destination.mkdir(exist_ok=False)
    started=time.perf_counter();records=[]
    with urlopen(Request(URL,method='HEAD',headers={'User-Agent':'CattleResearch-MP4-metadata-only/1.0'}),timeout=20) as r:
        assert r.status==200;size=int(r.headers['Content-Length']);etag=r.headers.get('ETag')
    def get(offset,length):
        assert 0<=offset<size and 0<length<=16*1024*1024
        end=min(size-1,offset+length-1)
        headers={'User-Agent':'CattleResearch-MP4-metadata-only/1.0','Range':f'bytes={offset}-{end}',
                 'Accept-Encoding':'identity'}
        if etag and not etag.startswith('W/'):headers['If-Match']=etag
        with urlopen(Request(URL,headers=headers),timeout=30) as r:
            assert r.status==206 and r.headers['Content-Range']==f'bytes {offset}-{end}/{size}'
            assert urlparse(r.url).hostname=='zenodo.org'
            data=r.read(end-offset+2);assert len(data)==end-offset+1
        records.append({'offset':offset,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        return data
    offset=0;top=[];metadata=None
    for _ in range(32):
        if offset>=size:break
        header=get(offset,8);length,kind=struct.unpack('>I4s',header);header_size=8
        if length==1:length=struct.unpack('>Q',get(offset+8,8))[0];header_size=16
        elif length==0:length=size-offset
        assert length>=header_size and offset+length<=size
        top.append({'type':kind.decode('ascii'),'offset':offset,'size':length,'header_bytes':header_size})
        print(json.dumps({'top_level_box':top[-1],'elapsed_s':time.perf_counter()-started}),flush=True)
        if kind==b'moov':
            metadata=get(offset,length)
            (destination/'moov.bin').write_bytes(metadata)
            break
        offset+=length
    assert metadata is not None
    streams=parse_moov(metadata)
    for request in records:
        for box in top:
            if box['type']=='mdat':
                assert request['offset']+request['bytes']<=box['offset']+box['header_bytes'] or request['offset']>=box['offset']+box['size']
    result={'status':'MP4_CONTAINER_METADATA_READ_WITHOUT_MDAT_PAYLOAD','source_url':URL,'source_bytes':size,'ETag':etag,
            'top_level_boxes':top,'range_reads':records,'streams':streams,
            'metadata_bytes_read':sum(r['bytes'] for r in records),'moov_sha256':hashlib.sha256(metadata).hexdigest(),
            'mdat_payload_read':False,'video_frames_decoded':False,'new_model_prediction':False,
            'GT_to_raw_video_alignment_verified':False,'elapsed_s':time.perf_counter()-started}
    (destination/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
