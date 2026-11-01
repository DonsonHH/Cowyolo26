"""Physical-channel admission before association; weak continuation is not new identity."""
import json
import unittest
from pathlib import Path

from .tracking import TrackingSession


ROOT = Path(__file__).resolve().parents[1] / "maintenance/offline_counting"


def profile():
    return json.loads((ROOT / "selected_camera24_profile_v3.json").read_text())


def box(x, score=.9, y=80):
    return [x - 10, y - 15, x + 10, y + 15, score, 0]


class ChannelTrackingProfileTests(unittest.TestCase):
    def test_channel_filter_requires_a_boolean(self):
        config = profile()
        config["track_only_in_channel"] = "false"
        with self.assertRaisesRegex(ValueError, "boolean"):
            TrackingSession(config, 100, 100, 5, "invalid")

    def test_outside_detections_do_not_enter_association(self):
        session = TrackingSession(profile(), 100, 100, 5, "outside")
        for frame in range(4):
            tracks, events, _ = session.update(frame, frame * .2, [box(20, y=20)])
            self.assertEqual(tracks, [])
            self.assertEqual(events, [])
        self.assertEqual(session.tracker.tracked_stracks, [])

    def test_legacy_default_keeps_outside_tracking_behavior(self):
        config = profile()
        del config["track_only_in_channel"]
        session = TrackingSession(config, 100, 100, 5, "legacy")
        tracks = []
        for frame in range(3):
            tracks, events, _ = session.update(frame, frame * .2, [box(20, y=20)])
            self.assertEqual(events, [])
        self.assertTrue(tracks)

    def test_vertical_channel_filters_on_x_in_original_coordinates(self):
        for x, y, admitted in ((20, 80, False), (80, 20, True)):
            config = profile()
            config["axis"] = "y"
            session = TrackingSession(config, 100, 100, 5, "vertical")
            for frame in range(3):
                tracks, _, _ = session.update(frame, frame * .2, [box(x, y=y)])
            self.assertEqual(bool(tracks), admitted)

    def test_channel_boundary_uses_the_same_strict_membership(self):
        config = profile()
        config["axis"] = "y"
        session = TrackingSession(config, 100, 100, 5, "boundary")
        for frame in range(3):
            tracks, _, _ = session.update(frame, frame * .2, [box(40)])
            self.assertEqual(tracks, [])

    def test_weak_association_reactivates_an_existing_strong_identity(self):
        session = TrackingSession(profile(), 100, 100, 5, "continuation")
        session.update(0, 0., [box(20)])
        tracks, _, _ = session.update(1, .2, [box(20)])
        original_id = tracks[0]["track_id"]
        session.update(2, .4, [])
        tracks, _, _ = session.update(3, .6, [box(20, .22)])
        self.assertEqual([track["track_id"] for track in tracks], [original_id])

    def test_weak_only_detections_cannot_create_an_identity(self):
        session = TrackingSession(profile(), 100, 100, 5, "weak-only")
        for frame, position in enumerate((20, 25, 35, 45, 55, 65, 75)):
            tracks, events, _ = session.update(frame, frame * .2, [box(position, .22)])
            self.assertEqual(tracks, [])
            self.assertEqual(events, [])

    def test_actual_calibration_does_not_inherit_empty_scene_origin(self):
        fixture = json.loads((ROOT / "results/purdue_day1_detection_fixture.json").read_text())
        session = TrackingSession(profile(), fixture["width"], fixture["height"], 5, "actual-calibration")
        events = []
        for row in fixture["observations"]:
            _, emitted, _ = session.update(row["frame0"], row["time_s"], row["detections"])
            events.extend(emitted)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "IN")
        self.assertGreater(events[0]["entry_frame0"], fixture["empty_source_frame0"])


if __name__ == "__main__":
    unittest.main()
