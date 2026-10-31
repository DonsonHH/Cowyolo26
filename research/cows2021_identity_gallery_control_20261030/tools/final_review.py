from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


summary = load(ROOT / "results/summary.json")
verified = load(ROOT / "results/independent_verification.json")
assert len(summary["conditions"]) == 16 and verified["query_decisions_checked"] == 2880 and verified["ID_score_cells_checked"] == 86400
counts = [row["unknown_FA"] for row in summary["conditions"] if row["model"] == "C_trained_seed26" and row["threshold_policy"] == "Cows2021_calibrated"]
assert counts == [12, 20, 16, 20]
documents = [ROOT / "计划与验收.md", ROOT / "图库规模控制与拒识限制.md"]
local = []
for document in documents:
    for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        path = (document.parent / target.strip("<>")).resolve()
        assert path.exists()
        local.append(str(path))
evidence = [path for name in ["tools", "protocol", "results"] for path in (ROOT / name).rglob("*") if path.is_file()]
result = {"status": "POSTHOC20_VS40_ID_GALLERIES16_FIXED_CONTROLS2880_DECISIONS_AND_SCOPE_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "conditions": 16, "query_decisions": 2880,
          "independently_recomputed_ID_score_cells": 86400, "score_monotonicity_pairs": 720,
          "current_encoder_calibrated_FA_by_fold20_then40": [12, 20, 16, 20], "unknown_queries_per_condition": 120,
          "same_query_and_threshold_within_gallery_expansion": True, "both_folds_preserved": True,
          "posthoc_control_and_repeated_unknown_queries_disclosed": True,
          "new_model_forwards": 0, "new_training_updates": 0, "new_threshold_search": False,
          "new_independent_test": False, "new_deployment_policy_adopted": False,
          "documents": [{"path": str(path), "sha256": sha(path)} for path in documents],
          "evidence_hashes": {path.relative_to(ROOT).as_posix(): sha(path) for path in evidence},
          "local_links_checked": len(local), "assistant_self_review_not_independent_human": True, "whole_goal_complete": False}
output = ROOT / "results/final_review.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: value for key,value in result.items() if key not in ["documents", "evidence_hashes"]}))
