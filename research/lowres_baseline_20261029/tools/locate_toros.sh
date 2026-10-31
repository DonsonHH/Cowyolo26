set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026
find . -maxdepth 8 -type f -name Toros.mp4 -printf '%p|%s bytes\n'
