"""Source-time contracts, including continuous variable-frame-rate input."""
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from .source_clock import SourceSampler, SourceTimeTracker, predict_interval
from .tracking import DEFAULT_TRACKER
from frame_pipeline import Boxes
from cow_tracker.kalman_filter import KalmanFilterXYAH


class SourceClockTests(unittest.TestCase):
    def test_cfr_sampling_matches_existing_original_phase(self):
        sampler = SourceSampler(5)
        selected = [i for i in range(8860, 10874) if sampler.select(i / 25 + .004)]
        self.assertEqual(selected, list(range(8860, 10874, 5)))

    def test_sparse_source_never_invents_observations(self):
        sampler = SourceSampler(5)
        self.assertEqual([t for t in (0., .5, 1.) if sampler.select(t)], [0., .5, 1.])
        self.assertGreater(sampler.unavailable_slots, 0)

    def test_unit_kalman_step_is_exactly_frozen(self):
        kalman = KalmanFilterXYAH()
        mean = np.array([100., 100., 1., 80., 4., 2., 0., 0.])
        covariance = np.eye(8)
        old = kalman.predict(mean, covariance)
        new = predict_interval(kalman, mean, covariance, 1.)
        for a, b in zip(old, new):
            np.testing.assert_array_equal(a, b)

    def test_variable_dt_motion_and_covariance_are_valid(self):
        kalman = KalmanFilterXYAH()
        mean = np.array([100., 100., 1., 80., 4., 2., 0., 0.])
        for interval in (.01, .25, .625, 1.5, 2.5, 5.):
            moved, covariance = predict_interval(kalman, mean, np.zeros((8, 8)), interval)
            self.assertAlmostEqual(moved[0], 100 + 4 * interval)
            self.assertAlmostEqual(moved[1], 100 + 2 * interval)
            self.assertGreaterEqual(float(np.linalg.eigvalsh(covariance).min()), -1e-10)

    def test_two_unit_noise_steps_equal_two_tick_extension(self):
        kalman = KalmanFilterXYAH()
        mean = np.array([100., 100., 1., 80., 0., 0., 0., 0.])
        _, unit = kalman.predict(mean, np.zeros((8, 8)))
        _, two = predict_interval(kalman, mean, np.zeros((8, 8)), 2.)
        F = kalman._motion_mat
        np.testing.assert_allclose(two, F @ unit @ F.T + unit, rtol=1e-14, atol=1e-13)

    def test_lost_expiry_uses_seconds_not_number_of_calls(self):
        tracker = SourceTimeTracker(SimpleNamespace(**DEFAULT_TRACKER), 5, .5)
        detected = Boxes(np.array([[0, 0, 40, 40, .9, 0]], np.float32))
        empty = Boxes(np.zeros((0, 6), np.float32))
        tracker.update_at(0., detected)
        tracker.update_at(.3, empty)
        self.assertEqual(len(tracker.lost_stracks), 1)
        tracker.update_at(.5, empty)
        self.assertEqual(len(tracker.lost_stracks), 1)
        tracker.update_at(.6, empty)
        self.assertFalse(tracker.lost_stracks)

    def vfr_trial(self, config=None):
        import cv2
        from . import runner
        timestamps = [i * .1 for i in range(20)] + [2 + i * .025 for i in range(80)]
        class Capture:
            seek_calls = 0
            def __init__(self, *_):
                self.index = -1
            def isOpened(self):
                return True
            def get(self, prop):
                return {cv2.CAP_PROP_FPS: 25, cv2.CAP_PROP_FRAME_WIDTH: 100,
                        cv2.CAP_PROP_FRAME_HEIGHT: 100, cv2.CAP_PROP_POS_FRAMES: self.index + 1,
                        cv2.CAP_PROP_POS_MSEC: timestamps[max(0, self.index)] * 1000}.get(prop, 0)
            def read(self):
                self.index += 1
                return (True, np.zeros((100, 100, 3), np.uint8)) if self.index < len(timestamps) else (False, None)
            def release(self):
                pass
            def set(self, *_):
                Capture.seek_calls += 1
                raise AssertionError("Unverified nominal-frame seek used on VFR input")
        class Detector:
            size = 32
            def infer(self, _):
                return np.zeros((1, 0, 6), np.float32)
            def close(self):
                pass
        class Stream(io.StringIO):
            def close(self):
                pass
        streams = {}
        def open_stream(path, *_, **__):
            streams[path.name] = Stream()
            return streams[path.name]
        with patch.object(cv2, "VideoCapture", Capture), patch.object(Path, "mkdir"), \
                patch.object(Path, "open", open_stream), patch.object(runner, "sha", return_value="SOFTWARE_FIXTURE"), \
                patch.object(runner, "save"):
            result = runner.run("SOFTWARE_FIXTURE", {"sample_hz": 5, "detector": {}, **(config or {})}, "IN_MEMORY",
                                detector_factory=lambda _: Detector())
        observations = [json.loads(line) for line in streams["frames.jsonl"].getvalue().splitlines()]
        return result, observations, Capture.seek_calls

    def test_full_runner_selects_continuous_vfr_by_pts(self):
        result, observations, _ = self.vfr_trial()
        self.assertEqual(len(observations), 20)
        np.testing.assert_allclose([row["time_s"] for row in observations], np.arange(20) * .2, atol=1e-9)
        self.assertEqual({row["tracker_epoch"] for row in observations}, {0})
        self.assertIsNone(result["source_stride"])
        self.assertEqual(result["sampling"]["minimum_source_frame_gap"], 2)
        self.assertEqual(result["sampling"]["maximum_source_frame_gap"], 8)

    def test_nonzero_vfr_start_uses_decode_ordinal_not_nominal_seek(self):
        result, observations, seeks = self.vfr_trial({"decode_start_frame0": 20})
        self.assertEqual(seeks, 0)
        self.assertEqual(observations[0]["frame0"], 20)
        self.assertAlmostEqual(observations[0]["time_s"], 2.)
        self.assertEqual(result["sequential_lead_in_frames"], 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
