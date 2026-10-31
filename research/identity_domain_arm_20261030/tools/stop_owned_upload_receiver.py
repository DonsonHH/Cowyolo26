"""Stop only our nonce-bound, interrupted raw-UART file receiver; preserve prefix."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'pynq_lowres_20261029/serial_deps'))
import serial

control=json.loads((ROOT/'evidence/binary_upload_v2_control.json').read_text())
progress=json.loads((ROOT/'evidence/binary_upload_v2_progress.json').read_text())
assert progress['acknowledged_bytes']==1245184 and progress['blocks']==19
token=control['token'];out=ROOT/'evidence/upload_v2_receiver_terminal_recovery.json';assert not out.exists()
port=serial.Serial(port=None,baudrate=115200,timeout=.06,write_timeout=5,xonxoff=False,rtscts=False,dsrdtr=False)
port.dtr=False;port.rts=False;port.port='COM6'
data=bytearray();filled=0;newline_sent=False;start=time.monotonic()
try:
 port.open();data.extend(port.read(8192));port.write(('COW_PUT_ABORT '+token+'\n').encode());port.flush()
 end=time.monotonic()+2
 while time.monotonic()<end:
  data.extend(port.read(8192))
  if('COW_PUT_TTY_DONE '+token+' rc=1 restored=1').encode()in data:break
 while('COW_PUT_TTY_DONE '+token+' rc=1 restored=1').encode()not in data:
  assert time.monotonic()-start<30 and filled<=65536
  if('COW_PUT_NACK '+token).encode()in data:
   if not newline_sent:port.write(b'\n');port.flush();newline_sent=True
  else:
   # If interrupted inside read(n), complete this one block with ASCII only.
   # The hash fails; any surplus ASCII remains one line consumed by the receiver.
   port.write(b'X'*256);port.flush();filled+=256
  data.extend(port.read(8192))
 status='OWNED_INTERRUPTED_RECEIVER_EXIT1_AND_ORIGINAL_TTY_RESTORED_PREFIX_RETAINED'
finally:
 if port.is_open:port.close()
 record={'created_UTC':datetime.now(timezone.utc).isoformat(),'status':locals().get('status','OWNED_RECEIVER_TERMINAL_NOT_YET_CONFIRMED'),
         'token':token,'last_host_acknowledged_bytes':progress['acknowledged_bytes'],'ASCII_fill_bytes':filled,
         'no_binary_payload_replayed':True,'only_owned_file_receiver_affected':True,'output':data.decode('utf-8','replace'),
         'new_model_forwards':0,'elapsed_s':time.monotonic()-start}
 out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
assert record['status']=='OWNED_INTERRUPTED_RECEIVER_EXIT1_AND_ORIGINAL_TTY_RESTORED_PREFIX_RETAINED'
