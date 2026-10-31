from pathlib import Path
from datetime import datetime, timezone
import ast
import copy
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
OLD = PROJECT / "backend_service_20261030"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


worker = (OLD / "tools/background_selected_worker.py").read_text(encoding="utf-8")
replacements = [
    ("out=Path(destination);out.mkdir(exist_ok=False);root=Path(root);os.nice(protocol['backend_nice_increment'])",
     "out=Path(destination);out.mkdir(exist_ok=False);root=Path(root);os.sched_setaffinity(0,set(protocol['background_affinity']));os.nice(protocol['backend_nice_increment'])"),
    ("  ready.put({'status':'READY','PID':os.getpid()})",
     "  state['CPU_assignment_policy']=protocol['CPU_assignment_policy'];state['NCNN_threads']=1\n  state['after_warmup_thread_affinities']={q.name:sorted(os.sched_getaffinity(int(q.name))) for q in Path('/proc/self/task').iterdir()}\n  assert all(v==protocol['background_affinity'] for v in state['after_warmup_thread_affinities'].values())\n  ready.put({'status':'READY','PID':os.getpid()})"),
    ("   result['vector_file']=vector.name;result['vector_sha256']=sha(vector)",
     "   result['vector_file']=vector.name;result['vector_sha256']=sha(vector)\n   result['fixed_job_index']=job['fixed_job_index'];result['requested_enqueue_monotonic_ns']=job['requested_enqueue_monotonic_ns']\n   result['thread_affinities_after_job']={q.name:sorted(os.sched_getaffinity(int(q.name))) for q in Path('/proc/self/task').iterdir()}\n   assert all(v==protocol['background_affinity'] for v in result['thread_affinities_after_job'].values())\n   expected=protocol['fixed_jobs'][job['fixed_job_index']]['expected_prior_actual']\n   for key in ['photo_sha256','input_tensor_sha256','raw_feature_sha256']:assert result[key]==expected[key],('same_fixed_job',job['fixed_job_index'],key)\n   assert result['predicted_id']==expected['predicted_id'] and result['accepted']==expected['accepted'] and result['similarity']==expected['similarity']")]
for old, new in replacements:
    assert worker.count(old) == 1
    worker = worker.replace(old, new)
for name, text in [("background_fixed_worker.py", worker), ("process_cpu.py", (OLD / "tools/process_cpu.py").read_text(encoding="utf-8"))]:
    path = ROOT / "tools" / name
    assert not path.exists()
    ast.parse(text)
    path.write_text(text, encoding="utf-8")
base = load(OLD / "protocol/run_v1.json")
prior_folder = OLD / "delivery/results/r1_idle_gate"
enqueued = load(prior_folder / "enqueued_identity_jobs.json")
actual = load(prior_folder / "background/record.json")["jobs"]
epoch = load(OLD / "delivery/results/record.json")["cases"][0]["clock_start_monotonic_ns"]
jobs = []
for index, (source, prior) in enumerate(zip(enqueued, actual)):
    offset = source["enqueued_monotonic_ns"] - epoch
    job = copy.deepcopy(source)
    for key in ["release_monotonic_ns", "enqueued_monotonic_ns"]:
        del job[key]
    job.update({"fixed_job_index": index, "requested_enqueue_offset_ns": offset,
                "expected_prior_actual": {key: prior[key] for key in ["photo_sha256", "input_tensor_sha256", "raw_feature_sha256", "predicted_id", "accepted", "similarity"]}})
    assert source["source_frame0"] == prior["source_frame0"]
    assert offset >= (source["source_frame0"] - 8915) * 40000000 and offset < 78400000000
    jobs.append(job)
assert len(jobs) == 10
protocol = {key: base[key] for key in ["video", "tracker_config", "counter_kwargs", "registered_IDs", "fixed_identity_threshold",
                                     "backend_nice_increment", "foreground_source_model", "background_encoder", "O8_bit_sha256", "camera_root", "runtime_files"]}
payload_names = ["board_partition_repeats.py", "background_fixed_worker.py", "fixed_arrivals.py", "process_cpu.py", "collect_results.py"]
protocol.update({"status": "FROZEN_BEFORE_FIXED_JOB_CPU_AFFINITY_REAL_BOARD_RUNS", "created_UTC": datetime.now(timezone.utc).isoformat(),
                 "period_ns": 200000000, "offered_slots_per_case": 392, "foreground_affinity": [0], "background_NCNN_threads": 1,
                 "runs": [{"run": "r1_shared", "policy": "shared", "repeat": 1, "background_affinity": [0, 1]},
                          {"run": "r1_core1", "policy": "core1", "repeat": 1, "background_affinity": [1]},
                          {"run": "r2_core1", "policy": "core1", "repeat": 2, "background_affinity": [1]},
                          {"run": "r2_shared", "policy": "shared", "repeat": 2, "background_affinity": [0, 1]}],
                 "fixed_jobs": jobs, "fixed_jobs_per_case": 10, "jobs_decoupled_from_current_counter": True,
                 "prior_job_definition": "backend_service_20261030/r1_idle_gate actual ten photographs and original enqueue offsets",
                 "prior_protocol_sha256": sha(OLD / "protocol/run_v1.json"),
                 "prior_enqueued_jobs_sha256": sha(prior_folder / "enqueued_identity_jobs.json"),
                 "prior_actual_background_sha256": sha(prior_folder / "background/record.json"),
                 "plan_sha256": sha(ROOT / "计划与验收.md"),
                 "payload_files": [{"file": name, "sha256": sha(ROOT / "tools" / name)} for name in payload_names],
                 "camera_JPEG_integrity_read_before_period_disclosed": True, "no_every_frame_highres_ring": True,
                 "original_framebank_is_ready_lowres_replay": True, "actual_camera_or_RFID_hardware": False,
                 "expected_qualification_O8_forwards": 8, "expected_O8_warmups": 8, "expected_identity_queries": 40,
                 "expected_identity_warmups": 4, "expected_timed_O8_maximum": 1568,
                 "default_policy_changed": False, "new_training_updates": 0, "new_independent_test": False, "whole_goal_complete": False})
target = ROOT / "protocol/run_v1.json"
target.parent.mkdir(exist_ok=False)
target.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
archive = ROOT / "cpu_partition_input_v1.tar.gz"
assert not archive.exists()
for name in payload_names:
    ast.parse((ROOT / "tools" / name).read_text(encoding="utf-8"))
with tarfile.open(archive, "w:gz") as stream:
    for name in payload_names:
        stream.add(ROOT / "tools" / name, arcname=name, recursive=False)
    stream.add(target, arcname="run_protocol.json", recursive=False)
record = {"bytes": archive.stat().st_size, "sha256": sha(archive), "members": len(payload_names) + 1,
          "protocol_sha256": sha(target), "source_job_count": len(jobs), "new_model_forwards": 0}
(ROOT / "evidence/input_bundle.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record))
