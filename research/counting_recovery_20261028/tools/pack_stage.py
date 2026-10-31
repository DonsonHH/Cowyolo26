from pathlib import Path
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1];archive=ROOT/'staging.tar.gz';assert not archive.exists()
paths=sorted(p for directory in ['tools','protocol','input'] for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
manifest=[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
with tarfile.open(archive,'w:gz') as tf:
    for path in paths:tf.add(path,arcname=path.relative_to(ROOT).as_posix())
record={'files':len(paths),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'input_files':manifest}
(ROOT/'results/staging_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='input_files'}))
