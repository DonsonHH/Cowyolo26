python - <<'PY'
from pathlib import Path
root=Path('/share/home/renly/projects/idcoo_research_20261026/env/lib/python3.13/site-packages/ultralytics')
for p in root.rglob('*.py'):
 for i,l in enumerate(p.read_text().splitlines(),1):
  if 'import polars' in l or 'from polars' in l:print(str(p.relative_to(root)),i,repr(l))
PY
