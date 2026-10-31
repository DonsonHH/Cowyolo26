from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import gzip, hashlib, importlib.util, json, math, re, sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    instance = importlib.util.module_from_spec(spec)
    sys.modules[name] = instance
    spec.loader.exec_module(instance)
    return instance


scanner = module("fixed_job_independent_counter", PROJECT / "long_video_fixed_replay_20261029/tools/verify_delivery.py")
body = module("fixed_job_body_tensor", PROJECT / "pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py")
oldsource = PROJECT / "pynq_mosaic192_eval_20261030/board_delivery/results/original"
oldraw = np.load(oldsource / "all_raw.npy", mmap_mode="r")
oldtrace = gz(oldsource / "stride5_counter_trace.json.gz")
camera = PROJECT / "pynq_periodic_joint_20261030/camera_delivery/highres"
prior_bg = PROJECT / "backend_service_20261030/delivery/results/r1_idle_gate/background"
prior_jobs = load(prior_bg / "record.json")["jobs"]
with np.load(PROJECT / "pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz") as data:
    gallery = data["new_gallery"].astype(float)
galleryrows = load(PROJECT / "pynq_identity_ncnn_20261029/input/images.json")["new_gallery"]
final = load(ROOT / "delivery/collection/final_board_state.json")
assert final["all_checked_PIDs_absent"] and final["shared_lock_available"] and all(final["local_services"].values())
assert final["PL_bit_sha256"] == "5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8"
raw_count = ticks = counter_paths = photos = identity_warmups = 0
cases = []
actual_jobs = []
for stage, directory in [("foregroundCPU0", "cpu_partition_20261030"), ("foregroundCPU01", "cpu_partition_free_20261030")]:
    folder = ROOT / "delivery" / stage
    plan = load(folder / "run_protocol.json")
    assert sha(folder / "run_protocol.json") == sha(PROJECT / directory / "protocol/run_v1.json")
    state, terminal = load(folder / "results/record.json"), load(folder / "results/terminal.json")
    assert state["status"] == terminal["status"] == "ALL4_FIXED10_JOB_CPU_AFFINITY_O8_ARM_REPEATS_COMPLETE"
    assert terminal["record_sha256"] == sha(folder / "results/record.json") and terminal["close_error"] is None
    assert state["qualification_forwards"] == state["warmup_forwards"] == 8
    assert state["hardware_status"]["error"] == "0x0" and state["parent_affinity_restored_before_exit"] == [0, 1]
    for spec, case in zip(plan["runs"], state["cases"]):
        runfolder = folder / "results" / spec["run"]
        rows, skips = load(runfolder / "timing_rows.json"), load(runfolder / "skipped_slots.json")
        trace = gz(runfolder / "counter_trace.json.gz")
        epoch = case["clock_start_monotonic_ns"]
        assert sorted([row["slot"] for row in rows] + [row["slot"] for row in skips]) == list(range(392))
        assert case["foreground_affinity"] == plan["foreground_affinity"]
        for row in rows:
            assert row["frame0"] == 8915 + row["slot"] * 5
            assert row["release_monotonic_ns"] == epoch + row["slot"] * 200000000
            assert row["release_monotonic_ns"] <= row["started_monotonic_ns"] <= row["completed_monotonic_ns"]
            assert row["release_to_count_ms"] == (row["completed_monotonic_ns"] - row["release_monotonic_ns"]) / 1e6
            assert row["processing_ms"] == (row["completed_monotonic_ns"] - row["started_monotonic_ns"]) / 1e6
            assert 0 <= row["model_ms"] <= row["processing_ms"]
            assert row["deadline_met"] == (row["completed_monotonic_ns"] <= row["release_monotonic_ns"] + 200000000)
            before, after = row["worker_CPU_before"], row["worker_CPU_after"]
            assert before["PID"] == after["PID"] and before["starttime_ticks"] == after["starttime_ticks"]
            assert before["nice"] == after["nice"] == 10
            assert before["clock_ticks_per_second"] == after["clock_ticks_per_second"] == 100
            assert before["snapshot_finished_monotonic_ns"] <= row["started_monotonic_ns"]
            assert after["snapshot_finished_monotonic_ns"] <= row["completed_monotonic_ns"]
            assert row["worker_CPU_tick_delta"] == after["total_CPU_ticks"] - before["total_CPU_ticks"] >= 0
        for row in skips:
            assert row["skip_observed_monotonic_ns"] >= epoch + (row["slot"] + 1) * 200000000
        assert len(rows) == case["processed_frames"] and len(skips) == case["skipped_slots"]
        assert sum(not row["deadline_met"] for row in rows) == case["deadline_misses"]
        assert float(np.mean([row["processing_ms"] for row in rows])) == case["mean_processing_ms"]
        assert float(np.quantile([row["release_to_count_ms"] for row in rows], .95)) == case["P95_release_to_count_ms"]
        assert len(rows) / 78.4 == case["processed_per_second_over_offered_duration"]
        with np.load(runfolder / "actual_raw.npz") as data:
            assert data["frame0"].tolist() == [row["frame0"] for row in rows]
            for frame, raw in zip(data["frame0"], data["raw"]):
                assert raw.tobytes() == oldraw[int(frame) // 5].tobytes()
                raw_count += 1
        assert [row["frame0"] for row in trace["observations"]] == list(range(0, 8915, 5)) + [row["frame0"] for row in rows]
        for key in trace:
            assert [row for row in trace[key] if row["frame0"] < 8915] == [row for row in oldtrace[key] if row["frame0"] < 8915]
        post = defaultdict(list)
        for row in trace["post_tracker"]:
            post[row["frame0"]].append(row)
        for observation in trace["observations"]:
            positions, ids = {}, set()
            for row in post[observation["frame0"]]:
                tid = row["track_id"]
                if tid is None:
                    continue
                ids.add(tid)
                x1, y1, x2, y2 = row["xyxy"]
                if .34 < (x1 + x2) / (2 * 2560) < .75:
                    positions[str(tid)] = (y1 + y2) / (2 * 1440)
            assert observation["confirmed_positions"] == positions and observation["confirmed_IDs"] == sorted(ids)
        ticks += len(trace["observations"])
        for key, handoff in [("confirmed_only_events", False), ("handoff_events", True)]:
            events, _ = scanner.batch_events(trace["observations"], handoff)
            assert events == trace[key]
            counter_paths += 1
            if handoff:
                scoped = [event for event in events if 8912 <= event["frame0"] <= 10873]
                assert scoped == case["periodic_events"]
                assert sum(event["direction"] == "A->B" for event in scoped) == case["source_down_count"]
        publications = load(runfolder / "fixed_job_publication.json")["records"]
        worker = load(runfolder / "background/record.json")
        assert len(publications) == len(worker["jobs"]) == worker["model_forwards"] == case["actual_background_jobs"] == 10
        assert worker["actual_nice"] == 10 and worker["actual_CPU_affinity"] == spec["background_affinity"] and worker["NCNN_threads"] == 1
        assert all(mask == spec["background_affinity"] for mask in worker["after_warmup_thread_affinities"].values())
        identity_warmups += len(worker["warmups"])
        for index, (published, actual, fixed, prior) in enumerate(zip(publications, worker["jobs"], plan["fixed_jobs"], prior_jobs)):
            assert published["fixed_job_index"] == actual["fixed_job_index"] == fixed["fixed_job_index"] == index
            assert published["requested_monotonic_ns"] == epoch + fixed["requested_enqueue_offset_ns"] == actual["requested_enqueue_monotonic_ns"]
            assert actual["release_monotonic_ns"] == published["requested_monotonic_ns"]
            assert actual["enqueued_monotonic_ns"] == published["enqueue_started_monotonic_ns"] >= published["requested_monotonic_ns"]
            assert published["publisher_lateness_ms"] == (published["enqueue_started_monotonic_ns"] - published["requested_monotonic_ns"]) / 1e6
            assert published["publisher_CPU_affinity"] == plan["foreground_affinity"]
            assert all(mask == spec["background_affinity"] for mask in actual["thread_affinities_after_job"].values())
            assert actual["source_frame0"] == fixed["source_frame0"] == prior["source_frame0"]
            assert actual["event"] == fixed["event"] and actual["selection"] == fixed["selection"]
            assert actual["identity_reference_available"] is False and actual["JPEG_source"] == "same_frame_file_read"
            assert actual["queue_wait_ms"] == (actual["started_monotonic_ns"] - actual["enqueued_monotonic_ns"]) / 1e6
            assert actual["enqueue_to_result_ms"] == (actual["completed_monotonic_ns"] - actual["enqueued_monotonic_ns"]) / 1e6
            jpeg = camera / ("f" + str(actual["source_frame0"]).zfill(5) + ".jpg")
            assert sha(jpeg) == actual["source_JPEG_sha256"] == fixed["source_JPEG_sha256"]
            with Image.open(jpeg) as image:
                native = image.convert("RGB")
            left, top, right, bottom = fixed["box_native_xyxy"]
            crop = [max(0, math.floor(left-870)), max(0, math.floor(top)), min(1050, math.ceil(right-870)), min(1440, math.ceil(bottom))]
            expected_photo = native.crop(crop).transpose(Image.Transpose.ROTATE_270)
            photo = runfolder / "background" / actual["photo_file"]
            assert sha(photo) == actual["photo_sha256"] == prior["photo_sha256"]
            with Image.open(photo) as image:
                assert image.convert("RGB").tobytes() == expected_photo.tobytes()
            tensor = body.body_tensor(expected_photo)
            vector = runfolder / "background" / actual["vector_file"]
            assert sha(vector) == actual["vector_sha256"]
            with np.load(vector) as data, np.load(prior_bg / prior["vector_file"]) as reference:
                for key in ["input", "raw", "normalized", "scores"]:
                    assert data[key].tobytes() == reference[key].tobytes()
                assert tensor.tobytes() == data["input"].tobytes()
                assert hashlib.sha256(data["raw"].tobytes()).hexdigest() == actual["raw_feature_sha256"]
                norm = data["raw"].astype(float) / np.linalg.norm(data["raw"].astype(float))
                assert float(np.max(np.abs(norm - data["normalized"]))) < 1e-7
                dots = data["normalized"].astype(float) @ gallery.T
                scores = np.asarray([max(dots[i] for i, row in enumerate(galleryrows) if row["identity"] == label) for label in plan["registered_IDs"]])
                assert float(np.max(np.abs(scores - data["scores"]))) < 1e-12
                winner = int(np.argmax(scores))
                assert plan["registered_IDs"][winner] == actual["predicted_id"] == prior["predicted_id"]
                assert abs(float(scores[winner]) - actual["similarity"]) < 1e-12
                assert bool(scores[winner] >= plan["fixed_identity_threshold"]) == actual["accepted"] == prior["accepted"]
            photos += 1
            actual_jobs.append({"stage": stage, "run": spec["run"], "repeat": spec["repeat"], "policy": spec["policy"], "fixed_job_index": index,
                                "source_frame0": actual["source_frame0"], "photo_file": str(photo.resolve()), "photo_sha256": sha(photo),
                                "accepted": actual["accepted"], "predicted_id": actual["predicted_id"], "similarity": actual["similarity"],
                                "queue_ms": actual["queue_wait_ms"], "enqueue_to_result_ms": actual["enqueue_to_result_ms"],
                                "network_ms": actual["actual_identity_network_ms"]})
        cases.append({"stage": stage, **{key: value for key, value in case.items() if key not in ["periodic_events", "foreground_proc_status"]},
                      "mean_model_ms": float(np.mean([row["model_ms"] for row in rows])),
                      "positive_worker_CPU_windows": sum(row["worker_CPU_tick_delta"] > 0 for row in rows),
                      "worker_CPU_ticks": sum(row["worker_CPU_tick_delta"] for row in rows),
                      "maximum_identity_result_ms": max(job["enqueue_to_result_ms"] for job in worker["jobs"]),
                      "maximum_identity_queue_ms": max(job["queue_wait_ms"] for job in worker["jobs"]),
                      "accepted_predictions": sum(job["accepted"] for job in worker["jobs"])})
assert raw_count == 2963 and photos == 80 and identity_warmups == 8 and ticks == 17227 and counter_paths == 16
assert [row["source_down_count"] for row in cases] == [9, 10, 9, 8, 10, 10, 8, 10]
assert len({row["photo_sha256"] for row in actual_jobs}) == 10
pairs = []
for stage in ["foregroundCPU0", "foregroundCPU01"]:
    for repeat in [1, 2]:
        for index in range(10):
            a = next(row for row in actual_jobs if row["stage"] == stage and row["repeat"] == repeat and row["policy"] == "shared" and row["fixed_job_index"] == index)
            b = next(row for row in actual_jobs if row["stage"] == stage and row["repeat"] == repeat and row["policy"] == "core1" and row["fixed_job_index"] == index)
            assert a["photo_sha256"] == b["photo_sha256"]
            pairs.append({"stage": stage, "repeat": repeat, "fixed_job_index": index, "photo_sha256": a["photo_sha256"],
                          "core1_minus_shared_result_ms": b["enqueue_to_result_ms"] - a["enqueue_to_result_ms"],
                          "core1_minus_shared_queue_ms": b["queue_ms"] - a["queue_ms"]})
result = {"status": "ALL8_REAL_AFFINITY_RUNS2963_RAW17227_OBSERVATIONS80_ORIGINAL_PHOTOS_FEATURES_AND40_FIXED_JOB_PAIRS_VERIFIED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "actual_timed_O8_forwards": raw_count,
          "actual_O8_qualification_forwards": 16, "actual_O8_warmups": 16, "actual_ARM_identity_queries": 80, "actual_ARM_identity_warmups": 8,
          "all_new_actual_model_forwards": 3083, "new_Torch_reference_forwards": 0,
          "counter_observation_ticks": ticks, "counter_paths": counter_paths, "actual_photos_inputs_and_features_verified": photos,
          "unique_photo_pixel_inputs": 10, "fixed_job_pair_comparisons": len(pairs),
          "all80_prior_same_photo_input_raw_normalized_scores_arrays_byte_equal": True,
          "foreground_affinity_scope": "main thread and recorded publisher only; not every preexisting library thread independently observed",
          "background_thread_affinities_checked": True, "cases": cases,
          "new_training_updates": 0, "new_independent_test_or_identity_GT": False, "whole_goal_complete": False}
for filename, value in [("independent_verification.json", result), ("actual_job_rows.json", actual_jobs), ("fixed_job_pair_differences.json", pairs)]:
    output = ROOT / "results" / filename
    assert not output.exists()
    output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key != "cases"}))
