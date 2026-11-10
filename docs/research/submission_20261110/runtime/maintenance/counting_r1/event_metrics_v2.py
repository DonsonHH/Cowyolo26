"""Versioned directional event-set scoring with optional independent correspondence.

No detector dependencies. Run from repository root with:
python -m maintenance.counting_r1.event_metrics_v2 reference.json predictions.json
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

VERSION = "directional-event-set-v2.1"
DIRECTIONS = ("A->B", "B->A")


def _prepare(events):
    rows = []
    identified = set()
    for index, event in enumerate(events):
        time = float(event["time_s"])
        if not math.isfinite(time) or event["direction"] not in DIRECTIONS:
            raise ValueError("Events need finite time_s and direction A->B or B->A")
        scope = (str(event.get("video_id", "")), str(event.get("session_id", "")))
        event_id = event.get('event_id')
        if event_id is not None:
            if not isinstance(event_id, str) or not event_id.strip() or (scope, event_id) in identified:
                raise ValueError('Explicit event_id must be nonempty and unique within video/session scope')
            identified.add((scope, event_id))
        # Canonical ordering is independent of input order. Byte-identical duplicates
        # are indistinguishable; indices still refer to their original input rows.
        key = json.dumps(event, sort_keys=True, ensure_ascii=False, allow_nan=False)
        rows.append({"index": index, "event": event, "time": time,
                     "scope": scope, "key": (time, key)})
    return rows


def _match_group(reference, prediction, tolerance):
    """Maximum cardinality, then minimum absolute time error, for sorted times.

    Absolute-distance cost on a line admits an uncrossed optimum. A crossed
    feasible pair can be uncrossed without losing feasibility or increasing cost.
    DP therefore considers all needed optima without a floating dummy penalty.
    """
    reference = sorted(reference, key=lambda row: row["key"])
    prediction = sorted(prediction, key=lambda row: row["key"])
    n, m = len(reference), len(prediction)
    scores = [[(0, 0.0) for _ in range(m + 1)] for _ in range(n + 1)]
    actions = [[None for _ in range(m + 1)] for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            # Lower priority wins exact ties after canonical sorting.
            choices = [(scores[i - 1][j], 1, "skip_reference"),
                       (scores[i][j - 1], 2, "skip_prediction")]
            error = abs(reference[i - 1]["time"] - prediction[j - 1]["time"])
            if error <= tolerance:
                count, cost = scores[i - 1][j - 1]
                choices.append(((count + 1, cost + error), 0, "match"))
            best = min(choices, key=lambda item: (-item[0][0], item[0][1], item[1]))
            scores[i][j], _, actions[i][j] = best
    pairs = []
    i, j = n, m
    while i and j:
        action = actions[i][j]
        if action == "match":
            pairs.append((reference[i - 1], prediction[j - 1]))
            i -= 1
            j -= 1
        elif action == "skip_reference":
            i -= 1
        else:
            j -= 1
    return list(reversed(pairs))


def _metrics(n, m, tp):
    return {"reference_events": n, "predicted_events": m, "TP": tp,
            "FP": m - tp, "FN": n - tp,
            "precision": tp / m if m else None,
            "recall": tp / n if n else None,
            "f1": 2 * tp / (n + m) if n + m else None,
            "count_error": m - n, "absolute_count_error": abs(m - n)}


def _physical_correspondence(reference, prediction, physical_pairs):
    """Judge direction only for independently reviewed one-to-one physical pairs."""
    result = {"status": "UNDETERMINED_WITHOUT_INDEPENDENT_CORRESPONDENCE",
              "evaluated_pairs": 0, "correct_direction_pairs": None,
              "wrong_direction_pairs": None,
              "unpaired_reference_events": len(reference),
              "unpaired_prediction_events": len(prediction), "pairs": []}
    if not physical_pairs:
        return result
    by_id = []
    for rows in (reference, prediction):
        mapping = {}
        for row in rows:
            event_id = row["event"].get("event_id")
            if not isinstance(event_id, str) or not event_id or event_id in mapping:
                raise ValueError("Independent correspondence needs unique nonempty event_id on both sides")
            mapping[event_id] = row
        by_id.append(mapping)
    used_r, used_p, pairs = set(), set(), []
    for link in physical_pairs:
        if (link.get("independently_verified") is not True
                or link.get("evidence_type") not in {"video_review", "spatial_correspondence", "trajectory_correspondence"}
                or not isinstance(link.get("evidence"), str) or not link["evidence"].strip()):
            raise ValueError("Physical links require independent review and concrete spatial/trajectory/video evidence")
        rid, pid = link["reference_event_id"], link["prediction_event_id"]
        if rid in used_r or pid in used_p:
            raise ValueError("Physical correspondence must be one-to-one")
        r, p = by_id[0][rid], by_id[1][pid]
        if r["scope"] != p["scope"]:
            raise ValueError("Physical correspondence cannot cross video/session scope")
        used_r.add(rid)
        used_p.add(pid)
        pairs.append({**link, "direction_correct": r["event"]["direction"] == p["event"]["direction"]})
    pairs.sort(key=lambda row: (row["reference_event_id"], row["prediction_event_id"]))
    correct = sum(row["direction_correct"] for row in pairs)
    result.update(status="INDEPENDENT_CORRESPONDENCE_ONLY", evaluated_pairs=len(pairs),
                  correct_direction_pairs=correct, wrong_direction_pairs=len(pairs) - correct,
                  unpaired_reference_events=len(reference) - len(pairs),
                  unpaired_prediction_events=len(prediction) - len(pairs), pairs=pairs)
    return result


def evaluate_events(reference, prediction, tolerance_s=2.0, physical_pairs=None):
    """Score complete events; callers predeclare scope, censoring and time tolerance.

    Missing video/session identifiers mean one shared scope. Supplying these
    identifiers prevents assignment across sessions. Ambiguous candidate sets are
    reported, never silently removed from the directional event denominators.
    """
    tolerance_s = float(tolerance_s)
    if not math.isfinite(tolerance_s) or tolerance_s <= 0:
        raise ValueError("Positive finite tolerance required")
    reference, prediction = _prepare(reference), _prepare(prediction)
    groups_r, groups_p = defaultdict(list), defaultdict(list)
    for rows, groups in ((reference, groups_r), (prediction, groups_p)):
        for row in rows:
            groups[(row["scope"], row["event"]["direction"])].append(row)
    matched = []
    for group in sorted(groups_r.keys() | groups_p.keys()):
        matched.extend(_match_group(groups_r[group], groups_p[group], tolerance_s))

    # All temporal candidates are evidence of possible physical ambiguity, including
    # opposite directions. Degree>1 is a conservative flag, not an optimality claim.
    candidates_r, candidates_p = defaultdict(list), defaultdict(list)
    for r in reference:
        for p in prediction:
            if r["scope"] == p["scope"] and abs(r["time"] - p["time"]) <= tolerance_s:
                candidates_r[r["index"]].append(p["index"])
                candidates_p[p["index"]].append(r["index"])
    pairs = []
    for r, p in matched:
        pairs.append({"reference_index": r["index"], "prediction_index": p["index"],
                      "reference_event_id": r["event"].get("event_id"),
                      "prediction_event_id": p["event"].get("event_id"),
                      "video_id": r["scope"][0], "session_id": r["scope"][1],
                      "direction": r["event"]["direction"],
                      "reference_time_s": r["time"], "prediction_time_s": p["time"],
                      "time_error_s": abs(r["time"] - p["time"]),
                      "ambiguous_temporal_candidates": len(candidates_r[r["index"]]) > 1 or len(candidates_p[p["index"]]) > 1})
    counts = {}
    for direction in DIRECTIONS:
        n = sum(r["event"]["direction"] == direction for r in reference)
        m = sum(p["event"]["direction"] == direction for p in prediction)
        tp = sum(pair["direction"] == direction for pair in pairs)
        counts[direction] = _metrics(n, m, tp)
    used_r = {pair["reference_index"] for pair in pairs}
    used_p = {pair["prediction_index"] for pair in pairs}
    return {"evaluation_version": VERSION, **_metrics(len(reference), len(prediction), len(pairs)),
            "matching_tolerance_s": tolerance_s,
            "assignment_objective": "same scope and direction; maximum cardinality then minimum absolute time error",
            "total_time_error_s": math.fsum(pair["time_error_s"] for pair in pairs),
            "counts": counts, "pairs": pairs,
            "unmatched_reference_indices": [i for i in range(len(reference)) if i not in used_r],
            "unmatched_prediction_indices": [i for i in range(len(prediction)) if i not in used_p],
            "ambiguity": {"policy": "flag temporal candidate competition; retain all events in set metrics",
                          "reference_indices": sorted(i for i, rows in candidates_r.items() if len(rows) > 1),
                          "prediction_indices": sorted(i for i, rows in candidates_p.items() if len(rows) > 1),
                          "does_not_certify_unique_physical_correspondence": True},
            "physical_direction": _physical_correspondence(reference, prediction, physical_pairs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("prediction", type=Path)
    parser.add_argument("--tolerance-s", type=float, default=2.0)
    parser.add_argument("--physical-pairs", type=Path)
    args = parser.parse_args()
    def read(path):
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(value, dict):
            if value.get("review_status") in {"pending", "draft"}:
                raise ValueError("Pending/draft manual records cannot be scored")
            return value["events"]
        return value
    links = json.loads(args.physical_pairs.read_text(encoding="utf-8-sig")) if args.physical_pairs else None
    print(json.dumps(evaluate_events(read(args.reference), read(args.prediction), args.tolerance_s, links),
                     ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
