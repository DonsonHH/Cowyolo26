"""Independent scalar IoU and maximum-matching certificates; no inference."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, deque, defaultdict
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def scalar_overlap(left, right):
    intersection = max(0., min(left[2], right[2]) - max(left[0], right[0])) * max(0., min(left[3], right[3]) - max(left[1], right[1]))
    area1 = max(0., left[2] - left[0]) * max(0., left[3] - left[1])
    area2 = max(0., right[2] - right[0]) * max(0., right[3] - right[1])
    return intersection / (area1 + area2 - intersection) if area1 + area2 > intersection else 0.


plan = load(ROOT / "protocol/run_v1.json")
source = Path(plan["source_directory"])
for relative, digest in plan["source_file_hashes"].items():
    assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest
source_plan = load(source / "protocol/run_v1.json")
gt = load(source / "input/GT_valid450_clipped.json")
source_images = source_plan["images"]
summary = load(ROOT / "results/summary.json")
rows = load(ROOT / "results/GT4050_rows.json")
fps = load(ROOT / "results/FP_rows.json")
graphs = load(ROOT / "results/oracle5400_cases.json")
assert len(rows) == 4050 and len(graphs) == 5400
row_index = {(row["condition"], row["annotation_id"]): row for row in rows}
assert len(row_index) == 4050
cache = {}
conditions = {}
checked_rows = 0
for model in plan["models"]:
    for size in plan["sizes"]:
        condition = model["name"] + "_s" + str(size)
        fixed = load(source / "delivery/results/evaluation" / condition / "fixed_clipped.json")
        with np.load(source / "delivery/results/evaluation" / condition / "all_raw.npz") as archive:
            raw = archive["raw"].copy()
        counter = Counter()
        groups = defaultdict(Counter)
        for image_index, item in enumerate(source_images):
            image_id = item["image"]["id"]
            annotations = sorted([row for row in gt["annotations"] if row["image_id"] == image_id], key=lambda row: row["id"])
            coordinates = []
            for value in raw[image_index]:
                coordinates.append([max(0., min(640., float(number) * (640. / size))) for number in value[:4]])
            positive = [index for index, box in enumerate(coordinates) if box[2] > box[0] and box[3] > box[1]]
            cow = [index for index in positive if int(raw[image_index, index, 5]) == model["cow_class"]]
            matrix = np.zeros((len(annotations), 300), dtype=float)
            for gi, annotation in enumerate(annotations):
                x, y, width, height = annotation["bbox"]
                box = [x, y, x + width, y + height]
                for pi in positive:
                    matrix[gi, pi] = scalar_overlap(box, coordinates[pi])
            cache[(condition, image_id)] = {"matrix": matrix, "values": raw[image_index], "positive": positive,
                                             "cow": cow, "annotation_ids": [row["id"] for row in annotations]}
            previous = next(row for row in fixed["records"] if row["image_id"] == image_id)
            matched = {row["annotation_id"] for row in previous["matches"]}
            for gi, annotation in enumerate(annotations):
                row = row_index[(condition, annotation["id"])]
                candidates = [pi for pi in cow if matrix[gi, pi] >= .50]
                if annotation["id"] in matched:
                    category = "matched_TP"
                elif any(raw[image_index, pi, 4] >= .20 for pi in candidates):
                    category = "eligible_cow_geometry_unmatched"
                elif any(raw[image_index, pi, 4] >= .001 for pi in candidates):
                    category = "cow_score_0_001_to_0_20"
                elif candidates:
                    category = "cow_score_below_0_001"
                elif any(matrix[gi, pi] >= .50 for pi in positive):
                    category = "only_other_class_geometry"
                else:
                    category = "no_geometry_in_retained300"
                assert row["category"] == category
                for field, indices in [("best_cow_geometry", cow), ("best_anyclass_geometry", positive)]:
                    candidate = row[field]
                    if not indices:
                        assert candidate is None
                        continue
                    pi = candidate["raw_index"]
                    assert pi in indices and abs(matrix[gi, pi] - max(matrix[gi, index] for index in indices)) < 1e-12
                    assert abs(candidate["IoU"] - matrix[gi, pi]) < 1e-12
                    assert candidate["xyxy"] == coordinates[pi] and candidate["score"] == float(raw[image_index, pi, 4])
                x, y, width, height = annotation["bbox"]
                border = min(x, y, 640. - x - width, 640. - y - height) <= 1.
                short = min(width, height) * size / 640.
                short_group = "lt16" if short < 16 else "16to24" if short < 24 else "ge24"
                assert row["touches_border1px_proxy"] == border and row["short_edge_group"] == short_group
                counter[category] += 1
                for key in ["all", "border" if border else "interior", "short_" + short_group, "light_" + item["lighting"]]:
                    groups[key][category] += 1
                checked_rows += 1
        record = next(row for row in summary["conditions"] if row["condition"] == condition)
        assert dict(counter) == record["GT_partition"]
        assert {key: dict(value) for key, value in groups.items()} == record["GT_geometry_groups"]
        conditions[condition] = record
certificates = []
oracle_sums = defaultdict(Counter)
for graph in graphs:
    cached = cache[(graph["condition"], graph["image_id"])]
    assert graph["GT_annotation_ids"] == cached["annotation_ids"]
    if graph["cow_score"] == "anyclass":
        selected = cached["positive"]
        key = "anyclass_IoU" + str(graph["IoU"])
    else:
        selected = [pi for pi in cached["cow"] if graph["cow_score"] is None or cached["values"][pi, 4] >= graph["cow_score"]]
        key = "cow_score" + str(graph["cow_score"]) + "_IoU" + str(graph["IoU"])
    assert selected == graph["raw_indices"]
    matrix = cached["matrix"][:, selected]
    pairs = graph["pairs_GTindex_selectedindex"]
    assert len({pair[0] for pair in pairs}) == len({pair[1] for pair in pairs}) == len(pairs)
    assert all(matrix[gi, pi] >= graph["IoU"] for gi, pi in pairs)
    g_owner = {gi: pi for gi, pi in pairs}
    p_owner = {pi: gi for gi, pi in pairs}
    reached_g = set(range(len(matrix))) - set(g_owner)
    reached_p = set()
    pending = deque(sorted(reached_g))
    while pending:
        gi = pending.popleft()
        for pi in np.flatnonzero(matrix[gi] >= graph["IoU"]):
            pi = int(pi)
            if g_owner.get(gi) == pi or pi in reached_p:
                continue
            reached_p.add(pi)
            assert pi in p_owner, "augmenting path exists: saved matching is not maximum"
            following = p_owner[pi]
            if following not in reached_g:
                reached_g.add(following)
                pending.append(following)
    cover_g = set(range(len(matrix))) - reached_g
    cover_p = reached_p
    assert len(cover_g) + len(cover_p) == len(pairs)
    for gi, pi in np.argwhere(matrix >= graph["IoU"]):
        assert int(gi) in cover_g or int(pi) in cover_p
    certificates.append({"condition": graph["condition"], "image_id": graph["image_id"], "key": key,
                         "matching_size": len(pairs), "GT_vertex_cover": sorted(cover_g), "prediction_vertex_cover": sorted(cover_p)})
    oracle_sums[graph["condition"]][key] += len(pairs)
for condition, counts in oracle_sums.items():
    assert dict(counts) == conditions[condition]["maximum_one_to_one_geometry_oracles_not_deployable"]
for row in fps:
    cached = cache[(row["condition"], row["image_id"])]
    pi = row["raw_index"]
    overlap = float(cached["matrix"][:, pi].max())
    assert abs(overlap - row["maximum_GT_IoU"]) < 1e-12
    assert row["FP_category"] == ("has_GT_IoU0_50_duplicate_or_competition" if overlap >= .50 else "no_GT_IoU0_50")
output = ROOT / "results/oracle_independent_vertex_cover_certificates.json"
assert not output.exists()
output.write_text(json.dumps(certificates, indent=2) + "\n", encoding="utf-8")
result = {"status": "ALL4050_GT_ERROR_ROWS_FP_ROWS_AND5400_MAXIMUM_MATCHINGS_INDEPENDENTLY_CERTIFIED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "GT_rows": checked_rows, "FP_rows": len(fps),
          "maximum_matching_certificates": len(certificates), "certificate_method": "independent scalar IoU, no augmenting path and vertex cover size equal to matching size, every edge covered",
          "original_fixed_evaluation_unchanged": True, "new_model_forwards": 0, "new_training_updates": 0,
          "new_board_forwards": 0, "whole_goal_complete": False}
output = ROOT / "results/independent_verification.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
