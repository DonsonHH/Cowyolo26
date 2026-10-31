set -euo pipefail
id -un
hostname
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
scontrol show partition -o
df -hT /share/home/renly/projects/idcoo_research_20261026
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
models=[{'name': 'old_C', 'checkpoint': '/share/home/renly/projects/idcoo_research_20261026/identity_training/results/study/C_letterbox_trained_seed26/best_encoder.pt', 'checkpoint_sha256': '6653555c9c806e23d2747b06db53424541254364065c53c5311b7ae2ded06b8b', 'local_checkpoint': 'C:\\Users\\Donson\\Documents\\ChatGPT\\奶牛\\identity_training_20261026\\delivery\\results\\study\\C_letterbox_trained_seed26\\best_encoder.pt'}, {'name': 'new_C_domain_seed26', 'checkpoint': '/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030/results/training/C_domain_seed26/last_encoder.pt', 'checkpoint_sha256': 'b435fb4599d307c0dd8bf3adccb42a466c271a3fdf23ab91d585d463b70cc912', 'local_checkpoint': 'C:\\Users\\Donson\\Documents\\ChatGPT\\奶牛\\identity_domain_adapt_20261030\\delivery\\results\\training\\C_domain_seed26\\last_encoder.pt'}]
for row in models:
 p=Path(row['checkpoint']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['checkpoint_sha256']
 print(json.dumps({'model':row['name'],'checkpoint_SHA256':row['checkpoint_sha256'],'file_exists':True}))
PY
