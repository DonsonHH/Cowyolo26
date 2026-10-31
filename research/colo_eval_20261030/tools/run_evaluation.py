from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import os
import socket
import sys
import time
import cv2
import numpy as np
from PIL import Image
import PIL
import torch
import ultralytics
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT / "vendor"))
from metrics import decode, fixed_metrics, coco_metrics


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert os.environ.get("SLURM_JOB_ID") and socket.gethostname() != "mu01"
cv2.setNumThreads(1)
torch.set_num_threads(4)
torch.set_num_interop_threads(1)
torch.manual_seed(26)
torch.use_deterministic_algorithms(True)
plan = load(ROOT / "protocol/run_v1.json")
execution = load(ROOT / "protocol/execution_v1.json")
assert execution["protocol_sha256"] == sha(ROOT / "protocol/run_v1.json")
for relative, digest in execution["files_sha256"].items():
    assert sha(ROOT / relative) == digest, relative
assert torch.__version__ == "2.8.0+cu128" and ultralytics.__version__ == "8.4.63"
out = ROOT / "results/evaluation"
out.mkdir(parents=True, exist_ok=False)
acquisition = load(ROOT / "results/test50_acquisition.json")
assert acquisition["protocol_sha256"] == sha(ROOT / "protocol/run_v1.json")
source_records = {row["file_name"]: row for row in acquisition["records"]}
images = []
for item in plan["images"]:
    path = ROOT / "input/test50" / item["file_name"]
    assert sha(path) == source_records[path.name]["sha256"]
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"))
    assert rgb.shape == (640, 640, 3) and hashlib.sha256(rgb.tobytes()).hexdigest() == source_records[path.name]["RGB_sha256"]
    images.append(rgb.copy())
total_images = 0
total_calls = 0
per_condition = Counter()
active = {}
input_hashes = {}
started = time.monotonic()


def record_forward(module, args):
    global total_images, total_calls
    value = args[0]
    assert value.dtype == torch.float32 and value.device.type == "cpu" and len(value) == 10
    assert tuple(value.shape[1:]) == (3, active["size"], active["size"])
    total_images += len(value)
    total_calls += 1
    per_condition[active["name"]] += len(value)


for model_spec in plan["models"]:
    checkpoint = PROJECT / model_spec["relative_checkpoint"]
    assert sha(checkpoint) == model_spec["sha256"]
    wrapper = YOLO(str(checkpoint))
    assert wrapper.names[model_spec["cow_class"]] == "cow"
    network = wrapper.model.float().cpu().eval()
    assert network.model[-1].end2end
    handle = network.register_forward_pre_hook(record_forward)
    for size in plan["sizes"]:
        name = model_spec["name"] + "_s" + str(size)
        active.update({"name": name, "size": size})
        folder = out / name
        folder.mkdir()
        raws = []
        hash_rows = []
        for start in range(0, 50, 10):
            tensors = [np.ascontiguousarray(cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR).transpose(2, 0, 1), dtype=np.float32) / np.float32(255.) for rgb in images[start:start + 10]]
            for offset, value in enumerate(tensors):
                item = plan["images"][start + offset]
                digest = hashlib.sha256(value.tobytes()).hexdigest()
                key = (size, item["file_name"])
                if key in input_hashes:
                    assert digest == input_hashes[key]
                else:
                    input_hashes[key] = digest
                hash_rows.append({"file_name": item["file_name"], "image_id": item["image"]["id"], "tensor_sha256": digest})
            tensor = torch.from_numpy(np.stack(tensors))
            with torch.inference_mode():
                result = network(tensor)
            raw = result if isinstance(result, torch.Tensor) else result[0]
            assert raw.shape == (10, 300, 6) and raw.dtype == torch.float32
            array = raw.detach().cpu().contiguous().numpy()
            assert np.isfinite(array).all()
            raws.extend(array.copy())
        np.savez_compressed(folder / "all_raw.npz", raw=np.stack(raws))
        (folder / "input_hashes.json").write_text(json.dumps(hash_rows, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"condition_done": name, "source_image_forwards": total_images, "network_calls": total_calls}), flush=True)
    handle.remove()
assert total_images == 450 and total_calls == 45 and len(input_hashes) == 150
assert len(per_condition) == 9 and all(value == 50 for value in per_condition.values())
freeze = {"status": "ALL9_CONDITIONS450_RAW_PERSISTED_BEFORE_SCORING", "created_UTC": datetime.now(timezone.utc).isoformat(),
          "files": {str(path.relative_to(out)): sha(path) for path in out.rglob("*") if path.is_file()},
          "actual_source_image_forwards": total_images, "actual_network_calls": total_calls, "warmup_forwards": 0,
          "actual_model_image_forwards_by_condition": dict(per_condition)}
(out / "all_raw_frozen_before_scoring.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
metrics = []
for model_spec in plan["models"]:
    for size in plan["sizes"]:
        name = model_spec["name"] + "_s" + str(size)
        folder = out / name
        with np.load(folder / "all_raw.npz") as data:
            raws = data["raw"].copy()
        predictions = {item["image"]["id"]: decode(raw, size, model_spec["cow_class"], plan["COCO_score_threshold"]) for item, raw in zip(plan["images"], raws)}
        (folder / "all_decoded_predictions.json").write_text(json.dumps(predictions, indent=2) + "\n", encoding="utf-8")
        for policy, gt_file in [("clipped", "GT_valid450_clipped.json"), ("unclipped", "GT_valid450_unclipped.json")]:
            gt = load(ROOT / "input" / gt_file)
            fixed = fixed_metrics(gt["images"], gt["annotations"], predictions, plan["fixed_score_threshold"], plan["fixed_IoU_threshold"])
            (folder / ("fixed_" + policy + ".json")).write_text(json.dumps(fixed, indent=2) + "\n", encoding="utf-8")
            for light in ["all", "daylight", "indoorlight", "infrared"]:
                ids = [row["image"]["id"] for row in plan["images"] if light == "all" or row["lighting"] == light]
                coco = coco_metrics(gt, predictions, ids, folder / ("COCO_" + policy + "_" + light + ".npz"))
                metrics.append({"condition": name, "model": model_spec["name"], "input_size": size, "GT_policy": policy,
                                "lighting": light, "images": len(ids), "references": sum(row["image_id"] in ids for row in gt["annotations"]),
                                **coco, "fixed_all_images": {key: value for key, value in fixed.items() if key != "records"} if light == "all" else None})
import pycocotools.cocoeval
summary = {"status": "NINE_FROZEN_MODEL_SIZE_CONDITIONS450_CPU_FORWARDS_AND72_COCO_METRIC_GROUPS_COMPLETE",
           "created_UTC": datetime.now(timezone.utc).isoformat(), "Slurm_job_id": os.environ["SLURM_JOB_ID"],
           "host": socket.gethostname(), "elapsed_s_not_board_benchmark": time.monotonic() - started,
           "protocol_sha256": sha(ROOT / "protocol/run_v1.json"), "actual_source_image_forwards": total_images,
           "actual_network_forward_calls": total_calls, "warmup_forwards": 0, "models": plan["models"],
           "environment": {"torch": torch.__version__, "ultralytics": ultralytics.__version__, "numpy": np.__version__, "PIL": PIL.__version__, "cv2": cv2.__version__,
                           "COCOeval_file_sha256": sha(Path(pycocotools.cocoeval.__file__))},
           "metrics": metrics, "new_training_updates": 0, "new_board_forwards": 0,
           "permanent_identity_or_passage_accuracy_proven": False, "global_default_changed": False, "whole_goal_complete": False}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in summary.items() if key not in ["metrics", "models"]}), flush=True)
