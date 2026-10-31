from pathlib import Path, PurePosixPath
import hashlib, json, tarfile
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
record = load(ROOT / 'results/delivery_record.json')
archive = ROOT / 'results/delivery.tar.gz'
assert archive.stat().st_size == record['bytes'] and sha(archive) == record['sha256']
destination = ROOT / 'delivery'
assert not destination.exists()
with tarfile.open(archive, 'r:gz') as tf:
    data = tf.extractfile('delivery_manifest.json').read()
    assert hashlib.sha256(data).hexdigest() == record['manifest_sha256']
    rows = json.loads(data)
    expected = {r['path']: r for r in rows}
    members = tf.getmembers()
    assert len(expected) == record['manifest_files'] == 19
    assert len(members) == record['archive_members'] == 20
    assert {m.name for m in members} == set(expected) | {'delivery_manifest.json'}
    for member in members:
        name = PurePosixPath(member.name)
        assert member.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in member.name
        target = destination.joinpath(*name.parts).resolve()
        assert target.is_relative_to(destination.resolve())
        payload = tf.extractfile(member).read()
        if member.name in expected:
            row = expected[member.name]
            assert len(payload) == row['bytes'] and hashlib.sha256(payload).hexdigest() == row['sha256']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        assert sha(target) == hashlib.sha256(payload).hexdigest()
for name in ['summary.json', 'per_query660.json', 'all_wrong_and_unknown_accepts.json', 'independent_verification.json', 'matched_coverage.json']:
    assert sha(ROOT / 'results' / name) == sha(destination / 'input' / name)
render = load(destination / 'results/render_record.json')
assert render['score_plot_query_condition_points'] == 330 and render['cases'] == 5 and render['image_panels'] == 12
assert len(render['source_images']) == 12
images = []
for row in render['files']:
    path = destination / row['path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    if path.suffix in ['.png', '.jpg']:
        with Image.open(path) as im:
            im.load()
            images.append({'file': row['path'], 'size': im.size, 'full_decode': 'PASS'})
    else:
        text = path.read_text(encoding='utf-8')
        assert '<svg' in text and '</svg>' in text
assert '130002|idcoo-id-risk-fig|COMPLETED|0:0|' in (ROOT / 'results/render_status_01.txt').read_text()
result = {'status': 'ALL19_RENDER_DELIVERY_FILES_SOURCE_HASHES_AND_IMAGE_DECODES_VERIFIED',
          'files': 19, 'bytes': record['bytes'], 'archive_sha256': record['sha256'],
          'plot_query_condition_points': 330, 'all_QAT_accepted_error_cases': 5, 'source_image_panels': 12,
          'image_decodes': images, 'manual_visual_QA': 'pending',
          'new_model_inference_or_training': False, 'whole_goal_complete': False}
target = ROOT / 'results/local_delivery_verification.json'
assert not target.exists()
target.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
