from pathlib import Path
import os, json, hashlib, tarfile, traceback, lzma
from pynq import PL

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2) + "\n")


try:
    state = load(ROOT / "results/record.json")
    terminal = load(ROOT / "results/terminal.json")
    protocol = load(ROOT / "run_protocol.json")
    assert state["status"] == terminal["status"] == "ALL4_FIXED10_JOB_CPU_AFFINITY_O8_ARM_REPEATS_COMPLETE"
    assert terminal["record_sha256"] == sha(ROOT / "results/record.json") and terminal["close_error"] is None
    assert not (Path("/proc") / str(terminal["PID"])).exists()
    assert state["actual_O8_forwards"] == sum(row["processed_frames"] for row in state["cases"])
    assert state["qualification_forwards"] == state["warmup_forwards"] == 8
    assert state["PL_after_sha256"] == protocol["O8_bit_sha256"] == sha(Path(PL.bitfile_name))
    children = []
    for run in protocol["runs"]:
        folder = ROOT / "results" / run["run"] / "background"
        child = load(folder / "record.json")
        done = load(folder / "terminal.json")
        assert child["status"] == done["status"] == "ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE"
        assert done["record_sha256"] == sha(folder / "record.json") and not (Path("/proc") / str(done["PID"])).exists()
        assert len(child["jobs"]) == child["model_forwards"] == 10 and len(child["warmups"]) == 1
        children.append({"PID": done["PID"], "proc_exists": False, "run": run["run"], "jobs": 10})
    write(ROOT / "final_state.json", {"status": "FOUR_FIXED_JOB_RUN_PARENT_AND_CHILDREN_ABSENT_SAME_O8", "parent_PID": terminal["PID"],
                                       "children": children, "PL_bitfile": PL.bitfile_name, "PL_bit_sha256": sha(Path(PL.bitfile_name)),
                                       "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "memory": Path("/proc/meminfo").read_text()})
    # Group repeated original files adjacently so the lossless xz dictionary can reuse them.
    files = sorted([path for path in (ROOT / "results").rglob("*") if path.is_file()], key=lambda path: (path.suffix, path.name, str(path)))
    files += [ROOT / row["file"] for row in protocol["payload_files"]]
    files += [ROOT / name for name in ["run_protocol.json", "launch.json", "run.log", "final_state.json"]]
    manifest = [{"file": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)} for path in files]
    write(ROOT / "result_manifest.json", manifest)
    archive = ROOT / "cpu_partition_delivery_v1.tar.xz"
    assert not archive.exists()
    with tarfile.open(archive, "w:xz", preset=3) as stream:
        for path in files + [ROOT / "result_manifest.json"]:
            stream.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
    os.sync()
    transfer = {"archive": str(archive), "bytes": archive.stat().st_size, "sha256": sha(archive), "members": len(files) + 1,
                "manifest_files": len(files), "all_original_files_included": True, "lossless_archive_compression": "xz preset3 grouped repeated filenames; source files unchanged"}
    write(ROOT / "transfer.json", transfer)
    write(ROOT / "collection_terminal.json", {"status": "FULL_ORIGINAL_FIXED_JOB_ARCHIVE_COMPLETE", "PID": os.getpid(), "transfer": transfer})
    print(json.dumps(transfer), flush=True)
except BaseException as error:
    write(ROOT / "collection_terminal.json", {"status": "FAILED", "PID": os.getpid(), "error": repr(error), "traceback": traceback.format_exc()})
    raise
