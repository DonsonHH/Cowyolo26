"""Independent local source selection, tensors, similarities, thresholds and outcomes."""
from pathlib import Path
from datetime import date, datetime, timezone
from collections import Counter, defaultdict
import hashlib, importlib.util, json, sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


module = importlib.util.spec_from_file_location("independent_identity_body", ROOT / "tools/frozen_body_tensor.py")
body = importlib.util.module_from_spec(module)
module.loader.exec_module(body)
plan = load(ROOT / "protocol/run_v1.json")
execution = load(ROOT / "protocol/execution_v1.json")
assert execution["protocol_sha256"] == sha(ROOT / "protocol/run_v1.json")
for relative, digest in execution["files_sha256"].items():
    assert sha(ROOT / relative) == digest
for row in load(ROOT / "delivery/result_manifest.json"):
    assert sha(ROOT / "delivery" / row["file"]) == row["sha256"]
summary = load(ROOT / "delivery/results/evaluation/summary.json")
freeze_path = ROOT / "delivery/results/evaluation/both_thresholds_frozen.json"
freeze = load(freeze_path)
assert summary["calibration_threshold_freeze_sha256"] == sha(freeze_path)
assert freeze["source_model_image_forwards_at_freeze"] == 360 and freeze["evaluation_model_image_forwards_at_freeze"] == 0
assert summary["actual_model_image_forwards"] == 1080 and summary["actual_network_calls"] == 90 and summary["warmup_forwards"] == 0
freeze_time = datetime.fromisoformat(freeze["created_UTC"])
assert all(datetime.fromisoformat(row["finished_UTC"]) < freeze_time for row in summary["timeline"] if row["phase"] == "calibration")
assert all(datetime.fromisoformat(row["finished_UTC"]) > freeze_time for row in summary["timeline"] if row["phase"] == "evaluation")
rows = plan["selected_images"]
role_sets = [set(value) for value in plan["roles"].values()]
assert len(set.union(*role_sets)) == sum(map(len, role_sets)) == 120
assert len(rows) == 540 and len({row["archive_member"] for row in rows}) == 540
assert all(row["date"] <= "2020-03-04" and row["day_gap"] >= 7 for row in rows)
source = load(PROJECT / "cows2021_identity_intake_20261030/results/test8670_members.json")
source_by_member = {row["archive_member"]: row for row in source}
for row in rows:
    assert source_by_member[row["archive_member"]]["zip_entry"] == row["zip_entry"]
    if row["is_known"]:
        assert date.fromisoformat(row["registered_gallery_date"]) < date.fromisoformat(row["query_date"])
all_hashes = {}
for spec in plan["models"]:
    for phase in ["calibration", "evaluation"]:
        folder = ROOT / "delivery/results/evaluation" / phase / spec["name"]
        for row in load(folder / "source_indices_and_input_hashes.json"):
            index = row["source_index"]
            assert rows[index]["phase"] == phase
            if index in all_hashes:
                assert all_hashes[index] == row["input_tensor_sha256"]
            else:
                all_hashes[index] = row["input_tensor_sha256"]
assert len(all_hashes) == 540
for index, row in enumerate(rows):
    with Image.open(ROOT / row["local_relative_file"]) as image:
        tensor = body.body_tensor(image)
    assert hashlib.sha256(tensor.tobytes()).hexdigest() == all_hashes[index]
    if index in plan["qualification_tensor_indices"]:
        with np.load(ROOT / "delivery/results/evaluation/input_tensor_anchors" / ("image" + str(index) + ".npz")) as archive:
            assert tensor.tobytes() == archive["input"].tobytes()


def independent_metrics(records):
    known = [row for row in records if row["is_known"]]
    unknown = [row for row in records if not row["is_known"]]
    correct = sum(row["accepted"] and row["predicted_id"] == row["identity"] for row in known)
    wrong = sum(row["accepted"] and row["predicted_id"] != row["identity"] for row in known)
    reject = sum(not row["accepted"] for row in known)
    fa = sum(row["accepted"] for row in unknown)
    top1 = sum(row["predicted_id"] == row["identity"] for row in known)
    top5 = sum(row["identity"] in row["top5_IDs"] for row in known)
    assert correct + wrong + reject == len(known)
    per = []
    for identity in sorted({row["identity"] for row in records}):
        group = [row for row in records if row["identity"] == identity]
        is_known = group[0]["is_known"]
        assert len(group) == 3 and all(row["is_known"] == is_known for row in group)
        per.append({"identity": identity, "is_known": is_known, "queries": 3,
                    "closed_top1_accuracy": sum(row["predicted_id"] == identity for row in group)/3 if is_known else None,
                    "correct_accepted_rate": sum(row["accepted"] and row["predicted_id"] == identity for row in group)/3 if is_known else None,
                    "false_accept_rate": sum(row["accepted"] for row in group)/3 if not is_known else None})
    result = {"known_queries": len(known), "unknown_queries": len(unknown), "known_correct_accepted_C": correct,
              "known_wrong_accepted_W": wrong, "known_rejected_U": reject, "query_missing_M": 0,
              "known_closed_top1_correct": top1, "known_closed_top1_accuracy": top1/len(known),
              "known_correct_accepted_rate": correct/len(known), "known_wrong_accepted_rate": wrong/len(known),
              "unknown_false_accepts": fa, "unknown_false_acceptance_rate": fa/len(unknown),
              "all_accepted_wrong_fraction": (wrong+fa)/(correct+wrong+fa) if correct+wrong+fa else None,
              "known_closed_top5_correct": top5, "known_closed_top5_accuracy": top5/len(known), "per_identity": per}
    return result


max_normalized_error = max_score_error = 0.
similarity_cells = retrieval_rows = 0
verified_outcomes = []
calibration_counts = []
for spec in plan["models"]:
    phase_predictions = {}
    for phase in ["calibration", "evaluation"]:
        selected = [(index, row) for index, row in enumerate(rows) if row["phase"] == phase]
        folder = ROOT / "delivery/results/evaluation" / phase / spec["name"]
        with np.load(folder / "all_features.npz") as data:
            raw, normalized = data["raw"].copy(), data["normalized"].copy()
        assert raw.shape == normalized.shape == (len(selected), 576) and np.isfinite(raw).all()
        norms = np.sqrt(np.sum(raw.astype(float)**2, axis=1))
        error = float(np.max(np.abs(raw.astype(float)/norms[:,None] - normalized)))
        assert error < 1e-7
        max_normalized_error = max(max_normalized_error, error)
        gallery_indices = [i for i, (_, row) in enumerate(selected) if row["purpose"] == "gallery"]
        query_indices = [i for i, (_, row) in enumerate(selected) if row["purpose"] != "gallery"]
        labels = sorted({selected[i][1]["identity_namespace"] for i in gallery_indices})
        filename = "retrieval.json" if phase == "calibration" else "retrieval_unthresholded.json"
        saved = load(folder / filename)
        assert len(saved) == len(query_indices)
        for actual, qi in zip(saved, query_indices):
            index, source_row = selected[qi]
            assert actual["source_index"] == index and actual["identity"] == source_row["identity_namespace"] and actual["is_known"] == source_row["is_known"]
            independent = {}
            for label in labels:
                scores = [float(np.dot(normalized[qi].astype(float), normalized[gi].astype(float))) for gi in gallery_indices if selected[gi][1]["identity_namespace"] == label]
                independent[label] = max(scores)
            assert set(independent) == set(actual["all_registered_identity_scores"])
            error = max(abs(independent[label] - actual["all_registered_identity_scores"][label]) for label in labels)
            assert error < 1e-12
            max_score_error = max(max_score_error, error)
            order = sorted(labels, key=lambda label: (-independent[label], label))
            assert actual["predicted_id"] == order[0] and actual["top5_IDs"] == order[:5]
            assert abs(actual["similarity"] - independent[order[0]]) < 1e-12
            similarity_cells += len(labels)
            retrieval_rows += 1
        phase_predictions[phase] = saved
    cal = phase_predictions["calibration"]
    candidates = sorted({row["similarity"] for row in cal} | {float(np.nextafter(max(row["similarity"] for row in cal), np.inf))})
    legal = []
    for threshold in candidates:
        decided = [{**row, "accepted": row["similarity"] >= threshold} for row in cal]
        metric = independent_metrics(decided)
        if metric["unknown_false_accepts"] <= 3:
            legal.append((metric["known_correct_accepted_C"], -metric["known_wrong_accepted_W"], threshold, metric))
    selected_threshold = max(legal, key=lambda row: row[:3])
    frozen = next(row for row in freeze["models"] if row["model"] == spec["name"])
    assert selected_threshold[2] == frozen["threshold"]["threshold"]
    assert selected_threshold[0] == frozen["threshold"]["calibration_known_correct_accepted"]
    assert -selected_threshold[1] == frozen["threshold"]["calibration_known_wrong_accepted"]
    calibration_counts.append({"model": spec["name"], "threshold": selected_threshold[2], "known_C_W": [selected_threshold[0], -selected_threshold[1]],
                               "unknown_FA": selected_threshold[3]["unknown_false_accepts"]})
    for policy, threshold in [("original_MultiCam", spec["original_MultiCam_threshold"]), ("Cows2021_calibrated", selected_threshold[2])]:
        decisions = load(ROOT / "delivery/results/evaluation/evaluation" / spec["name"] / (policy + "_decisions.json"))
        assert decisions == [{**row, "accepted": row["similarity"] >= threshold} for row in phase_predictions["evaluation"]]
        metrics = independent_metrics(decisions)
        saved = next(row for row in summary["outcomes"] if row["model"] == spec["name"] and row["threshold_policy"] == policy)
        for key, value in metrics.items():
            assert saved["metrics"][key] == value
        rng = np.random.default_rng(26)
        for field, known in [("closed_top1_accuracy", True), ("correct_accepted_rate", True), ("false_accept_rate", False)]:
            values = np.array([row[field] for row in metrics["per_identity"] if row["is_known"] == known])
            means = np.array([values[rng.integers(0, len(values), len(values))].mean() for _ in range(2000)])
            expected = saved["ID_cluster_intervals"][field]
            assert abs(float(values.mean())-expected["macro_mean"]) < 1e-12
            np.testing.assert_allclose(np.quantile(means, [.025, .975]), expected["percentile_95_interval"], rtol=0, atol=1e-12)
        verified_outcomes.append({"model": spec["name"], "policy": policy, "known_C_W_U": [metrics["known_correct_accepted_C"], metrics["known_wrong_accepted_W"], metrics["known_rejected_U"]],
                                  "unknown_FA": metrics["unknown_false_accepts"], "known_Top1": metrics["known_closed_top1_correct"], "known_Top5": metrics["known_closed_top5_correct"]})
assert retrieval_rows == 720 and similarity_cells == 24000
result = {"status": "ALL540_INPUT_TENSORS1080_FEATURES24000_RETRIEVAL_SCORES_THRESHOLDS_AND960_EVALUATION_DECISIONS_RECOMPUTED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "input_tensor_hashes_checked": 540,
          "feature_vectors_checked": 1080, "query_retrieval_rows_checked": retrieval_rows,
          "registered_identity_score_cells_checked": similarity_cells, "evaluation_decisions_checked": 960,
          "maximum_double_normalization_difference": max_normalized_error, "maximum_independent_score_difference": max_score_error,
          "both_thresholds_frozen_before_evaluation_feature_generation": True, "calibration": calibration_counts,
          "outcomes": verified_outcomes, "per_identity_bootstrap_all4_conditions_reproduced": True,
          "new_model_forwards": 0, "new_training_updates": 0, "whole_goal_complete": False}
output = ROOT / "results/independent_verification.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
