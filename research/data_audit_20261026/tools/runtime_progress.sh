python - <<'PY'
import os,pathlib,json
pid='4159233';fd=pathlib.Path('/proc')/pid/'fd'
if fd.exists():
 for p in fd.iterdir():
  try:
   target=os.readlink(p)
   if target.endswith('.whl'):
    f=pathlib.Path(target);print(json.dumps({'runtime_download':f.name,'bytes':f.stat().st_size}))
  except (FileNotFoundError,PermissionError):pass
else:print('runtime_install_process_terminal')
PY
tail -n 3 /share/home/renly/projects/idcoo_research_20261026/logs/install_runtime_dependencies.log
