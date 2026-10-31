set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129663,129664,129666 --format=JobID,JobName%24,State,ExitCode,Elapsed -P
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
python - <<'PY'
import os,signal,socket,json
p='/proc/4079247/cmdline'
if os.path.exists(p):
 data=open(p,'rb').read()
 if b'/share/home/renly/.cache/idcoo_us3_20261026' not in data:raise SystemExit('Unexpected helper identity; not stopping')
 os.kill(4079247,signal.SIGTERM)
 print('Stopped isolated task US3 proxy; original proxy configuration was not changed')
PY
