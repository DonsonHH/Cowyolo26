from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
plan = json.loads((ROOT / "protocol/run_v1.json").read_text(encoding="utf-8"))
SOURCE = Path(plan["source_directory"])


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def matrix_iou(a, b):
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)), dtype=np.float64)
    width = np.maximum(0., np.minimum(a[:, None, 2:], b[None, :, 2:]) - np.maximum(a[:, None, :2], b[None, :, :2]))
    intersection = width.prod(axis=2)
    aa = (a[:, 2:] - a[:, :2]).prod(axis=1)
    bb = (b[:, 2:] - b[:, :2]).prod(axis=1)
    return intersection / (aa[:, None] + bb[None, :] - intersection)


def maximum_matching(matrix, threshold):
    edges = [list(np.flatnonzero(row >= threshold)) for row in matrix]
    owner = {}

    def visit(gi, seen):
        for pi in edges[gi]:
            pi = int(pi)
            if pi in seen:
                continue
            seen.add(pi)
            if pi not in owner or visit(owner[pi], seen):
                owner[pi] = gi
                return True
        return False

    for gi in range(len(edges)):
        visit(gi, set())
    return sorted([[gi, pi] for pi, gi in owner.items()])


for file, expected in plan["source_file_hashes"].items():
    assert hashlib.sha256((SOURCE / file).read_bytes()).hexdigest() == expected
old_plan = load(SOURCE / "protocol/run_v1.json")
gt = load(SOURCE / "input/GT_valid450_clipped.json")
images = old_plan["images"]
lighting = {row["image"]["id"]: row["lighting"] for row in images}
assert len(gt["annotations"]) == 450
out = ROOT / "results"
out.mkdir(exist_ok=False)
conditions = []
all_gt_rows = []
all_fp_rows = []
oracle_cases = []
for model in plan["models"]:
    for size in plan["sizes"]:
        condition = model["name"] + "_s" + str(size)
        folder = SOURCE / "delivery/results/evaluation" / condition
        previous = load(folder / "fixed_clipped.json")
        with np.load(folder / "all_raw.npz") as archive:
            raw = archive["raw"].copy()
        assert raw.shape == (50, 300, 6)
        counters = Counter()
        groups = defaultdict(Counter)
        oracle_sums = Counter()
        current_rows = []
        for image_index, item in enumerate(images):
            image_id = item["image"]["id"]
            annotations = sorted([row for row in gt["annotations"] if row["image_id"] == image_id], key=lambda row: row["id"])
            boxes = np.array([[x, y, x + width, y + height] for x, y, width, height in [row["bbox"] for row in annotations]], dtype=np.float64)
            values = raw[image_index].astype(np.float64)
            coordinates = np.clip(values[:, :4] * (640. / size), 0., 640.)
            positive = np.all(coordinates[:, 2:] > coordinates[:, :2], axis=1)
            cow = (values[:, 5] == model["cow_class"]) & positive
            iou = matrix_iou(boxes, coordinates)
            # Invalid zero-area output has no possible match; avoid its area division.
            iou[:, ~positive] = 0.
            previous_image = next(row for row in previous["records"] if row["image_id"] == image_id)
            matched_ids = {row["annotation_id"] for row in previous_image["matches"]}
            matched_raw = {row["raw_index"] for row in previous_image["matches"]}
            order = sorted(np.flatnonzero(cow & (values[:, 4] >= .20)), key=lambda index: (-values[index, 4], index))
            available = set(range(len(annotations)))
            reproduced_matches = []
            for pi in order:
                eligible = [gi for gi in available if iou[gi, pi] >= .50]
                if eligible:
                    gi = max(eligible, key=lambda index: (iou[index, pi], -annotations[index]["id"]))
                    available.remove(gi)
                    reproduced_matches.append((annotations[gi]["id"], int(pi)))
            assert set(reproduced_matches) == {(row["annotation_id"], row["raw_index"]) for row in previous_image["matches"]}
            assert len(order) == previous_image["predictions"]
            for threshold in plan["IoU_diagnostic_levels"]:
                for score in plan["cow_score_diagnostic_levels"]:
                    selected = np.flatnonzero(cow & ((values[:, 4] >= score) if score is not None else np.ones(300, dtype=bool)))
                    matching = maximum_matching(iou[:, selected], threshold)
                    key = "cow_score" + str(score) + "_IoU" + str(threshold)
                    oracle_sums[key] += len(matching)
                    oracle_cases.append({"condition": condition, "image_id": image_id, "IoU": threshold, "cow_score": score,
                                         "raw_indices": selected.astype(int).tolist(), "pairs_GTindex_selectedindex": matching,
                                         "GT_annotation_ids": [row["id"] for row in annotations]})
                selected = np.flatnonzero(positive)
                matching = maximum_matching(iou[:, selected], threshold)
                key = "anyclass_IoU" + str(threshold)
                oracle_sums[key] += len(matching)
                oracle_cases.append({"condition": condition, "image_id": image_id, "IoU": threshold, "cow_score": "anyclass",
                                     "raw_indices": selected.astype(int).tolist(), "pairs_GTindex_selectedindex": matching,
                                     "GT_annotation_ids": [row["id"] for row in annotations]})
            for gi, annotation in enumerate(annotations):
                geometry = iou[gi] >= .50
                if annotation["id"] in matched_ids:
                    category = "matched_TP"
                elif np.any(geometry & cow & (values[:, 4] >= .20)):
                    category = "eligible_cow_geometry_unmatched"
                elif np.any(geometry & cow & (values[:, 4] >= .001)):
                    category = "cow_score_0_001_to_0_20"
                elif np.any(geometry & cow):
                    category = "cow_score_below_0_001"
                elif np.any(geometry & positive):
                    category = "only_other_class_geometry"
                else:
                    category = "no_geometry_in_retained300"
                cow_indices = np.flatnonzero(cow)
                best_cow = int(cow_indices[np.argmax(iou[gi, cow_indices])]) if len(cow_indices) else None
                all_indices = np.flatnonzero(positive)
                best_any = int(all_indices[np.argmax(iou[gi, all_indices])]) if len(all_indices) else None
                x, y, width, height = annotation["bbox"]
                border = min(x, y, 640. - x - width, 640. - y - height) <= 1.
                short = min(width, height) * size / 640.
                short_group = "lt16" if short < 16 else "16to24" if short < 24 else "ge24"
                def candidate(index):
                    if index is None:
                        return None
                    box = coordinates[index]
                    area = float(np.prod(box[2:] - box[:2]))
                    intersection = float(np.prod(np.maximum(0., np.minimum(boxes[gi, 2:], box[2:]) - np.maximum(boxes[gi, :2], box[:2]))))
                    return {"raw_index": index, "xyxy": box.tolist(), "score": float(values[index, 4]), "class": int(values[index, 5]),
                            "IoU": float(iou[gi, index]), "prediction_area_over_GT": area / (width * height),
                            "intersection_over_prediction_area": intersection / area}
                row = {"condition": condition, "image_index": image_index, "image_id": image_id, "file_name": item["file_name"],
                       "annotation_id": annotation["id"], "GT_xyxy": boxes[gi].tolist(), "category": category,
                       "touches_border1px_proxy": bool(border), "input_short_edge_px": short, "short_edge_group": short_group,
                       "lighting": lighting[image_id], "best_cow_geometry": candidate(best_cow), "best_anyclass_geometry": candidate(best_any)}
                counters[category] += 1
                for group in ["all", "border" if border else "interior", "short_" + short_group, "light_" + lighting[image_id]]:
                    groups[group][category] += 1
                current_rows.append(row)
            for pi in order:
                if pi not in matched_raw:
                    max_overlap = float(iou[:, pi].max()) if len(annotations) else 0.
                    fp_category = "has_GT_IoU0_50_duplicate_or_competition" if max_overlap >= .50 else "no_GT_IoU0_50"
                    all_fp_rows.append({"condition": condition, "image_index": image_index, "image_id": image_id, "file_name": item["file_name"],
                                        "raw_index": int(pi), "xyxy": coordinates[pi].tolist(), "score": float(values[pi, 4]),
                                        "FP_category": fp_category, "maximum_GT_IoU": max_overlap})
        assert sum(counters.values()) == 450 and counters["matched_TP"] == previous["TP"]
        assert sum(value for key, value in counters.items() if key != "matched_TP") == previous["FN"]
        fps = [row for row in all_fp_rows if row["condition"] == condition]
        assert len(fps) == previous["FP"]
        all_gt_rows.extend(current_rows)
        conditions.append({"condition": condition, "fixed_TP": previous["TP"], "fixed_FP": previous["FP"], "fixed_FN": previous["FN"],
                           "GT_partition": dict(counters), "GT_geometry_groups": {key: dict(value) for key, value in groups.items()},
                           "maximum_one_to_one_geometry_oracles_not_deployable": dict(oracle_sums),
                           "FP_partition": dict(Counter(row["FP_category"] for row in fps))})
selected = []
for model in plan["models"]:
    name = model["name"] + "_s192"
    for category in plan["FN_partition_priority"]:
        choices = sorted([row for row in all_gt_rows if row["condition"] == name and row["category"] == category], key=lambda row: row["annotation_id"])
        if choices:
            selected.append({"kind": "GT_FN", **choices[0]})
    choices = sorted([row for row in all_fp_rows if row["condition"] == name], key=lambda row: (row["image_index"], row["raw_index"]))
    if choices:
        selected.append({"kind": "FP", **choices[0]})
transitions = []
for size in plan["sizes"]:
    old = {row["annotation_id"] for row in all_gt_rows if row["condition"] == "old_rot192_s" + str(size) and row["category"] == "matched_TP"}
    new = {row["annotation_id"] for row in all_gt_rows if row["condition"] == "new_mosaic050_s" + str(size) and row["category"] == "matched_TP"}
    transitions.append({"size": size, "both_matched": sorted(old & new), "old_only_matched": sorted(old - new), "new_only_matched": sorted(new - old)})
for filename, value in [("GT4050_rows.json", all_gt_rows), ("FP_rows.json", all_fp_rows), ("oracle5400_cases.json", oracle_cases),
                        ("selected_192_cases.json", selected), ("old_new_transitions.json", transitions)]:
    (out / filename).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
assert len(all_gt_rows) == 4050 and len(oracle_cases) == 5400
summary = {"status": "ALL9_CONDITIONS4050_GT_ROWS5400_ORACLE_GRAPHS_AND_FIXED_ERROR_PARTITIONS_COMPLETE",
           "created_UTC": datetime.now(timezone.utc).isoformat(), "conditions": conditions, "selected_192_cases": len(selected),
           "new_model_forwards": 0, "new_training_updates": 0, "new_board_forwards": 0,
           "diagnostic_oracles_are_deployable": False, "new_independent_test": False, "whole_goal_complete": False}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in summary.items() if key != "conditions"}))
for row in conditions:
    print(json.dumps({key: row[key] for key in ["condition", "fixed_TP", "fixed_FP", "GT_partition", "maximum_one_to_one_geometry_oracles_not_deployable"]}))
