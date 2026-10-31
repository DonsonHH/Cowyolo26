set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/home/xilinx/jupyter_notebooks')
o8=root/'yolo26_optimization_8';model=root/'cow_research_o8_mosaic192_qual_20261030'
files=[o8/'native_sources/native_queue.so',o8/'hardware/accepted/firmware_manifest.json',
       model/'program/program.json',model/'program/graph.bin',
       model/'resident_plan/resident_plan.bin',model/'resident_plan/resident_plan.json']
rows=[]
for path in files:
 assert path.is_file(),str(path)
 rows.append({'file':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
print(json.dumps({'status':'O8_NATIVE_RUNTIME_AND_MODEL_METADATA_HASHED_NO_IMPORT_OR_FORWARD',
                  'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'files':rows,'new_model_forwards':0}),flush=True)
PY
