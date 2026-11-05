"""Coordinate/layout and documented numerical boundary of resize-first inputs."""
import unittest
import numpy as np
from .geometry import Transform


class ResizeFirstTests(unittest.TestCase):
    def test_all_rotations_keep_rgb_layout_padding_and_coordinate_geometry(self):
        generator = np.random.default_rng(26)
        image = generator.integers(0, 256, (137, 223, 3), dtype=np.uint8)
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                transform = Transform.create(223, 137, [11, 7, 212, 129], rotation, 192)
                legacy = transform.preprocess(image)
                fast = transform.preprocess_resize_first(image)
                self.assertEqual(fast.shape, (1, 3, 192, 192))
                self.assertEqual(fast.dtype, np.float32)
                self.assertTrue(fast.flags.c_contiguous)
                self.assertLessEqual(float(np.max(np.abs(legacy - fast))), 2. / 255 + 1e-6)
                boxes = np.array([[21, 17, 192, 117]], dtype=float)
                np.testing.assert_allclose(transform.boxes(transform.boxes(boxes), inverse=True), boxes, atol=1e-10)

    def test_color_channels_and_padding_remain_normalized(self):
        image = np.zeros((60, 120, 3), np.uint8)
        image[:, :, 2] = 255
        transform = Transform.create(120, 60, None, 90, 64)
        fast = transform.preprocess_resize_first(image)
        self.assertAlmostEqual(float(fast[0, 0, 32, 32]), 1.)
        self.assertAlmostEqual(float(fast[0, 2, 32, 32]), 0.)
        np.testing.assert_allclose(fast[0, :, 0, 0], np.full(3, 114 / 255), atol=1e-7)

    def test_changed_source_dimensions_are_rejected(self):
        transform = Transform.create(120, 60, None, 90, 64)
        with self.assertRaises(ValueError):
            transform.preprocess_resize_first(np.zeros((61, 120, 3), np.uint8))

    def test_native_bgr_canvas_matches_the_public_normalization_layout(self):
        image = np.random.default_rng(26).integers(0, 256, (137, 223, 3), dtype=np.uint8)
        for rotation in (0, 90, 180, 270):
            transform = Transform.create(223, 137, [11, 7, 212, 129], rotation, 192)
            canvas = transform.prepare_bgr(image)
            self.assertEqual(canvas.dtype, np.uint8)
            self.assertTrue(canvas.flags.c_contiguous)
            reconstructed = np.ascontiguousarray(canvas[..., ::-1].transpose(2, 0, 1)[None], np.float32) / np.float32(255)
            np.testing.assert_array_equal(reconstructed, transform.preprocess(image))


if __name__ == "__main__":
    unittest.main(verbosity=2)
