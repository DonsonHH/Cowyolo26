"""Run an explicit task command through an already logged-in serial shell."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,time,re,uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'serial_deps'));import serial
p=argparse.ArgumentParser();p.add_argument('--command-file',required=True);p.add_argument('--output',required=True);p.add_argument('--timeout',type=int,default=12);a=p.parse_args()
out=Path(a.output);assert not out.exists();command=Path(a.command_file).read_text(encoding='utf-8').strip();assert '\n' not in command
marker='COW_SERIAL_DONE_'+uuid.uuid4().hex[:12];record={'created_UTC':datetime.now(timezone.utc).isoformat(),
 'port':'COM6','baud':115200,'format':'8N1','command_file':str(Path(a.command_file).resolve()),'no_reset_command':True}
port=None;parts=[];started=time.monotonic()
try:
    port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.3,xonxoff=False,rtscts=False,dsrdtr=False)
    port.dtr=False;port.rts=False;port.port='COM6';port.open();prefix=port.read(4096).decode('utf-8','replace')
    port.write((command+"; printf '\\n"+marker+" rc=%s\\n' \"$?\"\r").encode());port.flush()
    while time.monotonic()-started<a.timeout:
        parts.append(port.read(16000).decode('utf-8','replace'));text=''.join(parts)
        if re.search(r'\r?\n'+marker+r' rc=\d+\r?\n',text):break
    text=''.join(parts);text=re.sub(r'(?i)((?:token|password|passwd|secret)[=: ]+)([^\s&]+)',r'\1<REDACTED>',text)
    match=re.search(r'\r?\n'+marker+r' rc=(\d+)\r?\n',text)
    record.update({'status':'SERIAL_COMMAND_COMPLETE' if match else 'SERIAL_COMMAND_TERMINAL_NOT_OBSERVED',
                   'exit_code':int(match.group(1)) if match else None,'output':text,'prefix':prefix,'elapsed_s':time.monotonic()-started})
except Exception as e:record.update({'status':'SERIAL_COMMAND_ERROR','error_type':type(e).__name__,'detail':str(e)})
finally:
    if port and port.is_open:port.close()
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,ensure_ascii=True))
