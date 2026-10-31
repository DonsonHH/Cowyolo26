set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,os,statistics
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
terminal=json.loads((root/'input_probe/terminal.json').read_text())
assert terminal['status']=='BOARD_INPUT12_NATIVE_AND36_LETTERBOX_CONDITIONS_COMPLETE' and not (Path('/proc')/str(terminal['PID'])).exists()
summary=json.loads((root/'input_probe/summary.json').read_text());assert terminal['summary_sha256']==sha(root/'input_probe/summary.json')
files=[f for f in sorted((root/'input_probe').rglob('*')) if f.is_file()]
files.extend([root/'input_probe.log',root/'launch_input_probe.json',root/'input_gate.json',root/'board_input_probe.py'])
manifest=root/'input_probe_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'relative_file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=root/'input_probe_complete.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
file=root/'input_probe_transfer.json';assert not file.exists();file.write_text(json.dumps(transfer,indent=2)+'\n');os.sync()
times={}
for name in ['np_rot90_copy_native_baseline','cv2_rotate_native','cv2_resize_before_rotate']:
    values=[v for row in summary['rows'] for c in row['size_conditions'] for v in c['timing_ms'][name]]
    times[name]={'samples':len(values),'mean_ms':statistics.mean(values),'maximum_ms':max(values)}
print(json.dumps({'transfer':transfer,'timing':times,'native_cv2_rotation_exact_all12':summary['native_cv2_rotation_exact_all12'],
    'cv2native_letterbox_exact_all36':summary['cv2native_letterbox_exact_all36'],'resizefirst_letterbox_exact_all36':summary['resizefirst_letterbox_exact_all36']}))
PY
