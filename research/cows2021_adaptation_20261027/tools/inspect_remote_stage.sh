set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
printf 'stage_exists=%s\n' "$(test -e "$stage" && echo yes || echo no)"
printf 'staging_archive_exists=%s\n' "$(test -e "$project/cows2021_adaptation_20261027.staging_metadata.tar.gz" && echo yes || echo no)"
ps -u renly -o pid,lstart,args | awk '/[f]etch_images.py/ {print}'
"$project/env/bin/python" - <<'PY'
import ssl,requests,certifi,json
from urllib.parse import urlparse
print(json.dumps({'requests':requests.__version__,'OpenSSL':ssl.OPENSSL_VERSION,'CA_path_exists':__import__('pathlib').Path(certifi.where()).is_file()}))
PY
