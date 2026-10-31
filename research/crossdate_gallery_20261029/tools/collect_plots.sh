set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130424 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130424 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
cat /share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029/logs/plot-130424.out
cat /share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029/logs/plot-130424.err
test "$(sacct -j 130424 --noheader --format=State -P | head -n1)" = COMPLETED
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029')
paths=[p for p in sorted((root/'results/plots').iterdir()) if p.is_file()]
paths+=[root/'logs/plot-130424.out',root/'logs/plot-130424.err',root/'tools/plot_counts.py']
archive=root.parent/'crossdate_gallery_20261029_plots.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in paths:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
m={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':len(paths)}
out=root.parent/'crossdate_gallery_20261029_plots_transfer.json';assert not out.exists();out.write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps(m))
PY
