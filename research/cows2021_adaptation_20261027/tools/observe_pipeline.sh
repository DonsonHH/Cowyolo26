set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
def read(relative):
    p=root/relative
    return json.loads(p.read_text()) if p.exists() else None
accounting=subprocess.run(['sacct','-j','129918,129919,129920','--format=JobID,JobName%28,State,ExitCode,Elapsed,MaxRSS','-P'],capture_output=True,text=True,check=True)
queue=subprocess.run(['squeue','-j','129918,129919,129920','-o','%.18i|%.9P|%.24j|%.8T|%.10M|%R'],capture_output=True,text=True,check=True)
value={'observed_UTC':datetime.now(timezone.utc).isoformat(),'accounting':accounting.stdout.strip(),
       'queue':queue.stdout.strip(),'training_progress':read('results/training/progress.json'),
       'completed_seed_records':[{'seed':seed,'record':read(f'results/training/seed{seed}/condition_complete.json')}
                                  for seed in [26,27,28] if (root/f'results/training/seed{seed}/condition_complete.json').exists()],
       'training_summary':read('results/training/summary.json'),
       'all_models_frozen':(root/'results/training/all_checkpoints_frozen_before_video.json').exists(),
       'inference_summary':read('results/inference/summary.json'),'bundle':read('delivery_bundle.json')}
print(json.dumps(value),flush=True)
PY
