"""Explicitly prepare the already registered volatile O8 overlay; no model run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time


def sha(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def durable_json(path, value):
    temporary = path.with_suffix(".partial")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verified_core_state(core, manifest):
    # The registered O8 custom RTL uses bit2 as BUSY, not HLS AP_IDLE.
    state = {"version": core.read(4), "capability": core.read(8), "cache_bytes": core.read(12),
             "control": core.read(0), "error": core.read(0x64)}
    state["busy"] = bool(state["control"] & 4)
    expected = {"version": int(manifest["core_version"], 0), "capability": int(manifest["capability"], 0),
                "cache_bytes": manifest["cache_capacity_bytes"]}
    if any(state[key] != value for key, value in expected.items()) or state["busy"] or state["error"]:
        raise ValueError("Registered O8 core ABI, idle state or error mismatch: " + repr(state))
    return state


def prepare(args):
    import fcntl
    root, output = args.root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = {"status": "RUNNING", "PID": os.getpid(), "started_UTC": datetime.now(timezone.utc).isoformat(),
              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
              "model_forwards": 0, "overlay_downloaded": False, "download_attempted": False, "DMA_accessed": False,
              "explicit_registered_overlay_action": args.program_registered_overlay}
    started = time.monotonic()

    def mark(phase):
        record.update(phase=phase, elapsed_s=time.monotonic() - started)
        durable_json(output / "preparation.json", record)
        print(phase, flush=True)

    lock = None
    try:
        mark("VERIFY_ASSETS")
        manifest_path = root / "hardware/accepted/firmware_manifest.json"
        if sha(manifest_path) != args.expected_manifest_sha256:
            raise ValueError("Registered firmware manifest hash mismatch")
        manifest = json.loads(manifest_path.read_text())
        bit = root / "hardware/accepted/optimization_8_resident.bit"
        hwh = bit.with_suffix(".hwh")
        for path, kind in ((bit, "bit"), (hwh, "hwh")):
            if sha(path) != manifest[kind]["sha256"]:
                raise ValueError("Registered " + kind + " hash mismatch")
        record.update(manifest_sha256=sha(manifest_path), bit_sha256=sha(bit), hwh_sha256=sha(hwh))
        lock = (root.parent / "yolo26_stage_d/reports/accelerator_job.lock").open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        mark("IMPORT_PYNQ")
        from pynq import Overlay, PL, Clocks
        record["previous_bitfile"] = PL.bitfile_name
        record["previous_FCLK0_MHz"] = Clocks.fclk0_mhz
        old_bit = Path(PL.bitfile_name) if PL.bitfile_name else None
        registered = old_bit is not None and old_bit.is_file() and sha(old_bit) == manifest["bit"]["sha256"]
        if not registered and not args.program_registered_overlay:
            raise ValueError("Matching O8 overlay is not registered; an explicit preparation action is required")
        if not registered:
            record.update(download_attempted=True, overlay_downloaded=None)
        mark("ATTACH_REGISTERED_OVERLAY" if registered else "DOWNLOAD_REGISTERED_OVERLAY")
        overlay = Overlay(str(bit), download=not registered)
        record["overlay_downloaded"] = not registered
        mark("VERIFY_CLOCK_AND_REGISTRATION")
        record["FCLK0_MHz"] = Clocks.fclk0_mhz
        if abs(record["FCLK0_MHz"] - float(manifest["clock_MHz"])) > .01:
            raise ValueError("O8 PS clock does not match the registered firmware")
        if not overlay.is_loaded() or sha(PL.bitfile_name) != manifest["bit"]["sha256"]:
            raise ValueError("Overlay registration did not match after preparation")
        mark("VERIFY_CORE_ABI")
        core = overlay.conv_accel_0
        record["core"] = verified_core_state(core, manifest)
        record["status"] = "READY_REGISTERED_O8_NO_MODEL_FORWARD"
        mark("READY")
    except BaseException as error:
        record.update(status="FAILED", failed_phase=record.get("phase"), error=repr(error))
        mark("FAILED")
        raise
    finally:
        if lock is not None:
            lock.close()
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--program-registered-overlay", action="store_true")
    prepare(parser.parse_args())
