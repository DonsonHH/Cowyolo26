from pathlib import Path
from datetime import date, datetime, timezone
from collections import defaultdict
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
SOURCE = PROJECT / "cows2021_identity_intake_20261030"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


rows = json.loads((SOURCE / "results/test8670_members.json").read_text())
by_id = defaultdict(lambda: defaultdict(list))
for row in rows:
    if row["date"] <= "2020-03-04":
        by_id[row["publisher_identity"]][row["date"]].append(row)
eligible = {}
for identity, dates in by_id.items():
    permitted = sorted(day for day, images in dates.items() if len(images) >= 3)
    if len(permitted) >= 2 and (date.fromisoformat(permitted[-1]) - date.fromisoformat(permitted[0])).days >= 7:
        eligible[identity] = permitted
assert len(eligible) == 156
ranked = sorted(eligible, key=lambda identity: hashlib.sha256(("Cows2021-open-identity-20261030-v1:" + identity).encode()).hexdigest())
roles = {"calibration_registered": ranked[:20], "calibration_unknown": ranked[20:40],
         "evaluation_registered": ranked[40:80], "evaluation_unknown": ranked[80:120]}
assert len(set(sum(roles.values(), []))) == 120


def select_three(images):
    sessions = defaultdict(list)
    for image in images:
        sessions[image["source_session_filename_key"]].append(image)
    session_names = sorted(sessions)
    count = min(3, len(session_names))
    session_indices = [round(index * (len(session_names) - 1) / (count - 1)) for index in range(count)] if count > 1 else [0]
    selected = []
    for index in session_indices:
        candidates = sorted(sessions[session_names[index]], key=lambda row: row["file_name"])
        selected.append(candidates[len(candidates)//2])
    for image in sorted(images, key=lambda row: row["file_name"]):
        if len(selected) == 3:
            break
        if image["archive_member"] not in {row["archive_member"] for row in selected}:
            selected.append(image)
    assert len(selected) == 3
    return sorted(selected, key=lambda row: row["file_name"])


selected = []
for role, identities in roles.items():
    phase = "calibration" if role.startswith("calibration") else "evaluation"
    known = role.endswith("registered")
    for identity in identities:
        dates = eligible[identity]
        for purpose, day in ([("gallery", dates[0]), ("known_query", dates[-1])] if known else [("unknown_query", dates[-1])]):
            for row in select_three(by_id[identity][day]):
                selected.append({**row, "phase": phase, "purpose": purpose, "is_known": known,
                                 "local_relative_file": "input/images/" + identity + "/" + row["file_name"],
                                 "registered_gallery_date": dates[0] if known else None,
                                 "query_date": dates[-1], "day_gap": (date.fromisoformat(dates[-1])-date.fromisoformat(dates[0])).days})
assert len(selected) == len({row["archive_member"] for row in selected}) == 540
assert sum(row["phase"] == "calibration" for row in selected) == 180
assert sum(row["phase"] == "evaluation" for row in selected) == 360
assert all(row["date"] <= "2020-03-04" and row["day_gap"] >= 7 for row in selected)
source_plan = json.loads((PROJECT / "pynq_identity_ncnn_20261029/protocol/encoder_v1.json").read_text())
base = json.loads((PROJECT / "identity_training_20261026/delivery/results/study/B_letterbox_frozen/summary.json").read_text())
models = [{"name": "B_ImageNet_letterbox", "checkpoint": base["checkpoint"], "checkpoint_sha256": base["checkpoint_sha256"],
           "checkpoint_kind": "full_torchvision_mobilenet_state", "original_MultiCam_threshold": base["threshold"]["threshold"]},
          {"name": "C_trained_seed26", "checkpoint": source_plan["encoder_condition"]["checkpoint"],
           "checkpoint_sha256": source_plan["encoder_condition"]["checkpoint_sha256"],
           "checkpoint_kind": "sequential_features_avgpool_flatten_state", "original_MultiCam_threshold": source_plan["fixed_threshold"]}]
protocol = {"status": "FROZEN_BEFORE_FIRST_COWS2021_IDENTITY_TEST_JPEG_REQUEST_OR_FEATURE_FORWARD",
            "created_UTC": datetime.now(timezone.utc).isoformat(), "eligible_IDs": 156, "roles": roles,
            "identity_ranking_prefix": "Cows2021-open-identity-20261030-v1:", "maximum_capture_date_inclusive": "2020-03-04",
            "reserved_pixels_from_2020_03_05_through_2020_03_11_excluded": True,
            "selected_images": selected, "unique_image_count": 540, "models": models,
            "source_base_URL": "https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Test/",
            "source_intake_final_review_sha256": sha(SOURCE / "results/final_review.json"),
            "source_metadata_sha256": sha(SOURCE / "results/metadata_audit_v2.json"),
            "body_tensor_module_sha256": sha(PROJECT / "pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py"),
            "metrics_module_sha256": sha(PROJECT / "identity_training_20261026/tools/identity_metrics.py"),
            "maximum_unknown_calibration_empirical_FAR": .05, "calibration_unknown_queries": 60,
            "threshold_rule": "calibrate_threshold frozen existing module, maximise known correct, minimise known wrong, higher threshold; no evaluation features before joint threshold freeze",
            "expected_calibration_model_image_forwards": 360, "expected_evaluation_model_image_forwards": 720,
            "expected_all_model_image_forwards": 1080, "inference_batch": 12, "expected_forward_calls": 90, "warmup_forwards": 0,
            "gallery_references_per_ID": 3, "query_images_per_ID": 3,
            "bootstrap": {"cluster": "publisher_cow_ID", "seed": 26, "draws": 2000},
            "qualification_tensor_indices": [0, 60, 120, 180, 300, 420, 539],
            "qualitative_source_indices": [0, 59, 60, 119, 120, 179, 180, 299, 300, 419, 420, 539],
            "plan_sha256": sha(ROOT / "计划与验收.md"), "new_training_updates": 0, "new_board_forwards": 0,
            "physical_cross_dataset_individual_disjointness_proven": False,
            "author_curated_crops_not_full_passage_or_12_current_event_IDs": True, "whole_goal_complete": False}
output = ROOT / "protocol/run_v1.json"
output.parent.mkdir(exist_ok=False)
output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"protocol_SHA256": sha(output), "images": 540, "IDs": 120, "role_ID_counts": {key: len(value) for key,value in roles.items()},
                  "latest_date": max(row["date"] for row in selected), "planned_model_image_forwards": 1080, "new_pixels_read": 0}))
