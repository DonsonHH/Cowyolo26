set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130518,130537 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib
root=Path('detector_factorial_20261029');raw=subprocess.check_output(['sacct','-j','130518','-X','--noheader','--format=JobID,State,ExitCode','-P'],text=True)
tasks={}
for line in raw.splitlines():
    parts=line.strip().split('|')
    if len(parts)>=3 and parts[0] in {'130518_'+str(i) for i in range(15)}:tasks[parts[0]]=parts[1]+'|'+parts[2]
assert len(tasks)==15 and all(value=='FAILED|1:0' for value in tasks.values()),tasks
file=root/'input/training_terminal_states.json';assert not file.exists();file.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),
  'source':'LiveSACCTonmu01afterallarraytasksterminal;CPUworkerscannotqueryaccountingservice','tasks':tasks,'raw':raw},indent=2)+'
')
assert not (root/'results/all_checkpoints_frozen.json').exists()
print('ALL15_TASKS_TERMINAL_SNAPSHOT_SAVED_ON_LOGIN;NO_NEW_TRAINING')
PY
sbatch --parsable detector_factorial_20261029/tools/recover_v2.slurm
