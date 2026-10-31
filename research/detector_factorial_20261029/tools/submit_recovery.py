from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029';bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
for relative in ['tools/recover_completion.py','tools/recover.slurm']:subprocess.run([sys.executable,str(bridge),'put',str(ROOT/relative),REMOTE+'/'+relative],check=True)
script=ROOT/'tools/submit_recovery_generated.sh';assert not script.exists()
script.write_text('''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
cd /share/home/renly/projects/idcoo_research_20261026
test ! -e detector_factorial_20261029/results/all_checkpoints_frozen.json
sbatch --parsable --dependency=afterany:130518 detector_factorial_20261029/tools/recover.slurm
''',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/recovery_submit.txt')],check=True)
