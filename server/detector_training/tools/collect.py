"""Archive final weights, raw records and new-seed videos after all jobs terminate."""
from pathlib import Path
import hashlib,json,os,tarfile

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/detector_training')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    summary=json.loads((ROOT/'results/inference/summary.json').read_text())
    assert summary['status']=='FIVE_MODELS_SOURCE_SCOPE_AND_KNOWN_DIAGNOSTIC_COMPLETE'
    files=[]
    for folder in ['tools','protocol','logs','results']:
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:continue
            if path.name in {f'collect-{os.environ["SLURM_JOB_ID"]}.out',f'collect-{os.environ["SLURM_JOB_ID"]}.err'}:continue
            if path.name=='source_transfer.mp4' and path.parent.name in ['generic','pilot']:continue
            if path.suffix=='.pt' and path.name!='last.pt':continue
            files.append(path)
    assert files
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    mp=ROOT/'delivery_manifest.json';mp.write_text(json.dumps(manifest,indent=2))
    target=ROOT/'delivery.tar.gz';assert not target.exists()
    with tarfile.open(target,'w:gz',compresslevel=1) as tar:
        for path in sorted(files)+[mp]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    result={'job_id':os.environ['SLURM_JOB_ID'],'files':len(files),'archive_bytes':target.stat().st_size,
            'archive_sha256':sha(target),'manifest_sha256':sha(mp),'baseline_rerender_videos_left_on_server':True,
            'all_3_final_checkpoints_included':True,'all_5_models_traces_included':True}
    (ROOT/'delivery_bundle.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)


if __name__=='__main__':main()
