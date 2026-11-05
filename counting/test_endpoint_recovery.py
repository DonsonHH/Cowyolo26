"""Software contracts for measured, bounded endpoint recovery; no cow accuracy GT."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from .counter import State
from .endpoint_recovery import EndpointRecovery
from .runner import run
from .test_video_integration import GreenPixelAdapter
from .tracking import TrackingSession


CONFIG = {
    "endpoint_recovery": {"enabled": True, "maximum_extra_forwards": 3},
    "confidence": .2,
    "counter": {"lower": .4, "upper": .6, "stable_samples": 2},
}


class EndpointPolicyTests(unittest.TestCase):
    def policy(self, **options):
        cfg = {**CONFIG, "endpoint_recovery": {**CONFIG["endpoint_recovery"], **options}}
        policy = EndpointRecovery(cfg, 1000, 1000)
        self.states = {"a": State(origin="B", candidate="A", streak=1, last_seen=1.2, origin_time=0.)}
        for stamp, box in ((1., [300, 300, 500, 600]), (1.2, [300, 280, 500, 580])):
            self.states["a"].last_seen = stamp
            policy.record(stamp, [{"track_id": "a", "xyxy": box}], self.states)
        return policy

    def test_pending_opposite_endpoint_uses_past_observations(self):
        policy = self.policy()
        proposal, = policy.proposals(1.4, [], self.states, 2)
        np.testing.assert_allclose(proposal["predicted_box"], [300, 260, 500, 560])
        self.assertEqual(proposal["roi"], [250, 185, 550, 635])
        self.assertEqual(policy.reserved_forwards, 1)

    def test_default_off_and_missing_origin_do_not_propose(self):
        policy = self.policy(enabled=False)
        self.assertEqual(policy.proposals(1.4, [], self.states, 2), [])
        policy = self.policy()
        self.states["a"].origin = None
        self.assertEqual(policy.proposals(1.4, [], self.states, 2), [])

    def test_counted_arrival_is_not_rechecked_but_pending_return_can_be(self):
        policy = self.policy()
        self.states["a"].emitted = True
        self.assertEqual(len(policy.proposals(1.4, [], self.states, 2)), 1)
        self.states["a"].origin = "A"
        self.assertEqual(policy.proposals(1.6, [], self.states, 2), [])

    def test_base_detection_same_frame_avoids_extra_forward(self):
        policy = self.policy()
        self.assertEqual(policy.proposals(1.4, [[300, 260, 500, 560, .7, 0]], self.states, 2), [])
        self.assertEqual(policy.reserved_forwards, 0)

    def test_stale_history_and_unconfirmed_track_cannot_trigger(self):
        policy = self.policy()
        self.assertEqual(policy.proposals(2.4, [], self.states, 2), [])
        self.states["a"].streak = 0
        self.assertEqual(policy.proposals(1.4, [], self.states, 2), [])

    def test_per_passage_and_whole_video_budgets(self):
        policy = self.policy(maximum_extra_forwards=1)
        self.assertEqual(len(policy.proposals(1.4, [], self.states, 2)), 1)
        self.assertEqual(policy.proposals(1.6, [], self.states, 2), [])
        policy = self.policy()
        self.assertEqual(len(policy.proposals(1.4, [], self.states, 2)), 1)
        self.assertEqual(len(policy.proposals(1.6, [], self.states, 2)), 1)
        self.assertEqual(policy.proposals(1.8, [], self.states, 2), [])

    def test_history_and_attempts_evicted_with_counter_state(self):
        policy = self.policy()
        policy.proposals(1.4, [], self.states, 2)
        policy.record(1.6, [], {})
        self.assertEqual(policy.history, {})
        self.assertEqual(policy.attempts, {})

    def test_candidate_must_be_measured_near_target_inside_channel(self):
        policy = self.policy()
        proposal, = policy.proposals(1.4, [], self.states, 2)
        good = [300, 260, 500, 560, .6, 0]
        invalid = [[300, 260, 500, 560, .19, 0], [700, 260, 900, 560, .99, 0],
                   [0, 0, 1000, 1000, .99, 0]]
        self.assertIsNone(policy.select(proposal, invalid, []))
        np.testing.assert_array_equal(policy.select(proposal, invalid + [good], []), good)
        self.assertIsNone(policy.select(proposal, [good], [good]))
        policy.polygon = type("Outside", (), {"contains": lambda self, x, y: False})()
        self.assertIsNone(policy.select(proposal, [good], []))

    def test_roi_clips_to_source_and_frame_budget_is_shared(self):
        policy = self.policy(maximum_per_frame=1, roi_scale=3)
        self.states["b"] = self.states["a"]
        policy.history["b"] = policy.history["a"]
        proposals = policy.proposals(1.4, [], self.states, 2)
        self.assertEqual(len(proposals), 1)
        self.assertTrue(all(0 <= value <= 1000 for value in proposals[0]["roi"]))

    def test_invalid_unbounded_configuration_is_rejected(self):
        for options in ({"enabled": 1}, {"maximum_extra_forwards": True}, {"maximum_per_frame": 9},
                        {"roi_scale": float("nan")}, {"maximum_age_s": 0}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.policy(**options)


class ScaleSensitivePixelAdapter(GreenPixelAdapter):
    """Test pixels disappear from a wide view but remain detectable after a crop."""
    def __init__(self, local_detection=True):
        self.local_detection = local_detection
    cutoff = .35

    def infer(self, tensor):
        result = super().infer(tensor)
        if result.shape[1]:
            box = result[0, 0]
            local = box[2] - box[0] > 25
            too_far = (box[1] + box[3]) / (2 * self.size) < self.cutoff
            if local and not self.local_detection or not local and too_far:
                return np.zeros((1, 0, 6), np.float32)
        return result


class EndpointRunnerTests(unittest.TestCase):
    def trial(self, enabled, local_detection=True, reacquire=False, drop_before_gate=False):
        import cv2
        with tempfile.TemporaryDirectory(prefix="endpoint-software-fixture-") as folder:
            root = Path(folder)
            video = root / "SOFTWARE_FIXTURE.avi"
            positions = [.78] * 3 + [round(.74 - .04 * i, 2) for i in range(13)]
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 5, (256, 256))
            self.assertTrue(writer.isOpened())
            for position in positions:
                image = np.zeros((256, 256, 3), np.uint8)
                cy = round(position * 256)
                cv2.rectangle(image, (116, cy - 30), (140, cy + 30), (0, 255, 0), -1)
                writer.write(image)
            writer.release()
            config = {**CONFIG, "session_id": "SOFTWARE_FIXTURE", "in_direction": "B->A",
                      "detector": {"backend": "software_fixture"},
                      "endpoint_recovery": {"enabled": enabled, "maximum_extra_forwards": None if reacquire else 3,
                                            "reacquire_missing_tracks": reacquire}}
            class BeforeGatePixelAdapter(ScaleSensitivePixelAdapter):
                cutoff = .43
            adapter = BeforeGatePixelAdapter if drop_before_gate else ScaleSensitivePixelAdapter
            summary = run(video, config, root / "output",
                          detector_factory=lambda _: adapter(local_detection))
            rows = [json.loads(line) for line in (root / "output/frames.jsonl").read_text().splitlines()]
            return summary, rows

    def test_runner_obtains_additional_measurement_without_relaxing_stability(self):
        baseline, _ = self.trial(False)
        recovered, rows = self.trial(True)
        self.assertEqual(baseline["counts"]["IN"], 0)
        self.assertEqual(recovered["counts"]["IN"], 1)
        self.assertEqual(recovered["config"]["counter"]["stable_samples"], 2)
        self.assertEqual(recovered["base_model_forwards"], len(rows))
        self.assertEqual(recovered["model_forwards"], recovered["base_model_forwards"] + recovered["endpoint_recovery_forwards"])
        self.assertGreater(recovered["endpoint_recovery_forwards"], 0)
        self.assertLessEqual(recovered["endpoint_recovery_forwards"], 3)
        self.assertFalse(recovered["accuracy_verified"])
        refinements = [item for row in rows for item in row["endpoint_recovery"]]
        self.assertTrue(any(item["accepted_detection"] is not None for item in refinements))
        self.assertTrue(all(item["transform"]["source_width"] == 256 for item in refinements))

    def test_no_additional_real_detection_never_creates_a_passage(self):
        summary, rows = self.trial(True, local_detection=False)
        self.assertEqual(summary["counts"]["IN"], 0)
        self.assertGreater(summary["endpoint_recovery_forwards"], 0)
        self.assertTrue(all(item["accepted_detection"] is None for row in rows for item in row["endpoint_recovery"]))

    def test_measured_reacquisition_can_recover_loss_before_the_first_endpoint_sample(self):
        baseline, _ = self.trial(True, drop_before_gate=True)
        recovered, rows = self.trial(True, reacquire=True, drop_before_gate=True)
        self.assertEqual(baseline["counts"]["IN"], 0)
        self.assertEqual(recovered["counts"]["IN"], 1)
        self.assertEqual(recovered["config"]["counter"]["stable_samples"], 2)
        self.assertTrue(any(item["reason"] == "anchored_track_reacquisition" for row in rows for item in row["endpoint_recovery"]))

    def test_missing_local_image_evidence_never_turns_reacquisition_into_a_passage(self):
        result, rows = self.trial(True, local_detection=False, reacquire=True, drop_before_gate=True)
        self.assertEqual(result["counts"]["IN"], 0)
        self.assertTrue(all(item["accepted_detection"] is None for row in rows for item in row["endpoint_recovery"]))


class ReacquisitionPolicyTests(unittest.TestCase):
    policy = EndpointPolicyTests.policy
    def test_middle_gap_requires_an_existing_origin_and_correct_motion(self):
        policy = self.policy(reacquire_missing_tracks=True)
        self.states["a"].candidate, self.states["a"].streak = None, 0
        self.assertEqual(len(policy.proposals(1.4, [], self.states, 2)), 1)
        policy = self.policy(reacquire_missing_tracks=True)
        self.states["a"].candidate, self.states["a"].streak, self.states["a"].origin = None, 0, "A"
        self.assertEqual(policy.proposals(1.4, [], self.states, 2), [])

    def test_geometry_association_precedes_a_higher_score_on_a_worse_box(self):
        policy = self.policy(reacquire_missing_tracks=True)
        proposal, = policy.proposals(1.4, [], self.states, 2)
        close = [300, 260, 500, 560, .3, 0]
        displaced = [340, 260, 540, 560, .95, 0]
        np.testing.assert_array_equal(policy.select(proposal, [displaced, close], []), close)

    def test_continuous_mode_keeps_per_origin_and_frame_limits(self):
        policy = self.policy(reacquire_missing_tracks=True, maximum_extra_forwards=None,
                             maximum_reacquisitions_per_origin=1, maximum_per_frame=1)
        self.states["a"].candidate, self.states["a"].streak = None, 0
        self.assertEqual(len(policy.proposals(1.4, [], self.states, 2)), 1)
        self.assertEqual(policy.proposals(1.6, [], self.states, 2), [])

    def test_both_reacquisition_observations_must_be_within_the_age_window(self):
        policy = self.policy(reacquire_missing_tracks=True)
        self.states["a"].candidate, self.states["a"].streak = None, 0
        history = policy.history["a"]
        history[0] = (.4, history[0][1])
        history[1] = (1.3, history[1][1])
        self.assertEqual(policy.proposals(1.5, [], self.states, 2), [])
        history[0] = (.5, history[0][1])
        self.assertEqual(len(policy.proposals(1.5, [], self.states, 2)), 1)


class EndpointNeighborTests(unittest.TestCase):
    def history(self, x1=300, polygon=None):
        config = {**CONFIG, "axis": "y", "in_direction": "B->A", "track_only_in_channel": True,
                  "tracker": {"track_high_thresh": .2, "track_low_thresh": .1,
                              "new_track_thresh": .25, "fuse_score": False}}
        if polygon is not None:
            config["channel_polygon"] = polygon
        tracking = TrackingSession(config, 1000, 1000, 5, "SOFTWARE_NEIGHBOR")
        recovery = EndpointRecovery(config, 1000, 1000)
        for frame, y in enumerate([800, 800, 760, 720, 680, 640, 600, 560, 520, 480, 440, 400, 380]):
            values = np.array([[x1, y - 150, x1 + 200, y + 150, .95, 0],
                               [500, 210, 700, 510, .95, 0]], np.float32)
            tracks, _, _ = tracking.update(frame, frame * .2, values)
            recovery.record(frame * .2, tracks, tracking.counter.states)
        return tracking, recovery

    def test_offset_neighbor_detection_cannot_confirm_another_cows_endpoint(self):
        tracking, recovery = self.history()
        base = np.array([[500, 210, 700, 510, .95, 0]], np.float32)
        proposal, = recovery.proposals(2.6, base, tracking.counter.states, 2)
        neighbor_again = np.array([[400, 210, 600, 510, .95, 0]], np.float32)
        selected = recovery.select(proposal, neighbor_again, base)
        combined = base if selected is None else np.concatenate((base, selected[None]))
        tracking.update(13, 2.6, combined)
        self.assertEqual(tracking.counter.counts["IN"], 0)
        self.assertIsNone(selected)

    def test_outside_cow_does_not_suppress_in_channel_recovery(self):
        polygon = [[.2, .1], [.5, .1], [.5, .9], [.2, .9]]
        tracking, recovery = self.history(x1=390, polygon=polygon)
        outside = np.array([[500, 210, 700, 510, .95, 0]], np.float32)
        proposals = recovery.proposals(2.6, outside, tracking.counter.states, 2)
        self.assertEqual(len(proposals), 1)
        self.assertTrue(proposals[0]["track_id"].startswith("0:"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
