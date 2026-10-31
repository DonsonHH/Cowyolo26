set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,os,statistics
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
terminal=json.loads((root/'framebank_replay/terminal.json').read_text())
assert terminal['status']=='ALL3_REAL_BOARD_PERIODIC_LOWRES_REPLAYS_COMPLETED' and terminal['close_error'] is None
assert not (Path('/proc')/str(terminal['PID'])).exists(),'Replayprocessstillpresent'
record=json.loads((root/'framebank_replay/record.json').read_text());assert terminal['record_sha256']==sha(root/'framebank_replay/record.json')
files=[f for f in sorted((root/'framebank_replay').rglob('*')) if f.is_file()]
files.extend([root/'framebank_replay.log',root/'launch_framebank_replay.json',root/'framebank_protocol.json',root/'board_framebank_replay.py'])
manifest=root/'framebank_artifact_manifest.json';assert not manifest.exists()
manifest.write_text(json.dumps([{'relative_file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=root/'framebank_replay_complete.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
file=root/'framebank_transfer.json';assert not file.exists();file.write_text(json.dumps(transfer,indent=2)+'\n');os.sync()
print(json.dumps({'transfer':transfer,'actual_image_forwards':record['total_actual_image_forwards'],
 'cases':[{k:c[k] for k in ['size','engine','processed','skipped','deadline_misses','on_time','observed_processed_fps','frontend_statistics']}|
          {'mean_read_ms':statistics.mean(r['lowres_input_copy_ms'] for r in c['rows'])} for c in record['cases']]}))
PY
