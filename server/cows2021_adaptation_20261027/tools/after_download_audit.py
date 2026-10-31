"""One bounded handoff from an existing transfer to a CPU-only Slurm audit.

It never retries the transfer or submits training. The running downloader
must become terminal and publish a complete byte manifest before submission.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,socket,subprocess,time

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_DOWNLOAD_COMMAND=str(ROOT/'tools/fetch_images.py')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--download-pid',required=True,type=int)
    parser.add_argument('--download-attempt',required=True,choices=[f'{i:02d}' for i in range(1,20)])
    parser.add_argument('--audit-attempt',required=True,choices=[f'{i:02d}' for i in range(1,20)])
    parser.add_argument('--handoff',required=True,choices=[f'{i:02d}' for i in range(1,20)])
    args=parser.parse_args()
    assert socket.gethostname()=='mu01' and os.environ.get('HOME')=='/share/home/renly'
    assert ROOT==Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
    task=ROOT/f'results/download_handoff_{args.handoff}';task.mkdir(exist_ok=False)
    process=Path('/proc')/str(args.download_pid)
    def transfer_live():
        try:
            command=(process/'cmdline').read_bytes().replace(b'\0',b' ').decode()
            return (process.stat().st_uid==os.getuid() and EXPECTED_DOWNLOAD_COMMAND in command
                    and f'--attempt {args.download_attempt}' in command)
        except (FileNotFoundError,ProcessLookupError):return False
    def save(name,value):
        (task/name).write_text(json.dumps(value,indent=2))
    started=time.monotonic()
    assert transfer_live(),'Original transfer must be verified live when handoff is installed'
    save('process.json',{'PID':os.getpid(),'created_UTC':datetime.now(timezone.utc).isoformat(),
         'download_PID':args.download_pid,'download_attempt':args.download_attempt,
         'deadline_seconds':7200,'audit_attempt':args.audit_attempt,'training_submission_allowed':False})
    while transfer_live():
        if time.monotonic()-started>7200:
            save('summary.json',{'status':'BOUNDED_HANDOFF_DEADLINE_REACHED_TRANSFER_NOT_RESTARTED',
                                 'submitted_job':None,'elapsed_s':time.monotonic()-started})
            raise SystemExit(3)
        time.sleep(20)
    summary_path=ROOT/f'results/download_attempt_{args.download_attempt}/summary.json'
    if not summary_path.exists():
        save('summary.json',{'status':'TRANSFER_PROCESS_TERMINAL_NO_COMPLETE_SUMMARY',
                             'submitted_job':None,'transfer_restarted':False})
        raise SystemExit(2)
    summary=json.loads(summary_path.read_text())
    if summary['status']!='ALL_8380_DEVELOPMENT_IMAGE_BYTES_STAGED_DECODE_PENDING':
        save('summary.json',{'status':'TRANSFER_FAILURE_PRESERVED_WAITING_FOR_TARGETED_RECOVERY',
             'transfer_summary_sha256':sha(summary_path),'transfer_saved':summary['saved_images'],
             'transfer_failed':summary['failed_images'],'submitted_job':None,'transfer_restarted':False})
        raise SystemExit(2)
    assert summary['saved_images']==8380 and summary['failed_images']==0
    manifest_path=summary_path.parent/'image_manifest.json'
    assert sha(manifest_path)==summary['image_manifest_sha256']
    manifest=json.loads(manifest_path.read_text());assert len(manifest)==8380
    expected=json.loads((ROOT/'input/image_fetch_manifest.json').read_text())['items']
    assert {r['file_name'] for r in manifest}=={r['file_name'] for r in expected}
    assert all((ROOT/r['relative_image_path']).is_file() for r in manifest)
    assert not (ROOT/f'results/image_audit_{args.audit_attempt}').exists()
    tools={r['path']:r for r in json.loads((ROOT/'results/auxiliary_tools_v1.json').read_text())}
    for relative in ['tools/audit_images.py','tools/audit.slurm']:
        assert sha(ROOT/relative)==tools[relative]['sha256']
    for title,command in [('live_partitions',['sinfo','-o','%P|%a|%D|%t|%N|%G']),
                          ('current_renly_jobs',['squeue','-u','renly','-o','%.18i|%.9P|%.24j|%.8T|%R'])]:
        response=subprocess.run(command,capture_output=True,text=True,check=True)
        (task/(title+'.txt')).write_text(response.stdout)
    job=subprocess.run(['sbatch','--parsable',str(ROOT/'tools/audit.slurm'),args.download_attempt,args.audit_attempt],
                       capture_output=True,text=True,check=True).stdout.strip()
    assert job.split(';')[0].isdigit()
    result={'status':'COMPLETE_TRANSFER_VERIFIED_CPU_IMAGE_AUDIT_SUBMITTED','job_id':job,
            'transfer_summary_sha256':sha(summary_path),'byte_manifest_sha256':sha(manifest_path),
            'audit_attempt':args.audit_attempt,'submitted_UTC':datetime.now(timezone.utc).isoformat(),
            'training_submitted':False,'audit_completion_verified':False,'whole_goal_complete':False}
    save('summary.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
