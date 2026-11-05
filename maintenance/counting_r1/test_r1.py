"""Behavior regressions; all generated observations are software fixtures."""
import ast
import hashlib
import importlib.util
import itertools
import json
import random
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .event_metrics_v2 import evaluate_events
from .tracker import BYTETracker, SecondStageIoUTracker, FROZEN_ROOT, verify_method_scope
from frame_pipeline import Boxes

REPO = Path(__file__).resolve().parents[2]
CONFIG = json.loads((FROZEN_ROOT / "tracker_config.json").read_text())


def event(time, direction="A->B", event_id=None, **extra):
    return {"time_s": time, "direction": direction,
            **({"event_id": event_id} if event_id else {}), **extra}


def boxes(scores, xs=None):
    xs = xs or [20 + 200 * i for i in range(len(scores))]
    return Boxes(np.array([[x, 20, x + 80, 100, score, 0] for x, score in zip(xs, scores)],
                          dtype=np.float32).reshape(-1, 6))


class ScorerTests(unittest.TestCase):
    def test_simultaneous_opposite_and_reordering(self):
        ref = [event(1, d, "r" + str(i)) for i, d in enumerate(("A->B", "B->A"))]
        pred = [event(1, d, "p" + str(i)) for i, d in enumerate(("B->A", "A->B"))]
        for r in itertools.permutations(ref):
            for p in itertools.permutations(pred):
                result = evaluate_events(r, p)
                self.assertEqual((result["TP"], result["FP"], result["FN"], result["f1"]), (2, 0, 0, 1))
                self.assertEqual(len(result["ambiguity"]["reference_indices"]), 2)
                self.assertIsNone(result["physical_direction"]["wrong_direction_pairs"])

    def test_duplicates_count_as_false_positives(self):
        result = evaluate_events([event(1)], [event(1), event(1)])
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (1, 1, 0))
        self.assertTrue(result["pairs"][0]["ambiguous_temporal_candidates"])

    def test_wrong_direction_is_unmatched_without_physical_evidence(self):
        result = evaluate_events([event(1)], [event(1, "B->A")])
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (0, 1, 1))
        self.assertEqual(result["counts"]["A->B"]["FN"], 1)
        self.assertEqual(result["counts"]["B->A"]["FP"], 1)
        self.assertIsNone(result["physical_direction"]["wrong_direction_pairs"])

    def test_empty_is_undefined_not_perfect(self):
        result = evaluate_events([], [])
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (0, 0, 0))
        self.assertIsNone(result["f1"])
        self.assertIsNone(evaluate_events([event(1)], [])["precision"])
        self.assertIsNone(evaluate_events([], [event(1)])["recall"])

    def test_tolerance_boundary(self):
        self.assertEqual(evaluate_events([event(1)], [event(3)])["TP"], 1)
        self.assertEqual(evaluate_events([event(1)], [event(3.0001)])["TP"], 0)

    def test_invalid_values_rejected(self):
        for tolerance in (0, -1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                evaluate_events([], [], tolerance)
        for row in (event(float("nan")), event(1, "unknown")):
            with self.assertRaises(ValueError):
                evaluate_events([row], [])

    def test_no_cross_video_or_session_assignment(self):
        for field in ("video_id", "session_id"):
            result = evaluate_events([event(1, **{field: "a"})], [event(1, **{field: "b"})])
            self.assertEqual(result["TP"], 0)

    def test_maximum_cardinality_before_nearest_time(self):
        result = evaluate_events([event(0), event(2)], [event(1.5), event(3.5)], 2)
        self.assertEqual(result["TP"], 2)
        self.assertEqual(result["total_time_error_s"], 3)

    def test_minimum_time_error_after_cardinality(self):
        result = evaluate_events([event(0), event(4)], [event(0.1), event(1), event(4.2)], 2)
        self.assertEqual(result["TP"], 2)
        self.assertAlmostEqual(result["total_time_error_s"], 0.3)

    def test_stable_pair_ids_under_ties_and_permutation(self):
        ref = [event(1, event_id="r1"), event(1, event_id="r2")]
        pred = [event(1, event_id="p1"), event(1, event_id="p2"), event(1, event_id="p3")]
        expected = None
        for r in itertools.permutations(ref):
            for p in itertools.permutations(pred):
                result = evaluate_events(r, p)
                pairs = [(x["reference_event_id"], x["prediction_event_id"]) for x in result["pairs"]]
                expected = pairs if expected is None else expected
                self.assertEqual(pairs, expected)

    def test_physical_direction_requires_and_uses_independent_evidence(self):
        ref, pred = [event(1, event_id="r")], [event(1, "B->A", "p")]
        link = dict(reference_event_id="r", prediction_event_id="p", independently_verified=True,
                    evidence_type="video_review", evidence="SOFTWARE FIXTURE: independent keyframe correspondence")
        result = evaluate_events(ref, pred, physical_pairs=[link])
        self.assertEqual(result["physical_direction"]["wrong_direction_pairs"], 1)
        self.assertEqual(result["TP"], 0)
        with self.assertRaises(ValueError):
            evaluate_events(ref, pred, physical_pairs=[{**link, "independently_verified": False}])
        with self.assertRaises(ValueError):
            evaluate_events(ref, pred, physical_pairs=[link, link])

    def test_dp_matches_exhaustive_small_event_sets(self):
        # Independent brute-force oracle also includes crossings and unmatched rows.
        rng = random.Random(26)
        for _ in range(60):
            r = [event(rng.randrange(8) / 2) for _ in range(rng.randrange(5))]
            p = [event(rng.randrange(8) / 2) for _ in range(rng.randrange(5))]
            tol = 1.0
            best = (0, 0.0)
            def search(i, used, count, cost):
                nonlocal best
                if i == len(r):
                    if (-count, cost) < (-best[0], best[1]):
                        best = count, cost
                    return
                search(i + 1, used, count, cost)
                for j, row in enumerate(p):
                    error = abs(row["time_s"] - r[i]["time_s"])
                    if j not in used and error <= tol:
                        search(i + 1, used | {j}, count + 1, cost + error)
            search(0, set(), 0, 0.0)
            actual = evaluate_events(r, p, tol)
            self.assertEqual((actual["TP"], actual["total_time_error_s"]), best)


class TrackerTests(unittest.TestCase):
    def tracker(self, cls=SecondStageIoUTracker):
        return cls(SimpleNamespace(**CONFIG))

    def test_scope_only_secondstage_changed(self):
        self.assertTrue(verify_method_scope()["all_other_secondstage_AST_identical"])

    def test_original_failure_reproduced_and_high_low_high_fixed(self):
        for cls, expected in ((BYTETracker, [1, 0, 1]), (SecondStageIoUTracker, [1, 1, 1])):
            tracker = self.tracker(cls)
            rows = [tracker.update(boxes([score])) for score in (0.9, 0.22, 0.9)]
            self.assertEqual([len(row) for row in rows], expected)
            self.assertEqual(int(rows[0][0, 4]), int(rows[-1][0, 4]))

    def test_two_neighbors_keep_ids_during_low_scores(self):
        tracker = self.tracker()
        first = tracker.update(boxes([0.9, 0.9]))
        second = tracker.update(boxes([0.22, 0.21]))
        third = tracker.update(boxes([0.9, 0.9]))
        self.assertEqual([len(first), len(second), len(third)], [2, 2, 2])
        self.assertEqual(first[:, 4].tolist(), second[:, 4].tolist())
        self.assertEqual(first[:, 4].tolist(), third[:, 4].tolist())

    def test_short_loss_high_score_recovers_original_id(self):
        tracker = self.tracker()
        first = tracker.update(boxes([0.9]))
        self.assertEqual(len(tracker.update(boxes([]))), 0)
        third = tracker.update(boxes([0.9]))
        self.assertEqual(int(first[0, 4]), int(third[0, 4]))

    def test_low_cannot_reactivate_lost(self):
        tracker = self.tracker()
        tracker.update(boxes([0.9]))
        tracker.update(boxes([]))
        self.assertEqual(len(tracker.update(boxes([0.22]))), 0)

    def test_low_cannot_create_track(self):
        tracker = self.tracker()
        self.assertEqual(len(tracker.update(boxes([0.22]))), 0)
        self.assertFalse(tracker.tracked_stracks)

    def test_nonoverlap_low_not_associated(self):
        tracker = self.tracker()
        tracker.update(boxes([0.9]))
        self.assertEqual(len(tracker.update(boxes([0.22], [1000]))), 0)

    def test_high_only_sequence_unchanged(self):
        def sequence(cls):
            tracker = self.tracker(cls)
            return [tracker.update(boxes([0.9], [20 + step])) for step in range(4)]
        for old, new in zip(sequence(BYTETracker), sequence(SecondStageIoUTracker)):
            np.testing.assert_array_equal(old, new)

    def test_split_threshold_exact_boundaries(self):
        tracker = self.tracker()
        values = boxes([0.099, 0.1, 0.10001, 0.19999, 0.2, 0.24999, 0.25])
        high, low, *_ = tracker._split_detections(values)
        self.assertEqual(len(high), 1)
        self.assertEqual(len(low), 4)
        self.assertAlmostEqual(float(high.conf[0]), 0.25)

    def test_real_decode_still_keeps_point_two_and_above(self):
        # Execute the archived decode function itself, with no cv2/UI/hardware import.
        path = REPO / "pynq/yolo26_optimization_8/runtime_fast/board_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "decode")
        namespace = {"np": np}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
        raw = boxes([0.1, 0.19999, 0.2, 0.24999, 0.25]).data[None]
        selected = namespace["decode"](raw, (192, 192), threshold=0.2, size=192)
        self.assertEqual(len(selected), 3)
        self.assertAlmostEqual(float(selected[0, 4]), 0.2)


class ArchiveTests(unittest.TestCase):
    def test_inc_selected_but_payloads_remain_excluded(self):
        path = REPO / "archive_tools/selection_policy.py"
        spec = importlib.util.spec_from_file_location("r1_selection", path)
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
        for file in ("native_sources/resident_methods.inc", "native_sources/software_fusion.inc"):
            self.assertTrue(policy.choose(file, 5000)[0])
        for file in ("model.pt", "graph.bin", "frame.npz", "source.mp4", "overlay.bit"):
            self.assertFalse(policy.choose(file, 5000)[0])

    def test_restored_source_matches_release_hash(self):
        record = json.loads((Path(__file__).parent / "results/source_recovery.json").read_text(encoding="utf-8"))
        for row in record["files"]:
            self.assertEqual(hashlib.sha256((REPO / row["file"]).read_bytes()).hexdigest(), row["sha256"])

    def test_manual_template_has_no_fabricated_events(self):
        value = json.loads((Path(__file__).parent / "manual_event_template.json").read_text(encoding="utf-8"))
        self.assertEqual(value["events"], [])
        self.assertEqual(value["review_status"], "pending")
        self.assertEqual(value["user_confirmed_total"]["complete_passages"], 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
