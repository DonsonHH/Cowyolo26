from pathlib import Path
import os, sys, json, gzip, hashlib, time, fcntl, multiprocessing, traceback
os.environ["XILINX_XRT"] = "/usr"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import cv2
import numpy as np
from pynq import PL

ROOT = Path(__file__).resolve().parent
O8 = Path("/home/xilinx/jupyter_notebooks/yolo26_optimization_8")
PORT = Path("/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029")
VIDEO = Path("/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030")
MODEL = Path("/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030")
sys.path[:0] = [str(O8), str(O8 / "runtime_fast"), str(PORT), str(PORT / "source/lap-0.5.13")]
from native_graph import NativeGraph
from device_initialize import initialize
from board_runtime import decode
from frame_pipeline import FramePipeline
from background_fixed_worker import worker
from fixed_arrivals import FixedArrivals
from process_cpu import snapshot


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    partial = path.with_suffix(path.suffix + ".partial")
    with partial.open("w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    partial.replace(path)


def gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def canonical(value):
    return json.loads(json.dumps(value))


def main():
    protocol = load(ROOT / "run_protocol.json")
    out = ROOT / "results"
    out.mkdir(exist_ok=False)
    cv2.setNumThreads(1)
    initial_affinity = sorted(os.sched_getaffinity(0))
    assert initial_affinity == [0, 1]
    os.sched_setaffinity(0, set(protocol['foreground_affinity']))
    state = {"status": "RUNNING", "PID": os.getpid(), "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
             "protocol_sha256": sha(ROOT / "run_protocol.json"), "actual_O8_forwards": 0, "qualification_forwards": 0,
             "warmup_forwards": 0, "cases": [], "initial_affinity": initial_affinity,
             "foreground_affinity": sorted(os.sched_getaffinity(0)), "new_training_updates": 0,
             "actual_camera_or_RFID_hardware": False, "whole_goal_complete": False}
    graph = lock = child = publisher = None
    failure = close_error = None
    try:
        for row in protocol["payload_files"]:
            assert sha(ROOT / row["file"]) == row["sha256"]
        for row in protocol["runtime_files"]:
            assert sha(row["file"]) == row["sha256"]
        assert sha(PL.bitfile_name) == protocol["O8_bit_sha256"]
        prior = load(VIDEO / "results/record.json")
        terminal = load(VIDEO / "results/terminal.json")
        assert terminal["record_sha256"] == sha(VIDEO / "results/record.json") and not (Path("/proc") / str(terminal["PID"])).exists()
        assert prior["model_checkpoint_sha256"] == protocol["foreground_source_model"]
        inputs = load(VIDEO / "board_input_manifest.json")
        selected = [row for row in inputs if row["scene"] == "original" and 8912 <= row["frame0"] <= 10873]
        assert len(selected) == 392
        framebank = np.empty((392, 192, 192, 3), dtype=np.uint8)
        for index, row in enumerate(selected):
            assert sha(VIDEO / row["file"]) == row["sha256"]
            framebank[index] = cv2.imread(str(VIDEO / row["file"]))
        for job in protocol["fixed_jobs"]:
            assert sha(Path(protocol["camera_root"]) / "highres" / ("f" + str(job["source_frame0"]).zfill(5) + ".jpg")) == job["source_JPEG_sha256"]
        lock = Path("/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock").open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state["initialization"] = initialize(O8)
        graph = NativeGraph(192, program=str(MODEL / "program"), plan=str(MODEL / "resident_plan/resident_plan.bin"), options=4,
                            firmware_manifest="hardware/accepted/firmware_manifest.json")
        vector_gate = []
        for row in [row for row in inputs if row["anchor"]]:
            actual = graph.run_image(cv2.imread(str(VIDEO / row["file"]))).copy()
            state["qualification_forwards"] += 1
            with np.load(VIDEO / "native_integer_anchors" / (row["scene"] + "_f" + str(row["frame0"]) + ".npz")) as archive:
                assert actual.tobytes() == archive["native_integer_raw"].tobytes()
            vector_gate.append({"scene": row["scene"], "frame0": row["frame0"], "raw_byte_exact": True})
        assert len(vector_gate) == 8
        state["qualification_gate"] = vector_gate
        old_records = {row["frame0"]: row for row in gz(VIDEO / "results/original/raw_predictions.json.gz")}
        old_trace = gz(VIDEO / "results/original/stride5_counter_trace.json.gz")
        old_raw = np.load(VIDEO / "results/original/all_raw.npy", mmap_mode="r")
        for run in protocol["runs"]:
            folder = out / run["run"]
            folder.mkdir()
            pipeline = FramePipeline(protocol["video"], protocol["tracker_config"], protocol["counter_kwargs"])
            trace = {key: [] for key in ["observations", "post_tracker", "confirmed_only_events", "handoff_events"]}
            for frame in range(0, 8915, 5):
                result = pipeline.update(frame, old_records[frame]["predictions"])
                trace["observations"].append(result["observation"])
                for key in trace:
                    if key != "observations":
                        trace[key].extend(result[key])
            for key in trace:
                assert canonical(trace[key]) == [row for row in old_trace[key] if row["frame0"] < 8915]
            write(folder / "prewarm_history_gate.json", {"cached_ticks": 1783, "all_four_traces_exact": True, "new_model_forwards": 0})
            for _ in range(2):
                graph.run_image(framebank[0])
                state["warmup_forwards"] += 1
            context = multiprocessing.get_context("spawn")
            requests, ready = context.Queue(maxsize=16), context.Queue(maxsize=2)
            worker_protocol = {**protocol, "worker_idle_gated": False, "background_affinity": run["background_affinity"], "CPU_assignment_policy": run["policy"]}
            child = context.Process(target=worker, args=(requests, ready, str(folder / "background"), str(Path(protocol["camera_root"]).parent), worker_protocol))
            child.start()
            response = ready.get(timeout=40)
            assert response["status"] == "READY", response
            t0 = time.monotonic_ns() + 100000000
            period = protocol["period_ns"]
            publisher = FixedArrivals(protocol["fixed_jobs"], requests, t0)
            publisher.start()
            rows, raws, raw_frames, skips = [], [], [], []
            slot = 0
            while slot < 392:
                release = t0 + slot * period
                now = time.monotonic_ns()
                if now < release:
                    time.sleep((release - now) / 1e9)
                now = time.monotonic_ns()
                newest = max(slot, int((now - t0) // period))
                for missed in range(slot, min(newest, 392)):
                    skips.append({"slot": missed, "source_frame0": selected[missed]["frame0"], "release_monotonic_ns": t0 + missed * period, "skip_observed_monotonic_ns": now})
                slot = newest
                if slot >= 392:
                    break
                release = t0 + slot * period
                before = snapshot(child.pid)
                started = time.monotonic_ns()
                actual = graph.run_image(framebank[slot]).copy()
                state["actual_O8_forwards"] += 1
                model_end = time.monotonic_ns()
                oriented = decode(actual, [1050, 1440, 3], .2, 192)
                boxes = [{"xyxy": [float(value[1]) + 870, 1440 - float(value[2]), float(value[3]) + 870, 1440 - float(value[0])],
                          "confidence": float(value[4]), "class": 0} for value in oriented]
                frame = selected[slot]["frame0"]
                result = pipeline.update(frame, boxes)
                trace["observations"].append(result["observation"])
                for key in trace:
                    if key != "observations":
                        trace[key].extend(result[key])
                after = snapshot(child.pid)
                completed = time.monotonic_ns()
                assert before["PID"] == after["PID"] == child.pid and before["starttime_ticks"] == after["starttime_ticks"]
                assert before["nice"] == after["nice"] == 10
                assert sorted(os.sched_getaffinity(0)) == protocol['foreground_affinity']
                rows.append({"slot": slot, "frame0": frame, "release_monotonic_ns": release, "started_monotonic_ns": started,
                             "completed_monotonic_ns": completed, "model_ms": (model_end - started) / 1e6,
                             "processing_ms": (completed - started) / 1e6, "release_to_count_ms": (completed - release) / 1e6,
                             "deadline_met": completed <= release + period, "worker_CPU_before": before, "worker_CPU_after": after,
                             "worker_CPU_tick_delta": after["total_CPU_ticks"] - before["total_CPU_ticks"]})
                raws.append(actual[0])
                raw_frames.append(frame)
                if len(rows) % 50 == 0:
                    write(out / "progress.json", {"status": "RUNNING", "PID": os.getpid(), "run": run["run"], "processed_slots": len(rows), "actual_O8_forwards": state["actual_O8_forwards"]})
                slot += 1
            period_end = t0 + 392 * period
            remaining = period_end - time.monotonic_ns()
            if remaining > 0:
                time.sleep(remaining / 1e9)
            published = publisher.finish()
            publisher = None
            requests.put(None)
            child.join(timeout=90)
            assert not child.is_alive(), "Keep same worker PID; do not restart experiment"
            background = load(folder / "background/record.json")
            assert background["status"] == "ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE" and len(background["jobs"]) == background["model_forwards"] == 10
            child = None
            assert len(rows) + len(skips) == 392
            for frame, raw in zip(raw_frames, raws):
                assert raw.tobytes() == old_raw[frame // 5].tobytes()
            np.savez_compressed(folder / "actual_raw.npz", frame0=np.asarray(raw_frames, dtype=np.int64), raw=np.stack(raws))
            with gzip.GzipFile(filename=str(folder / "counter_trace.json.gz"), mode="wb", mtime=0) as stream:
                stream.write(json.dumps(trace, separators=(",", ":")).encode())
            write(folder / "timing_rows.json", rows)
            write(folder / "skipped_slots.json", skips)
            write(folder / "fixed_job_publication.json", published)
            events = [row for row in trace["handoff_events"] if 8912 <= row["frame0"] <= 10873]
            case = {**run, "offered_slots": 392, "processed_frames": len(rows), "skipped_slots": len(skips),
                    "deadline_misses": sum(not row["deadline_met"] for row in rows),
                    "mean_processing_ms": float(np.mean([row["processing_ms"] for row in rows])),
                    "P95_release_to_count_ms": float(np.quantile([row["release_to_count_ms"] for row in rows], .95)),
                    "processed_per_second_over_offered_duration": len(rows) / 78.4,
                    "source_down_count": sum(row["direction"] == "A->B" for row in events),
                    "source_up_count": sum(row["direction"] == "B->A" for row in events),
                    "periodic_events": events, "actual_background_jobs": 10, "fixed_jobs_not_triggered_by_this_counter": True,
                    "clock_start_monotonic_ns": t0, "period_end_monotonic_ns": period_end,
                    "maximum_fixed_job_publisher_lateness_ms": max(row["publisher_lateness_ms"] for row in published["records"]),
                    "foreground_proc_status": Path("/proc/self/status").read_text(), "foreground_affinity": sorted(os.sched_getaffinity(0))}
            state["cases"].append(case)
            write(out / "record.json", state)
            print(json.dumps(case), flush=True)
        assert len(state["cases"]) == 4
        state.update({"status": "ALL4_FIXED10_JOB_CPU_AFFINITY_O8_ARM_REPEATS_COMPLETE", "hardware_status": graph.status()})
    except BaseException as error:
        failure = error
        state.update({"status": "FAILED", "error": repr(error), "traceback": traceback.format_exc()})
    finally:
        if publisher is not None:
            state["publisher_after_failure"] = publisher.close()
        if child is not None:
            try:
                requests.put_nowait(None)
            except Exception:
                pass
            child.join(timeout=10)
            state["pending_background_child"] = {"PID": child.pid, "alive": child.is_alive()}
        try:
            if graph:
                graph.close()
        except BaseException as error:
            close_error = repr(error)
            state["status"] = "CLOSE_FAILED_DEVICE_STATE_UNCERTAIN"
        state["close_error"] = close_error
        state["PL_after"] = PL.bitfile_name
        if PL.bitfile_name:
            state["PL_after_sha256"] = sha(PL.bitfile_name)
        os.sched_setaffinity(0, initial_affinity)
        state["parent_affinity_restored_before_exit"] = sorted(os.sched_getaffinity(0))
        write(out / "record.json", state)
        os.sync()
        write(out / "terminal.json", {"status": state["status"], "PID": os.getpid(), "actual_O8_forwards": state["actual_O8_forwards"],
                                       "record_sha256": sha(out / "record.json"), "close_error": close_error})
        if lock:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
    if failure or close_error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
