"""Measure every published JSON rectangle against its source XML rectangles.

Preserve rounding/representation differences and count conflicts. This does
not repair labels or approve an image for model training automatically.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, itertools, json, math, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REVIEW_CUE_PIXELS = 2.0  # review cue only, never a widened acceptance tolerance


def rectangle(cx, cy, width, height, angle):
    radius = math.hypot(width, height) / 2
    phi = math.atan2(height, width)
    return [(cx + radius * math.cos(angle + a), cy + radius * math.sin(angle + a))
            for a in [phi, math.pi - phi, math.pi + phi, -phi]]


def vertex_error(first, second):
    values = []
    for order in [second, list(reversed(second))]:
        for i in range(4):
            shifted = order[i:] + order[:i]
            values.append(max(math.dist(a, b) for a, b in zip(first, shifted)))
    return min(values)


def main():
    verification = json.loads((ROOT / 'results/source_recovery_independent_verification.json').read_text(encoding='utf-8'))
    metadata_path = ROOT / 'results/source_metadata_all.json'
    assert hashlib.sha256(metadata_path.read_bytes()).hexdigest() == verification['source_metadata_sha256']
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    assert len(metadata) == 10402
    by_file = defaultdict(list)
    for role in ['train', 'validation', 'reserved_test']:
        source = json.loads((ROOT / 'catalog' / f'{role}_annotations.json').read_text(encoding='utf-8'))
        images = {row['id']: row for row in source['images']}
        for label in source['annotations']:
            by_file[images[label['image_id']]['file_name']].append(label)
    rows = []
    count_conflicts = []
    zero = Counter()
    object_types = Counter()
    size_swaps = 0
    for source in metadata:
        name = source['file_name']
        path = ROOT / 'source_XML' / source['role'] / Path(name).with_suffix('.xml')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['XML_sha256']
        tree = ET.parse(path).getroot()
        candidates = []
        for i, obj in enumerate(tree.findall('object')):
            object_types[(obj.findtext('type') or 'unspecified') + ':' + (obj.findtext('name') or '')] += 1
            box = obj.find('robndbox')
            if box is None:
                continue
            cx, cy, width, height, angle = [float(box.findtext(k)) for k in ['cx', 'cy', 'w', 'h', 'angle']]
            assert all(math.isfinite(v) for v in [cx, cy, width, height, angle])
            if width <= 0 or height <= 0:
                zero[source['role']] += 1
                continue
            candidates.append({'object_index': i, 'polygon': rectangle(cx, cy, width, height, angle),
                               'width': width, 'height': height, 'name': obj.findtext('name')})
        labels = sorted(by_file[name], key=lambda row: row['id'])
        if len(labels) != len(candidates) or len(candidates) > 8:
            count_conflicts.append({'file_name': name, 'role': source['role'],
                                    'JSON_labels': len(labels), 'positive_XML_rotated_objects': len(candidates),
                                    'reason': 'count_difference_or_assignment_size_guard'})
            continue
        polygons = []
        for label in labels:
            x, y, w, h, a = label['bbox']
            polygons.append(rectangle(x + w / 2, y + h / 2, w, h, a))
        errors = [[vertex_error(poly, candidate['polygon']) for candidate in candidates] for poly in polygons]
        # Explicit one-to-one global minimum of summed polygon errors; up to5
        # published cow objects occur per image in the actual JSON inventory.
        assignment = min(itertools.permutations(range(len(candidates))),
                         key=lambda p: sum(errors[i][j] for i, j in enumerate(p)))
        for label, candidates_index, polygon_errors in zip(labels, assignment, errors):
            candidate = candidates[candidates_index]
            error = polygon_errors[candidates_index]
            _, _, width, height, _ = label['bbox']
            swapped = (abs(width - candidate['height']) + abs(height - candidate['width'])
                       < abs(width - candidate['width']) + abs(height - candidate['height']))
            size_swaps += swapped
            rows.append({'file_name': name, 'role': source['role'], 'annotation_id': label['id'],
                         'XML_object_index': candidate['object_index'], 'XML_name': candidate['name'],
                         'matched_polygon_vertex_max_difference_pixels': error,
                         'width_height_swapped_representation': swapped,
                         'review_cue_above_2_pixels': error > REVIEW_CUE_PIXELS})
    assert len(rows) + sum(r['JSON_labels'] for r in count_conflicts) == 13165
    ordered = sorted(row['matched_polygon_vertex_max_difference_pixels'] for row in rows)
    result = {'status': 'ALL_XML_JSON_RECTANGLES_COMPARED_DIFFERENCES_PRESERVED',
              'XML_images': len(metadata), 'published_JSON_labels': 13165,
              'one_to_one_matched_labels': len(rows), 'image_count_conflicts': count_conflicts,
              'XML_nonpositive_rotated_objects_not_added_to_JSON': dict(zero),
              'XML_object_types': dict(object_types), 'width_height_swapped_representations': size_swaps,
              'polygon_error_pixels': {'maximum': max(ordered),
                                       'median': ordered[len(ordered) // 2],
                                       'p95': ordered[int((len(ordered) - 1) * .95)]},
              'review_cue_threshold_pixels': REVIEW_CUE_PIXELS,
              'labels_above_review_cue': sum(r['review_cue_above_2_pixels'] for r in rows),
              'automatic_training_approval_or_label_repair': False,
              'validation_or_test_image_pixels_opened': False,
              'new_model_forward_or_training': False, 'records': rows}
    target = ROOT / 'results/full_XML_JSON_geometry_comparison.json'
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}), flush=True)


if __name__ == '__main__':
    main()
