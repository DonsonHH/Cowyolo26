"""Read-only privileged UART command; password stdin only, guarded echo-off."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,sys,time,json,uuid,re,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'pynq_lowres_20261029/serial_deps'))
import serial
p=argparse.ArgumentParser();p.add_argument('--command-file',required=True);p.add_argument('--output',required=True);a=p.parse_args()
command=Path(a.command_file).read_text(encoding='utf-8').strip();assert '\n' not in command and command.startswith('XILINX_XRT=/usr ')
out=Path(a.output);assert not out.exists();password=sys.stdin.readline().rstrip('\r\n');assert password
token=uuid.uuid4().hex;echo=('\r\nUART_ECHO_OFF_'+token+'\r\n').encode();auth=('UART_AUTH_'+token+':').encode();done='UART_PRIV_DONE_'+token
shell="if stty -echo; then printf '\\nUART_ECHO_OFF_"+token+"\\n'; sudo -S -p '"+auth.decode()+"' env "+command+"; cow_uart_rc=$?; else cow_uart_rc=98; fi; stty echo; printf '\\n"+done+" rc=%s\\n' \"$cow_uart_rc\""
state={'created_UTC':datetime.now(timezone.utc).isoformat(),'port':'COM6','baud':115200,'command_file':str(Path(a.command_file).resolve()),
 'command_sha256':hashlib.sha256(command.encode()).hexdigest(),'password_recorded':False,'hardware_reset_or_experiment_rerun':False}
port=None;stream=bytearray();echo_off=False;sent=False;started=time.monotonic();marker=None
try:
 port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.2,xonxoff=False,rtscts=False,dsrdtr=False)
 port.dtr=False;port.rts=False;port.port='COM6';port.open();port.read(4096);port.write((shell+'\r').encode());port.flush()
 while time.monotonic()-started<45:
  stream.extend(port.read(16384))
  if not echo_off:
   index=stream.find(echo)
   if index>=0:stream=stream[index+len(echo):];echo_off=True
  if echo_off and auth in stream:
   if not sent:port.write((password+'\n').encode());port.flush();sent=True
   if stream.count(auth)>1:port.write(b'\x03');port.flush();raise RuntimeError('sudo_authentication_reprompted; interrupted_own_readonly_command')
  match=re.search(rb'\r?\n'+done.encode()+rb' rc=(\d+)\r?\n',stream)
  if match:marker=match;break
 if marker is None:raise TimeoutError('Privileged read terminal not observed')
 text=bytes(stream[:marker.start()]).decode('utf-8','replace').replace(auth.decode(),'[sudo prompt]')
 assert password not in text or password=='xilinx'  # username/path may equal the public default; echo was already disabled before auth.
 state.update({'status':'PRIVILEGED_UART_READ_FINISHED','exit_code':int(marker.group(1)),'guarded_echo_off_observed':echo_off,'password_sent_only_after_actual_sudo_prompt':sent,'output':text,'elapsed_s':time.monotonic()-started})
except BaseException as e:
 if port and port.is_open:
  try:port.write(b'\x03stty echo\r');port.flush()
  except Exception:pass
 state.update({'status':'PRIVILEGED_UART_READ_FAILED','error':repr(e),'guarded_echo_off_observed':echo_off,'password_sent_only_after_actual_sudo_prompt':sent,'elapsed_s':time.monotonic()-started})
finally:
 password=''
 if port and port.is_open:port.close()
 out.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
print(json.dumps(state),flush=True)
if state.get('exit_code')!=0:raise SystemExit(1)
