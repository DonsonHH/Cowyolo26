"""Coordinate, passage lifecycle and file-interface behavior regressions."""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from .geometry import Transform
from .counter import PassageCounter
from .backends import decode
from .runner import Timing, validate_config
from .tracking import TrackingSession
from .evaluate import evaluate_run


class GeometryTests(unittest.TestCase):
    def test_crop_rotation_and_odd_padding_roundtrip(self):
        native = np.array([[101, 53, 601, 399], [220, 130, 450, 250]], float)
        for rotation in (0, 90, 180, 270):
            for size in (191, 256, 321):
                transform = Transform.create(801, 451, (100, 50, 701, 401), rotation, size)
                np.testing.assert_allclose(transform.boxes(transform.boxes(native), inverse=True), native, atol=1e-10)

    def test_clockwise_known_corners(self):
        transform = Transform.create(100, 60, None, 90, 100)
        np.testing.assert_allclose(transform._points([[0, 0], [100, 60]]), [[80, 0], [20, 100]])

    def test_invalid_roi_rejected(self):
        with self.assertRaises(ValueError):
            Transform.create(100, 100, [0, 0, 101, 100], 0, 192)

    def test_inverse_clips_to_source(self):
        transform = Transform.create(100, 60, None, 0, 100)
        restored = transform.boxes([[-100, -100, 300, 300]], inverse=True)
        np.testing.assert_array_equal(restored, [[0, 0, 100, 60]])

    def test_decoder_maps_only_declared_cow_class(self):
        transform = Transform.create(100, 60, None, 0, 100)
        raw = np.array([[[1, 21, 10, 40, .9, 0], [1, 21, 10, 40, .95, 20], [1, 21, 10, 40, .1, 20]]])
        self.assertEqual(len(decode(raw, transform, .2, [20])), 1)
        self.assertEqual(len(decode(raw, transform, .2, [0])), 1)


class CounterTests(unittest.TestCase):
    def play(self, values, **kwargs):
        counter = PassageCounter("fixture", **kwargs)
        events = []
        for i, values_at_tick in enumerate(values):
            positions = values_at_tick if isinstance(values_at_tick, dict) else {1: values_at_tick}
            emitted, _ = counter.update(i * .2, i, positions, {}, set(positions), {1, 2})
            events.extend(emitted)
        return counter, events

    def test_bidirectional_and_return(self):
        counter, events = self.play([.2] * 3 + [.5] + [.8] * 3 + [.5] + [.2] * 3)
        self.assertEqual([row["direction"] for row in events], ["A->B", "B->A"])
        self.assertEqual(counter.summary()["NET"], 0)

    def test_approach_return_is_not_complete(self):
        _, events = self.play([.2] * 3 + [.5] * 2 + [.2] * 3)
        self.assertEqual(events, [])

    def test_simultaneous_opposite_animals(self):
        _, events = self.play([{1: .2, 2: .8}] * 3 + [{1: .8, 2: .2}] * 3)
        self.assertCountEqual([row["direction"] for row in events], ["A->B", "B->A"])

    def test_missing_observation_breaks_stability(self):
        _, events = self.play([.2, .2, {}, .2, .8, .8, .8])
        self.assertEqual(events, [])

    def test_video_starts_in_middle_does_not_count(self):
        _, events = self.play([.5, .5, .8, .8, .8])
        self.assertEqual(events, [])

    def test_first_observation_in_middle_is_explicitly_flagged(self):
        counter = PassageCounter("fixture")
        events, uncertain = counter.update(0., 0, {1: .5}, {}, {1}, {1})
        self.assertEqual(events, [])
        self.assertEqual(uncertain[0]["reason"], "track_first_observed_between_zones")
        _, again = counter.update(.2, 1, {1: .5}, {}, {1}, {1})
        self.assertEqual(again, [])

    def test_preceding_tentative_admitted_only_at_confirmation(self):
        counter = PassageCounter("fixture")
        counter.update(0, 0, {}, {1: .2}, set(), {1})
        events = []
        for i, value in enumerate([.2, .2, .8, .8, .8], 1):
            result, _ = counter.update(i * .2, i, {1: value}, {}, {1}, {1})
            events.extend(result)
        self.assertEqual(len(events), 1)

    def test_failed_tentatives_do_not_accumulate_stability(self):
        counter = PassageCounter("fixture")
        for i in range(3):
            counter.update(i * .2, i, {}, {1: .2}, set(), {1})
        counter.update(.6, 3, {1: .2}, {}, {1}, {1})
        events = []
        for i in range(4, 7):
            result, _ = counter.update(i * .2, i, {1: .8}, {}, {1}, {1})
            events.extend(result)
        self.assertEqual(events, [])

    def test_confirmation_outside_lane_breaks_tentative_streak(self):
        counter = PassageCounter("fixture")
        counter.update(0., 0, {}, {1: .2}, set(), {1})
        counter.update(.2, 1, {}, {}, {1}, {1})
        events = []
        for i, pos in enumerate((.2, .2, .8, .8, .8), 2):
            emitted, _ = counter.update(i * .2, i, {1: pos}, {}, {1}, {1})
            events.extend(emitted)
        self.assertEqual(events, [])

    def test_long_gap_censors_origin(self):
        counter, _ = self.play([.2] * 3)
        events = []
        for i in range(3):
            result, _ = counter.update(10 + i * .2, 50 + i, {1: .8}, {}, {1}, {1})
            events.extend(result)
        self.assertEqual(events, [])

    def test_removed_tracks_are_reclaimed_and_totals_remain(self):
        counter, events = self.play([.2] * 3 + [.8] * 3)
        self.assertEqual(len(events), 1)
        counter.update(2, 10, {}, {}, set(), set())
        self.assertEqual(counter.summary()["IN"], 1)
        self.assertEqual((len(counter.states), len(counter.pending), len(counter.seen)), (0, 0, 0))

    def test_ten_thousand_ids_keep_state_bounded(self):
        counter = PassageCounter("fixture", stable_samples=1)
        for i in range(10000):
            counter.update(i * .1, i, {i: .5}, {}, {i}, {i})
        self.assertLessEqual(len(counter.states) + len(counter.pending) + len(counter.seen), 2)
        self.assertLessEqual(counter.maximum_state_count, 2)

    def test_right_censored_middle_logged_without_count(self):
        counter, events = self.play([.2] * 3 + [.5])
        self.assertEqual(events, [])
        records = counter.finish()
        self.assertEqual(records[0]["reason"], "video_end")
        self.assertFalse(records[0]["counts_as_complete_passage"])


class ContractTests(unittest.TestCase):
    def test_source_gap_resets_observation_and_keeps_event_ids_unique(self):
        session = TrackingSession({"counter": {"stable_samples": 1}}, 100, 100, 5, "fixture")
        emitted = []
        for epoch, start in enumerate((0., 10.)):
            for i, pos in enumerate((.2, .3, .4, .5, .6, .7)):
                detection = np.array([[40, pos * 100 - 30, 60, pos * 100 + 30, .9, 0]])
                _, events, _ = session.update(epoch * 100 + i, start + i * .2, detection)
                emitted.extend(events)
        self.assertEqual(len(emitted), 2)
        self.assertEqual(len({row["event_id"] for row in emitted}), 2)
        self.assertEqual(session.epoch, 1)

    def test_unreviewed_reference_cannot_become_accuracy_result(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "summary.json").write_text(json.dumps({"status": "COMPLETED_UNSCORED"}))
            (path / "reference.json").write_text(json.dumps({"review_status": "pending"}))
            with self.assertRaisesRegex(ValueError, "pending"):
                evaluate_run(path, path / "reference.json")

    def test_reviewed_record_still_requires_source_position(self):
        with tempfile.TemporaryDirectory(prefix="cow-software-fixture-") as folder:
            path = Path(folder)
            summary = {"status": "COMPLETED_UNSCORED", "video_sha256": "SOFTWARE_FIXTURE_HASH",
                       "video_id": "fixture", "session_id": "fixture",
                       "config": {"scope_start_frame0": 0, "end_frame0_exclusive": 21}}
            reference = {"review_status": "reviewed", "reviewer": "SOFTWARE_FIXTURE", "reviewed_at": "fixture",
                         "source_video_sha256": "SOFTWARE_FIXTURE_HASH",
                         "reviewed_interval": {"start_frame0": 0, "end_frame0": 20},
                         "events": [{"status": "complete", "review_status": "reviewed",
                                     "key_source_frames0": [0, 10], "completion_source_frame0": 10}]}
            (path / "summary.json").write_text(json.dumps(summary))
            (path / "reference.json").write_text(json.dumps(reference))
            with self.assertRaisesRegex(ValueError, "position or local trajectory"):
                evaluate_run(path, path / "reference.json")

    def test_unbounded_timing_history_not_retained(self):
        timer = Timing()
        for i in range(20000):
            timer.add(i)
        self.assertEqual(timer.summary()["count"], 20000)
        self.assertEqual(timer.summary()["retained_samples"], 10000)

    def test_invalid_configuration(self):
        for value in ({"axis": "z"}, {"sample_hz": 0}, {"perpendicular_roi": [.8, .3]}):
            with self.assertRaises(ValueError):
                validate_config(value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
