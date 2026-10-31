from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib, json, os, socket, sys, time
import numpy as np
from PIL import Image
import PIL
import torch
import torchvision
from torchvision.models import mobilenet_v3_small

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from frozen_body_tensor import body_tensor
from frozen_identity_metrics import calibrate_threshold, summarise, cluster_intervals
from frozen_training_primitives import BodyTransform


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    assert not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def retrieve(records, features):
    gallery_indices = [index for index, row in enumerate(records) if row["purpose"] == "gallery"]
    query_indices = [index for index, row in enumerate(records) if row["purpose"] != "gallery"]
    labels = sorted({records[index]["identity_namespace"] for index in gallery_indices})
    scores = features[query_indices].astype(float) @ features[gallery_indices].astype(float).T
    by_identity = np.stack([np.max(scores[:, [position for position, index in enumerate(gallery_indices) if records[index]["identity_namespace"] == label]], axis=1) for label in labels], axis=1)
    rows = []
    for position, index in enumerate(query_indices):
        order = sorted(range(len(labels)), key=lambda item: (-by_identity[position, item], labels[item]))
        source = records[index]
        rows.append({"source_index": source["source_index"], "identity": source["identity_namespace"], "publisher_identity": source["publisher_identity"],
                     "date": source["date"], "purpose": source["purpose"], "is_known": source["is_known"],
                     "predicted_id": labels[order[0]], "similarity": float(by_identity[position, order[0]]),
                     "top5_IDs": [labels[i] for i in order[:5]], "all_registered_identity_scores": {label: float(value) for label, value in zip(labels, by_identity[position])}})
    return rows


assert os.environ.get("SLURM_JOB_ID") and socket.gethostname() != "mu01"
torch.set_num_threads(4)
torch.set_num_interop_threads(1)
torch.manual_seed(26)
torch.use_deterministic_algorithms(True)
plan = load(ROOT / "protocol/run_v1.json")
execution = load(ROOT / "protocol/execution_v1.json")
assert execution["protocol_sha256"] == sha(ROOT / "protocol/run_v1.json")
for name, digest in execution["files_sha256"].items():
    assert sha(ROOT / name) == digest, name
assert torch.__version__ == "2.8.0+cu128" and PIL.__version__ == "11.3.0"
acquisition = load(ROOT / "results/acquisition_v2.json")
by_source = {row["index"]: row for row in acquisition["records"]}
assert len(by_source) == 540 and load(ROOT / "results/pixel_admission.json")["admitted_for_fixed_feature_study"]
out = ROOT / "results/evaluation"
out.mkdir(exist_ok=False)
anchor = out / "input_tensor_anchors"
anchor.mkdir()
active = {}
forward_images = forward_calls = 0
counts = Counter()
timeline = []
all_input_hashes = {}
models = {}
old_transform = BodyTransform(augment=False)


def hook(module, args):
    global forward_images, forward_calls
    value = args[0]
    assert value.shape[1:] == (3, 224, 224) and value.dtype == torch.float32 and value.device.type == "cpu"
    assert len(value) <= 12
    forward_images += len(value)
    forward_calls += 1
    counts[active["model"] + ":" + active["phase"]] += len(value)


for spec in plan["models"]:
    checkpoint = Path(spec["checkpoint"])
    assert sha(checkpoint) == spec["checkpoint_sha256"]
    full = mobilenet_v3_small(weights=None)
    if spec["checkpoint_kind"] == "full_torchvision_mobilenet_state":
        full.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    encoder = torch.nn.Sequential(full.features, full.avgpool, torch.nn.Flatten()).eval()
    if spec["checkpoint_kind"] == "sequential_features_avgpool_flatten_state":
        encoder.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    encoder.register_forward_pre_hook(hook)
    models[spec["name"]] = encoder


def extract(spec, phase):
    active.update({"model": spec["name"], "phase": phase})
    records = [{**row, "source_index": index} for index, row in enumerate(plan["selected_images"]) if row["phase"] == phase]
    raw_features, image_hashes = [], []
    for start in range(0, len(records), 12):
        batch = records[start:start+12]
        tensors = []
        for row in batch:
            source_index = row["source_index"]
            path = ROOT / row["local_relative_file"]
            assert sha(path) == by_source[source_index]["sha256"]
            with Image.open(path) as image:
                image.load()
                image = image.convert("RGB")
                value = body_tensor(image)
                previous_transform = old_transform(image).unsqueeze(0).contiguous().numpy()
            assert value.tobytes() == previous_transform.tobytes(), ("preprocess", source_index)
            digest = hashlib.sha256(value.tobytes()).hexdigest()
            if source_index in all_input_hashes:
                assert all_input_hashes[source_index] == digest
            else:
                all_input_hashes[source_index] = digest
                if source_index in plan["qualification_tensor_indices"]:
                    np.savez_compressed(anchor / ("image" + str(source_index) + ".npz"), input=value)
            tensors.append(value[0])
            image_hashes.append({"source_index": source_index, "input_tensor_sha256": digest})
        with torch.inference_mode():
            values = models[spec["name"]](torch.from_numpy(np.stack(tensors))).detach().cpu().contiguous().numpy()
        assert values.shape == (len(batch), 576) and values.dtype == np.float32 and np.isfinite(values).all()
        raw_features.extend(values.copy())
    raw = np.stack(raw_features)
    normalized = raw / np.linalg.norm(raw, axis=1, keepdims=True)
    assert np.isfinite(normalized).all()
    folder = out / phase / spec["name"]
    folder.mkdir(parents=True)
    np.savez_compressed(folder / "all_features.npz", raw=raw, normalized=normalized)
    save(folder / "source_indices_and_input_hashes.json", image_hashes)
    timeline.append({"model": spec["name"], "phase": phase, "source_image_forwards": len(records), "finished_UTC": datetime.now(timezone.utc).isoformat(),
                     "cumulative_source_image_forwards": forward_images, "feature_file_sha256": sha(folder / "all_features.npz")})
    print(json.dumps(timeline[-1]), flush=True)
    return records, normalized


calibration = []
for spec in plan["models"]:
    records, features = extract(spec, "calibration")
    predictions = retrieve(records, features)
    threshold = calibrate_threshold([row["similarity"] for row in predictions], [row["predicted_id"] for row in predictions],
                                    [row["identity"] for row in predictions], [row["is_known"] for row in predictions], .05)
    save(out / "calibration" / spec["name"] / "retrieval.json", predictions)
    calibration.append({"model": spec["name"], "checkpoint_sha256": spec["checkpoint_sha256"], "threshold": threshold,
                        "original_MultiCam_threshold": spec["original_MultiCam_threshold"],
                        "calibration_feature_sha256": sha(out / "calibration" / spec["name"] / "all_features.npz"),
                        "calibration_retrieval_sha256": sha(out / "calibration" / spec["name"] / "retrieval.json")})
assert forward_images == 360 and forward_calls == 30 and all("evaluation" not in key for key in counts)
freeze = {"status": "BOTH_MODELS_THRESHOLDS_FROZEN_BEFORE_ANY_EVALUATION_FEATURE_FORWARD", "created_UTC": datetime.now(timezone.utc).isoformat(),
          "models": calibration, "source_model_image_forwards_at_freeze": forward_images, "network_calls_at_freeze": forward_calls,
          "evaluation_model_image_forwards_at_freeze": 0, "protocol_sha256": sha(ROOT / "protocol/run_v1.json")}
save(out / "both_thresholds_frozen.json", freeze)
threshold_freeze_sha = sha(out / "both_thresholds_frozen.json")
outcomes = []
for spec in plan["models"]:
    assert sha(out / "both_thresholds_frozen.json") == threshold_freeze_sha
    records, features = extract(spec, "evaluation")
    predictions = retrieve(records, features)
    save(out / "evaluation" / spec["name"] / "retrieval_unthresholded.json", predictions)
    frozen_model = next(row for row in calibration if row["model"] == spec["name"])
    for policy, threshold in [("original_MultiCam", spec["original_MultiCam_threshold"]), ("Cows2021_calibrated", frozen_model["threshold"]["threshold"])]:
        decided = [{**row, "accepted": row["similarity"] >= threshold} for row in predictions]
        metrics = summarise(decided)
        known = [row for row in decided if row["is_known"]]
        metrics["known_closed_top5_correct"] = sum(row["identity"] in row["top5_IDs"] for row in known)
        metrics["known_closed_top5_accuracy"] = metrics["known_closed_top5_correct"] / len(known)
        intervals = cluster_intervals(metrics["per_identity"], seed=26, draws=2000)
        save(out / "evaluation" / spec["name"] / (policy + "_decisions.json"), decided)
        outcomes.append({"model": spec["name"], "threshold_policy": policy, "threshold": threshold, "metrics": metrics, "ID_cluster_intervals": intervals})
assert forward_images == 1080 and forward_calls == 90 and len(all_input_hashes) == 540
summary = {"status": "TWO_FIXED_ENCODERS540_CROPS1080_CPU_FORWARDS_CALIBRATION_THEN_EVALUATION_COMPLETE",
           "created_UTC": datetime.now(timezone.utc).isoformat(), "Slurm_job_id": os.environ["SLURM_JOB_ID"], "host": socket.gethostname(),
           "protocol_sha256": sha(ROOT / "protocol/run_v1.json"), "actual_model_image_forwards": forward_images, "actual_network_calls": forward_calls,
           "by_model_and_phase_forwards": dict(counts), "warmup_forwards": 0, "calibration_threshold_freeze_sha256": threshold_freeze_sha,
           "timeline": timeline, "calibration": calibration, "outcomes": outcomes,
           "preprocessing_byte_exact_to_frozen_original_BodyTransform": True, "actual_input_hashes_equal_for_both_models": 540,
           "environment": {"torch": torch.__version__, "torchvision": torchvision.__version__, "PIL": PIL.__version__, "numpy": np.__version__},
           "new_training_updates": 0, "new_board_forwards": 0, "original12_events_permanent_IDs_obtained": False,
           "whole_goal_complete": False}
save(out / "summary.json", summary)
print(json.dumps({key: value for key, value in summary.items() if key not in ["timeline", "calibration", "outcomes"]}), flush=True)
