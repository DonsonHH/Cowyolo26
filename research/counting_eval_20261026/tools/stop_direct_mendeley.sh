python - <<'PY'
import os,signal
for pid in os.listdir('/proc'):
 if not pid.isdigit():continue
 try:
  data=open('/proc/'+pid+'/cmdline','rb').read()
  if data.startswith(b'curl\x00') and b'/phase2/data/mendeley_counting/Dataset_Files.zip.partial' in data and b'--noproxy' in data:
   os.kill(int(pid),signal.SIGTERM);print('Stopped own incomplete direct transfer',pid)
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
PY
