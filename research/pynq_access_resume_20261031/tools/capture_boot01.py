"""Bounded passive UART boot capture; reconnect FTDI after power cycling, never resets."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/"pynq_lowres_20261029/serial_deps"))
import serial
from serial.tools import list_ports
E=ROOT/"evidence"
out=E/"boot_capture01.json";raw_path=E/"boot_capture01.bin";journal=E/"boot_capture01.events.jsonl"
assert not any(p.exists()for p in[out,raw_path,journal])
start=time.monotonic();port=None;events=[];total=0
def event(kind,**extra):
    row={"at_s":round(time.monotonic()-start,3),"UTC":datetime.now(timezone.utc).isoformat(),"event":kind,**extra}
    events.append(row)
    with journal.open("a",encoding="utf-8")as f:f.write(json.dumps(row,ensure_ascii=False)+chr(10))
    print(json.dumps(row,ensure_ascii=False),flush=True)
last_presence=None;last_heartbeat=start;retry_after=start
event("PASSIVE_CAPTURE_STARTED",port="COM6",baud=115200,maximum_s=120)
with raw_path.open("xb")as raw:
    try:
        while time.monotonic()-start<120 and total<2*1024*1024:
            if port is None:
                present=any(p.device=="COM6"for p in list_ports.comports())
                if present!=last_presence:
                    event("COM6_PRESENT"if present else"COM6_ABSENT");last_presence=present
                if present and time.monotonic()>=retry_after:
                    try:
                        port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity="N",stopbits=1,timeout=.2,
                                           xonxoff=False,rtscts=False,dsrdtr=False)
                        port.dtr=False;port.rts=False;port.port="COM6";port.open()
                        event("SERIAL_OPENED_NO_CONTROL_SIGNALS_OR_TX")
                    except Exception as error:
                        event("SERIAL_OPEN_FAILED",error=type(error).__name__,detail=str(error))
                        port=None;retry_after=time.monotonic()+2
                else:time.sleep(.2)
            else:
                try:
                    chunk=port.read(8192)
                    if chunk:
                        raw.write(chunk);raw.flush();total+=len(chunk)
                        event("RX",bytes=len(chunk),cumulative_bytes=total,text=chunk.decode("utf-8","replace")[-6000:])
                except Exception as error:
                    event("SERIAL_DISCONNECTED_OR_READ_ERROR",error=type(error).__name__,detail=str(error))
                    try:port.close()
                    except Exception:pass
                    port=None;retry_after=time.monotonic()+.5
            if time.monotonic()-last_heartbeat>=25:
                event("CAPTURE_STILL_LISTENING",cumulative_bytes=total);last_heartbeat=time.monotonic()
    finally:
        if port and port.is_open:port.close()
record={"status":"PASSIVE_BOOT_CAPTURE_WINDOW_FINISHED","completed_UTC":datetime.now(timezone.utc).isoformat(),
        "elapsed_s":time.monotonic()-start,"port":"COM6","baud":115200,"received_bytes":total,
        "raw_file":str(raw_path.resolve()),"raw_SHA256":hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "events":events,"TX_bytes":0,"reset_DTR_RTS_or_baud_changed":False,"new_model_forwards":0,
        "source_experiment_restarted":False}
out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:v for k,v in record.items()if k!="events"},ensure_ascii=False),flush=True)
