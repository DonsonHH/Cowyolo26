"""Recover successful range payloads after final index path assertion; no HTTP."""
from pathlib import Path
from datetime import datetime,timezone
import json,struct,io,zipfile,zlib,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/COLO_zip_metadata_v2'
release=json.loads((ROOT/'evidence/data_endpoint_probes/COLO_release.response').read_text(encoding='utf-8'));asset=next(a for a in release['assets'] if a['name']=='COLO_COCO.zip');size=asset['size']
tail=(OUT/'zip_tail.range').read_bytes();directory=(OUT/'central_directory.range').read_bytes()
idx=tail.rfind(b'PK\x05\x06');assert idx>=0;end=struct.unpack_from('<4s4H2IH',tail,idx)
assert end[5]==len(directory);central_start=end[6];tail_start=size-len(tail)
class SavedDirectoryFile(io.RawIOBase):
 def __init__(self):self.pos=0
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):
  self.pos=offset if whence==0 else self.pos+offset if whence==1 else size+offset;return self.pos
 def read(self,n=-1):
  n=size-self.pos if n<0 else min(n,size-self.pos);start=self.pos;stop=start+n
  for offset,data in [(central_start,directory),(tail_start,tail)]:
   if offset<=start and stop<=offset+len(data):self.pos=stop;return data[start-offset:stop-offset]
  raise AssertionError(('unsaved_metadata_range_requested',start,n))
z=zipfile.ZipFile(SavedDirectoryFile());entries=z.infolist();assert len(entries)==end[4]
original=json.loads((OUT/'entries.json').read_text(encoding='utf-8'));assert len(entries)==len(original)
for a,b in zip(entries,original):
 assert a.filename==b['name'] and a.header_offset==b['local_header_offset'] and a.CRC==b['CRC32'] and a.compress_size==b['compressed_bytes'] and a.file_size==b['uncompressed_bytes'] and a.compress_type==b['method']
jsonfiles=[e for e in entries if e.filename.lower().endswith('.json')];records=[];ranges=[]
for i,e in enumerate(jsonfiles):
 hf=OUT/('json'+str(i).zfill(2)+'_header.range');df=OUT/('json'+str(i).zfill(2)+'_data.range');jf=OUT/('annotations_'+str(i).zfill(2)+'.json')
 header=hf.read_bytes();h=struct.unpack('<4s5H3I2H',header);assert h[0]==b'PK\x03\x04' and h[3]==e.compress_type
 data=df.read_bytes();assert len(data)==e.compress_size;decoded=zlib.decompress(data,-15) if e.compress_type==8 else data
 assert len(decoded)==e.file_size and (zlib.crc32(decoded)&0xffffffff)==e.CRC and decoded==jf.read_bytes()
 d=json.loads(decoded);records.append({'archive_member':e.filename,'file':str(jf.resolve()),'sha256':hashlib.sha256(decoded).hexdigest(),
  'CRC32':e.CRC,'images':len(d.get('images',[])),'annotations':len(d.get('annotations',[])),'categories':d.get('categories'),
  'first_filenames':[r.get('file_name') for r in d.get('images',[])[:3]]})
 ranges.extend([{'file':str(hf.resolve()),'bytes':len(header),'sha256':hashlib.sha256(header).hexdigest(),'expected_start':e.header_offset},
  {'file':str(df.resolve()),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'expected_start':e.header_offset+30+h[9]+h[10]}])
assert len(jsonfiles)==22
report={'status':'ALL_ZIP_DIRECTORY_AND22_JSON_CRC_RECOVERED_FROM_SAVED_SUCCESSFUL_RANGES','created_UTC':datetime.now(timezone.utc).isoformat(),
 'asset_id':asset['id'],'asset_name':asset['name'],'asset_bytes':size,'requested_public_URL':asset['browser_download_url'],'entries':len(entries),
 'central_directory_sha256':hashlib.sha256(directory).hexdigest(),'central_directory_bytes':len(directory),'json_files':records,'range_payloads':ranges,
 'downloaded_range_bytes':len(tail)+len(directory)+sum(r['bytes'] for r in ranges),'local_image_pixels_decoded':0,'new_model_forwards':0,
 'capture_final_index_write_failed_due_to_old_v1_path_collision':True,'initial_direct_access_failed_response_preserved':True,
 'successful_data_not_downloaded_again':True,'request_specific_HTTP_headers_not_recovered_from_lost_in_memory_index':True,'independent_standard_library_zip_directory_check':True,'whole_goal_complete':False}
f=ROOT/'results/COLO_zip_metadata_recovered_v2.json';assert not f.exists();f.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'entries':len(entries),'JSON_files':len(records),'downloaded_range_bytes':report['downloaded_range_bytes'],'new_pixels':0}))
for r in records:print(json.dumps({k:v for k,v in r.items() if k in ['archive_member','images','annotations','categories']}))
