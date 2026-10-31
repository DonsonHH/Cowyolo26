"""Send an immutable task bundle to a new task directory with block ACKs."""
from pathlib import Path
from datetime import datetime,timezone
import base64,hashlib,json,os,shlex,sys,time,uuid,zlib

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent/'pynq_lowres_20261029/serial_deps'))
import serial

archive=ROOT/'new_identity_board_input_v1.tar.gz';bundle=json.loads((ROOT/'evidence/input_bundle.json').read_text());raw=archive.read_bytes()
assert len(raw)==bundle['bytes']and hashlib.sha256(raw).hexdigest()==bundle['sha256']
token=uuid.uuid4().hex[:16];remote='/home/xilinx/jupyter_notebooks/cow_research_identity_domain_arm_20261030'
receiver=f'''from pathlib import Path,PurePosixPath
import sys,hashlib,json,tarfile
r=Path({remote!r});assert r.parent==Path('/home/xilinx/jupyter_notebooks')and r.is_dir();assert sorted(x.name for x in r.iterdir())==['input_v1.tar.gz.partial'];assert(r/'input_v1.tar.gz.partial').stat().st_size==0
p=r/'input_v1.tar.gz.partial';out=sys.stdout.buffer;inp=sys.stdin.buffer;offset=0;digest=hashlib.sha256();token={token!r}
out.write(('COW_PUT_READY '+token+'\\n').encode());out.flush()
with p.open('ab')as sink:
 while offset<{len(raw)}:
  header=inp.readline().decode().strip().split();assert header[:2]==['COW_PUT',token]and int(header[2])==offset
  n=int(header[3]);assert n==min(65536,{len(raw)}-offset);data=inp.read(n);assert len(data)==n;h=hashlib.sha256(data).hexdigest()
  if h!=header[4]:out.write(('COW_PUT_NACK '+token+' '+str(offset)+'\\n').encode());out.flush();continue
  sink.write(data);sink.flush();digest.update(data);offset+=n
  out.write(('COW_PUT_ACK '+token+' '+str(offset)+' '+h+'\\n').encode());out.flush()
assert digest.hexdigest()=={bundle['sha256']!r}
final=r/'input_v1.tar.gz';p.rename(final)
with tarfile.open(final)as tar:
 members=tar.getmembers();assert len(members)=={bundle['members']}
 for member in members:
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  dest=(r/member.name).resolve();assert dest.is_relative_to(r)and not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(member).read())
plan=json.loads((r/'run_protocol.json').read_text());assert hashlib.sha256((r/'run_protocol.json').read_bytes()).hexdigest()=={bundle['protocol_sha256']!r}
for row in plan['payload_files']:assert hashlib.sha256((r/row['file']).read_bytes()).hexdigest()==row['sha256']
out.write(('COW_PUT_DONE '+token+' '+str(offset)+' '+digest.hexdigest()+'\\n').encode());out.flush()
'''
code='import base64,zlib;exec(zlib.decompress(base64.b64decode('+repr(base64.b64encode(zlib.compress(receiver.encode())).decode())+')))'
command='cow_uart_saved=$(stty -g); stty raw -echo; python3 -u -c '+shlex.quote(code)+"; cow_uart_rc=$?; stty \"$cow_uart_saved\"; cow_uart_now=$(stty -g); cow_uart_ok=0; if [ \"$cow_uart_now\" = \"$cow_uart_saved\" ]; then cow_uart_ok=1; fi; printf '\\nCOW_PUT_TTY_DONE "+token+" rc=%s restored=%s\\n' \"$cow_uart_rc\" \"$cow_uart_ok\""
assert len(command.encode())<4096
control=ROOT/'evidence/binary_upload_v2_control.json';progress=ROOT/'evidence/binary_upload_v2_progress.json';terminal=ROOT/'evidence/binary_upload_v2_terminal.json'
assert all(not p.exists()for p in[control,progress,terminal])
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'token':token,'remote_directory':remote,'bytes':len(raw),'sha256':bundle['sha256'],
        'temporary_raw_TTY_restored_after_transfer':True,'no_baud_or_reset':True,'new_model_forwards':0}
control.write_text(json.dumps(record,indent=2)+'\n');port=serial.Serial(port=None,baudrate=115200,timeout=.2,write_timeout=15,xonxoff=False,rtscts=False,dsrdtr=False)
port.dtr=False;port.rts=False;port.port='COM6';buffer=bytearray();started=time.monotonic();offset=0;blocks=0;retries=0


def line(timeout=30):
 deadline=time.monotonic()+timeout
 while b'\n'not in buffer:
  assert time.monotonic()<deadline,'Same UART receiver observation timeout; retain control and offset, do not restart'
  buffer.extend(port.read(8192))
 end=buffer.index(10);value=bytes(buffer[:end]).decode('utf-8','replace').strip();del buffer[:end+1];return value


try:
 port.open();port.read(4096);port.write((command+'\r').encode());port.flush()
 while True:
  value=line()
  if value.endswith('COW_PUT_READY '+token):
   record['observed_readiness_line']=value;break
 while offset<len(raw):
  payload=raw[offset:offset+65536];digest=hashlib.sha256(payload).hexdigest();header=f'COW_PUT {token} {offset} {len(payload)} {digest}\n'
  port.write(header.encode());port.write(payload);port.flush();ack=line()
  if ack==f'COW_PUT_NACK {token} {offset}':
   retries+=1;assert retries<=3;continue
  assert ack==f'COW_PUT_ACK {token} {offset+len(payload)} {digest}',ack
  offset+=len(payload);blocks+=1
  value={'status':'RUNNING_SAME_NEW_TASK_INPUT_RECEIVER','acknowledged_bytes':offset,'total_bytes':len(raw),'blocks':blocks,'retries':retries,'elapsed_s':time.monotonic()-started}
  tmp=progress.with_suffix('.json.partial');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(progress)
  if blocks%8==0:print(json.dumps(value),flush=True)
 assert line()=='COW_PUT_DONE '+token+' '+str(offset)+' '+bundle['sha256']
 ending=line()
 while not ending.startswith('COW_PUT_TTY_DONE '+token):ending=line()
 assert ending==f'COW_PUT_TTY_DONE {token} rc=0 restored=1',ending
 record.update({'status':'NEW_TASK_INPUT13_MEMBERS_BLOCKS_AND_FULL_SHA_VERIFIED_TTY_RESTORED','acknowledged_bytes':offset,'blocks':blocks,'retries':retries,'tty_restored_verified':True,'elapsed_s':time.monotonic()-started})
except BaseException as error:
 record.update({'last_read_line':locals().get('value',''),'status':'UART_NEW_TASK_INPUT_TERMINAL_UNVERIFIED_RETAIN_SAME_CONTROL','error':repr(error),'acknowledged_bytes':offset,'blocks':blocks,'elapsed_s':time.monotonic()-started})
finally:
 if port.is_open:port.close()
 terminal.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
if record['status']!='NEW_TASK_INPUT13_MEMBERS_BLOCKS_AND_FULL_SHA_VERIFIED_TTY_RESTORED':raise SystemExit(1)
