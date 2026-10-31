"""Build isolated detection aliases and actual-loader checks after image audit."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, hashlib, json, math, os, socket
import numpy as np
import ultralytics
from ultralytics.cfg import get_cfg
from ultralytics.data.build import build_yolo_dataset
from ultralytics.data.utils import check_det_dataset

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda: file.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def corners(box):
    x, y, width, height, angle = map(float, box)
    centre = [x + width / 2, y + height / 2]
    cosine, sine = math.cos(angle), math.sin(angle)
    return [(centre[0] + dx * cosine - dy * sine, centre[1] + dx * sine + dy * cosine)
            for dx, dy in [(-width / 2, -height / 2), (width / 2, -height / 2),
                           (width / 2, height / 2), (-width / 2, height / 2)]]


def independent_envelope(box, width, height):
    # Enumerate vertices and line intersections with image edges rather than
    # importing the earlier clipping implementation.
    polygon = corners(box)
    points = [(x, y) for x, y in polygon if 0 <= x <= width and 0 <= y <= height]
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        for axis, boundary in [(0, 0), (0, width), (1, 0), (1, height)]:
            if a[axis] == b[axis]:
                continue
            t = (boundary - a[axis]) / (b[axis] - a[axis])
            if 0 <= t <= 1:
                p = [a[i] + t * (b[i] - a[i]) for i in [0, 1]]
                p[axis] = boundary
                if -1e-8 <= p[0] <= width + 1e-8 and -1e-8 <= p[1] <= height + 1e-8:
                    points.append(tuple(p))
    def inside(point):
        cross = [(b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])
                 for a, b in zip(polygon, polygon[1:] + polygon[:1])]
        return all(v >= -1e-9 for v in cross) or all(v <= 1e-9 for v in cross)
    points += [p for p in [(0, 0), (width, 0), (width, height), (0, height)] if inside(p)]
    assert points
    xs, ys = zip(*points)
    return [min(xs), min(ys), max(xs), max(ys)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit-attempt', required=True, choices=[f'{i:02d}' for i in range(1, 20)])
    parser.add_argument('--output-tag', default='v1')
    args = parser.parse_args()
    assert args.output_tag.replace('_', '').isalnum()
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname() != 'mu01'
    assert ultralytics.__version__ == '8.4.63'
    audit = ROOT / f'results/image_audit_{args.audit_attempt}'
    summary = json.loads((audit / 'summary.json').read_text())
    assert summary['status'] == 'ALL_8380_DEVELOPMENT_IMAGES_DECODED_OVERLAP_SCREENED_LABEL_LOADER_PENDING'
    admission_path = audit / 'image_admission_manifest.json'
    assert sha(admission_path) == summary['admission_manifest_sha256']
    images = json.loads(admission_path.read_text())
    assert len(images) == 8380
    catalog = json.loads((ROOT / 'input/derived_box_catalog.json').read_text())
    labels = defaultdict(list)
    published = {}
    for split in ['train', 'validation', 'reserved_test']:
        source = json.loads((ROOT / f'input/annotations/{split}.json').read_text())
        for row in source['annotations']:
            published[(split, row['id'])] = row
    max_envelope_difference = 0.
    for row in catalog:
        assert row['valid'] and row['derived_class'] == 0
        original = published[(row['role'], row['annotation_id'])]
        assert original['bbox'] == row['bbox_xywh_angle_radians']
        envelope = independent_envelope(original['bbox'], 1280, 720)
        max_envelope_difference = max(max_envelope_difference,
                                      max(abs(a - b) for a, b in zip(envelope, row['axis_box_xyxy'])))
        assert max(abs(a - b) for a, b in zip(envelope, row['axis_box_xyxy'])) < 1e-8
        x1, y1, x2, y2 = envelope
        values = [0, (x1 + x2) / 2560, (y1 + y2) / 1440, (x2 - x1) / 1280, (y2 - y1) / 720]
        assert np.allclose(values, row['yolo_class_cxcywh'], rtol=0, atol=1e-10)
        labels[row['file_name']].append((row['annotation_id'], row['yolo_class_cxcywh']))
    data = ROOT / f'data_{args.output_tag}'
    data.mkdir(exist_ok=False)
    out = ROOT / f'results/labels_{args.output_tag}'
    out.mkdir(exist_ok=False)
    records, quarantine = [], []
    for row in sorted(images, key=lambda r: r['file_name']):
        if row['admission'] == 'quarantine_cross_role_duplicate':
            quarantine.append(row)
            continue
        assert row['admission'] == 'development_image_bytes_and_decode_verified'
        source = ROOT / row['relative_image_path']
        assert source.is_file() and source.stat().st_size == row['bytes'] and sha(source) == row['sha256']
        split = 'train' if row['development_role'] == 'train' else 'val'
        image_dir = data / 'images' / split
        label_dir = data / 'labels' / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        alias = image_dir / row['file_name']
        alias.symlink_to(source)
        assert alias.resolve() == source.resolve()
        ordered = sorted(labels[row['file_name']])
        lines = ['0 ' + ' '.join(f'{v:.9f}' for v in values[1:]) for _, values in ordered]
        assert lines
        text = '\n'.join(lines) + '\n'
        label = label_dir / (Path(row['file_name']).stem + '.txt')
        label.write_text(text)
        expected = np.asarray([list(map(float, line.split())) for line in lines], dtype=np.float32)
        assert np.isfinite(expected).all() and (expected[:, 3:] > 0).all()
        assert (expected[:, 1:] >= 0).all() and (expected[:, 1:] <= 1).all()
        assert len(np.unique(expected, axis=0)) == len(expected)
        records.append({**row, 'actual_split': split, 'image_alias': str(alias),
                        'label_path': str(label), 'label_sha256': sha(label),
                        'published_annotation_IDs': [r[0] for r in ordered],
                        'expected_float32_rows': expected.tolist()})
    yaml = data / 'data.yaml'
    yaml.write_text(f'path: {data}\ntrain: images/train\nval: images/val\nnames:\n  0: cow\n')
    save(out / 'prepared_image_label_manifest.json', records)
    save(out / 'quarantined_images.json', quarantine)
    config = get_cfg(overrides={'task': 'detect', 'mode': 'train', 'imgsz': 320, 'batch': 32,
                                'cache': False, 'workers': 2})
    actual_data = check_det_dataset(yaml, autodownload=False)
    loader_results = []
    for mode, split in [('train', 'train'), ('val', 'val')]:
        dataset = build_yolo_dataset(config, str(data / 'images' / split), 32,
                                     actual_data, mode=mode, rect=(mode == 'val'), stride=32)
        expected = {r['image_alias']: r for r in records if r['actual_split'] == split}
        assert len(dataset) == len(expected) and set(dataset.im_files) == set(expected)
        count = 0
        for label in dataset.labels:
            record = expected[label['im_file']]
            actual = np.concatenate([label['cls'], label['bboxes']], axis=1)
            wanted = np.asarray(record['expected_float32_rows'], dtype=np.float32)
            assert actual.shape == wanted.shape and np.array_equal(actual, wanted)
            assert label['normalized'] is True and label['bbox_format'] == 'xywh'
            count += len(actual)
        loader_results.append({'split': split, 'images': len(dataset), 'actual_loaded_annotation_rows': count})
    result = {'status': 'DERIVED_LABELS_AND_REAL_ULTRALYTICS_LOADER_PASS',
              'job_id': os.environ['SLURM_JOB_ID'], 'created_UTC': datetime.now(timezone.utc).isoformat(),
              'Ultralytics': ultralytics.__version__, 'data_yaml': str(yaml), 'data_yaml_sha256': sha(yaml),
              'prepared_manifest_sha256': sha(out / 'prepared_image_label_manifest.json'),
              'source_image_audit_sha256': sha(audit / 'summary.json'),
              'loader_results': loader_results, 'quarantined_images': len(quarantine),
              'all_13165_metadata_geometries_recomputed_max_difference_pixels': max_envelope_difference,
              'dHash_candidate_review_still_pending': summary['cross_role_dHash_le2_review_pairs'] > 0,
              'candidate_final_image_pixels_accessed': False, 'final_independent_test_certified': False,
              'new_model_training_or_forward': False, 'whole_goal_complete': False}
    save(out / 'summary.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
