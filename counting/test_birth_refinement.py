"""Weak-origin regressions from real probes; fixtures are not accuracy proof."""
from types import SimpleNamespace
import unittest
import numpy as np

from .birth_refinement import BirthRefinement
from .tracking import TrackingSession


WEAK = [726.5675, 33.8795, 845.0575, 257.4084, .1246463, 0]
ZOOM = [724.7911, 44.0566, 839.0623, 231.701, .930788, 0]


def config():
    return {"confidence": .02, "perpendicular_roi": [.34, .75],
            "counter": {"stable_samples": 2},
            "tracker": {"track_high_thresh": .15, "new_track_thresh": .25,
                        "track_low_thresh": .1, "fuse_score": False},
            "endpoint_recovery": {"maximum_per_frame": 1},
            "birth_refinement": {"enabled": True}}


class BirthRefinementTests(unittest.TestCase):
    def test_coherent_real_weak_motion_can_trigger_but_static_background_cannot(self):
        value = config()
        value['confidence'] = .01
        value['birth_refinement'].update(weak_motion_support=True, minimum_motion_per_s=.05)
        policy = BirthRefinement(value,1280,720)
        previous = [731.184,18.464,848.135,254.325,.0104773,0]
        current = [724.735,55.7558,838.6085,296.2421,.0564957,0]
        policy.record(27.,[previous])
        proposal = policy.proposal(27.4,[current],[])
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal['support']['kind'],'weak_motion')
        self.assertEqual(proposal['support']['time_s'],27.)
        self.assertIsNone(policy.proposal(29.,[current],[]))
        background = [434,473,526,681,.037,0]
        other = BirthRefinement(value,1280,720)
        other.record(21.4,[background])
        self.assertIsNone(other.proposal(21.8,[background],[]))

    def test_real_weak_origin_gets_crop_but_weak_local_does_not_get_promoted(self):
        policy = BirthRefinement(config(), 1280, 720)
        proposal = policy.proposal(27.2, [WEAK], [])
        self.assertEqual(proposal["roi"], [697, 0, 875, 313])
        accepted = policy.select(proposal, [ZOOM], [WEAK])
        np.testing.assert_allclose(accepted, ZOOM)
        weak_local = list(ZOOM)
        weak_local[4] = .084533
        self.assertIsNone(policy.select(proposal, [weak_local], [WEAK]))

    def test_middle_outside_and_strong_or_covered_seeds_do_not_trigger(self):
        policy = BirthRefinement(config(), 1280, 720)
        for box in ([726, 320, 845, 400, .12, 0], [0, 0, 120, 200, .12, 0],
                    [726, 30, 845, 250, .25, 0]):
            self.assertIsNone(policy.proposal(1., [box], []))
        strong = list(WEAK)
        strong[4] = .9
        self.assertIsNone(policy.proposal(1., [WEAK, strong], []))

    def test_confirmed_usable_track_skipped_but_unconfirmed_or_unusable_not_skipped(self):
        policy = BirthRefinement(config(), 1280, 720)
        track = SimpleNamespace(is_activated=True, observations=[(.8, np.array(WEAK[:4]))],
                                box_at=lambda _: np.array(WEAK[:4]))
        self.assertIsNone(policy.proposal(1., [WEAK], [track]))
        track.is_activated = False
        self.assertIsNotNone(policy.proposal(1., [WEAK], [track]))
        track.is_activated = True
        weak = list(WEAK)
        weak[4] = .03
        self.assertIsNotNone(policy.proposal(1., [weak], [track]))

    def test_skip_uses_actual_second_stage_threshold_and_current_prediction(self):
        policy = BirthRefinement(config(), 1280, 720)
        box = np.array(WEAK[:4])
        shifted = box + np.array([60., 0., 60., 0.])  # IoU about .33: fails low stage.
        track = SimpleNamespace(is_activated=True, observations=[(.8, box)], box_at=lambda _: shifted)
        self.assertIsNotNone(policy.proposal(1., [WEAK], [track]))
        high = list(WEAK)
        high[4] = .2
        self.assertIsNone(policy.proposal(1., [high], [track]))
        # Previous box overlaps perfectly, but current-time prediction is distant.
        track.box_at = lambda _: box + np.array([300., 0., 300., 0.])
        self.assertIsNotNone(policy.proposal(1., [high], [track]))
        track.box_at = lambda _: box
        boundary = np.array(WEAK, dtype=np.float32)
        boundary[4] = .1
        self.assertIsNotNone(policy.proposal(1., [boundary], [track]))

    def test_neighbor_and_outside_local_rejected_seed_itself_does_not_suppress(self):
        policy = BirthRefinement(config(), 1280, 720)
        proposal = policy.proposal(1., [WEAK], [])
        self.assertIsNotNone(policy.select(proposal, [ZOOM], [WEAK]))
        neighbor = list(ZOOM)
        neighbor[4] = .8
        self.assertIsNone(policy.select(proposal, [ZOOM], [WEAK, neighbor]))
        self.assertIsNone(policy.select(proposal, [[0, 0, 120, 200, .9, 0]], [WEAK]))

    def test_disabled_default_and_shared_single_extra_call_contract(self):
        self.assertIsNone(BirthRefinement({}, 1280, 720).proposal(1., [WEAK], []))
        bad = config()
        bad["endpoint_recovery"] = {"enabled": True, "maximum_per_frame": 2}
        with self.assertRaisesRegex(ValueError, "one"):
            BirthRefinement(bad, 1280, 720)

    def test_two_model_calls_on_one_image_still_supply_one_counter_observation(self):
        value = config()
        session = TrackingSession(value, 1280, 720, 5., "fixture")
        policy = BirthRefinement(value, 1280, 720)
        proposal = policy.proposal(1., [WEAK], [])
        row = policy.select(proposal, [ZOOM], [WEAK])
        tracks, events, _ = session.update(5, 1., [row])
        self.assertEqual(events, [])
        state = session.counter.states[tracks[0]["track_id"]]
        self.assertIsNone(state.origin)
        self.assertEqual(state.streak, 1)
        session.update(6, 1.2, [row])
        self.assertEqual(state.origin, "A")

    def test_truncated_edge_seeds_are_deferred_until_body_enters_detection_roi(self):
        policy = BirthRefinement(config(), 1280, 720)
        edge = [732.7228, 2.7537, 855.8293, 204.7005, .0692116, 0]
        self.assertIsNone(policy.proposal(26.8, [edge], []))
        self.assertIsNotNone(policy.proposal(27.2, [WEAK], []))
        bottom = [732, 600, 855, 720, .07, 0]
        self.assertIsNone(policy.proposal(1., [bottom], []))
        value = config()
        value["detection_roi_xyxy"] = [435, 50, 960, 700]
        cropped_policy = BirthRefinement(value, 1280, 720)
        edge[1] = 55
        self.assertIsNone(cropped_policy.proposal(1., [edge], []))

    def test_sub_low_background_needs_prior_track_and_unconfirmed_uses_own_stage(self):
        policy = BirthRefinement(config(), 1280, 720)
        background = [434, 473, 526, 681, .037, 0]  # Actual useless Aug15 21.8s crop.
        self.assertIsNone(policy.proposal(21.8, [background], []))
        weak = list(WEAK)
        weak[4] = .03
        self.assertIsNone(policy.proposal(1., [weak], []))
        track = SimpleNamespace(is_activated=False, observations=[(.8, np.array(WEAK[:4]))],
                                box_at=lambda _: np.array(WEAK[:4]))
        self.assertIsNotNone(policy.proposal(1., [weak], [track]))
        high = list(WEAK)
        high[4] = .2
        self.assertIsNone(policy.proposal(1., [high], [track]))

    def test_realtime_integration_shares_budget_and_accounts_actual_calls(self):
        import json
        from pathlib import Path
        import tempfile
        from .realtime import run
        from .test_realtime import video
        from .test_video_integration import GreenPixelAdapter

        class WeakGlobalAdapter(GreenPixelAdapter):
            def infer(self, tensor):
                result = super().infer(tensor)
                if result.shape[1]:
                    box = result[0, 0]
                    box[4] = .12 if box[2] - box[0] < 40 else .9
                return result

        with tempfile.TemporaryDirectory(prefix="rt-birth-software-fixture-") as directory:
            root = Path(directory)
            source = root / "SOFTWARE_FIXTURE.avi"
            positions = [.22] * 3 + [.26, .32, .38, .44, .5, .56, .62, .68, .74] + [.78] * 3
            video(source, positions, 20)
            value = config()
            value.update(detector={}, sample_hz=20., perpendicular_roi=[0., 1.])
            value["tracker"]["motion_box"] = "observed_velocity"
            value["endpoint_recovery"].update(enabled=True, reacquire_missing_tracks=True,
                                                maximum_extra_forwards=None)
            result = run(source, value, root / "output", detector_factory=lambda _: WeakGlobalAdapter())
            rows = [json.loads(line) for line in (root / "output/frames.jsonl").read_text().splitlines()]
            self.assertGreater(result["birth_refinement_forwards"], 0)
            self.assertGreater(result["endpoint_recovery_forwards"], 0)
            self.assertTrue(all(len(row["endpoint_recovery"]) + len(row["birth_refinement"]) <= 1 for row in rows))
            self.assertEqual(result["model_forwards"], result["base_model_forwards"] +
                             result["endpoint_recovery_forwards"] + result["birth_refinement_forwards"])
            self.assertEqual(result["counts"]["IN"], 1)


if __name__ == "__main__":
    unittest.main()
