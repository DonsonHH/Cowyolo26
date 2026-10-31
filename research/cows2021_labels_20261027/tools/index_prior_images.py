"""Build a decoded-pixel reference for previously accessed OpenCows images.

No Cows2021 candidate holdout image is opened. A dHash is only a review cue.
"""
from pathlib import Path
from PIL import Image
from collections import Counter
import csv, hashlib, io, json, struct, time, zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
ARCHIVE = Path(r'C:\Users\Donson\Downloads\10m32xl88x2b61zlkkgz3fml17.zip\10m32xl88x2b61zlkkgz3fml17.zip')
MANIFEST = PROJECT / 'data_audit_20261026/local_opencows/image_manifest.csv'
EXPECTED_ARCHIVE_SHA = '53c437eb2e383092967d218655afac74a20403850ab9dde1d136a570d948362c'


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def fingerprint(rgb):
    pixel_sha = hashlib.sha256(struct.pack('>II', *rgb.size) + rgb.tobytes()).hexdigest()
    small = list(rgb.convert('L').resize((9, 8), Image.Resampling.BILINEAR).getdata())
    bits = [small[y * 9 + x + 1] > small[y * 9 + x] for y in range(8) for x in range(8)]
    dh = sum(int(value) << i for i, value in enumerate(bits))
    return pixel_sha, f'{dh:016x}'


def main():
    target = ROOT / 'results/prior_OpenCows_pixel_index.json'
    assert not target.exists()
    started = time.perf_counter()
    assert ARCHIVE.stat().st_size == 2272138852 and sha_file(ARCHIVE) == EXPECTED_ARCHIVE_SHA
    rows = list(csv.DictReader(MANIFEST.open(encoding='utf-8-sig', newline='')))
    assert len(rows) == 11779
    records = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for row in rows:
            data = archive.read(row['name'])
            assert len(data) == int(row['bytes']) and hashlib.sha256(data).hexdigest() == row['sha256']
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                rgb = image.convert('RGB')
                assert rgb.size == (int(row['width']), int(row['height']))
                pixel_sha, dh = fingerprint(rgb)
            records.append({**row, 'RGB_dimensions_prefixed_sha256': pixel_sha,
                            'dHash64_bilinear_L_9x8_hex': dh})
            if len(records) % 1000 == 0:
                print(json.dumps({'verified_prior_images': len(records), 'total': len(rows),
                                  'elapsed_s': time.perf_counter() - started}), flush=True)
    result = {'status': 'ALL_11779_PRIOR_OPEN_COWS_BYTES_AND_RGB_PIXELS_INDEXED',
              'source_archive_sha256': EXPECTED_ARCHIVE_SHA,
              'source_manifest_sha256': sha_file(MANIFEST),
              'images': len(records), 'groups': dict(Counter(r['group'] for r in records)),
              'pixel_fingerprint': 'SHA256(big-endian uint32 width,height + RGB uint8 row-major bytes)',
              'dHash_scope': 'Screening only, not proof of a common event, cow identity or source session',
              'Cows2021_image_pixels_opened': False, 'new_model_forward_or_training': False,
              'records': records, 'elapsed_s': time.perf_counter() - started}
    partial = target.with_suffix('.json.partial')
    partial.write_text(json.dumps(result, indent=2), encoding='utf-8')
    partial.replace(target)
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}), flush=True)


if __name__ == '__main__':
    main()
