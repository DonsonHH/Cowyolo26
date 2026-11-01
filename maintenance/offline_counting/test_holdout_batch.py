"""Supervisor process/path contracts; no detector, board, network or video work."""
import argparse
import contextlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from maintenance.offline_counting.run_holdout_batch import main


class BatchContracts(unittest.TestCase):
    def setup_paths(self, root):
        for name in ("repo", "inputs", "configs"):
            (root / name).mkdir()
        return argparse.Namespace(repo=root / "repo", inputs=root / "inputs",
                                  configs=root / "configs", output=root / "runs", cases=["one", "two"])

    def test_relative_paths_bound_to_launch_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            args = self.setup_paths(root)
            for name in ("repo", "inputs", "configs", "output"):
                setattr(args, name, getattr(args, name).relative_to(root))
            child = Mock(pid=101)
            child.wait.return_value = 0
            with contextlib.chdir(root), patch("subprocess.Popen", return_value=child) as popen:
                main(args)
            command = popen.call_args_list[0].args[0]
            self.assertEqual(command[command.index("--video") + 1], str(root / "inputs/one.mp4"))
            self.assertEqual(command[command.index("--config") + 1], str(root / "configs/one.json"))
            self.assertEqual(command[command.index("--output") + 1], str(root / "runs/one"))
            self.assertEqual(popen.call_args_list[0].kwargs["cwd"], root / "repo")
            self.assertEqual(json.loads((root / "runs/batch_status.json").read_text())["status"], "COMPLETED_UNSCORED")

    def check_interruption(self, timeout=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self.setup_paths(root)
            child = Mock(pid=102)
            child.wait.side_effect = ([KeyboardInterrupt(), subprocess.TimeoutExpired("child", 5), -9]
                                      if timeout else [KeyboardInterrupt(), -15])
            with patch("subprocess.Popen", return_value=child) as popen:
                with self.assertRaises(KeyboardInterrupt):
                    main(args)
            child.terminate.assert_called_once()
            self.assertEqual(child.kill.call_count, int(timeout))
            self.assertEqual(popen.call_count, 1)
            record = json.loads((root / "runs/batch_status.json").read_text())
            self.assertEqual(record["status"], "FAILED")
            self.assertEqual(record["cases"][0]["status"], "ABORTED")
            self.assertEqual(record["cases"][0]["exit_code"], -9 if timeout else -15)

    def test_interrupt_terminates_and_reaps_child(self):
        self.check_interruption()

    def test_native_avi_input_keeps_its_extension(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            args = self.setup_paths(root)
            args.video_suffix = ".avi"
            child = Mock(pid=104)
            child.wait.return_value = 0
            with patch("subprocess.Popen", return_value=child) as popen:
                main(args)
            command = popen.call_args_list[0].args[0]
            self.assertEqual(command[command.index("--video") + 1], str(root / "inputs/one.avi"))

    def test_interrupt_kills_child_after_grace_period(self):
        self.check_interruption(timeout=True)

    def test_failure_stops_before_next_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self.setup_paths(root)
            child = Mock(pid=103)
            child.wait.return_value = 2
            with patch("subprocess.Popen", return_value=child) as popen:
                with self.assertRaises(RuntimeError):
                    main(args)
            self.assertEqual(popen.call_count, 1)
            record = json.loads((root / "runs/batch_status.json").read_text())
            self.assertEqual(record["status"], "FAILED")
            self.assertEqual(record["cases"][0]["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
