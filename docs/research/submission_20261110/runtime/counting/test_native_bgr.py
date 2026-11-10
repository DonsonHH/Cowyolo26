"""Native pointer contract rejection with a fake graph; no real model execution."""
import unittest
import numpy as np
from .backends import O8Detector


class NativeBgrTests(unittest.TestCase):
    def detector(self):
        class FakeGraph:
            has_bgr = True
            calls = 0
            def run_image(self, image):
                self.calls += 1
                return np.zeros((1, 1, 6), np.float32)
        detector = object.__new__(O8Detector)
        detector.size, detector.graph = 32, FakeGraph()
        return detector

    def test_wrong_dtype_shape_or_stride_never_reaches_the_native_graph(self):
        detector = self.detector()
        for image in (np.zeros((32, 32, 3), np.float32), np.zeros((31, 32, 3), np.uint8),
                      np.zeros((32, 32, 3), np.uint8)[:, ::-1]):
            with self.subTest(shape=image.shape), self.assertRaises(ValueError):
                detector.infer_bgr(image)
        self.assertEqual(detector.graph.calls, 0)

    def test_valid_input_calls_graph_once_and_missing_entry_is_rejected(self):
        detector = self.detector()
        self.assertEqual(detector.infer_bgr(np.zeros((32, 32, 3), np.uint8)).shape, (1, 1, 6))
        self.assertEqual(detector.graph.calls, 1)
        detector.graph.has_bgr = False
        with self.assertRaises(ValueError):
            detector.infer_bgr(np.zeros((32, 32, 3), np.uint8))
        self.assertEqual(detector.graph.calls, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
