set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
id -un
hostname
printf '%s\n' "$HOME"
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
scontrol show partition -o
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from ultralytics.models.yolo.detect.train import DetectionTrainer
from ultralytics.engine.trainer import BaseTrainer
import inspect,hashlib
for cls,name in [(DetectionTrainer,'preprocess_batch'),(BaseTrainer,'_setup_train'),(BaseTrainer,'_do_train')]:
    text=inspect.getsource(getattr(cls,name))
    print('SOURCE',cls.__name__,name,hashlib.sha256(text.encode()).hexdigest())
    if name=='preprocess_batch':print(text)
    elif name=='_setup_train':
        for line in text.splitlines():
            if any(word in line for word in ['init_seeds','seed','setup_model','build_optimizer','accumulate','batch_size','warmup']):print(line)
    else:
        for line in text.splitlines():
            if any(word in line for word in ['preprocess_batch','on_train_batch','optimizer_step','accumulate','warmup','ni =']):print(line)
PY
