set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,os,sys
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_rot192_qual_20261029');archive=root/'payload.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='89fcb9fb88753714fcf2faefdf93c08889b828e3bfb454514e957ba2e2047605'
assert not (root/'launch.json').exists() and not (root/'results').exists()
with tarfile.open(archive) as tar:
    assert len(tar.getmembers())==14
    for member in tar.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(root/member.name).resolve();assert file.is_relative_to(root.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
protocol=json.loads((root/'protocol.json').read_text())
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='60b96d83d9355fc5572b651d9f701c45e6aa26ad0d6bf76b0bc5dd1be763c84b'
for row in protocol['payload_files']:
    file=root/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
with (root/'run.log').open('xb') as log:
    child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_cow_vectors.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
record={'status':'REAL_BOARD_SINGLE_CLASS_COW_VECTOR_PROCESS_STARTED','PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'size':192,'class_count':1,'expected_actual_model_forwards':10,'new_bitstream_programming':False,'candidate_final_or_source_video_inputs':False}
with (root/'launch.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(record))
PY
