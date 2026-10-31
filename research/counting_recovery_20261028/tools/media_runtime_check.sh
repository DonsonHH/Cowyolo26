set -euo pipefail
command -v ffmpeg || true
test ! -x /usr/bin/ffmpeg || /usr/bin/ffmpeg -version | head -n 1
test ! -x /share/home/renly/projects/idcoo_research_20261026/env/bin/ffmpeg || /share/home/renly/projects/idcoo_research_20261026/env/bin/ffmpeg -version | head -n 1
du -h /share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/results/delivery.tar.gz
