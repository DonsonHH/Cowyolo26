"""Evidence admission on retained small records; no video decode or inference."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from .replay_endpoint_probe import replay, sha, validate_probe


class ProbeEvidenceTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent
        read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
        self.source = read("results/camera2_v4_summary.json")
        self.config = read("camera2_v5_configs/camera2_aug19_endpoint_81s.json")
        self.probe = read("results/camera2_endpoint_object_context_native_probe.json")
        self.binding = read("results/camera2_endpoint_object_context_binding.json")
        self.probe_sha = sha(root / "results/camera2_endpoint_object_context_native_probe.json")

    def validate(self):
        return validate_probe(self.source, self.config, self.probe, self.binding, self.probe_sha)

    def test_registered_completed_measurements_are_admitted(self):
        self.assertEqual(len(self.validate()), 4)

    def test_failed_probe_rejected_even_if_content_hash_supplied(self):
        self.probe["status"] = "FAILED"
        with self.assertRaisesRegex(ValueError, "did not complete"):
            self.validate()

    def test_source_model_config_identity_mismatches_rejected(self):
        for target, name in ((self.source, "video_sha256"), (self.source, "model_sha256"),
                             (self.probe, "config_sha256"), (self.probe, "inputs_manifest_sha256")):
            with self.subTest(name=name):
                old = target[name]
                target[name] = "0" * 64
                with self.assertRaisesRegex(ValueError, "binding mismatch"):
                    self.validate()
                target[name] = old

    def test_source_pts_or_tensor_identity_mismatch_rejected(self):
        for name, value in (("source_time_s", 123.), ("input_tensor_sha256", "0" * 64)):
            with self.subTest(name=name):
                old = self.probe["rows"][0][name]
                self.probe["rows"][0][name] = value
                with self.assertRaisesRegex(ValueError, "recomputed source input"):
                    self.validate()
                self.probe["rows"][0][name] = old

    def test_full_transform_mismatch_rejected_with_same_roi(self):
        for field, value in (("rotation", 0), ("pad_left", 2), ("size", 256)):
            with self.subTest(field=field):
                old_probe = copy.deepcopy(self.probe)
                old_binding = copy.deepcopy(self.binding)
                self.probe["rows"][0]["transform"][field] = value
                self.binding["verified_inputs"][0]["transform"][field] = value
                with self.assertRaisesRegex(ValueError, "full Transform"):
                    self.validate()
                self.probe, self.binding = old_probe, old_binding

    def test_modified_bytes_or_detector_settings_rejected(self):
        self.probe_sha = "0" * 64
        with self.assertRaisesRegex(ValueError, "binding mismatch"):
            self.validate()
        self.probe_sha = self.binding["probe_sha256"]
        self.config["detector"]["size"] = 256
        with self.assertRaisesRegex(ValueError, "cannot change"):
            self.validate()

    def test_mixed_base_run_rejected_without_creating_output(self):
        root = Path(__file__).parent
        with tempfile.TemporaryDirectory(prefix="mixed-evidence-software-fixture-") as folder:
            run = Path(folder)
            (run / "summary.json").write_text(json.dumps(self.source))
            (run / "frames.jsonl").write_text(json.dumps({"run_id": "OTHER_SOFTWARE_RUN", "frame0": 350, "time_s": 14.}) + "\n")
            output = run / "result.json"
            with self.assertRaisesRegex(ValueError, "another run"):
                replay(run, root / "camera2_v5_configs/camera2_aug19_endpoint_81s.json",
                       root / "results/camera2_endpoint_object_context_native_probe.json",
                       root / "results/camera2_endpoint_object_context_binding.json", output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
