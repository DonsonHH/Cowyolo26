from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'serial_deps'))
import serial
from serial.tools import list_ports
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);assert not out.exists()
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'port':'COM6','baud':115200,'format':'8N1','flow_control':False,
        'no_reset_or_reboot_sent':True,'transmitted_only_carriage_return':True,
        'matching_ports':[{'device':r.device,'description':r.description,'hwid':r.hwid} for r in list_ports.comports() if r.device=='COM6']}
port=None
try:
    port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.8,xonxoff=False,rtscts=False,dsrdtr=False)
    port.dtr=False;port.rts=False;port.port='COM6';port.open();chunks=[]
    chunks.append(port.read(6000));port.write(b'\r');port.flush()
    for _ in range(3):chunks.append(port.read(6000))
    raw=b''.join(chunks);record.update({'status':'SERIAL_OPEN','received_bytes':len(raw),'received':raw.decode('utf-8','replace')})
except Exception as e:record.update({'status':'SERIAL_UNAVAILABLE','error_type':type(e).__name__,'detail':str(e)[:350]})
finally:
    if port and port.is_open:port.close()
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
