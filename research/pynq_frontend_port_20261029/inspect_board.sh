set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,importlib.util,shutil,sys,os
record={'status':'READONLY_BOARD_TRACKER_DEPENDENCY_GATE','python':sys.version,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'machine':os.uname().machine,'modules':{name:bool(importlib.util.find_spec(name)) for name in ['numpy','cv2','scipy','lap','torch','cython']},
        'tools':{name:shutil.which(name) for name in ['g++','gcc','cmake','make']},'model_forwards':0,'PL_actions':0}
print(json.dumps(record))
PY
