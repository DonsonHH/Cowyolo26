set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,numpy as np
root=Path('/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030');out=root/'encoding_results'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((out/'terminal.json').read_text());s=json.loads((out/'summary.json').read_text());assert t['success'] and not (Path('/proc')/str(t['PID'])).exists() and t['rows']==len(s['rows'])==22
files=[p for p in sorted(out.iterdir()) if p.is_file()]+[root/p for p in ['protocol.json','board_benchmark.py','benchmark_launch.json','benchmark.log']]
manifest=root/'benchmark_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],indent=2)+'\n')
archive=root/'benchmark_delivery.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
stats=[]
for level in [6,0]:
 rows=[r for r in s['rows'] if r['PNG_compress_level']==level];assert len(rows)==11 and all(r['pixels_exact'] for r in rows)
 stats.append({'PNG_level':level,'mean_save_wall_ms':float(np.mean([r['encode_file_wall_ms'] for r in rows])),'mean_save_CPU_ms':float(np.mean([r['encode_file_CPU_ms'] for r in rows])),'sum_file_bytes':sum(r['output_bytes'] for r in rows)})
print(json.dumps({'transfer':r,'encoding_statistics':stats,'all11_decoded_pixels_exact_at_both_levels':True,'actual_model_forwards':0,'whole_goal_complete':False}))
PY
