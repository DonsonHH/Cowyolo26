set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,subprocess,inspect,PIL
from PIL import ImageOps
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
r={'Pillow':PIL.__version__,'contain_source':inspect.getsource(ImageOps.contain),'pad_source':inspect.getsource(ImageOps.pad),
 'processes':subprocess.run(['pgrep','-af','diagnose_preprocess.py'],capture_output=True,text=True).stdout,
 'produced_diagnostic_files':len(list((root/'preprocessing_diagnostic').glob('*.npz'))),
 'summary':(root/'preprocessing_diagnostic/summary.json').read_text() if (root/'preprocessing_diagnostic/summary.json').exists() else None}
print(json.dumps(r))
PY
