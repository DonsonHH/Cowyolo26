from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
text=(ROOT/'tools/recover_completion.py').read_text();old="state=subprocess.check_output(['sacct','-j','130518_'+str(index),'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()"
assert old in text;text=text.replace(old,"state=load(ROOT/'input/training_terminal_states.json')['tasks']['130518_'+str(index)]")
file=ROOT/'tools/recover_completion_v2.py';assert not file.exists();file.write_text(text,newline='\n')
slurm=ROOT/'tools/recover_v2.slurm';assert not slurm.exists();slurm.write_text((ROOT/'tools/recover.slurm').read_text().replace('tools/recover_completion.py','tools/recover_completion_v2.py'),newline='\n')
for relative in ['tools/recover_completion_v2.py','tools/recover_v2.slurm']:
    subprocess.run([sys.executable,str(bridge),'put',str(ROOT/relative),'/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/'+relative],check=True)
script=ROOT/'tools/submit_recovery_v2_generated.sh';assert not script.exists()
script.write_text('''set -euo pipefail
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
  'source':'LiveSACCTonmu01afterallarraytasksterminal;CPUworkerscannotqueryaccountingservice','tasks':tasks,'raw':raw},indent=2)+'\n')
assert not (root/'results/all_checkpoints_frozen.json').exists()
print('ALL15_TASKS_TERMINAL_SNAPSHOT_SAVED_ON_LOGIN;NO_NEW_TRAINING')
PY
sbatch --parsable detector_factorial_20261029/tools/recover_v2.slurm
''',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/recovery_v2_submit.txt')],check=True)
