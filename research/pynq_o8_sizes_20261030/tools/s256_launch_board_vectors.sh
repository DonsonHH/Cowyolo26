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
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_s256_qual_20261030');archive=root/'payload.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e665063749526b9d3807fb946b0230ad70bf0b82efdc86fbcffcf60b350bd55b'
assert not (root/'launch.json').exists() and not (root/'results').exists()
with tarfile.open(archive) as tar:
    assert len(tar.getmembers())==14
    for member in tar.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(root/member.name).resolve();assert file.is_relative_to(root.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
protocol=json.loads((root/'protocol.json').read_text())
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='44115dd48410635fe9eebc48a672ec0388ac3f0cef452c665b2baa1819422ca2'
for row in protocol['payload_files']:
    file=root/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
with (root/'run.log').open('xb') as log:
    child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_s256_vectors.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
record={'status':'REAL_BOARD_SINGLE_CLASS_COW_VECTOR_PROCESS_STARTED','PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'size':256,'class_count':1,'expected_actual_model_forwards':10,'new_bitstream_programming':False,'candidate_final_or_source_video_inputs':False}
with (root/'launch.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(record))
PY
