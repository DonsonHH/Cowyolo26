sacct -j 129663,129664,129666,129667 --format=JobID,JobName%24,State,ExitCode,Elapsed -P
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
python - <<'PY'
import socket,json
with socket.socket() as s:print(json.dumps({'isolated_task_proxy_listener_active':s.connect_ex(('127.0.0.1',27831))==0}))
PY
