set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,os,pynq
old=Path('/home/xilinx/jupyter_notebooks/cow_research_lowres_20261029')
new=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029');new.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[f for f in sorted(old.rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
manifest=new/'prior_interrupted_manifest.json';manifest.write_text(json.dumps([{'relative':f.relative_to(old).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=new/'prior_interrupted_test.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for f in files:tar.add(f,arcname=f.relative_to(old).as_posix(),recursive=False)
os.sync()
record={'status':'PRIOR_PARTIAL_TEST_PRESERVED_BEFORE_NEW_HARDWARE_ACTION','board_UTC_may_be_wrong':datetime.now(timezone.utc).isoformat(),
        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'prior_PID8082_exists':Path('/proc/8082').exists(),
        'prior_manifest_sha256':sha(manifest),'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),
        'members':len(files),'empty_files':[f.relative_to(old).as_posix() for f in files if not f.stat().st_size],
        'XILINX_XRT':os.environ.get('XILINX_XRT'),'PL_bitfile_name':pynq.PL.bitfile_name,'PL_IP_names':list(pynq.PL.ip_dict),
        'memory':Path('/proc/meminfo').read_text(),'no_new_overlay_loaded':True,'new_inference_calls':0}
(new/'recovery_record.json').write_text(json.dumps(record,indent=2)+'\n');os.sync();print(json.dumps(record))
PY
