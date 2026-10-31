"""Run frozen-config video cases serially on one board; preserve every exit code."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def save(path, value):
    temporary = path.with_suffix(".partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(args):
    # The child changes cwd to repo; resolve all user paths in the launch cwd first.
    for name in ("repo", "inputs", "configs", "output"):
        setattr(args, name, getattr(args, name).resolve())
    args.output.mkdir(parents=True, exist_ok=False)
    record = {"status": "RUNNING", "PID": os.getpid(),
              "started_at_UTC": datetime.now(timezone.utc).isoformat(),
              "case_order": args.cases, "cases": [], "accuracy_verified": False}
    boot = Path("/proc/sys/kernel/random/boot_id")
    if boot.exists():
        record["boot_id"] = boot.read_text().strip()
    status_file = args.output / "batch_status.json"
    save(status_file, record)
    try:
        for case in args.cases:
            if Path(case).name != case or case in (".", ".."):
                raise ValueError("Case must be a simple name")
            command = [sys.executable, "-u", "-m", "counting", "--video",
                       str(args.inputs / (case + ".mp4")), "--config",
                       str(args.configs / (case + ".json")), "--output", str(args.output / case)]
            row = {"case_id": case, "command": command, "status": "RUNNING"}
            record["cases"].append(row)
            save(status_file, record)
            with (args.output / (case + ".log")).open("wb") as log:
                child = subprocess.Popen(command, cwd=args.repo, stdout=log, stderr=subprocess.STDOUT)
                row["PID"] = child.pid
                save(status_file, record)
                try:
                    row["exit_code"] = child.wait()
                except BaseException:
                    child.terminate()
                    try:
                        row["exit_code"] = child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        row["exit_code"] = child.wait()
                    row["status"] = "ABORTED"
                    save(status_file, record)
                    raise
            row["status"] = "EXITED"
            save(status_file, record)
            if row["exit_code"]:
                raise RuntimeError(f"{case} failed; see its preserved log")
        record["status"] = "COMPLETED_UNSCORED"
    except BaseException as error:
        record.update(status="FAILED", error=repr(error))
        raise
    finally:
        record["updated_at_UTC"] = datetime.now(timezone.utc).isoformat()
        save(status_file, record)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "inputs", "configs", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--cases", nargs="+", required=True)
    main(parser.parse_args())
