"""Strict floating-output evidence: signed zero and NaNs cannot fake bit parity."""
import unittest
import numpy as np
from .native_bgr_parity import same_finite_bits


class NativeParityContractTests(unittest.TestCase):
    def test_signed_zero_is_not_bitwise_equal(self):
        positive = np.array([0.], np.float32)
        negative = np.array([-0.], np.float32)
        self.assertTrue(np.array_equal(positive, negative))
        self.assertFalse(same_finite_bits(positive, negative))

    def test_identical_nan_payload_is_not_a_healthy_output(self):
        values = np.array([float("nan")], np.float32)
        self.assertFalse(same_finite_bits(values, values.copy()))

    def test_finite_bytes_shape_and_dtype_must_all_match(self):
        values = np.array([[1., 2., 3.]], np.float32)
        self.assertTrue(same_finite_bits(values, values.copy()))
        self.assertFalse(same_finite_bits(values, values.ravel()))
        self.assertFalse(same_finite_bits(values, values.astype(np.float64)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
