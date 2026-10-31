"""Slurm-only complete image decode, source reconciliation and overlap screen."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, hashlib, io, itertools, json, os, socket, struct, time, zipfile
import numpy as np
import PIL
from PIL import Image, features
import cv2

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def save(path, value):
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def fingerprint(rgb):
    pixel_sha = hashlib.sha256(struct.pack('>II', *rgb.size) + rgb.tobytes()).hexdigest()
    small = np.asarray(rgb.convert('L').resize((9, 8), Image.Resampling.BILINEAR))
    bits = (small[:, 1:] > small[:, :-1]).ravel()
    dh = sum(int(value) << i for i, value in enumerate(bits))
    return pixel_sha, f'{dh:016x}'


def duplicate_groups(records, field):
    index = defaultdict(list)
    for row in records:
        index[row[field]].append(row)
    groups = []
    for value, rows in index.items():
        if len(rows) < 2:
            continue
        groups.append({'fingerprint': value, 'roles': sorted({r['development_role'] for r in rows}),
                       'members': sorted(r['file_name'] for r in rows),
                       'dates': sorted({r['capture_date'] for r in rows})})
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-attempt', required=True, choices=[f'{i:02d}' for i in range(1, 20)])
    parser.add_argument('--audit-attempt', required=True, choices=[f'{i:02d}' for i in range(1, 20)])
    args = parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname() != 'mu01'
    cv2.setNumThreads(1)
    started = time.perf_counter()
    for row in json.loads((ROOT / 'input/staging_file_hashes.json').read_text()):
        path = ROOT / row['path']
        assert path.is_file() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    fetch_path = ROOT / 'input/image_fetch_manifest.json'
    fetch = json.loads(fetch_path.read_text())
    download = ROOT / f'results/download_attempt_{args.download_attempt}'
    status = json.loads((download / 'summary.json').read_text())
    assert status['status'] == 'ALL_8380_DEVELOPMENT_IMAGE_BYTES_STAGED_DECODE_PENDING'
    assert status['saved_images'] == 8380 and status['failed_images'] == 0
    byte_path = download / 'image_manifest.json'
    assert sha(byte_path) == status['image_manifest_sha256']
    byte_rows = json.loads(byte_path.read_text())
    expected = {r['file_name']: r for r in fetch['items']}
    assert len(expected) == len(byte_rows) == 8380 and len({r['file_name'] for r in byte_rows}) == 8380
    dates = {r['file_name']: r for r in json.loads((ROOT / 'input/date_roles.json').read_text())}
    out = ROOT / f'results/image_audit_{args.audit_attempt}'
    out.mkdir(exist_ok=False)
    records, errors = [], []
    for row in byte_rows:
        name = row['file_name']
        wanted = expected[name]
        assert all(row[k] == value for k, value in wanted.items())
        assert row['capture_date'] <= '2020-03-04'
        assert dates[name]['candidate_date_role'] in ['train_candidate', 'validation_development_candidate']
        path = ROOT / row['relative_image_path']
        assert path.resolve().is_relative_to(ROOT / 'raw_images')
        try:
            data = path.read_bytes()
            assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                rgb = image.convert('RGB')
                assert rgb.size == (row['width'], row['height']) == (1280, 720)
                pixel, dh = fingerprint(rgb)
            decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            assert decoded is not None and decoded.shape == (720, 1280, 3)
            records.append({**row, 'RGB_dimensions_prefixed_sha256': pixel,
                            'dHash64_bilinear_L_9x8_hex': dh,
                            'PIL_complete_decode_verified': True, 'OpenCV_complete_decode_verified': True})
        except Exception as exc:
            errors.append({'file_name': name, 'error_type': type(exc).__name__, 'message': str(exc)})
        if (len(records) + len(errors)) % 500 == 0:
            print(json.dumps({'decoded_new_images': len(records), 'errors': len(errors),
                              'elapsed_s': time.perf_counter() - started}), flush=True)
    save(out / 'decode_errors.json', errors)
    save(out / 'decoded_images.json', records)
    if errors:
        save(out / 'summary.json', {'status': 'DECODE_FAILURES_PRESERVED_ADMISSION_NOT_GRANTED',
                                   'decoded_images': len(records), 'errors': len(errors)})
        raise SystemExit(2)
    assert len(records) == 8380

    # Recompute prior RGB fingerprints with exactly this decoder and library.
    # Windows fingerprints remain an explicit cross-platform comparison only.
    prior_path = ROOT / 'input/prior_OpenCows_pixel_index.json'
    prior_windows = json.loads(prior_path.read_text())
    assert len(prior_windows['records']) == 11779
    archive_path = PROJECT / 'data/opencows2020/OpenCows2020.zip'
    assert archive_path.stat().st_size == 2272138852
    assert sha(archive_path) == prior_windows['source_archive_sha256']
    prior_records, pixel_platform_differences, dhash_platform_differences = [], 0, 0
    with zipfile.ZipFile(archive_path) as archive:
        for reference in prior_windows['records']:
            data = archive.read(reference['name'])
            assert len(data) == int(reference['bytes']) and hashlib.sha256(data).hexdigest() == reference['sha256']
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                assert image.size == (int(reference['width']), int(reference['height']))
                pixel, dh = fingerprint(image.convert('RGB'))
            pixel_platform_differences += pixel != reference['RGB_dimensions_prefixed_sha256']
            dhash_platform_differences += dh != reference['dHash64_bilinear_L_9x8_hex']
            prior_records.append({**reference, 'RGB_dimensions_prefixed_sha256': pixel,
                                  'dHash64_bilinear_L_9x8_hex': dh})
    save(out / 'prior_OpenCows_same_decoder_index.json', prior_records)
    exact = duplicate_groups(records, 'sha256')
    pixels = duplicate_groups(records, 'RGB_dimensions_prefixed_sha256')
    cross_members = sorted({name for group in exact + pixels if len(group['roles']) > 1 for name in group['members']})
    prior_bytes, prior_pixels = defaultdict(list), defaultdict(list)
    for row in prior_records:
        prior_bytes[row['sha256']].append(row['name'])
        prior_pixels[row['RGB_dimensions_prefixed_sha256']].append(row['name'])
    reused = []
    for row in records:
        matches_bytes = prior_bytes[row['sha256']]
        matches_pixels = prior_pixels[row['RGB_dimensions_prefixed_sha256']]
        if matches_bytes or matches_pixels:
            reused.append({'file_name': row['file_name'], 'development_role': row['development_role'],
                           'same_bytes_prior_names': matches_bytes, 'same_RGB_prior_names': matches_pixels})
    train_hashes = [(int(row['dHash64_bilinear_L_9x8_hex'], 16), row['file_name'])
                    for row in records if row['development_role'] == 'train']
    near_cross = []
    for row in records:
        if row['development_role'] != 'validation':
            continue
        value = int(row['dHash64_bilinear_L_9x8_hex'], 16)
        for previous, name in train_hashes:
            distance = (value ^ previous).bit_count()
            if distance <= 2:
                near_cross.append({'train': name, 'validation': row['file_name'], 'distance': distance})
    overlap = {'same_bytes_groups': exact, 'same_RGB_groups': pixels,
               'cross_development_role_exact_members_quarantined': cross_members,
               'same_prior_OpenCows_records': reused,
               'cross_development_role_dHash_le2_review_cues': near_cross,
               'dHash_is_source_similarity_screen_only': True,
               'all_temporal_neighbours_or_common_cow_sources_proven_absent': False,
               'Windows_to_Linux_RGB_fingerprint_differences': pixel_platform_differences,
               'Windows_to_Linux_dHash_differences': dhash_platform_differences}
    save(out / 'overlap.json', overlap)
    admitted = [dict(row, admission='quarantine_cross_role_duplicate' if row['file_name'] in cross_members else 'development_image_bytes_and_decode_verified')
                for row in records]
    save(out / 'image_admission_manifest.json', admitted)
    result = {'status': 'ALL_8380_DEVELOPMENT_IMAGES_DECODED_OVERLAP_SCREENED_LABEL_LOADER_PENDING',
              'job_id': os.environ['SLURM_JOB_ID'], 'host': socket.gethostname(),
              'Pillow': PIL.__version__, 'libjpeg': features.version_codec('jpg'), 'OpenCV': cv2.__version__,
              'source_fetch_manifest_sha256': sha(fetch_path), 'byte_manifest_sha256': sha(byte_path),
              'decoded_images_sha256': sha(out / 'decoded_images.json'),
              'admission_manifest_sha256': sha(out / 'image_admission_manifest.json'),
              'decoded_images': len(records), 'decode_errors': 0,
              'roles': dict(Counter(row['development_role'] for row in records)),
              'exact_byte_duplicate_groups': len(exact), 'exact_RGB_duplicate_groups': len(pixels),
              'cross_role_exact_members_quarantined': len(cross_members),
              'prior_OpenCows_same_decoder_images': len(prior_records), 'images_reusing_prior_OpenCows_bytes_or_RGB': len(reused),
              'cross_role_dHash_le2_review_pairs': len(near_cross),
              'Windows_to_Linux_RGB_fingerprint_differences': pixel_platform_differences,
              'Windows_to_Linux_dHash_differences': dhash_platform_differences,
              'candidate_final_image_pixels_accessed': False,
              'final_independent_test_certified': False, 'actual_loader_verified': False,
              'new_model_training_or_forward': False, 'whole_goal_complete': False,
              'elapsed_s': time.perf_counter() - started}
    save(out / 'summary.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
