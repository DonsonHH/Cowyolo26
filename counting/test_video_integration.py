"""Synthetic file integration: actual codec/preprocessing with a pixel test adapter."""
import tempfile
import json
import unittest
from pathlib import Path
import numpy as np
from .runner import run


class GreenPixelAdapter:
    size = 128

    def infer(self, tensor):
        image = tensor[0]
        mask = (image[1] > .65) & (image[1] > image[0] + .15) & (image[1] > image[2] + .15)
        y, x = np.where(mask)
        if not len(x):
            return np.zeros((1, 0, 6), np.float32)
        return np.array([[[x.min(), y.min(), x.max() + 1, y.max() + 1, .95, 0]]], np.float32)

    def close(self):
        pass


class VideoIntegrationTests(unittest.TestCase):
    def test_early_source_end_cannot_pass_declared_scope(self):
        import cv2
        with tempfile.TemporaryDirectory(prefix="cow-software-fixture-") as folder:
            root = Path(folder)
            video = root / "SHORT_SOFTWARE_FIXTURE.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 64))
            for _ in range(3):
                writer.write(np.zeros((64, 64, 3), np.uint8))
            writer.release()
            with self.assertRaisesRegex(ValueError, "before requested end"):
                run(video, {"detector": {"backend": "software_fixture"}, "end_frame0_exclusive": 10},
                    root / "output", detector_factory=lambda _: GreenPixelAdapter())
            summary = json.loads((root / "output/summary.json").read_text())
            self.assertEqual(summary["status"], "FAILED")
            self.assertFalse(summary["accuracy_verified"])

    def trial(self, width, height, fps, axis, rotation):
        import cv2
        positions = [.2] * 3 + [i / 20 for i in range(5, 16)] + [.8] * 3
        with tempfile.TemporaryDirectory(prefix="cow-software-fixture-") as folder:
            folder = Path(folder)
            video = folder / "SOFTWARE_FIXTURE.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
            self.assertTrue(writer.isOpened())
            for pos in positions:
                image = np.zeros((height, width, 3), np.uint8)
                cx, cy = (width // 2, round(height * pos)) if axis == "y" else (round(width * pos), height // 2)
                bw, bh = (32, round(height * .2)) if axis == "y" else (round(width * .2), 32)
                cv2.rectangle(image, (cx - bw // 2, cy - bh // 2), (cx + bw // 2, cy + bh // 2), (0, 255, 0), -1)
                writer.write(image)
            writer.release()
            config = {"detector": {"backend": "software_fixture"}, "axis": axis,
                      "rotation_clockwise": rotation, "sample_hz": None,
                      "counter": {"lower": .3, "upper": .7, "stable_samples": 3},
                      "session_id": "SOFTWARE_FIXTURE"}
            result = run(video, config, folder / "output", detector_factory=lambda _: GreenPixelAdapter())
            self.assertEqual(result["counts"], {"IN": 1, "OUT": 0, "NET": 1})
            self.assertEqual(result["decoded_frames"], len(positions))
            self.assertEqual(result["processed_frames"], len(positions))
            self.assertEqual(result["wall_clock_skipped_frames"], 0)
            self.assertTrue(result["software_fixture_only"])
            self.assertFalse(result["accuracy_verified"])
            self.assertEqual(result["counter_after_finish"]["active_states"], 0)

    def test_portrait_rotation_15fps_source(self):
        self.trial(160, 96, 15, "y", 90)

    def test_horizontal_30fps_source_other_dimensions(self):
        self.trial(320, 180, 30, "x", 270)


if __name__ == "__main__":
    unittest.main(verbosity=2)
