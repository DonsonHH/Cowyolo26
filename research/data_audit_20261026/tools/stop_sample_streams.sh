python - <<'PY'
import os,signal
targets={b'python\x00-u\x00/share/home/renly/projects/idcoo_research_20261026/tools/stage_media.py\x00',b'python\x00-u\x00/share/home/renly/projects/idcoo_research_20261026/tools/stage_cows21_priority.py\x00'}
for pid in os.listdir('/proc'):
 if not pid.isdigit():continue
 try:
  data=open('/proc/'+pid+'/cmdline','rb').read()
  if data in targets:os.kill(int(pid),signal.SIGTERM);print('Stopped own sequential sample downloader',pid)
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
PY
