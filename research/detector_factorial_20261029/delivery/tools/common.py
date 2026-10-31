from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    partial=path.with_name(path.name+'.partial');partial.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');partial.replace(path)
def save_new(path,value):
    path=Path(path);assert not path.exists(),path;save(path,value)
def state_digest(model):
    h=hashlib.sha256()
    for name,tensor in sorted(model.state_dict().items()):
        h.update(name.encode());h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
