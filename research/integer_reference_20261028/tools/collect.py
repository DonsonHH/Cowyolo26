from pathlib import Path
import hashlib, json, os, tarfile
ROOT = Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028')
assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
assert not (ROOT / 'results/delivery.tar.gz').exists()
check = json.loads((ROOT / 'results/independent_verification.json').read_text())
assert check['independent_integer_layer_cases'] == check['ORT_full_branch_exact_integer_cases'] == 416
paths = []
for directory in ['tools', 'protocol', 'results/reference', 'logs']:
    paths.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.extend([ROOT / 'results/independent_verification.json', ROOT / '执行计划.md',
              ROOT / 'job_id.txt', ROOT / 'job_id_v2.txt', ROOT / 'verification_job_id.txt'])
paths = sorted(set(paths))
manifest = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
manifest_path = ROOT / 'results/delivery_manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
archive = ROOT / 'results/delivery.tar.gz'
with tarfile.open(archive, 'w:gz') as tf:
    for path in paths:
        tf.add(path, arcname=path.relative_to(ROOT).as_posix())
    tf.add(manifest_path, arcname='delivery_manifest.json')
record = {'files_in_manifest': len(manifest), 'archive_file_members': len(manifest) + 1,
          'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
          'new_training_updates': 0, 'whole_goal_complete': False}
(ROOT / 'results/delivery_record.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record), flush=True)
