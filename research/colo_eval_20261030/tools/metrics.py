"""Decode every retained end-to-end candidate; official COCO bbox evaluator."""
from pathlib import Path
import contextlib
import copy
import io
import json
import numpy as np


def decode(raw, size, cow_class, minimum=.001):
    assert raw.shape == (300, 6) and np.isfinite(raw).all()
    predictions = []
    for index, row in enumerate(raw):
        x1, y1, x2, y2, score, category = [float(value) for value in row]
        assert category.is_integer()
        if int(category) != cow_class or score < minimum:
            continue
        coordinates = np.clip(np.asarray([x1, y1, x2, y2], dtype=np.float64) * (640. / size), 0., 640.)
        x1, y1, x2, y2 = coordinates.tolist()
        if x2 <= x1 or y2 <= y1:
            continue
        predictions.append({"raw_index": index, "xyxy": [x1, y1, x2, y2], "score": score})
    return sorted(predictions, key=lambda row: (-row["score"], row["raw_index"]))


def fixed_metrics(images, annotations, predictions, score=.20, overlap=.50):
    records = []
    for image in images:
        refs = sorted([row for row in annotations if row["image_id"] == image["id"]], key=lambda row: row["id"])
        preds = [row for row in predictions[image["id"]] if row["score"] >= score]
        available = set(range(len(refs)))
        matches = []
        for pi, pred in enumerate(preds):
            px1, py1, px2, py2 = pred["xyxy"]
            candidates = []
            for ri in available:
                x, y, width, height = refs[ri]["bbox"]
                intersection = max(0., min(px2, x + width) - max(px1, x)) * max(0., min(py2, y + height) - max(py1, y))
                union = (px2 - px1) * (py2 - py1) + width * height - intersection
                value = intersection / union if union > 0 else 0.
                if value >= overlap:
                    candidates.append((value, -refs[ri]["id"], ri))
            if candidates:
                value, _, ri = max(candidates)
                available.remove(ri)
                matches.append({"prediction_index": pi, "raw_index": pred["raw_index"], "annotation_id": refs[ri]["id"], "IoU": value})
        records.append({"image_id": image["id"], "file_name": image["file_name"], "references": len(refs), "predictions": len(preds),
                        "TP": len(matches), "FP": len(preds) - len(matches), "FN": len(available), "matches": matches,
                        "absolute_image_box_count_error": abs(len(preds) - len(refs))})
    tp, fp, fn = (sum(row[key] for row in records) for key in ["TP", "FP", "FN"])
    return {"TP": tp, "FP": fp, "FN": fn, "precision": tp / (tp + fp) if tp + fp else 0.,
            "recall": tp / (tp + fn) if tp + fn else 0., "F1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.,
            "image_box_count_MAE_not_passage_MAE": sum(row["absolute_image_box_count_error"] for row in records) / len(records),
            "images": len(records), "references": tp + fn, "records": records}


def coco_metrics(gt, predictions, ids, array_file):
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    results = []
    for image_id in ids:
        for row in predictions[image_id]:
            x1, y1, x2, y2 = row["xyxy"]
            results.append({"image_id": image_id, "category_id": 0, "bbox": [x1, y1, x2 - x1, y2 - y1], "score": row["score"]})
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        ground = COCO()
        ground.dataset = copy.deepcopy(gt)
        ground.createIndex()
        if results:
            found = ground.loadRes(results)
        else:
            found = COCO()
            found.dataset = {"images": copy.deepcopy(gt["images"]), "categories": copy.deepcopy(gt["categories"]), "annotations": []}
            found.createIndex()
        evaluator = COCOeval(ground, found, "bbox")
        evaluator.params.imgIds = sorted(ids)
        evaluator.params.catIds = [0]
        evaluator.params.maxDets = [1, 10, 100]
        evaluator.evaluate()
        evaluator.accumulate()
        evaluator.summarize()
    np.savez_compressed(array_file, precision=evaluator.eval["precision"], recall=evaluator.eval["recall"], scores=evaluator.eval["scores"])
    return {"AP": float(evaluator.stats[0]), "AP50": float(evaluator.stats[1]), "AP75": float(evaluator.stats[2]),
            "AR100": float(evaluator.stats[8]), "all12_COCO_stats": evaluator.stats.tolist(), "log": stream.getvalue()}
