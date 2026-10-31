from pathlib import Path
import hashlib, json, os, tarfile
ROOT = Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028')
assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
verification = json.loads((ROOT / 'results/optimizer_independent_verification.json').read_text())
assert verification['both_controlled_paths_exact_OFF_output'] is True
archive_path = ROOT / 'results/optimizer_delivery.tar.gz'
assert not archive_path.exists()
files = []
for folder in ['results/optimizer_probe', 'results/optimizer_isolation']:
    files.extend(p for p in (ROOT / folder).rglob('*') if p.is_file())
files.extend(p for p in (ROOT / 'tools').glob('*optimizer*') if p.is_file())
files.extend(p for p in (ROOT / 'protocol').glob('optimizer*.json'))
files.extend(p for p in (ROOT / 'logs').glob('optimizer-*') if p.is_file()
             and not p.name.startswith('optimizer-collect-' + os.environ['SLURM_JOB_ID']))
files.extend(ROOT / p for p in ['results/optimizer_independent_verification.json',
             'results/optimizer_independent_metrics.json', 'optimizer_probe_job_id.txt',
             'optimizer_isolation_job_id.txt', 'optimizer_verify_job_id.txt',
             'results/reference/integer_accumulator_candidate.onnx',
             'results/reference/whole_model_vectors.npz', 'results/reference/summary.json'])
files = sorted(set(files))
manifest = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
manifest_path = ROOT / 'results/optimizer_delivery_manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
with tarfile.open(archive_path, 'w:gz') as tf:
    for path in files:
        tf.add(path, arcname=path.relative_to(ROOT).as_posix())
    tf.add(manifest_path, arcname='optimizer_delivery_manifest.json')
record = {'manifest_files': len(manifest), 'archive_members': len(manifest) + 1,
          'bytes': archive_path.stat().st_size, 'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
          'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
          'running_collection_logs_excluded': True, 'new_training_updates': 0,
          'whole_goal_complete': False}
(ROOT / 'results/optimizer_delivery_record.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record), flush=True)
