from pathlib import Path
from datetime import datetime, timezone
import base64, hashlib, json, shlex, sys, time, uuid

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT / "pynq_lowres_20261029/serial_deps"))
import serial

archive = ROOT / "cpu_partition_input_v1.tar.gz"
payload = archive.read_bytes()
bundle = json.loads((ROOT / "evidence/input_bundle.json").read_text())
assert len(payload) == bundle["bytes"] and hashlib.sha256(payload).hexdigest() == bundle["sha256"]
encoded = base64.b64encode(payload).decode()
chunks = [encoded[index:index+1024] for index in range(0, len(encoded), 1024)]
token = uuid.uuid4().hex[:12]
remote = "/home/xilinx/jupyter_notebooks/cow_research_cpu_partition_20261030"
receiver = f'''from pathlib import Path,PurePosixPath
import sys,base64,hashlib,tarfile,json,lzma
r=Path({remote!r});assert r.parent==Path('/home/xilinx/jupyter_notebooks') and not r.exists();r.mkdir()
p=r/'cpu_partition_input_v1.tar.gz.partial';h=hashlib.sha256();n=0
print('UART_INPUT_READY_{token}',flush=True)
with p.open('xb') as f:
 for index in range({len(chunks)}):
  line=sys.stdin.buffer.readline();assert line.endswith(b'\\n') and len(line)<=1025
  raw=base64.b64decode(line.strip(),validate=True);f.write(raw);h.update(raw);n+=len(raw)
assert n=={len(payload)} and h.hexdigest()=={bundle['sha256']!r}
final=r/'cpu_partition_input_v1.tar.gz';p.rename(final)
with tarfile.open(final) as tar:
 members=tar.getmembers();assert len(members)=={bundle['members']}
 for member in members:
  rel=PurePosixPath(member.name);assert member.isfile() and not rel.is_absolute() and '..' not in rel.parts
  q=(r/member.name).resolve();assert q.is_relative_to(r) and not q.exists();q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(tar.extractfile(member).read())
plan=json.loads((r/'run_protocol.json').read_text())
for row in plan['payload_files']:assert hashlib.sha256((r/row['file']).read_bytes()).hexdigest()==row['sha256']
assert hashlib.sha256((r/'run_protocol.json').read_bytes()).hexdigest()=={bundle['protocol_sha256']!r}
print(json.dumps({{'status':'UART_INPUT6_MEMBERS_HASH_VERIFIED','bytes':n,'sha256':h.hexdigest(),'remote_directory':str(r),'new_model_forwards':0,'lzma_available':True}}),flush=True)
'''
command = "stty -echo; python3 -u -c " + shlex.quote(receiver) + "; cow_input_rc=$?; stty echo; printf '\\nUART_INPUT_DONE_" + token + " rc=%s\\n' \"$cow_input_rc\""
# Shell command uses real newlines inside one quoted Python argument. Keep each terminal input line bounded.
command = "stty -echo; python3 -u -c " + shlex.quote("import base64;exec(base64.b64decode(" + repr(base64.b64encode(receiver.encode()).decode()) + "))") + "; cow_input_rc=$?; stty echo; printf '\\nUART_INPUT_DONE_" + token + " rc=%s\\n' \"$cow_input_rc\""
assert len(command.encode()) < 4096
record = {"created_UTC": datetime.now(timezone.utc).isoformat(), "port": "COM6", "baud": 115200, "remote_directory": remote,
          "bytes": len(payload), "archive_sha256": bundle["sha256"], "input_lines": len(chunks),
          "DTR_RTS_reset": False, "new_model_forwards": 0}
output = ROOT / "evidence/input_UART_stage.json"
assert not output.exists()
port = None
stream = bytearray()
started = time.monotonic()
try:
    port = serial.Serial(port=None, baudrate=115200, timeout=.2, xonxoff=False, rtscts=False, dsrdtr=False)
    port.dtr = False
    port.rts = False
    port.port = "COM6"
    port.open()
    port.read(4096)
    port.write((command + "\r").encode())
    port.flush()
    ready = ("\r\nUART_INPUT_READY_" + token + "\r\n").encode()
    while ready not in stream and time.monotonic() - started < 15:
        stream.extend(port.read(8192))
    assert ready in stream, "No receiver readiness; do not send source bytes"
    stream = bytearray(stream[stream.index(ready) + len(ready):])
    for chunk in chunks:
        port.write((chunk + "\n").encode())
        port.flush()
    done = ("UART_INPUT_DONE_" + token + " rc=").encode()
    while done not in stream and time.monotonic() - started < 50:
        stream.extend(port.read(8192))
    text = stream.decode("utf-8", "replace")
    assert ("UART_INPUT_DONE_" + token + " rc=0") in text, text[-1000:]
    result = [json.loads(line) for line in text.splitlines() if line.startswith('{"status":')][-1]
    assert result["sha256"] == bundle["sha256"] and result["bytes"] == len(payload)
    record.update({"status": "UART_TASK_INPUT_STAGED_AND_HASH_VERIFIED", "remote_result": result, "elapsed_s": time.monotonic() - started})
except BaseException as error:
    record.update({"status": "UART_INPUT_STAGE_FAILED_OR_TERMINAL_UNOBSERVED", "error": repr(error), "partial_output": stream.decode("utf-8", "replace")[-2500:]})
finally:
    if port and port.is_open:
        port.close()
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record), flush=True)
if record["status"] != "UART_TASK_INPUT_STAGED_AND_HASH_VERIFIED":
    raise SystemExit(1)
