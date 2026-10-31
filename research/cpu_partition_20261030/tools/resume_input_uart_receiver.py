"""Continue the existing ready receiver; do not create or restart board tasks."""
from pathlib import Path
from datetime import datetime, timezone
import base64, hashlib, json, re, sys, time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "pynq_lowres_20261029/serial_deps"))
import serial

prior = json.loads((ROOT / "evidence/input_UART_stage.json").read_text())
assert prior["status"] == "UART_INPUT_STAGE_FAILED_OR_TERMINAL_UNOBSERVED"
assert "No receiver readiness; do not send source bytes" in prior["error"]
matches = re.findall(r"UART_INPUT_READY_([a-f0-9]{12})\r?\n", prior["partial_output"])
assert len(matches) == 1
token = matches[0]
assert "UART_INPUT_DONE_" + token + " rc=0" not in prior["partial_output"]
payload = (ROOT / "cpu_partition_input_v1.tar.gz").read_bytes()
assert hashlib.sha256(payload).hexdigest() == prior["archive_sha256"]
encoded = base64.b64encode(payload).decode()
output = ROOT / "evidence/input_UART_stage_resume.json"
assert not output.exists()
record = {"created_UTC": datetime.now(timezone.utc).isoformat(), "original_ready_token": token,
          "same_existing_receiver_continued": True, "board_receiver_or_model_not_restarted": True,
          "framing_correction": "Original receiver printed readiness after a carriage return without preceding newline; actual readiness was present in saved output.",
          "new_model_forwards": 0}
port = serial.Serial(port=None, baudrate=115200, timeout=.2, xonxoff=False, rtscts=False, dsrdtr=False)
port.dtr = False
port.rts = False
port.port = "COM6"
started = time.monotonic()
stream = bytearray()
try:
    port.open()
    pending = port.read(4096)
    assert b"rc=" not in pending and not pending.endswith(b"$ "), "Receiver terminal changed; do not send bytes"
    for index in range(0, len(encoded), 1024):
        port.write((encoded[index:index+1024] + "\n").encode())
        port.flush()
    done = ("UART_INPUT_DONE_" + token + " rc=").encode()
    while done not in stream and time.monotonic() - started < 40:
        stream.extend(port.read(8192))
    text = stream.decode("utf-8", "replace")
    assert "UART_INPUT_DONE_" + token + " rc=0" in text, text[-2000:]
    result = [json.loads(line.strip()) for line in text.splitlines() if line.strip().startswith('{"status":')][-1]
    assert result["bytes"] == len(payload) and result["sha256"] == prior["archive_sha256"]
    record.update({"status": "UART_TASK_INPUT_STAGED_AND_HASH_VERIFIED", "remote_result": result, "elapsed_s": time.monotonic() - started})
except BaseException as error:
    record.update({"status": "SAME_RECEIVER_CONTINUATION_TERMINAL_NOT_VERIFIED", "error": repr(error), "output": stream.decode("utf-8", "replace")[-2500:]})
finally:
    if port.is_open:
        port.close()
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record), flush=True)
if record["status"] != "UART_TASK_INPUT_STAGED_AND_HASH_VERIFIED":
    raise SystemExit(1)
