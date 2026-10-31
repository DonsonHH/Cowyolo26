from pathlib import Path
import hashlib, json, tarfile
ROOT = Path(__file__).resolve().parents[1]
target = ROOT / 'staging.tar.gz'
assert not target.exists()
files = [ROOT / 'protocol/integer_conv_v1.json', ROOT / '执行计划.md'] + sorted((ROOT / 'tools').glob('*'))
files = [p for p in files if p.is_file()]
with tarfile.open(target, 'w:gz') as archive:
    for path in files:
        archive.add(path, arcname=path.relative_to(ROOT).as_posix())
record = {'files': len(files), 'bytes': target.stat().st_size,
          'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
          'sources': [{'path': p.relative_to(ROOT).as_posix(),
                       'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(ROOT / 'results/staging_record.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in record.items() if k != 'sources'}))
