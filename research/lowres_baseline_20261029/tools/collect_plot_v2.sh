set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130505 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
test "$(sacct -j 130505 --noheader --format=State -P | head -n1)" = COMPLETED
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029')
files=list(sorted((root/'results/plots_v2').iterdir()))+[root/'logs/plot-v2-130505.out',root/'logs/plot-v2-130505.err',root/'tools/render_plot_v2.py']
archive=root.parent/'lowres_baseline_20261029_plot_v2.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
record={'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':len(files)}
out=root.parent/'lowres_baseline_20261029_plot_v2_transfer.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
