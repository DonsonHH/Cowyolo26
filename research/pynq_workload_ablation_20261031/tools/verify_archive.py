"""Extract only a terminal, hash-identified board archive into a fresh directory."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, tarfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--archive', required=True, type=Path)
parser.add_argument('--sha256', required=True)
parser.add_argument('--bytes', required=True, type=int)
parser.add_argument('--destination', default='delivery')
parser.add_argument('--result-name', default='board_archive_verification.json')
args = parser.parse_args()
assert args.destination in ('delivery', 'reference_delivery')
assert args.result_name in ('board_archive_verification.json', 'reference_archive_verification.json')
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert args.archive.stat().st_size == args.bytes
assert digest(args.archive) == args.sha256
destination = root / args.destination
assert not destination.exists(), 'Preserve any previous extraction for inspection'
with tarfile.open(args.archive, 'r:*') as archive:
    members = archive.getmembers()
    names = [member.name for member in members]
    assert len(names) == len(set(names))
    for member in members:
        part = PurePosixPath(member.name)
        assert member.isfile() and not part.is_absolute()
        assert all(value not in ('', '.', '..') for value in part.parts)
        assert '\\' not in member.name and ':' not in member.name
    manifest = json.load(archive.extractfile('result_manifest.json'))
    assert set(names) == {row['file'] for row in manifest} | {'result_manifest.json'}
    destination.mkdir()
    for member in members:
        path = destination.joinpath(*PurePosixPath(member.name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(archive.extractfile(member).read())
for row in manifest:
    path = destination / row['file']
    assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
result = {'status': 'TERMINAL_BOARD_ARCHIVE_ALL_MEMBERS_HASH_VERIFIED',
          'archive_sha256': args.sha256, 'archive_bytes': args.bytes,
          'members': len(names), 'manifest_files': len(manifest),
          'new_model_forwards': 0}
output = root / 'results' / args.result_name
output.parent.mkdir(exist_ok=True)
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
