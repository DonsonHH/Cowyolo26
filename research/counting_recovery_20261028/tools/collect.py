from pathlib import Path
import hashlib,json,os,tarfile
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028')
assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname()!='mu01'
summary=json.loads((ROOT/'results/replay_v2/summary.json').read_text())
check=json.loads((ROOT/'results/independent_verification.json').read_text())
assert check['baseline_exact_regressions']==1 and len(check['conditions'])==10
extension=json.loads((ROOT/'results/full640_confirmation/summary.json').read_text())
selected=[r['name'] for r in summary['conditions']+extension['conditions'] if r['arm']['name'] in ['full640_5hz','channel320_25hz']]
assert len(selected)==4
archive=ROOT/'results/delivery.tar.gz';assert not archive.exists()
paths=[];omitted=[]
for directory in ['tools','protocol','input','results/replay_v2','results/full640_confirmation']:
    for path in (ROOT/directory).rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:continue
        if path.name=='transfer.mp4' and path.parent.name not in selected:omitted.append(path.relative_to(ROOT).as_posix());continue
        paths.append(path)
paths.extend(p for p in (ROOT/'logs').glob('*') if p.is_file() and not p.name.startswith('collect-'+os.environ['SLURM_JOB_ID']))
paths.extend(ROOT/p for p in ['results/independent_verification.json','job_id.txt','retry_job_id.txt','verify_job_id.txt','full640_job_id.txt'])
paths=sorted(set(paths))
manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
mp=ROOT/'results/delivery_manifest.json';mp.write_text(json.dumps(manifest,indent=2))
with tarfile.open(archive,'w:gz') as tf:
    for p in paths:tf.add(p,arcname=p.relative_to(ROOT).as_posix())
    tf.add(mp,arcname='delivery_manifest.json')
record={'manifest_files':len(manifest),'archive_members':len(manifest)+1,'bytes':archive.stat().st_size,
    'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),
    'three_seed_full640_and_dense_diagnostic_transfer_videos':selected,'other_full_videos_retained_remote_not_downloaded':omitted,
    'all_traces_snapshots_and_results_included':True,'active_collection_logs_excluded':True,'whole_goal_complete':False}
(ROOT/'results/delivery_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
