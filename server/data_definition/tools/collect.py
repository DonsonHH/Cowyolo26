from pathlib import Path
import hashlib,json,os,tarfile
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/data_definition')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary=json.loads((ROOT/'results/audit/summary.json').read_text());assert len(summary['train_visual_samples'])==12
    files=[]
    for folder in ['protocol','tools','logs','results']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and
                     p.name not in {f'collect-{os.environ["SLURM_JOB_ID"]}.out',f'collect-{os.environ["SLURM_JOB_ID"]}.err'})
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    mp=ROOT/'delivery_manifest.json';mp.write_text(json.dumps(manifest,indent=2));dest=ROOT/'delivery.tar.gz';assert not dest.exists()
    with tarfile.open(dest,'w:gz',compresslevel=1) as tar:
        for path in sorted(files)+[mp]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    record={'job_id':os.environ['SLURM_JOB_ID'],'files':len(files),'bytes':dest.stat().st_size,'sha256':sha(dest),'manifest_sha256':sha(mp)}
    (ROOT/'delivery_bundle.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)


if __name__=='__main__':main()
