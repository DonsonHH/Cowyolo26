from pathlib import Path
import hashlib, json, os, socket, fcntl, tarfile, traceback
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
    plan = load(ROOT / "run_protocol.json")
    assert all(not (Path("/proc") / str(pid)).exists() for pid in plan["previous_task_PIDs_required_absent"])
    stages = []
    paths = []
    all_pids = []
    for spec in plan["stages"]:
        directory = Path(spec["directory"])
        protocol = load(directory / "run_protocol.json")
        assert sha(directory / "run_protocol.json") == spec["protocol_sha256"]
        state, terminal = load(directory / "results/record.json"), load(directory / "results/terminal.json")
        assert state["status"] == terminal["status"] == "ALL4_FIXED10_JOB_CPU_AFFINITY_O8_ARM_REPEATS_COMPLETE"
        assert terminal["record_sha256"] == sha(directory / "results/record.json") and terminal["close_error"] is None
        assert not (Path("/proc") / str(terminal["PID"])).exists()
        assert state["qualification_forwards"] == state["warmup_forwards"] == 8
        assert state["actual_O8_forwards"] == sum(row["processed_frames"] for row in state["cases"])
        assert state["PL_after_sha256"] == protocol["O8_bit_sha256"] == sha(Path(PL.bitfile_name))
        all_pids.append(terminal["PID"])
        children = []
        for run in protocol["runs"]:
            folder = directory / "results" / run["run"] / "background"
            worker, done = load(folder / "record.json"), load(folder / "terminal.json")
            assert worker["status"] == done["status"] == "ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE"
            assert done["record_sha256"] == sha(folder / "record.json") and not (Path("/proc") / str(done["PID"])).exists()
            assert len(worker["jobs"]) == worker["model_forwards"] == 10 and len(worker["warmups"]) == 1
            assert worker["actual_CPU_affinity"] == run["background_affinity"] and worker["NCNN_threads"] == 1
            for actual, expected in zip(worker["jobs"], protocol["fixed_jobs"]):
                assert actual["fixed_job_index"] == expected["fixed_job_index"]
                for key in ["photo_sha256", "input_tensor_sha256", "raw_feature_sha256"]:
                    assert actual[key] == expected["expected_prior_actual"][key]
                assert sha(folder / actual["photo_file"]) == actual["photo_sha256"]
                assert sha(folder / actual["vector_file"]) == actual["vector_sha256"]
            all_pids.append(done["PID"])
            children.append({"run": run["run"], "PID": done["PID"], "jobs": 10})
        for item in protocol["payload_files"]:
            assert sha(directory / item["file"]) == item["sha256"]
        stages.append({"stage": spec["name"], "foreground_affinity": protocol["foreground_affinity"], "parent_PID": terminal["PID"],
                       "timed_O8_forwards": state["actual_O8_forwards"], "qualification_O8_forwards": 8, "O8_warmups": 8,
                       "identity_queries": 40, "identity_warmups": 4, "cases": state["cases"], "children": children})
        for path in directory.rglob("*"):
            if path.is_file() and not path.name.endswith((".tar.gz", ".tar.xz", ".partial")):
                assert not path.is_symlink() and path.resolve().is_relative_to(directory)
                paths.append((spec["name"] + "/" + path.relative_to(directory).as_posix(), path))
    lock = Path("/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock").open("r")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(lock, fcntl.LOCK_UN)
    lock.close()
    services = {}
    for port in [22, 9090]:
        connection = socket.create_connection(("127.0.0.1", port), timeout=2)
        connection.close()
        services[str(port)] = True
    final = {"status": "ALL8_FIXED_JOB_PARENTS_AND_WORKERS_ABSENT_SAME_O8_LOCAL_SERVICES_UP", "stages": stages,
             "all_checked_PIDs": all_pids, "all_checked_PIDs_absent": True, "collector_PID": os.getpid(),
             "PL_bitfile": PL.bitfile_name, "PL_bit_sha256": sha(Path(PL.bitfile_name)), "shared_lock_available": True,
             "local_services": services, "eth0_carrier": Path("/sys/class/net/eth0/carrier").read_text().strip(),
             "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "new_model_forwards_by_collection": 0,
             "PL_programming": False, "whole_goal_complete": False}
    write(ROOT / "final_board_state.json", final)
    paths += [("collection/" + name, ROOT / name) for name in ["collect_eight.py", "run_protocol.json", "launch.json", "final_board_state.json"]]
    paths.sort(key=lambda item: (item[1].suffix, item[1].name, item[0]))
    manifest = [{"file": member, "bytes": path.stat().st_size, "sha256": sha(path)} for member, path in paths]
    write(ROOT / "result_manifest.json", manifest)
    archive = ROOT / "all8_fixed_job_original_delivery_v1.tar.xz"
    assert not archive.exists()
    with tarfile.open(archive, "w:xz", preset=3) as stream:
        for member, path in paths:
            stream.add(path, arcname=member, recursive=False)
        stream.add(ROOT / "result_manifest.json", arcname="result_manifest.json", recursive=False)
    os.sync()
    transfer = {"archive": str(archive), "bytes": archive.stat().st_size, "sha256": sha(archive), "members": len(paths) + 1,
                "manifest_files": len(paths), "all8_original_result_files_included": True, "lossless_compression": "xz preset3; no original file rewriting",
                "stage_timed_O8_forwards": [row["timed_O8_forwards"] for row in stages], "actual_identity_queries": 80}
    write(ROOT / "transfer.json", transfer)
    write(ROOT / "collection_terminal.json", {"status": "ALL8_FULL_ORIGINAL_ARCHIVE_COMPLETE", "PID": os.getpid(), "transfer": transfer})
    print(json.dumps(transfer), flush=True)
except BaseException as error:
    write(ROOT / "collection_terminal.json", {"status": "FAILED", "PID": os.getpid(), "error": repr(error), "traceback": traceback.format_exc()})
    raise
