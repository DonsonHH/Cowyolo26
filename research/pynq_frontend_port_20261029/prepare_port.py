"""Keep upstream tracker math; replace package imports and tensor interfaces."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,difflib,py_compile
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'upstream_manifest.json').read_text())
out=ROOT/'cow_tracker';out.mkdir(exist_ok=False)
(out/'__init__.py').write_text('"""Frozen AABB ByteTrack without a Torch import; upstream AGPL notices retained."""\n')
mapping={'ultralytics.trackers.byte_tracker':'byte_tracker.py','ultralytics.trackers.basetrack':'basetrack.py',
 'ultralytics.trackers.utils.matching':'matching.py','ultralytics.trackers.utils.kalman_filter':'kalman_filter.py','ultralytics.trackers.utils.stracks':'stracks.py'}
diffs=[]
for key,name in mapping.items():
    file=ROOT/'upstream'/manifest['sources'][key]['file'];assert sha(file)==manifest['sources'][key]['sha256']
    original=file.read_text(encoding='utf-8');text=original
    if name=='byte_tracker.py':
        text=text.replace('from ..utils import LOGGER','from .support import LOGGER').replace('from ..utils.ops import xywh2ltwh','from .support import xywh2ltwh')
        text=text.replace('from .utils import matching','from . import matching').replace('from .utils.kalman_filter import','from .kalman_filter import').replace('from .utils.stracks import','from .stracks import')
    elif name=='stracks.py':text=text.replace('from ..basetrack import','from .basetrack import')
    elif name=='matching.py':
        text=text.replace('from ultralytics.utils.metrics import batch_probiou, bbox_ioa','from .support import batch_probiou, bbox_ioa')
        start=text.index('try:\n    import lap');end=text.index('\n\ndef linear_assignment',start)
        text=text[:start]+"import lap\nassert lap.__version__ == '0.5.13', 'Frozen LAP solver version required'\n"+text[end:]
    (out/name).write_text(text,encoding='utf-8',newline='\n')
    diffs.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=key,tofile=name))
support='''# Adapted from Ultralytics; AGPL-3.0, https://ultralytics.com/license
import logging
import numpy as np
LOGGER=logging.getLogger('cow_tracker')
def batch_probiou(*args,**kwargs):
    raise NotImplementedError('This frozen deployment supports axis-aligned boxes only')
'''
for key in ['bbox_ioa','xywh2ltwh','xyxy2xywh']:
    row=manifest['sources'][key];p=ROOT/'upstream'/row['file'];assert sha(p)==row['sha256']
    text=p.read_text(encoding='utf-8')
    text=text.replace('x.clone() if isinstance(x, torch.Tensor) else np.copy(x)','np.copy(x)').replace('y = empty_like(x)','y = np.empty_like(x)')
    support+='\n'+text
(out/'support.py').write_text(support,encoding='utf-8',newline='\n')
for name in ['zone_counter.py','confirmation_counter.py']:
    source=PROJECT/'factorial_lane_crop_20261029/input'/name
    text=source.read_text(encoding='utf-8')
    if name=='confirmation_counter.py':text=text.replace('from zone_counter import ZoneCounter','from .zone_counter import ZoneCounter')
    (out/name).write_text(text,encoding='utf-8',newline='\n')
(ROOT/'source_import_changes.diff').write_text(''.join(diffs),encoding='utf-8')
cfg={}
for line in (ROOT/'upstream/bytetrack_config.yaml').read_text(encoding='utf-8').splitlines():
    if not line.strip() or line.lstrip().startswith('#'):continue
    k,v=line.split('#',1)[0].split(':',1);v=v.strip()
    cfg[k.strip()]=True if v=='True' else False if v=='False' else float(v) if '.' in v else int(v) if v.isdigit() else v
(ROOT/'tracker_config.json').write_text(json.dumps(cfg,indent=2)+'\n')
for p in out.glob('*.py'):py_compile.compile(str(p),doraise=True)
record={'status':'PORT_SOURCE_PREPARED_NOT_YET_REGRESSION_QUALIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'upstream_ultralytics':'8.4.63','lap_version_required':'0.5.13','model_inference':False,
 'tracker_algorithm_modified':False,'package_imports_and_NumPy_box_interface_only':True,
 'unsupported_OBB_explicitly_rejected':True,'files':[{'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in sorted(out.glob('*.py'))],
 'whole_goal_complete':False}
(ROOT/'source_preparation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'files':len(record['files']),'status':record['status']}))
