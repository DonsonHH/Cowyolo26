"""Fix the development-image inventory from the verified date protocol."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib, json, re, shutil, tarfile

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT.parent / 'cows2021_labels_20261027'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    assert not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def main():
    date_path = LABELS / 'results/date_roles_v1/manifest.json'
    check = json.loads((LABELS / 'results/date_roles_independent_verification.json').read_text(encoding='utf-8'))
    assert check['manifest_sha256'] == sha(date_path) and check['records'] == 10402
    assert check['date_or_original_name_crosses_roles'] is False
    dates = json.loads(date_path.read_text(encoding='utf-8'))
    assert len(dates) == 10402
    source_check = json.loads((LABELS / 'results/source_recovery_independent_verification.json').read_text(encoding='utf-8'))
    assert source_check['source_metadata_sha256'] == sha(LABELS / 'results/source_metadata_all.json')
    source = {r['file_name']: r for r in json.loads((LABELS / 'results/source_metadata_all.json').read_text(encoding='utf-8'))}
    urls = {}
    listing = {'train': 'train_train_image_listing.html.record.json',
               'validation': 'train_val_image_listing.html.record.json',
               'reserved_test': 'reserved_test_image_listing.html.record.json'}
    for role, filename in listing.items():
        links = json.loads((LABELS / 'catalog' / filename).read_text(encoding='utf-8'))['links']
        urls[role] = {url.rsplit('/', 1)[-1]: url for url in links if url.endswith('.jpg')}
    selected = []
    for row in dates:
        candidate = row['candidate_date_role']
        if candidate not in ['train_candidate', 'validation_development_candidate']:
            continue
        name = row['file_name']
        assert re.fullmatch(r'\d{5}\.jpg', name)
        image = source[name]
        assert image['width'] == 1280 and image['height'] == 720
        role = 'train' if candidate == 'train_candidate' else 'validation'
        native = LABELS / 'catalog/train_audit' / name
        selected.append({'file_name': name, 'development_role': role,
                         'candidate_date_role': candidate, 'published_role': row['published_role'],
                         'capture_date': row['capture_date'], 'source_block': row['source_block'],
                         'original_filename': row['original_filename'], 'source_XML_sha256': row['XML_sha256'],
                         'width': 1280, 'height': 720, 'url': urls[row['published_role']][name],
                         'relative_image_path': f'raw_images/{role}/{name}',
                         'previous_train_sample_sha256': sha(native) if native.exists() else None})
    assert len(selected) == 8380 and len({r['file_name'] for r in selected}) == 8380
    assert Counter(r['development_role'] for r in selected) == {'train': 6809, 'validation': 1571}
    assert all(r['capture_date'] <= '2020-03-04' for r in selected)
    protocol = {'name': 'Cows2021 date-grouped development-image admission v1',
                'created_UTC': datetime.now(timezone.utc).isoformat(),
                'source_date_manifest_sha256': sha(date_path),
                'source_date_verification_sha256': sha(LABELS / 'results/date_roles_independent_verification.json'),
                'source_metadata_sha256': sha(LABELS / 'results/source_metadata_all.json'),
                'class': 'cow body; image-clipped rotated polygon envelope, mapped to class0',
                'source_pixels': 'Official native JPEG; no model-generated labels or source-video pseudo-labels',
                'selected_counts': {'train': 6809, 'validation': 1571},
                'unaccessed_development_reserve_images': 1400,
                'unaccessed_candidate_final_date_images': 622,
                'candidate_final_dates': ['2020-03-10', '2020-03-11'],
                'download': {'workers': 6, 'attempts_per_missing_file': 3, 'maximum_image_bytes': 8 * 1024 * 1024,
                             'TLS_certificate_and_hostname_verification': True},
                'admission_rules': [
                    'All selected bytes and source URLs recorded, dimensions and complete decode checked in Slurm',
                    'Cross-role exact byte or RGB duplicates quarantine every member, without moving roles',
                    'Within-role duplicate groups retained explicitly and counted as groups, not independent sources',
                    'Prior OpenCows exact/RGB matches recorded as reused development material',
                    'dHash distance is a review cue only; no automatic claim of a common event or identity',
                    'Actual labels reloaded with the locked Ultralytics environment before training',
                    'No candidate-final image access, model scoring, or final independence certification in this stage'],
                'model_training_or_inference_started': False,
                'final_independent_test_certified': False}
    save(ROOT / 'protocol/data_admission_v1.json', protocol)
    save(ROOT / 'input/image_fetch_manifest.json', {'protocol_sha256': sha(ROOT / 'protocol/data_admission_v1.json'),
                                                 'items': selected})
    copies = {
        'results/label_audit/derived_box_catalog.json': 'input/derived_box_catalog.json',
        'results/source_metadata_all.json': 'input/source_metadata_all.json',
        'results/date_roles_v1/manifest.json': 'input/date_roles.json',
        'results/source_recovery_independent_verification.json': 'input/source_verification.json',
        'results/date_roles_independent_verification.json': 'input/date_verification.json',
        'results/full_XML_JSON_geometry_comparison.json': 'input/XML_JSON_comparison.json',
        'results/prior_OpenCows_pixel_index.json': 'input/prior_OpenCows_pixel_index.json',
        'catalog/train_annotations.json': 'input/annotations/train.json',
        'catalog/validation_annotations.json': 'input/annotations/validation.json',
        'catalog/reserved_test_annotations.json': 'input/annotations/reserved_test.json'}
    for source_path, destination in copies.items():
        target = ROOT / destination
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LABELS / source_path, target)
        assert sha(target) == sha(LABELS / source_path)
    snapshot = sorted(p for folder in ['input', 'protocol', 'tools'] for p in (ROOT / folder).rglob('*') if p.is_file())
    manifest = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in snapshot]
    save(ROOT / 'input/staging_file_hashes.json', manifest)
    bundle = ROOT / 'staging_metadata.tar.gz'
    assert not bundle.exists()
    with tarfile.open(bundle, 'w:gz') as archive:
        for path in snapshot + [ROOT / 'input/staging_file_hashes.json']:
            archive.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
    save(ROOT / 'results/staging_metadata.json', {'bundle': bundle.name, 'bytes': bundle.stat().st_size,
         'sha256': sha(bundle), 'selected_images': len(selected), 'counts': protocol['selected_counts'],
         'selected_published_roles': dict(Counter(r['published_role'] for r in selected)),
         'image_fetch_manifest_sha256': sha(ROOT / 'input/image_fetch_manifest.json'),
         'new_image_pixels_downloaded_by_builder': False, 'new_training_or_forward': False})
    print((ROOT / 'results/staging_metadata.json').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
