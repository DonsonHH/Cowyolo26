set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_long_session_20261028
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_long_session_20261028/results/native_review')
files=sorted(p.glob('overview_[0-9]*.jpg'));movie=p/'native_ROI_5hz.mp4'
print(json.dumps({'overview_snapshots_written':len(files),'last_snapshot_filename':files[-1].name if files else None,
                  'review_video_bytes_so_far':movie.stat().st_size if movie.exists() else None,
                  'summary_exists':(p/'summary.json').exists(),'final_archive_exists':(p.parents[1]/'native_review_delivery.tar.gz').exists()}))
PY
