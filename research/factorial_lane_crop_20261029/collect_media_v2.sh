set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130564 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/factorial_lane_crop_20261029/logs/media-130564.out /share/home/renly/projects/idcoo_research_20261026/factorial_lane_crop_20261029/logs/media-130564.err; do
    if [ -f "$file" ]; then tail -n 6 "$file"; fi
done
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('factorial_lane_crop_20261029').resolve()
state=subprocess.check_output(['sacct','-j','130564','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),state
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((root/'results/media_v2/media_metadata.json').read_text());assert len(meta['movies'])==2 and meta['science_bar_count']==36
files=[p for p in sorted((root/'results/media_v2').rglob('*')) if p.is_file()]
files.extend([root/'protocol/media_v1.json',root/'tools/render_media_v2.py',root/'media_v2.slurm',root/'logs/media-130564.out',root/'logs/media-130564.err'])
archive=root.parent/'factorial_lane_crop_20261029_media_v2.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in files:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
record={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)}
file=root.parent/'factorial_lane_crop_20261029_media_v2_transfer.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
