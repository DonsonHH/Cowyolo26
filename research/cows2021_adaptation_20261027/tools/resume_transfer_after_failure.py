"""Explicit terminal-failure recovery; never overlaps an existing downloader."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,hashlib,json,os,socket,subprocess

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as file:
        for part in iter(lambda:file.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--previous',required=True,choices=[f'{i:02d}' for i in range(1,19)])
    parser.add_argument('--next',required=True,choices=[f'{i:02d}' for i in range(2,20)])
    args=parser.parse_args();assert int(args.next)==int(args.previous)+1
    assert socket.gethostname()=='mu01' and os.environ['HOME']=='/share/home/renly'
    assert ROOT==Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
    expected=str(ROOT/'tools/fetch_images.py')
    # Inspect real /proc command lines and ownership, not a stale PID record.
    live=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            if proc.stat().st_uid!=os.getuid():continue
            command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if expected in command:live.append({'PID':int(proc.name),'command':command})
        except (PermissionError,FileNotFoundError,ProcessLookupError):continue
    assert not live,live
    previous=ROOT/f'results/download_attempt_{args.previous}'
    summary=json.loads((previous/'summary.json').read_text())
    assert summary['status']=='PARTIAL_IMAGE_TRANSFER_FAILURE' and summary['failed_images']>0
    cached_path=previous/'image_manifest.json';cached=json.loads(cached_path.read_text())
    errors=json.loads((previous/'errors.json').read_text())
    assert len(errors)==summary['failed_images'] and len(cached)==summary['saved_images']
    assert sha(cached_path)==summary['image_manifest_sha256']
    assert len(cached)+len(errors)==8380
    for row in cached:
        path=ROOT/row['relative_image_path'];assert path.resolve().is_relative_to(ROOT/'raw_images')
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
    target=ROOT/f'results/download_attempt_{args.next}';assert not target.exists()
    record_path=ROOT/f'results/transfer_resume_{args.previous}_to_{args.next}.json';assert not record_path.exists()
    command=[str(ROOT.parent/'env/bin/python'),'-u',expected,'--attempt',args.next]
    result={'observed_UTC':datetime.now(timezone.utc).isoformat(),'live_downloader_processes_before_resume':live,
            'prior_summary_sha256':sha(previous/'summary.json'),'prior_failed':len(errors),
            'prior_cached_files_rehashed':len(cached),'previous_attempt':args.previous,'next_attempt':args.next,
            'failure_reasons':dict(Counter(r['error']['type']+': '+r['error']['message'] for r in errors)),
            'default_TLS_verification_preserved':True,'prior_files_or_results_removed':False,
            'command':command,'created_new_model_or_training':False}
    record_path.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
    raise SystemExit(subprocess.run(command,cwd=ROOT).returncode)


if __name__=='__main__':main()
