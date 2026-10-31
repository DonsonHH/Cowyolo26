"""One read-only UART archive transfer; no network changes or experiment reruns."""
from pathlib import Path
from datetime import datetime,timezone
import sys,time,json,uuid,base64,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'pynq_lowres_20261029/serial_deps'))
import serial
expected_bytes=212282;expected_sha='394d04f3cb127e7746d7cb7632cdaf9bb8b4ae8a0fc0af3b05f8a1bd04a396aa'
dest=ROOT/'numeric_recovery_UART.tar.gz';evidence=ROOT/'evidence/numeric_UART_transfer.json'
assert not dest.exists() and not evidence.exists()
token=uuid.uuid4().hex[:16];begin=('\r\nMETA_BEGIN_'+token+'\r\n').encode();end=('\r\nMETA_END_'+token+'\r\n').encode()
command="python3 -c 'from pathlib import Path; import base64,sys; p=Path(\"/home/xilinx/jupyter_notebooks/cow_research_backend_serial_recovery_20261030/numeric_recovery.tar.gz\"); sys.stdout.write(\"\\nMETA_BEGIN_"+token+"\\n\"+base64.b64encode(p.read_bytes()).decode()+\"\\nMETA_END_"+token+"\\n\"); sys.stdout.flush()'"
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'port':'COM6','baud':115200,'status':'RUNNING','read_only_remote_archive':True,'no_reset_or_network_changes':True,'expected_bytes':expected_bytes,'expected_sha256':expected_sha}
port=None;data=bytearray();started=time.monotonic();found=False
try:
 port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.2,xonxoff=False,rtscts=False,dsrdtr=False)
 port.dtr=False;port.rts=False;port.port='COM6';port.open();port.read(4096)
 port.write((command+'\r').encode());port.flush();print(json.dumps({'status':'UART_NUMERIC_ARCHIVE_TRANSFER_STARTED','expected_bytes':expected_bytes}),flush=True)
 while time.monotonic()-started<240:
  chunk=port.read(16384)
  if chunk:data.extend(chunk)
  if not found:
   pos=data.find(begin)
   if pos>=0:data=data[pos+len(begin):];found=True
  if found:
   pos=data.find(end)
   if pos>=0:
    payload=base64.b64decode(bytes(data[:pos]).replace(b'\r',b'').replace(b'\n',b''),validate=True)
    assert len(payload)==expected_bytes and hashlib.sha256(payload).hexdigest()==expected_sha
    with dest.open('xb') as f:f.write(payload)
    record.update({'status':'UART_NUMERIC_ARCHIVE_COMPLETE_HASH_VERIFIED','bytes':len(payload),'sha256':expected_sha,'elapsed_s':time.monotonic()-started,'complete_full_board_delivery_recovered':False})
    break
 else:raise TimeoutError('UART metadata transfer terminal not seen')
except BaseException as e:
 partial=ROOT/'numeric_uart_received.partial';assert not partial.exists();partial.write_bytes(data)
 record.update({'status':'FAILED_PARTIAL_PRESERVED','error':repr(e),'received_stream_bytes':len(data),'begin_observed':found,'elapsed_s':time.monotonic()-started})
finally:
 if port and port.is_open:port.close()
 evidence.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record),flush=True)
if record['status']!='UART_NUMERIC_ARCHIVE_COMPLETE_HASH_VERIFIED':raise SystemExit(1)
