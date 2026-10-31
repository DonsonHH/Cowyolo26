from pathlib import Path
from datetime import datetime,timezone
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/"pynq_lowres_20261029/serial_deps"))
import serial
out=ROOT/"evidence/serial_observe01.json";assert not out.exists()
record={"created_UTC":datetime.now(timezone.utc).isoformat(),"port":"COM6","baud":115200,
        "format":"8N1_no_flow_control","DTR":False,"RTS":False,"hardware_reset":False,
        "sent_bytes":"one_CR_after_initial_observation","new_model_forwards":0}
parts=[];port=None;start=time.monotonic()
try:
    port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity="N",stopbits=1,timeout=.2,xonxoff=False,rtscts=False,dsrdtr=False)
    port.dtr=False;port.rts=False;port.port="COM6";port.open()
    until=time.monotonic()+2
    while time.monotonic()<until:parts.append(port.read(8192))
    port.write(b"\r");port.flush()
    until=time.monotonic()+6
    while time.monotonic()<until:parts.append(port.read(8192))
    raw=b"".join(parts)
    record.update({"status":"OBSERVATION_FINISHED","bytes":len(raw),"output":raw.decode("utf-8","replace")})
except Exception as error:
    record.update({"status":"OBSERVATION_FAILED","error_type":type(error).__name__,"detail":str(error)})
finally:
    if port and port.is_open:port.close()
    record["elapsed_s"]=time.monotonic()-start
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(record,ensure_ascii=False))
