from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "cows2021_identity_eval_20261030"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


protocol = load(ROOT / "protocol/run_v1.json")
plan = load(SOURCE / "protocol/run_v1.json")
assert hashlib.sha256((SOURCE / "protocol/run_v1.json").read_bytes()).hexdigest() == protocol["source_protocol_sha256"]
groups = load(ROOT / "results/decisions.json")
summary = load(ROOT / "results/summary.json")
assert len(groups) == len(summary["conditions"]) == 16
selected = [row for row in plan["selected_images"] if row["phase"] == "evaluation"]
checked, cells = 0, 0
for group in groups:
    fold = protocol["fold_IDs"][group["fold"]]
    allowed = fold if group["gallery_IDs"] == 20 else plan["roles"]["evaluation_registered"]
    model = group["model"]
    with np.load(SOURCE / "delivery/results/evaluation/evaluation" / model / "all_features.npz") as archive:
        features = archive["normalized"].copy()
    gallery = [index for index, row in enumerate(selected) if row["purpose"] == "gallery" and row["publisher_identity"] in allowed]
    counts = {key: 0 for key in ["C", "W", "U", "known_closed_Top1", "unknown_FA"]}
    expected_queries = [index for index, row in enumerate(selected) if row["purpose"] != "gallery" and (not row["is_known"] or row["publisher_identity"] in fold)]
    assert expected_queries == [row["evaluation_source_index"] for row in group["rows"]]
    for row in group["rows"]:
        qi = row["evaluation_source_index"]
        independent = {}
        for gi in gallery:
            value = float(np.dot(features[qi].astype(float), features[gi].astype(float)))
            identity = selected[gi]["identity_namespace"]
            independent[identity] = max(independent.get(identity, -1.), value)
        assert set(independent) == set(row["all_scores"])
        assert max(abs(independent[key] - row["all_scores"][key]) for key in independent) < 1e-12
        winner = sorted(independent, key=lambda identity: (-independent[identity], identity))[0]
        assert winner == row["predicted_id"] and abs(independent[winner] - row["similarity"]) < 1e-12
        assert row["accepted"] == (row["similarity"] >= group["threshold"])
        assert row["identity"] == selected[qi]["identity_namespace"]
        if row["is_known"]:
            counts["known_closed_Top1"] += winner == row["identity"]
            if not row["accepted"]:
                counts["U"] += 1
            elif winner == row["identity"]:
                counts["C"] += 1
            else:
                counts["W"] += 1
        else:
            counts["unknown_FA"] += row["accepted"]
        checked += 1
        cells += len(independent)
    actual = next(row for row in summary["conditions"] if all(row[key] == group[key] for key in ["model", "fold", "gallery_IDs", "threshold_policy"]))
    for key, value in counts.items():
        assert actual[key] == value
for group in groups:
    if group["gallery_IDs"] != 20:
        continue
    larger = next(row for row in groups if row["gallery_IDs"] == 40 and all(row[key] == group[key] for key in ["model", "fold", "threshold_policy"]))
    for small, big in zip(group["rows"], larger["rows"]):
        assert small["evaluation_source_index"] == big["evaluation_source_index"]
        assert set(small["all_scores"]).issubset(big["all_scores"])
        assert all(small["all_scores"][key] == big["all_scores"][key] for key in small["all_scores"])
        assert big["similarity"] >= small["similarity"] and (not small["accepted"] or big["accepted"])
assert checked == 2880 and cells == 86400
result = {"status": "ALL16_GALLERY_CONTROLS2880_DECISIONS86400_ID_SCORE_CELLS_AND_ACCEPTANCE_MONOTONICITY_RECOMPUTED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "query_decisions_checked": checked, "ID_score_cells_checked": cells,
          "same_query_and_threshold_for_registry_expansion": True, "new_model_forwards": 0, "new_threshold_selection": False,
          "repeated_unknown_queries_not_counted_as_independent_animals": True, "whole_goal_complete": False}
output = ROOT / "results/independent_verification.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
