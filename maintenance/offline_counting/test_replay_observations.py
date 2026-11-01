"""Cache admission and explicit postprocessing changes; never run a detector."""
import json
import tempfile
import unittest
from pathlib import Path

from counting.tracking import TrackingSession
from .replay_observations import replay


class ReplayContracts(unittest.TestCase):
    def source(self, root):
        run = root / "source"
        run.mkdir()
        config = {"axis": "x", "perpendicular_roi": [0., 1.], "sample_hz": 5,
                  "confidence": .2, "rotation_clockwise": 0, "scope_start_frame0": 0,
                  "end_frame0_exclusive": 1, "counter": {"stable_samples": 1},
                  "detector": {"backend": "SOFTWARE_FIXTURE"}}
        detections = [[10, 10, 30, 30, .9, 0]]
        tracks, _, _ = TrackingSession(config, 100, 100, 5, "software").update(0, 0., detections)
        summary = {"status": "COMPLETED_UNSCORED", "software_fixture_only": True,
                   "config": config, "source_size": [100, 100], "effective_nominal_sample_hz": 5,
                   "session_id": "software", "run_id": "software-source", "video_id": "software",
                   "video_sha256": "SOFTWARE_FIXTURE", "model_sha256": "SOFTWARE_FIXTURE",
                   "nominal_fps": 5, "processed_frames": 1}
        (run / "summary.json").write_text(json.dumps(summary))
        (run / "frames.jsonl").write_text(json.dumps({"frame0": 0, "time_s": 0.,
                                                     "detections": detections, "tracks": tracks}) + "\n")
        return run

    def test_input_and_detector_changes_are_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.source(root)
            for name, value in (("confidence", .1), ("sample_hz", 10),
                                ("rotation_clockwise", 90), ("end_frame0_exclusive", 2),
                                ("detector", {"backend": "OTHER"})):
                profile = root / "profile.json"
                profile.write_text(json.dumps({name: value}))
                output = root / ("output_" + name)
                with self.assertRaisesRegex(ValueError, "cannot change"):
                    replay(run, output, postprocess_profile=profile)
                self.assertFalse(output.exists())

    def test_explicit_profile_reports_changed_tracks_and_no_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.source(root)
            profile = root / "profile.json"
            profile.write_text(json.dumps({"track_only_in_channel": True, "perpendicular_roi": [.4, 1.]}))
            result = replay(run, root / "result", postprocess_profile=profile)
            self.assertEqual(result["status"], "COMPLETED_UNSCORED")
            self.assertEqual(result["model_forwards"], 0)
            self.assertEqual(result["new_video_decodes"], 0)
            self.assertTrue(result["software_fixture_only"])
            self.assertEqual(result["changed_track_rows_from_source"], 1)
            self.assertFalse(result["track_identity_rows_match_source"])
            self.assertIsNone(result["maximum_track_box_difference_px"])

    def test_default_replay_still_rejects_track_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.source(root)
            path = run / "frames.jsonl"
            row = json.loads(path.read_text())
            row["tracks"][0]["xyxy"][0] += 1
            path.write_text(json.dumps(row) + "\n")
            with self.assertRaisesRegex(AssertionError, "box mismatch"):
                replay(run, root / "result")
            self.assertEqual(json.loads((root / "result/summary.json").read_text())["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
