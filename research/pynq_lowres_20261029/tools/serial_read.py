from pathlib import Path
from datetime import datetime,timezone
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'serial_deps'));import serial
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'port':'COM6','baud':115200,'data_bits':8,'stop_bits':1,'parity':'none','flow_control':False,
'no_reboot_or_reset_command_sent':True};port=None
try:
    port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=1,xonxoff=False,rtscts=False,dsrdtr=False)
    port.dtr=False;port.rts=False;port.port='COM6';port.open()
    first=port.read(6000);port.write(b'\r');port.flush();second=port.read(6000)
    record.update({'status':'SERIAL_OPEN_READ_ONLY_NEWLINE_PROMPT','received':(first+second).decode('utf-8','replace')})
except Exception as e:record.update({'status':'SERIAL_UNAVAILABLE','error_type':type(e).__name__,'detail':str(e)[:350]})
finally:
    if port and port.is_open:port.close()
out=ROOT/'evidence/serial_prompt01.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
