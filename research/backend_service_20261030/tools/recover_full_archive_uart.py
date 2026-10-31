"""Read-only full UART transfer with bounded RAM, partial retention and progress."""
from pathlib import Path
from datetime import datetime,timezone
import sys,time,json,uuid,base64,hashlib,os
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'pynq_lowres_20261029/serial_deps'))
import serial
total=20018871;expected='b87a60784d7f414ae512855d3ed658613d8dc7c2e03cf6ec856d7d61856422a6'
dest=ROOT/'backend_service_delivery_v1.tar.gz';partial=ROOT/'full_archive_UART.partial';progress=ROOT/'evidence/full_archive_UART_progress.json';terminal=ROOT/'evidence/full_archive_UART_terminal.json'
assert not dest.exists() and not partial.exists() and not terminal.exists()
assert dest.resolve().is_relative_to(ROOT.resolve()) and partial.resolve().is_relative_to(ROOT.resolve())
token=uuid.uuid4().hex[:16];start_marker=('\r\nFULL_BEGIN_'+token+'\r\n').encode();end_marker=('\r\nFULL_END_'+token+'\r\n').encode()
command="python3 -c 'from pathlib import Path; import base64,sys,hashlib; p=Path(\"/home/xilinx/jupyter_notebooks/cow_research_backend_service_20261030/backend_service_delivery_v1.tar.gz\"); b=p.read_bytes(); assert len(b)=="+str(total)+" and hashlib.sha256(b).hexdigest()==\""+expected+"\"; sys.stdout.write(\"\\nFULL_BEGIN_"+token+"\\n\"+base64.b64encode(b).decode()+\"\\nFULL_END_"+token+"\\n\"); sys.stdout.flush()'"
state={'status':'RUNNING','created_UTC':datetime.now(timezone.utc).isoformat(),'port':'COM6','baud':115200,'expected_bytes':total,'expected_sha256':expected,
       'received_binary_bytes':0,'read_only_remote_archive':True,'new_model_forwards':0,'reset_or_network_configuration_changes':False}
def write_progress():
 temp=progress.with_suffix('.json.partial');temp.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8');temp.replace(progress)
port=None;stream=None;buf=bytearray();begun=False;digest=hashlib.sha256();started=time.monotonic();last_report=started
try:
 port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.2,xonxoff=False,rtscts=False,dsrdtr=False)
 port.dtr=False;port.rts=False;port.port='COM6';port.open();port.read(4096)
 stream=partial.open('xb');port.write((command+'\r').encode());port.flush();write_progress()
 print(json.dumps({'status':'FULL_ARCHIVE_UART_TRANSFER_STARTED','expected_bytes':total,'source_archive_unchanged':True}),flush=True)
 while time.monotonic()-started<4200:
  chunk=port.read(16384)
  if chunk:buf.extend(chunk)
  if not begun:
   index=buf.find(start_marker)
   if index>=0:buf=buf[index+len(start_marker):];begun=True
  if begun:
   index=buf.find(end_marker)
   if index>=0:
    encoded=bytes(buf[:index]).replace(b'\r',b'').replace(b'\n',b'')
    tail=base64.b64decode(encoded,validate=True);stream.write(tail);digest.update(tail);state['received_binary_bytes']+=len(tail)
    assert state['received_binary_bytes']==total and digest.hexdigest()==expected
    stream.flush();os.fsync(stream.fileno());stream.close();stream=None;assert not dest.exists();partial.replace(dest)
    state.update({'status':'FULL_ORIGINAL_ARCHIVE_UART_COMPLETE_HASH_VERIFIED','sha256':expected,'elapsed_s':time.monotonic()-started,'source_full_archive_locally_received':True})
    write_progress();break
   usable=max(0,len(buf)-len(end_marker)-8);usable=(usable//4)*4
   if usable:
    data=base64.b64decode(bytes(buf[:usable]),validate=True);del buf[:usable];stream.write(data);digest.update(data);state['received_binary_bytes']+=len(data)
  now=time.monotonic()
  if now-last_report>=30:
   state.update({'elapsed_s':now-started,'average_binary_bytes_per_s':state['received_binary_bytes']/max(now-started,1),'begin_observed':begun})
   stream.flush();write_progress();print(json.dumps({'status':'FULL_ARCHIVE_UART_RUNNING','received_binary_bytes':state['received_binary_bytes'],'total':total,'elapsed_s':round(now-started,1)}),flush=True);last_report=now
 else:raise TimeoutError('Full UART archive terminal not observed within70min')
except BaseException as e:
 state.update({'status':'TRANSFER_NOT_COMPLETE_PARTIAL_PRESERVED','error':repr(e),'elapsed_s':time.monotonic()-started,'begin_observed':begun,'partial_sha256_so_far':digest.hexdigest()})
 if buf:
  f=ROOT/'full_archive_UART_unparsed_tail.partial';assert not f.exists();f.write_bytes(buf)
 write_progress()
finally:
 if stream:stream.close()
 if port and port.is_open:port.close()
 terminal.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
print(json.dumps(state),flush=True)
if state['status']!='FULL_ORIGINAL_ARCHIVE_UART_COMPLETE_HASH_VERIFIED':raise SystemExit(1)
