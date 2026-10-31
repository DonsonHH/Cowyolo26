set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026
find "$ROOT/env/lib" -path '*/ultralytics/trackers/track.py' -o -path '*/ultralytics/engine/model.py'
find "$ROOT/phase2/results/external_counting" -path '*/Toros/*.csv' -printf '%s %p\n'
find "$ROOT/data" -maxdepth 2 -type d
find "$ROOT/catalog" -maxdepth 1 -type f -printf '%f\n'
