"""Compare only the 12 previously fixed train samples against all prior pixels."""
from pathlib import Path
from PIL import Image
from collections import defaultdict
import hashlib, json
from index_prior_images import fingerprint

ROOT = Path(__file__).resolve().parents[1]


def main():
    prior_path = ROOT / 'results/prior_OpenCows_pixel_index.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    assert prior['status'] == 'ALL_11779_PRIOR_OPEN_COWS_BYTES_AND_RGB_PIXELS_INDEXED'
    assert len(prior['records']) == 11779
    byte_hash = defaultdict(list)
    pixel_hash = defaultdict(list)
    hashes = []
    for record in prior['records']:
        byte_hash[record['sha256']].append(record['name'])
        pixel_hash[record['RGB_dimensions_prefixed_sha256']].append(record['name'])
        hashes.append((int(record['dHash64_bilinear_L_9x8_hex'], 16), record))
    protocol_path = ROOT / 'protocol/cows_labels_v1.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    records = []
    for selected in protocol['selected']:
        name = selected['image']['file_name']
        path = ROOT / 'catalog/train_audit' / name
        data_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as image:
            image.load()
            pixel_sha, dh = fingerprint(image.convert('RGB'))
        near = sorted(((int(dh, 16) ^ h).bit_count(), r['name'], r['group'], r['split'])
                      for h, r in hashes)[:3]
        records.append({'file_name': name, 'byte_sha256': data_sha,
                        'RGB_dimensions_prefixed_sha256': pixel_sha,
                        'same_bytes_prior_images': byte_hash[data_sha],
                        'same_RGB_prior_images': pixel_hash[pixel_sha],
                        'closest_dHash_review_cues': [dict(zip(['distance', 'name', 'group', 'split'], r)) for r in near]})
    target = ROOT / 'results/train_sample_prior_pixel_overlap.json'
    assert not target.exists()
    result = {'status': 'FIXED_12_TRAIN_SAMPLES_COMPARED_WITH_11779_PRIOR_IMAGES',
              'prior_index_sha256': hashlib.sha256(prior_path.read_bytes()).hexdigest(),
              'sample_protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
              'sample_count': len(records),
              'samples_with_same_bytes': sum(bool(r['same_bytes_prior_images']) for r in records),
              'samples_with_same_RGB': sum(bool(r['same_RGB_prior_images']) for r in records),
              'dHash_is_only_a_review_cue': True,
              'full_Cows2021_dataset_independence_established': False,
              'new_validation_or_test_pixels_opened': False,
              'new_model_forward_or_training': False, 'records': records}
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}), flush=True)


if __name__ == '__main__':
    main()
