from pathlib import Path
import hashlib,json,os,socket,tarfile

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    result=json.loads((ROOT/'results/control/summary.json').read_text())
    assert result['status']=='FROZEN_THREE_SEED_PAIRED_ORIENTATION_VALIDATION_COMPLETE'
    assert len(result['conditions'])==6 and result['new_training_updates']==0
    files=[]
    for folder in ['tools','protocol','input','results','logs']:
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.name.endswith('.partial'):continue
            if path.name in {f'collect-{os.environ["SLURM_JOB_ID"]}.out',f'collect-{os.environ["SLURM_JOB_ID"]}.err'}:continue
            files.append(path)
    entries=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    index=ROOT/'delivery_manifest.json';assert not index.exists();index.write_text(json.dumps(entries,indent=2))
    archive=ROOT/'delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
        for path in sorted(files)+[index]:tf.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    meta={'job_id':os.environ['SLURM_JOB_ID'],'files':len(entries),'bytes':archive.stat().st_size,
          'sha256':sha(archive),'manifest_sha256':sha(index),'native_full_dataset_images_archived':False,
          'fixed8_validation_overlay_pairs_all3seeds_included':True,'whole_goal_complete':False}
    target=ROOT/'delivery_bundle.json';assert not target.exists();target.write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta),flush=True)


if __name__=='__main__':main()
