"""Pause only the observed autoboot countdown; no environment or media writes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys,time
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/"pynq_lowres_20261029/serial_deps"))
import serial
out=ROOT/"evidence/uboot_pause01.json";raw_path=ROOT/"evidence/uboot_pause01.bin"
assert not out.exists()and not raw_path.exists()
record={"created_UTC":datetime.now(timezone.utc).isoformat(),"port":"COM6","baud":115200,
        "action":"one_space_only_after_observed_autoboot_countdown","media_or_environment_writes":False,
        "model_or_PL_programmed":False,"new_model_forwards":0,"hardware_reset":False}
port=None;raw=bytearray();sent=False;start=time.monotonic()
try:
    port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity="N",stopbits=1,timeout=.15,xonxoff=False,rtscts=False,dsrdtr=False)
    port.dtr=False;port.rts=False;port.port="COM6";port.open()
    while time.monotonic()-start<60:
        chunk=port.read(8192)
        if chunk:
            raw.extend(chunk)
            if not sent and b"Hit any key to stop autoboot:"in raw[-1000:]:
                port.write(b" ");port.flush();sent=True
            if sent and re.search(rb"(?:\r?\n)(?:Zynq>|zynq>|PYNQ>|=>)\s*$",bytes(raw)):
                record["status"]="OBSERVED_UBOOT_AUTOBOOT_PAUSED_PROMPT_REACHED";break
    else:record["status"]="PAUSE_PROMPT_NOT_OBSERVED_WITHIN60S"
except Exception as error:record.update({"status":"PAUSE_FAILED","error":repr(error)})
finally:
    if port and port.is_open:port.close()
    raw_path.write_bytes(raw)
    record.update({"space_sent":sent,"elapsed_s":time.monotonic()-start,"received_bytes":len(raw),
                   "raw_sha256":hashlib.sha256(raw).hexdigest(),"output_tail":bytes(raw[-8000:]).decode("utf-8","replace")})
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(record,ensure_ascii=False))
