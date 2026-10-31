from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "cows2021_identity_eval_20261030"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = load(SOURCE / "protocol/run_v1.json")
summary = load(SOURCE / "delivery/results/evaluation/summary.json")
ids = plan["roles"]["evaluation_registered"]
folds = [ids[:20], ids[20:]]
protocol = {"status": "POSTHOC_GALLERY_SIZE_CONTROL_FROZEN_BEFORE_RETRIEVAL_RECALCULATION",
            "created_UTC": datetime.now(timezone.utc).isoformat(), "source_protocol_sha256": sha(SOURCE / "protocol/run_v1.json"),
            "source_summary_sha256": sha(SOURCE / "delivery/results/evaluation/summary.json"),
            "fold_IDs": folds, "gallery_ID_counts": [20, 40], "same_known_queries_each_fold": 60, "same_unknown_queries_each_fold": 120,
            "new_model_forwards": 0, "new_threshold_selection": False, "plan_sha256": sha(ROOT / "计划与验收.md"), "whole_goal_complete": False}
(ROOT / "protocol").mkdir(exist_ok=False)
(ROOT / "protocol/run_v1.json").write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
results = []
decisions = []
checks = []
selected = [row for row in plan["selected_images"] if row["phase"] == "evaluation"]
for model in plan["models"]:
    with np.load(SOURCE / "delivery/results/evaluation/evaluation" / model["name"] / "all_features.npz") as archive:
        features = archive["normalized"].copy().astype(float)
    calibration = next(row for row in summary["calibration"] if row["model"] == model["name"])
    for fold_index, fold in enumerate(folds):
        qi = [index for index, row in enumerate(selected) if row["purpose"] != "gallery" and (not row["is_known"] or row["publisher_identity"] in fold)]
        assert len(qi) == 180 and sum(selected[index]["is_known"] for index in qi) == 60
        prediction_sets = {}
        for count in [20, 40]:
            permitted = fold if count == 20 else ids
            gi = [index for index, row in enumerate(selected) if row["purpose"] == "gallery" and row["publisher_identity"] in permitted]
            labels = sorted({selected[index]["identity_namespace"] for index in gi})
            values = features[qi] @ features[gi].T
            scores = np.stack([values[:, [position for position, index in enumerate(gi) if selected[index]["identity_namespace"] == label]].max(axis=1) for label in labels], axis=1)
            predictions = []
            for position, index in enumerate(qi):
                winner = int(np.argmax(scores[position]))
                predictions.append({"evaluation_source_index": index, "identity": selected[index]["identity_namespace"], "is_known": selected[index]["is_known"],
                                    "predicted_id": labels[winner], "similarity": float(scores[position, winner]),
                                    "all_scores": {label: float(value) for label, value in zip(labels, scores[position])}})
            prediction_sets[count] = predictions
            for policy, threshold in [("original_MultiCam", model["original_MultiCam_threshold"]), ("Cows2021_calibrated", calibration["threshold"]["threshold"])]:
                rows = [{**row, "accepted": row["similarity"] >= threshold} for row in predictions]
                known = [row for row in rows if row["is_known"]]
                unknown = [row for row in rows if not row["is_known"]]
                result = {"model": model["name"], "fold": fold_index, "gallery_IDs": count, "threshold_policy": policy, "threshold": threshold,
                          "known_queries": 60, "unknown_queries": 120,
                          "C": sum(row["accepted"] and row["predicted_id"] == row["identity"] for row in known),
                          "W": sum(row["accepted"] and row["predicted_id"] != row["identity"] for row in known),
                          "U": sum(not row["accepted"] for row in known),
                          "known_closed_Top1": sum(row["predicted_id"] == row["identity"] for row in known),
                          "unknown_FA": sum(row["accepted"] for row in unknown)}
                assert result["C"] + result["W"] + result["U"] == 60
                results.append(result)
                decisions.append({**{key: result[key] for key in ["model", "fold", "gallery_IDs", "threshold_policy", "threshold"]}, "rows": rows})
        for left, right in zip(prediction_sets[20], prediction_sets[40]):
            assert left["evaluation_source_index"] == right["evaluation_source_index"] and left["identity"] == right["identity"]
            assert right["similarity"] >= left["similarity"] - 1e-15
            checks.append({"model": model["name"], "fold": fold_index, "evaluation_source_index": left["evaluation_source_index"],
                           "score20": left["similarity"], "score40": right["similarity"], "delta": right["similarity"] - left["similarity"]})
assert len(results) == 16 and sum(len(group["rows"]) for group in decisions) == 2880 and len(checks) == 720
(ROOT / "results").mkdir(exist_ok=False)
output = {"status": "SAME_QUERY20_VS40_REGISTRY16_CONDITIONS2880_DECISIONS_AND720_SCORE_MONOTONICITY_CHECKS_COMPLETE",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "conditions": results, "query_decisions": 2880,
          "monotonic_score_pairs": 720, "new_model_forwards": 0, "new_training_updates": 0,
          "new_threshold_selection": False, "new_independent_test": False, "whole_goal_complete": False}
for filename, value in [("summary.json", output), ("decisions.json", decisions), ("score_monotonicity.json", checks)]:
    (ROOT / "results" / filename).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in output.items() if key != "conditions"}))
for row in results:
    if row["threshold_policy"] == "Cows2021_calibrated":
        print(json.dumps(row))
