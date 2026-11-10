"""Known custom O8 register semantics, using in-memory values only."""
import unittest
from .prepare_o8_boot import verified_core_state


class CoreContractTests(unittest.TestCase):
    manifest = {"core_version": "0x80001", "capability": "0x8000f", "cache_capacity_bytes": 131072}

    def core(self, control=0, error=0, version=0x80001):
        values = {0: control, 4: version, 8: 0x8000f, 12: 131072, 0x64: error}
        return type("MemoryRegisterFixture", (), {"read": lambda instance, address: values[address]})()

    def test_running_with_zero_error_cannot_be_ready(self):
        with self.assertRaisesRegex(ValueError, "idle state"):
            verified_core_state(self.core(control=4), self.manifest)

    def test_idle_without_error_is_ready(self):
        state = verified_core_state(self.core(), self.manifest)
        self.assertFalse(state["busy"])
        self.assertEqual(state["control"], 0)
        self.assertEqual(state["error"], 0)

    def test_done_without_busy_remains_idle(self):
        self.assertFalse(verified_core_state(self.core(control=2), self.manifest)["busy"])

    def test_error_or_incompatible_core_is_rejected(self):
        for core in (self.core(error=802), self.core(version=0x60004)):
            with self.subTest(core=core), self.assertRaises(ValueError):
                verified_core_state(core, self.manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
