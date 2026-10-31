set -euo pipefail
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
import inspect
from ultralytics.models.yolo.detect.train import DetectionTrainer
from ultralytics.engine.trainer import BaseTrainer
from ultralytics.data.build import build_yolo_dataset
from ultralytics.data.dataset import YOLODataset
print('optimizer_step')
print(inspect.getsource(BaseTrainer.optimizer_step))
print('train setup signature',inspect.signature(BaseTrainer._setup_train))
print('detection getmodel')
print(inspect.getsource(DetectionTrainer.get_model))
print('build dataset signature',inspect.signature(build_yolo_dataset))
print('dataset constructor',inspect.signature(YOLODataset))
print('trainer batch callbacks')
s=inspect.getsource(BaseTrainer._do_train)
for i,line in enumerate(s.splitlines()):
    if 'callback' in line or 'optimizer_step' in line or 'accumulate' in line:print(i,line)
PY
