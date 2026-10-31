"""Run the bounded R1 regression suite once and preserve a small result record."""
import argparse
import contextlib
import io
import json
import platform
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from . import test_r1
from .tracker import verify_method_scope


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        suite = unittest.defaultTestLoader.loadTestsFromModule(test_r1)
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".log").write_text(stream.getvalue(), encoding="utf-8")
    record = {"status": "PASS" if result.wasSuccessful() else "FAIL", "tests": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "python": sys.version, "platform": platform.platform(),
              "time_UTC": datetime.now(timezone.utc).isoformat(),
              "all_observations_are_software_fixtures": True,
              "real_cow_event_accuracy_verified": False,
              "secondstage_scope": verify_method_scope()}
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))
    if not result.wasSuccessful():
        print(stream.getvalue())
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
