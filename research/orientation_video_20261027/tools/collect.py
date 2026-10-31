from pathlib import Path
import hashlib,json,os,socket,tarfile

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    summary=json.loads((ROOT/'results/inference/summary.json').read_text())
    assert summary['status']=='SIX_VIDEO_ROTATION_CONDITIONS_COMPLETE_ORIGINAL_TRACES_REPRODUCED'
    assert len(summary['conditions'])==6 and summary['new_training_updates']==0
    files=[];omitted=[]
    for folder in ['input','protocol','tools','results','logs']:
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.name.endswith('.partial'):continue
            if path.name in {f'collect-{os.environ["SLURM_JOB_ID"]}.out',f'collect-{os.environ["SLURM_JOB_ID"]}.err'}:continue
            if path.name=='source_transfer.mp4' and path.parent.name.startswith('original_'):
                omitted.append(path.relative_to(ROOT).as_posix());continue
            files.append(path)
    entries=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    index=ROOT/'delivery_manifest.json';assert not index.exists();index.write_text(json.dumps(entries,indent=2))
    archive=ROOT/'delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for path in sorted(files)+[index]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    record={'job_id':os.environ['SLURM_JOB_ID'],'files':len(entries),'bytes':archive.stat().st_size,
            'sha256':sha(archive),'manifest_sha256':sha(index),'omitted_original_source_videos':omitted,
            'omission_reason':'All exact original track/event regressions passed; retain previous original3verified previews and all new traces/snapshots',
            'clockwise90_source_videos_included':3,'native_full_inputs_or_weight_files_archived':False,'whole_goal_complete':False}
    path=ROOT/'delivery_bundle.json';assert not path.exists();path.write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)


if __name__=='__main__':main()
