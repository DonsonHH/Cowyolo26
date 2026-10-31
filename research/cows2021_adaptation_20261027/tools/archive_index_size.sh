set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import struct,json
p=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/results/archive_index_probe/index_part_02.bin')
data=p.read_bytes();values=struct.unpack('<4sQHHLLQQQQ',data)
assert values[0]==b'PK\x06\x06'
print(json.dumps({'ZIP_entries':values[-3],'directory_bytes':values[-2],'directory_offset':values[-1],
                  'member_payload_bytes_requested':0}))
PY
