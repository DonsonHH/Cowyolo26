from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = load(ROOT / "protocol/run_v1.json")
source = Path(plan["source_directory"])
for relative, digest in plan["source_file_hashes"].items():
    assert sha(source / relative) == digest
summary = load(ROOT / "results/summary.json")
independent = load(ROOT / "results/independent_verification.json")
assert independent["GT_rows"] == 4050 and independent["FP_rows"] == 173 and independent["maximum_matching_certificates"] == 5400
assert len(summary["conditions"]) == 9 and summary["new_model_forwards"] == 0
assert all(row["GT_partition"].get("eligible_cow_geometry_unmatched", 0) == 0 for row in summary["conditions"])
assert all(row["maximum_one_to_one_geometry_oracles_not_deployable"]["cow_score0.2_IoU0.5"] == row["fixed_TP"] for row in summary["conditions"])
new = next(row for row in summary["conditions"] if row["condition"] == "new_mosaic050_s192")
assert new["GT_partition"] == {"matched_TP": 86, "cow_score_0_001_to_0_20": 104, "cow_score_below_0_001": 196, "no_geometry_in_retained300": 64}
assert sum(new["GT_geometry_groups"]["interior"].values()) == 186 and new["GT_geometry_groups"]["interior"]["matched_TP"] == 28
assert sum(new["GT_geometry_groups"]["border"].values()) == 264 and new["GT_geometry_groups"]["border"]["matched_TP"] == 58
visual = load(ROOT / "results/visual_review.json")
assert visual["actually_viewed"] and visual["panels"] == 13
for row in visual["files"]:
    assert row["actually_viewed"] and sha(Path(row["file"])) == row["sha256"]
assert load(ROOT / "results/witness_raw_verification.json")["witness_markers_checked"] == 7
documents = [ROOT / "计划与验收.md", ROOT / "检测对象与标注使用约定.md", ROOT / "低召回分解与检测对象约定.md"]
links = []
for path in documents:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        target = target.strip("<>")
        if not target.startswith(("http:", "https:")):
            linked = (path.parent / unquote(target)).resolve()
            assert linked.exists()
            links.append(str(linked))
evidence = [path for directory in ["tools", "protocol", "results"] for path in (ROOT / directory).rglob("*") if path.is_file() and path.suffix in [".py", ".json"]]
result = {"status": "NINE_RETAINED_OUTPUT_ERROR_PARTITIONS4050_GT173_FP5400_CERTIFIED_MATCHINGS_AND13_NATIVE_CASES_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "conditions": 9, "GT_condition_rows": 4050, "FP_condition_rows": 173,
          "independently_certified_maximum_matching_graphs": 5400, "all9_fixed_conf0_20_matching_upper_bounds_equal_existing_TP": True,
          "new192_FN_partition_low001_to020_below001_no_geometry": [104, 196, 64],
          "new192_interior_TP_denominator": [28, 186], "new192_border_TP_denominator": [58, 264],
          "old_new192_common_lost_gained_GT_counts": [71, 21, 15],
          "actual_panels_viewed": 13, "score_band_witnesses_independently_raw_checked": 7,
          "object_scope_contract_written_no_automatic_relabeling": True,
          "all450_original_positive_GT_kept": True, "GT_oracle_reported_as_deployable_improvement": False,
          "new_model_forwards": 0, "new_training_updates": 0, "new_board_forwards": 0,
          "new_independent_test_or_passage_identity_GT": False, "default_model_tracker_or_threshold_changed": False,
          "documents": [{"path": str(path), "sha256": sha(path)} for path in documents],
          "evidence_hashes": {path.relative_to(ROOT).as_posix(): sha(path) for path in evidence},
          "local_links_checked": len(links), "assistant_self_review_not_independent_human": True, "whole_goal_complete": False}
target = ROOT / "results/final_review.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key not in ["documents", "evidence_hashes"]}))
