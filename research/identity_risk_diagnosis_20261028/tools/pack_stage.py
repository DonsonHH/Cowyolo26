from pathlib import Path
import hashlib, json, tarfile
ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / 'staging.tar.gz'
assert not archive.exists()
paths = [('results/' + name, 'input/' + name) for name in ['summary.json', 'per_query660.json',
         'all_wrong_and_unknown_accepts.json', 'independent_verification.json', 'matched_coverage.json']]
paths.extend((p.relative_to(ROOT).as_posix(), p.relative_to(ROOT).as_posix()) for folder in ['tools', 'protocol']
             for p in (ROOT / folder).glob('*') if p.is_file())
manifest = [{'path': target, 'sha256': hashlib.sha256((ROOT / source).read_bytes()).hexdigest()} for source, target in paths]
manifest_path = ROOT / 'input_manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
with tarfile.open(archive, 'w:gz') as tf:
    for source, target in paths: tf.add(ROOT / source, arcname=target)
    tf.add(manifest_path, arcname='input_manifest.json')
record = {'files': len(paths) + 1, 'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
(ROOT / 'results/staging_record.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record))
