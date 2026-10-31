from pathlib import Path
import hashlib, json, os, shutil, tarfile
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_qat_20261028'
assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
check = json.loads((ROOT / 'results/independent_verification.json').read_text())
assert len(check['conditions']) == 12 and check['formal_QAT_updates'] == 360
assert not (ROOT / 'results/delivery.tar.gz').exists()
snapshots = ROOT / 'input_code'
snapshots.mkdir(exist_ok=False)
for folder, names in [('integer_trainable_20261028/tools', ['integer_trainable.py', 'export_integer.py', 'smoke.py']),
                      ('qat_study/tools', ['qat_components.py']),
                      ('identity_training/tools', ['training_primitives.py', 'identity_metrics.py'])]:
    for name in names: shutil.copyfile(PROJECT / folder / name, snapshots / name)
paths = []
for folder in ['tools', 'protocol', 'results/study', 'input_code']:
    paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.extend(p for p in (ROOT / 'logs').glob('*') if p.is_file() and not p.name.startswith('collect-' + os.environ['SLURM_JOB_ID']))
paths.extend(ROOT / p for p in ['results/independent_verification.json', '执行计划.md', 'train_job_id.txt', 'verify_job_id.txt'])
paths = sorted(set(paths))
manifest = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
mp = ROOT / 'results/delivery_manifest.json'
mp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
archive = ROOT / 'results/delivery.tar.gz'
with tarfile.open(archive, 'w:gz') as tf:
    for path in paths: tf.add(path, arcname=path.relative_to(ROOT).as_posix())
    tf.add(mp, arcname='delivery_manifest.json')
record = {'manifest_files': len(manifest), 'archive_members': len(manifest) + 1,
          'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'manifest_sha256': hashlib.sha256(mp.read_bytes()).hexdigest(),
          'running_collection_logs_excluded': True, 'formal_QAT_updates': 360, 'paired_float_updates': 360,
          'whole_goal_complete': False}
(ROOT / 'results/delivery_record.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record), flush=True)
