set -euo pipefail
test "$(id -un)" = root
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030');archive=root/'joint_results_delivery_v1.tar.gz'
holders=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  for fd in (proc/'fd').iterdir():
   try:target=str(fd.resolve())
   except (FileNotFoundError,PermissionError,ProcessLookupError):continue
   if target==str(archive):holders.append({'PID':int(proc.name),'archive_fd':fd.name,'state':(proc/'stat').read_text().split()[2],'proc_exists':True})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
r={'archive_exists':archive.exists(),'archive_bytes_now':archive.stat().st_size if archive.exists() else None,
 'archive_mtime_ns':archive.stat().st_mtime_ns if archive.exists() else None,'archive_open_processes':holders,
 'transfer_record':json.loads((root/'transfer.json').read_text()) if (root/'transfer.json').exists() else None,
 'result_manifest_exists':(root/'result_manifest.json').exists(),'new_launch_or_model_actions':0}
print(json.dumps(r))
PY
