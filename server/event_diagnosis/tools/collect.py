from pathlib import Path
import hashlib,json,os,tarfile
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/event_diagnosis')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    layers=json.loads((ROOT/'results/layers/diagnostic_summary.json').read_text())
    cases=json.loads((ROOT/'results/source_cases/summary.json').read_text())
    assert len(layers['interventions'])==24 and len(cases['frames'])==20
    files=[]
    for folder in ['tools','protocol','logs','results']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                     and p.name not in {f'collect-{os.environ["SLURM_JOB_ID"]}.out',f'collect-{os.environ["SLURM_JOB_ID"]}.err'})
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    mp=ROOT/'delivery_manifest.json';mp.write_text(json.dumps(manifest,indent=2))
    archive=ROOT/'delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for path in sorted(files)+[mp]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    record={'job_id':os.environ['SLURM_JOB_ID'],'files':len(files),'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
    (ROOT/'delivery_bundle.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)


if __name__=='__main__':main()
