set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((root/'regression_results/terminal.json').read_text());s=json.loads((root/'regression_results/summary.json').read_text())
assert t['status']==s['status']=='ALL90_REAL_ARM_TRACES180_COUNTER_PATHS82020_TICKS_PASS_FROZEN_TOLERANCES'
assert sha(root/'regression_results/summary.json')==t['summary_sha256'] and not (Path('/proc')/str(t['PID'])).exists()
assert len(s['reports'])==90 and s['observation_ticks']==82020 and s['counter_paths']==180
p=json.loads((root/'board_regression_v1.json').read_text())
for row in p['files']:assert sha(root/row['file'])==row['sha256']
files=[*sorted((root/'regression_results').rglob('*'))]
files=[p for p in files if p.is_file()]
files.extend(root/f for f in ['build_lap_board.py','build_result.json','build_environment.json','build_terminal.json','launch.json','compile.log','run.log',
 'regression_launch.json','regression.log','board_regression.py','board_regression_v1.json','frame_pipeline.py','tracker_config.json'])
files.extend(sorted((root/'cow_tracker').glob('*.py')))
files.append(root/'source/lap-0.5.13/lap/_lapjv.cpython-310-arm-linux-gnueabihf.so')
manifest=root/'result_manifest.json';assert not manifest.exists()
manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root/'results_delivery.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for p in files+[manifest]:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
result={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,
 'board_PID_absent':True,'maximum_box_pixel_difference':s['maximum_box_pixel_difference'],'model_or_PL_actions':0}
(root/'results_transfer.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
PY
