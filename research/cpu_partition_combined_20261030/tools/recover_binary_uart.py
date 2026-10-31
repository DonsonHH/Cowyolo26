"""Read an immutable task file in SHA-checked binary blocks, restore tty settings."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse, base64, hashlib, json, os, shlex, sys, time, uuid, zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "pynq_lowres_20261029/serial_deps"))
import serial

parser = argparse.ArgumentParser()
parser.add_argument("--remote-file", required=True)
parser.add_argument("--expected-bytes", type=int, required=True)
parser.add_argument("--expected-sha256", required=True)
parser.add_argument("--destination", required=True)
parser.add_argument("--record-prefix", required=True)
args = parser.parse_args()
remote = PurePosixPath(args.remote_file)
assert remote.is_absolute() and ".." not in remote.parts and str(remote).startswith("/home/xilinx/jupyter_notebooks/cow_research_")
assert args.expected_bytes > 0 and len(args.expected_sha256) == 64
destination = (ROOT / args.destination).resolve()
assert destination.is_relative_to(ROOT) and not destination.exists()
destination.parent.mkdir(parents=True, exist_ok=True)
partial = destination.with_suffix(destination.suffix + ".partial")
assert not partial.exists()
assert Path(args.record_prefix).name == args.record_prefix
control = ROOT / "evidence" / (args.record_prefix + "_control.json")
progress = ROOT / "evidence" / (args.record_prefix + "_progress.json")
terminal = ROOT / "evidence" / (args.record_prefix + "_terminal.json")
blocks = ROOT / "evidence" / (args.record_prefix + "_blocks.jsonl")
assert all(not path.exists() for path in [control, progress, terminal, blocks])
token = uuid.uuid4().hex[:16]
receiver = f'''from pathlib import Path
import sys,hashlib,os
p=Path({str(remote)!r});expected={args.expected_sha256!r};n={args.expected_bytes};token={token!r}
assert p.stat().st_size==n
h=hashlib.sha256()
with p.open('rb') as f:
 for part in iter(lambda:f.read(262144),b''):h.update(part)
assert h.hexdigest()==expected
out=sys.stdout.buffer;out.write(('\\nCOW_BEGIN '+token+' '+str(n)+' '+expected+' '+os.environ['COW_UART_TTY_ORIGINAL']+'\\n').encode());out.flush()
offset=0
with p.open('rb') as f:
 while offset<n:
  f.seek(offset);data=f.read(min(65536,n-offset));digest=hashlib.sha256(data).hexdigest()
  while True:
   out.write(('COW_BLOCK '+token+' '+str(offset)+' '+str(len(data))+' '+digest+'\\n').encode());out.flush();out.write(data);out.flush()
   answer=sys.stdin.buffer.readline().decode().strip().split()
   if answer==['ACK',token,str(offset+len(data)),digest]:offset+=len(data);break
   if answer==['RETRY',token,str(offset)]:continue
   if len(answer)==3 and answer[:2]==['RESUME',token]:
    new=int(answer[2]);assert 0<=new<=n and(new%65536==0 or new==n);offset=new;break
   raise RuntimeError('invalid_block_acknowledgement')
out.write(('COW_DONE '+token+' '+str(offset)+' '+expected+'\\n').encode());out.flush()
'''
payload_code = "import base64,zlib;exec(zlib.decompress(base64.b64decode(" + repr(base64.b64encode(zlib.compress(receiver.encode())).decode()) + ")))"
command = ("cow_uart_saved=$(stty -g); stty -echo -opost; COW_UART_TTY_ORIGINAL=\"$cow_uart_saved\" python3 -u -c " + shlex.quote(payload_code)
           + "; cow_uart_rc=$?; stty \"$cow_uart_saved\"; cow_uart_now=$(stty -g); cow_uart_ok=0; if [ \"$cow_uart_now\" = \"$cow_uart_saved\" ]; then cow_uart_ok=1; fi; printf '\\nCOW_TTY_DONE " + token + " rc=%s tty_restore=%s\\n' \"$cow_uart_rc\" \"$cow_uart_ok\"")
assert len(command.encode()) < 4096
record = {"created_UTC": datetime.now(timezone.utc).isoformat(), "token": token, "remote_file": str(remote),
          "expected_bytes": args.expected_bytes, "expected_sha256": args.expected_sha256,
          "destination": str(destination), "partial": str(partial), "port": "COM6", "baud": 115200,
          "block_size": 65536, "output_postprocessing_temporarily_disabled_and_restored": True,
          "hardware_reset_or_baud_change": False, "new_model_forwards": 0}
control.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
port = serial.Serial(port=None, baudrate=115200, timeout=.2, xonxoff=False, rtscts=False, dsrdtr=False)
port.dtr = False
port.rts = False
port.port = "COM6"
buffer = bytearray()
started = time.monotonic()
received = 0
block_count = 0
retry_count = 0
digest = hashlib.sha256()


def read_line(timeout=30):
    deadline = time.monotonic() + timeout
    while b"\n" not in buffer:
        assert time.monotonic() < deadline, "UART header observation timeout; retain same receiver control"
        buffer.extend(port.read(8192))
    index = buffer.index(10)
    line = bytes(buffer[:index]).decode("utf-8", "strict").strip()
    del buffer[:index+1]
    return line


def read_exact(length):
    deadline = time.monotonic() + 45
    while len(buffer) < length:
        assert time.monotonic() < deadline, "UART block observation timeout; retain same receiver control"
        buffer.extend(port.read(min(65536, length - len(buffer))))
    data = bytes(buffer[:length])
    del buffer[:length]
    return data


try:
    port.open()
    port.read(4096)
    port.write((command + "\r").encode())
    port.flush()
    while True:
        line = read_line()
        if line.startswith("COW_BEGIN " + token + " "):
            header = line.split()
            assert int(header[2]) == args.expected_bytes and header[3] == args.expected_sha256
            record["original_tty_settings"] = header[4]
            break
    with partial.open("xb") as sink, blocks.open("x", encoding="utf-8") as block_log:
        while received < args.expected_bytes:
            header = read_line().split()
            assert header[:2] == ["COW_BLOCK", token] and int(header[2]) == received
            length = int(header[3])
            assert length == min(65536, args.expected_bytes - received)
            data = read_exact(length)
            actual = hashlib.sha256(data).hexdigest()
            if actual != header[4]:
                retry_count += 1
                assert retry_count <= 3
                port.write(("RETRY " + token + " " + str(received) + "\n").encode())
                port.flush()
                continue
            sink.write(data)
            sink.flush()
            os.fsync(sink.fileno())
            digest.update(data)
            received += length
            block_count += 1
            block_log.write(json.dumps({"end_offset": received, "bytes": length, "sha256": actual}) + "\n")
            block_log.flush()
            os.fsync(block_log.fileno())
            status = {"status": "RUNNING_SAME_IMMUTABLE_FILE_RECEIVER", "received_bytes": received, "total_bytes": args.expected_bytes,
                      "blocks_verified": block_count, "retries": retry_count, "elapsed_s": time.monotonic() - started}
            temporary = progress.with_suffix(".json.partial")
            temporary.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
            temporary.replace(progress)
            port.write(("ACK " + token + " " + str(received) + " " + actual + "\n").encode())
            port.flush()
            if block_count % 8 == 0:
                print(json.dumps(status), flush=True)
    assert read_line() == "COW_DONE " + token + " " + str(received) + " " + args.expected_sha256
    line = read_line()
    while not line.startswith("COW_TTY_DONE " + token + " "):
        line = read_line()
    assert line == "COW_TTY_DONE " + token + " rc=0 tty_restore=1"
    assert received == args.expected_bytes and digest.hexdigest() == args.expected_sha256
    assert partial.resolve().is_relative_to(ROOT) and destination.resolve().is_relative_to(ROOT) and not destination.exists()
    partial.rename(destination)
    record.update({"status": "FULL_BINARY_UART_FILE_BLOCKS_AND_FINAL_SHA_VERIFIED_TTY_RESTORED", "received_bytes": received,
                   "blocks_verified": block_count, "retries": retry_count, "sha256": digest.hexdigest(),
                   "tty_restored_verified": True, "elapsed_s": time.monotonic() - started})
except BaseException as error:
    record.update({"status": "UART_BINARY_RECEIVER_TERMINAL_NOT_VERIFIED_RETAIN_SAME_CONTROL", "error": repr(error),
                   "received_bytes_verified": received, "blocks_verified": block_count,
                   "remaining_receiver_buffer_bytes": len(buffer), "elapsed_s": time.monotonic() - started})
finally:
    if port.is_open:
        port.close()
    terminal.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record), flush=True)
if record["status"] != "FULL_BINARY_UART_FILE_BLOCKS_AND_FINAL_SHA_VERIFIED_TTY_RESTORED":
    raise SystemExit(1)
