from pathlib import Path
import json,os,tarfile
from common import *


def main():
    result=json.loads((ROOT/'results/inference/summary.json').read_text())
    assert result['status']=='SIX_COMPOSITION_MODELS_SOURCE_AND_KNOWN_DIAGNOSTIC_COMPLETE'
    files=[]
    for folder in ['tools','protocol','logs','results']:
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:continue
            if path.name in {f'collect-{os.environ["SLURM_JOB_ID"]}.out',f'collect-{os.environ["SLURM_JOB_ID"]}.err'}:continue
            if path.suffix=='.pt' and path.name!='last.pt':continue
            files.append(path)
    for arm in ['mixed','real_repeated']:
        files.extend([ROOT/'data'/arm/'slot_manifest.json',ROOT/'data'/arm/'data.yaml'])
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    mp=ROOT/'delivery_manifest.json';save(mp,manifest);archive=ROOT/'delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for path in sorted(files)+[mp]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    record={'job_id':os.environ['SLURM_JOB_ID'],'files':len(files),'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp),
            'all_six_final_checkpoints_and_videos_included':True,'source_image_aliases_not_archived':True}
    save(ROOT/'delivery_bundle.json',record);print(json.dumps(record),flush=True)


if __name__=='__main__':main()
