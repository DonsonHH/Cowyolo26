"""Network-only staging on mu01; complete image decoding belongs to Slurm."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse
import argparse, concurrent.futures, hashlib, json, os, socket, threading, time
import requests

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    temporary = path.with_name(path.name + '.partial')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True, choices=[f'{i:02d}' for i in range(1, 20)])
    args = parser.parse_args()
    assert socket.gethostname() == 'mu01' and os.environ.get('HOME') == '/share/home/renly'
    assert ROOT == Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
    fetch_path = ROOT / 'input/image_fetch_manifest.json'
    manifest = json.loads(fetch_path.read_text(encoding='utf-8'))
    pp = ROOT / 'protocol/data_admission_v1.json'
    protocol = json.loads(pp.read_text(encoding='utf-8'))
    assert digest(pp) == manifest['protocol_sha256']
    items = manifest['items']
    assert len(items) == 8380 and Counter(r['development_role'] for r in items) == {'train': 6809, 'validation': 1571}
    out = ROOT / f'results/download_attempt_{args.attempt}'
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    local = threading.local()
    limit = protocol['download']['maximum_image_bytes']
    for name in ['train', 'validation']:
        (ROOT / 'raw_images' / name).mkdir(parents=True, exist_ok=True)

    def task(row):
        path = ROOT / row['relative_image_path']
        assert path.resolve().is_relative_to(ROOT / 'raw_images')
        assert urlparse(row['url']).scheme == 'https' and urlparse(row['url']).hostname == 'data.bris.ac.uk'
        if not hasattr(local, 'session'):
            local.session = requests.Session()
            local.session.trust_env = False
            local.session.headers['User-Agent'] = 'CattleResearch-public-development-images/1.0'
        error = None
        for attempt in range(protocol['download']['attempts_per_missing_file']):
            try:
                existed = path.exists()
                if not existed:
                    with local.session.get(row['url'], timeout=(10, 30), stream=True) as response:
                        response.raise_for_status()
                        endpoint = urlparse(response.url)
                        assert endpoint.scheme == 'https' and endpoint.hostname == 'data.bris.ac.uk'
                        temporary = path.with_name(path.name + '.partial')
                        length = 0
                        with temporary.open('wb') as file:
                            for chunk in response.iter_content(128 * 1024):
                                length += len(chunk)
                                assert length <= limit
                                file.write(chunk)
                        assert 0 < length <= limit
                        with temporary.open('rb') as file:
                            assert file.read(2) == b'\xff\xd8', 'Payload is not a JPEG byte stream'
                        expected = row['previous_train_sample_sha256']
                        assert expected is None or digest(temporary) == expected
                        temporary.replace(path)
                actual_sha = digest(path)
                assert 0 < path.stat().st_size <= limit
                assert row['previous_train_sample_sha256'] is None or actual_sha == row['previous_train_sample_sha256']
                return {**row, 'bytes': path.stat().st_size, 'sha256': actual_sha,
                        'reused_existing_bytes': existed, 'complete_decode_verified': False}
            except Exception as exc:
                error = {'type': type(exc).__name__, 'message': str(exc)}
                if attempt + 1 < protocol['download']['attempts_per_missing_file']:
                    time.sleep(1 + 2 * attempt)
        return {'file_name': row['file_name'], 'development_role': row['development_role'],
                'url': row['url'], 'error': error}

    records, errors = [], []
    save(out / 'process.json', {'PID': os.getpid(), 'host': socket.gethostname(),
                               'created_UTC': datetime.now(timezone.utc).isoformat(),
                               'image_fetch_manifest_sha256': digest(fetch_path)})
    with concurrent.futures.ThreadPoolExecutor(max_workers=protocol['download']['workers']) as pool:
        futures = [pool.submit(task, row) for row in items]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            (errors if 'error' in result else records).append(result)
            done = len(records) + len(errors)
            if done % 100 == 0 or done == len(items):
                progress = {'status': 'DOWNLOADING_DEVELOPMENT_IMAGES' if done < len(items) else 'TRANSFERS_TERMINAL',
                            'expected_images': len(items), 'saved_images': len(records), 'failed_images': len(errors),
                            'elapsed_s': time.perf_counter() - started,
                            'complete_decode_or_training_started': False, 'candidate_final_pixels_accessed': False}
                save(out / 'progress.json', progress)
                print(json.dumps(progress), flush=True)
    records.sort(key=lambda row: row['file_name'])
    save(out / 'image_manifest.json', records)
    save(out / 'errors.json', errors)
    summary = {'status': 'ALL_8380_DEVELOPMENT_IMAGE_BYTES_STAGED_DECODE_PENDING' if not errors else 'PARTIAL_IMAGE_TRANSFER_FAILURE',
               'saved_images': len(records), 'failed_images': len(errors),
               'roles': dict(Counter(r['development_role'] for r in records)),
               'total_image_bytes': sum(r['bytes'] for r in records),
               'image_manifest_sha256': digest(out / 'image_manifest.json'),
               'elapsed_s': time.perf_counter() - started,
               'complete_decode_verified': False, 'candidate_final_pixels_accessed': False,
               'new_training_or_forward': False, 'whole_goal_complete': False}
    save(out / 'summary.json', summary)
    print(json.dumps(summary), flush=True)
    raise SystemExit(0 if not errors else 2)


if __name__ == '__main__':
    main()
