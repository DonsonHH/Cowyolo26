"""Parse saved ZIP64 directory records without using zipfile."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    summary=load(ROOT/'evidence/zip_directory/summary.json');expected=load(ROOT/'evidence/zip_directory/entries.json')
    parts=summary['range_requests'];directory=next(r for r in parts if r['start']==summary['directory_start'])
    data=(ROOT/directory['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==directory['sha256']
    rows=[];position=0
    while position<len(data):
        assert data[position:position+4]==b'PK\x01\x02'
        fields=struct.unpack_from('<4s6H3I5H2I',data,position)
        _,made,need,flags,method,clock,date,crc,compressed,uncompressed,nlen,xlen,clen,disk,internal,external,offset=fields
        name=data[position+46:position+46+nlen].decode('utf-8' if flags&0x800 else 'cp437')
        extra=data[position+46+nlen:position+46+nlen+xlen];cursor=0;zip64=None
        while cursor<len(extra):
            tag,size=struct.unpack_from('<HH',extra,cursor);payload=extra[cursor+4:cursor+4+size]
            if tag==1:zip64=payload
            cursor+=4+size
        assert cursor==len(extra)
        if zip64 is not None:
            cursor=0
            if uncompressed==0xffffffff:uncompressed=struct.unpack_from('<Q',zip64,cursor)[0];cursor+=8
            if compressed==0xffffffff:compressed=struct.unpack_from('<Q',zip64,cursor)[0];cursor+=8
            if offset==0xffffffff:offset=struct.unpack_from('<Q',zip64,cursor)[0];cursor+=8
        rows.append({'name':name,'bytes':uncompressed,'compressed':compressed,'CRC32':crc,'method':method,
                     'header_offset':offset,'directory':name.endswith('/'),'extra_bytes':xlen,'comment_bytes':clen})
        position+=46+nlen+xlen+clen
    assert position==len(data) and rows==expected and len(rows)==103156
    result={'status':'ALL103156_ZIP64_CENTRAL_RECORDS_INDEPENDENT_STRUCT_PARSER_EXACT',
            'directory_bytes':len(data),'entries':len(rows),'unique_member_names':len({r['name'] for r in rows}),
            'CSV_members':sum(r['name'].lower().endswith('.csv') for r in rows),'no_image_or_video_payload_read':True,
            'whole_goal_complete':False}
    path=ROOT/'results/zip_directory_independent_verification.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
