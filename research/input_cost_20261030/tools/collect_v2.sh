set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,socket,fcntl
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_v2_20261030')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
p=load(root/'protocol.json');s=load(root/'results/record.json');t=load(root/'results/terminal.json')
assert t['status']==s['status']=='ALL256_JPEG_READ_CASES128_REAL_O8_AFTER_READS_AND16_RAW_IMAGES_COMPLETE'
assert t['record_sha256']==sha(root/'results/record.json') and t['close_error'] is None and not (Path('/proc')/str(t['PID'])).exists()
assert s['actual_O8_forwards']==128 and s['actual_qualification_forwards']==8 and s['actual_warmups']==2 and len(s['rows'])==256
assert sha(Path(PL.bitfile_name))==p['O8_bit_sha256']==s['PL_after_sha256']
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
ports={}
for port in [22,9090]:
 try:c=socket.create_connection(('127.0.0.1',port),timeout=1);c.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
final={'status':'INPUT_COST_BENCHMARK_TERMINAL_ABSENT_O8_LOCK_AND_SERVICES_READ','PID':t['PID'],'proc_exists':False,'PL_bitfile':PL.bitfile_name,'PL_bit_sha256':sha(Path(PL.bitfile_name)),'lock_available':True,'services':ports,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
f=root/'final_state.json';assert not f.exists();f.write_text(json.dumps(final,indent=2)+'\n')
files=[q for q in sorted((root/'results').rglob('*')) if q.is_file()]+[root/n for n in ['protocol.json','board_benchmark_v2.py','launch.json','run.log','final_state.json']]
manifest=root/'result_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
a=root/'input_cost_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
meta={'archive':str(a),'bytes':a.stat().st_size,'sha256':sha(a),'members':len(files)+1,'final_state':final}
f=root/'transfer.json';assert not f.exists();f.write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
PY
