from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "colo_eval_20261030"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = json.loads((SOURCE / "protocol/run_v1.json").read_text(encoding="utf-8"))
files = ["protocol/run_v1.json", "input/GT_valid450_clipped.json", "results/final_review.json", "results/test50_acquisition.json"]
for model in plan["models"]:
    for size in plan["sizes"]:
        name = model["name"] + "_s" + str(size)
        files += ["delivery/results/evaluation/" + name + "/" + file for file in ["all_raw.npz", "all_decoded_predictions.json", "fixed_clipped.json"]]
protocol = {"status": "FROZEN_BEFORE_RETAINED_OUTPUT_ERROR_PARTITION_OR_ORACLE_CALCULATION",
            "created_UTC": datetime.now(timezone.utc).isoformat(), "source_directory": str(SOURCE),
            "source_file_hashes": {file: sha(SOURCE / file) for file in files},
            "models": plan["models"], "sizes": [192, 256, 320],
            "IoU_diagnostic_levels": [.30, .50, .75], "cow_score_diagnostic_levels": [.20, .001, None],
            "GT_groups": {"border_distance_px": 1., "short_side_input_edges_px": [16., 24.]},
            "FN_partition_priority": ["eligible_cow_geometry_unmatched", "cow_score_0_001_to_0_20",
                                      "cow_score_below_0_001", "only_other_class_geometry", "no_geometry_in_retained300"],
            "qualitative_selection": "For official, old_rot192, new_mosaic050 at192: first annotationID of every nonempty FN category, then first FP by frozen image order and raw index",
            "plan_sha256": sha(ROOT / "计划与验收.md"), "new_model_forwards": 0,
            "new_training_updates": 0, "new_board_forwards": 0,
            "GT_oracle_is_deployment_metric": False, "new_independent_test": False, "whole_goal_complete": False}
output = ROOT / "protocol/run_v1.json"
output.parent.mkdir(exist_ok=False)
output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"source_files_frozen": len(files), "new_model_forwards": 0, "protocol_SHA256": sha(output)}))
