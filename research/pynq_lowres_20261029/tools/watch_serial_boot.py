"""Bounded UART boot capture; never sends login, reset or inference commands."""
from pathlib import Path
from datetime import datetime,timezone
import sys,time,json,re,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'serial_deps'));import serial
p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);p.add_argument('--seconds',type=int,default=180);a=p.parse_args()
out=Path(a.output_dir);out.mkdir(exist_ok=False);assert 10<=a.seconds<=300
def now():return datetime.now(timezone.utc).isoformat()
def scrub(text):
    text=re.sub(r'(?i)((?:token|password|passwd|secret|authorization)[=: ]+)([^\s&]+)',r'\1<REDACTED>',text)
    return text
started=time.monotonic();port=None;chunks=0;count=0;errors=[];log=out/'boot_sanitized.log'
state={'created_UTC':now(),'port':'COM6','baud':115200,'format':'8N1','flow_control':False,
       'status':'STARTING','transmit':'onecarriage-returnonlyaftereachsuccessfulopen','reset_or_PL_actions':0}
def save():
    state.update({'updated_UTC':now(),'received_bytes':count,'chunks':chunks,'elapsed_s':time.monotonic()-started,'serial_errors':errors})
    (out/'state.json').write_text(json.dumps(state,indent=2)+'\n')
with log.open('x',encoding='utf-8') as stream:
    while time.monotonic()-started<a.seconds:
        try:
            if port is None:
                port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.5,xonxoff=False,rtscts=False,dsrdtr=False)
                port.dtr=False;port.rts=False;port.port='COM6';port.open();port.write(b'\r');port.flush()
                state['status']='LISTENING';save();print('UART_BOOT_WATCH_LISTENING_COM6_115200',flush=True)
            raw=port.read(4096)
            if raw:
                count+=len(raw);chunks+=1;text=scrub(raw.decode('utf-8','replace'));stream.write(text);stream.flush()
                print('UART '+text[:12000],flush=True)
            save()
        except Exception as e:
            errors.append({'UTC':now(),'type':type(e).__name__,'detail':str(e)[:200]});state['status']='WAITING_FOR_SERIAL_RECONNECT';save()
            if port:
                try:port.close()
                except Exception:pass
            port=None;time.sleep(.3)
    if port:port.close()
state['status']='BOUNDED_CAPTURE_FINISHED';save();print(json.dumps(state),flush=True)
