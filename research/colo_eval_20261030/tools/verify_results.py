"""Independent local raw decoding, IoU matching and full COCO rerun. No Torch."""
from pathlib import Path
from datetime import datetime, timezone
import contextlib
import hashlib
import io
import json
import sys
import zipfile
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor_local_review"))
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
import pycocotools.cocoeval


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independently_match(images, labels, predictions):
    output = []
    for image in images:
        gt = sorted([row for row in labels if row["image_id"] == image["id"]], key=lambda row: row["id"])
        found = [row for row in predictions[image["id"]] if row["score"] >= .20]
        matrix = np.zeros((len(found), len(gt)), dtype=np.float64)
        for pi, pred in enumerate(found):
            p = np.array(pred["xyxy"], dtype=float)
            for gi, row in enumerate(gt):
                x, y, width, height = row["bbox"]
                g = np.array([x, y, x + width, y + height], dtype=float)
                sides = np.maximum(0., np.minimum(p[2:], g[2:]) - np.maximum(p[:2], g[:2]))
                intersection = sides.prod()
                matrix[pi, gi] = intersection / ((p[2:] - p[:2]).prod() + width * height - intersection)
        available = np.ones(len(gt), dtype=bool)
        matches = []
        for pi, pred in enumerate(found):
            candidates = np.flatnonzero(available & (matrix[pi] >= .50))
            if len(candidates):
                gi = int(candidates[np.argmax(matrix[pi, candidates])])
                available[gi] = False
                matches.append({"prediction_index": pi, "raw_index": pred["raw_index"], "annotation_id": gt[gi]["id"], "IoU": float(matrix[pi, gi])})
        output.append({"image_id": image["id"], "file_name": image["file_name"], "references": len(gt), "predictions": len(found),
                       "TP": len(matches), "FP": len(found) - len(matches), "FN": int(available.sum()), "matches": matches,
                       "absolute_image_box_count_error": abs(len(found) - len(gt))})
    return output


plan = load(ROOT / "protocol/run_v1.json")
execution = load(ROOT / "protocol/execution_v1.json")
assert execution["protocol_sha256"] == sha(ROOT / "protocol/run_v1.json")
for relative, digest in execution["files_sha256"].items():
    assert sha(ROOT / relative) == digest, relative
manifest = load(ROOT / "delivery/result_manifest.json")
for row in manifest:
    path = ROOT / "delivery" / row["file"]
    assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
summary = load(ROOT / "delivery/results/evaluation/summary.json")
assert summary["actual_source_image_forwards"] == 450 and summary["actual_network_forward_calls"] == 45
assert summary["warmup_forwards"] == 0 and len(summary["metrics"]) == 72
assert sha(Path(pycocotools.cocoeval.__file__)) == summary["environment"]["COCOeval_file_sha256"]
with zipfile.ZipFile(ROOT / "input" / plan["evaluation_library"]["wheel"]) as archive:
    assert hashlib.sha256(archive.read("pycocotools/cocoeval.py")).hexdigest() == sha(Path(pycocotools.cocoeval.__file__))
freeze = load(ROOT / "delivery/results/evaluation/all_raw_frozen_before_scoring.json")
for relative, digest in freeze["files"].items():
    assert sha(ROOT / "delivery/results/evaluation" / relative) == digest
records = []
local_arrays = ROOT / "results/local_COCO_rerun"
local_arrays.mkdir(exist_ok=False)
max_array_difference = 0.
for model in plan["models"]:
    for size in plan["sizes"]:
        condition = model["name"] + "_s" + str(size)
        folder = ROOT / "delivery/results/evaluation" / condition
        with np.load(folder / "all_raw.npz") as data:
            raw = data["raw"].copy()
        assert raw.shape == (50, 300, 6) and raw.dtype == np.float32 and np.isfinite(raw).all()
        predictions = {}
        for item, values in zip(plan["images"], raw):
            decoded = []
            for index in np.flatnonzero((values[:, 4] >= .001) & (values[:, 5] == model["cow_class"])):
                scaled = values[index, :4].astype(np.float64) / size * 640.
                scaled = np.maximum(0., np.minimum(640., scaled))
                if scaled[2] > scaled[0] and scaled[3] > scaled[1]:
                    decoded.append({"raw_index": int(index), "xyxy": scaled.tolist(), "score": float(values[index, 4])})
            predictions[item["image"]["id"]] = sorted(decoded, key=lambda row: (-row["score"], row["raw_index"]))
        saved = load(folder / "all_decoded_predictions.json")
        for image_id, rows in predictions.items():
            original_rows = saved[str(image_id)]
            assert len(rows) == len(original_rows)
            for local, prior in zip(rows, original_rows):
                assert local["raw_index"] == prior["raw_index"] and local["score"] == prior["score"]
                np.testing.assert_allclose(local["xyxy"], prior["xyxy"], rtol=0, atol=1e-12)
        for policy, filename in [("clipped", "GT_valid450_clipped.json"), ("unclipped", "GT_valid450_unclipped.json")]:
            gt = load(ROOT / "input" / filename)
            matching = independently_match(gt["images"], gt["annotations"], predictions)
            original_fixed = load(folder / ("fixed_" + policy + ".json"))
            for local, prior in zip(matching, original_fixed["records"]):
                assert {key: value for key, value in local.items() if key != "matches"} == {key: value for key, value in prior.items() if key != "matches"}
                assert len(local["matches"]) == len(prior["matches"])
                for left, right in zip(local["matches"], prior["matches"]):
                    assert {key: value for key, value in left.items() if key != "IoU"} == {key: value for key, value in right.items() if key != "IoU"}
                    assert abs(left["IoU"] - right["IoU"]) < 1e-12
            for light in ["all", "daylight", "indoorlight", "infrared"]:
                ids = [row["image"]["id"] for row in plan["images"] if light == "all" or row["lighting"] == light]
                detections = []
                for image_id in ids:
                    for row in predictions[image_id]:
                        x1, y1, x2, y2 = row["xyxy"]
                        detections.append({"image_id": image_id, "category_id": 0, "score": row["score"], "bbox": [x1, y1, x2 - x1, y2 - y1]})
                assert detections
                with contextlib.redirect_stdout(io.StringIO()):
                    ground = COCO()
                    ground.dataset = gt
                    ground.createIndex()
                    found = ground.loadRes(detections)
                    evaluator = COCOeval(ground, found, "bbox")
                    evaluator.params.imgIds = sorted(ids)
                    evaluator.params.catIds = [0]
                    evaluator.params.maxDets = [1, 10, 100]
                    evaluator.evaluate()
                    evaluator.accumulate()
                    evaluator.summarize()
                prior_metric = next(row for row in summary["metrics"] if row["condition"] == condition and row["GT_policy"] == policy and row["lighting"] == light)
                assert np.max(np.abs(evaluator.stats - prior_metric["all12_COCO_stats"])) < 1e-12
                with np.load(folder / ("COCO_" + policy + "_" + light + ".npz")) as previous:
                    for key in ["precision", "recall", "scores"]:
                        current = evaluator.eval[key]
                        difference = float(np.max(np.abs(current - previous[key])))
                        assert difference < 1e-12, (condition, policy, light, key, difference)
                        max_array_difference = max(max_array_difference, difference)
                np.savez_compressed(local_arrays / (condition + "_" + policy + "_" + light + ".npz"),
                                    precision=evaluator.eval["precision"], recall=evaluator.eval["recall"], scores=evaluator.eval["scores"])
                records.append({"condition": condition, "GT_policy": policy, "lighting": light,
                                "all12_COCO_stats": evaluator.stats.tolist(), "local_arrays_equal_within1e_12": True})
result = {"status": "ALL450_FULL_RAW9_CONDITIONS900_IMAGE_MATCHES_AND72_COCO_GROUPS_LOCALLY_RECOMPUTED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "raw_model_image_forwards_checked": 450,
          "fixed_condition_GT_policy_image_rows_checked": 900, "COCO_metric_groups_rerun": 72,
          "maximum_COCO_array_difference": max_array_difference, "new_model_forwards": 0,
          "new_training_updates": 0, "independent_implementation_for_raw_decoding_and_fixed_matching": True,
          "official_same_COCO_evaluator_independently_rerun_on_Windows_from_raw": True,
          "COCOeval_source_sha256": sha(Path(pycocotools.cocoeval.__file__)),
          "original451_GT_not_modified": True, "quarantined_zero_area_GT_ID": 127,
          "manifest_files_checked": len(manifest), "records": records, "whole_goal_complete": False}
target = ROOT / "results/independent_verification.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key != "records"}))
