"""Freeze a reproducibility bundle after replay, excluding native dataset images."""
from pathlib import Path
import json,os,socket,tarfile
from common import ROOT,sha,save


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    inference=json.loads((ROOT/'results/inference/summary.json').read_text())
    assert inference['status']=='THREE_COWS2021_MODELS_SOURCE_AND_KNOWN_DIAGNOSTIC_COMPLETE'
    assert len(inference['conditions'])==3
    files=[]
    for folder in ['tools','protocol','logs','results']:
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:continue
            if path.name in {f'collect-{os.environ["SLURM_JOB_ID"]}.out',f'collect-{os.environ["SLURM_JOB_ID"]}.err'}:continue
            if path.suffix=='.pt' and path.name!='last.pt':continue
            if path.suffix.lower() in ['.jpg','.jpeg','.png'] and 'inference' not in path.parts:continue
            files.append(path)
    files.extend([ROOT/'data_v1/data.yaml',ROOT/'input/image_fetch_manifest.json'])
    assert len(files)==len(set(files))
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    index=ROOT/'delivery_manifest.json';assert not index.exists();save(index,manifest)
    archive=ROOT/'delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
        for path in sorted(files)+[index]:tf.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    record={'job_id':os.environ['SLURM_JOB_ID'],'files':len(files),'bytes':archive.stat().st_size,
            'sha256':sha(archive),'manifest_sha256':sha(index),'all_three_last_checkpoints_and_replays_included':True,
            'native_training_or_candidate_final_images_archived':False,'whole_goal_complete':False}
    save(ROOT/'delivery_bundle.json',record);print(json.dumps(record),flush=True)


if __name__=='__main__':main()
