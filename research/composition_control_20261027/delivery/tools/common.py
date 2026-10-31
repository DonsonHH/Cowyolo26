from pathlib import Path
import hashlib,json
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'composition_control'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    partial=path.with_name(path.name+'.partial');partial.write_text(json.dumps(value,indent=2),encoding='utf-8');partial.replace(path)


def state_digest(model):
    h=hashlib.sha256()
    for name,tensor in sorted(model.state_dict().items()):
        h.update(name.encode());h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
