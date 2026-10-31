from pathlib import Path
import hashlib,json,tarfile
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

for name in ['qat_study','source_demo']:
    root=PROJECT/name
    files=[]
    for folder in ['tools','protocol','logs','results']:
        files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                     and p.name!='source_transfer.mp4')
    assert files and all(root.resolve() in p.resolve().parents for p in files)
    manifest=[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    manifest_path=root/'delivery_manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2))
    target=root/'delivery.tar.gz';assert not target.exists()
    with tarfile.open(target,'w:gz',compresslevel=1) as archive:
        for path in sorted(files)+[manifest_path]:archive.add(path,arcname=path.relative_to(root).as_posix(),recursive=False)
    record={'files':len(files),'bytes':target.stat().st_size,'sha256':sha(target),'manifest_sha256':sha(manifest_path),
            'source_clean_transfer_omitted':name=='source_demo','all_stage_jobs_terminal_before_collection':True}
    (root/'delivery_bundle.json').write_text(json.dumps(record,indent=2))
    print(json.dumps({'stage':name,**record}),flush=True)
