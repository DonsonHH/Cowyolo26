from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
payload=ROOT/"payload";payload.mkdir(exist_ok=False)
base=PROJECT/"identity_joint_pair_20261030/tools"
for name in["background_fixed_worker.py","process_cpu.py"]:
    (payload/name).write_bytes((base/name).read_bytes())
source=(base/"fixed_arrivals.py").read_text(encoding="utf-8")
assert source.count("assert len(self.records) == len(self.jobs) == 10")==1
source=source.replace("assert len(self.records) == len(self.jobs) == 10","assert len(self.records) == len(self.jobs) and len(self.jobs) in (0,10)")
source=source.replace('"ALL10_FIXED_JOBS_PUBLISHED"','"ALL_FIXED_JOBS_PUBLISHED"')
(payload/"fixed_arrivals.py").write_bytes(source.encode())
(payload/"jpeg_producer.py").write_bytes((PROJECT/"identity_trigger_pair_20261030/payload/jpeg_producer.py").read_bytes())
runner=(base/"board_pair_repeats.py").read_text(encoding="utf-8")
def replace(old,new,n=1):
    global runner
    assert runner.count(old)==n,(old,runner.count(old),n)
    runner=runner.replace(old,new)
replace("import os, sys, json, gzip, hashlib, time, fcntl, multiprocessing, traceback","import os, sys, json, gzip, hashlib, time, fcntl, multiprocessing, traceback, gc, resource")
replace("from pynq import PL","from pynq import PL, Overlay")
replace("from identity_qualification import qualify","from jpeg_producer import JPEGProducer")
replace("def main():",'''def sampled_system():
    vm = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in ["pswpin","pswpout","pgmajfault","pgfault"]:
            vm[key] = int(value)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {"sample_monotonic_ns":time.monotonic_ns(),"vmstat":vm,"ru_minflt":usage.ru_minflt,
            "ru_majflt":usage.ru_majflt,"ru_utime":usage.ru_utime,"ru_stime":usage.ru_stime,
            "process_status":Path("/proc/self/status").read_text()}


def main():''')
replace("graph = lock = child = publisher = None","graph = lock = child = publisher = producer = None")
replace('assert sha(PL.bitfile_name) == protocol["O8_bit_sha256"]',
        'state["PL_before"] = PL.bitfile_name\n        state["PL_before_IP_names"] = list(PL.ip_dict)\n        assert state["boot_id"] == protocol["expected_boot_id"]')
replace('lock = Path("/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock").open("a")',
        '''camera_manifest = load(Path(protocol["camera_root"])/"manifest.json")
        assert sha(Path(protocol["camera_root"])/"manifest.json") == protocol["camera_manifest_SHA256"]
        camera_byframe = {row["frame0"]:row for row in camera_manifest}
        assert all(row["frame0"] in camera_byframe for row in selected)
        lock = Path("/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock").open("a")''')
replace('state["identity_qualification"] = qualify(ROOT, protocol)', '''bit = O8/"hardware/accepted/optimization_8_resident.bit"
        assert sha(bit) == protocol["O8_bit_sha256"] and sha(bit.with_suffix(".hwh")) == protocol["O8_hwh_sha256"]
        state["explicit_O8_programming"] = not (PL.bitfile_name and sha(PL.bitfile_name) == protocol["O8_bit_sha256"])
        if state["explicit_O8_programming"]:
            overlay = Overlay(str(bit),download=True)
            assert overlay.is_loaded()
        assert sha(PL.bitfile_name) == protocol["O8_bit_sha256"]
        state["loaded_O8_sha256_before_model"] = sha(PL.bitfile_name)''')
replace('folder.mkdir()\n            pipeline', '''folder.mkdir()
            gc.collect()
            jpeg_prewarm_started = time.monotonic_ns()
            for input_row in selected:
                camera_row = camera_byframe[input_row["frame0"]]
                assert sha(Path(protocol["camera_root"])/camera_row["file"]) == camera_row["sha256"]
            jpeg_prewarm_ms = (time.monotonic_ns()-jpeg_prewarm_started)/1e6
            pipeline''')
replace('period = protocol["period_ns"]\n            publisher = FixedArrivals(protocol["fixed_jobs"], requests, t0)', '''period = protocol["period_ns"]
            source_rows = [camera_byframe[row["frame0"]] for row in selected]
            system_before = sampled_system()
            if run["input_producer"]:
                producer = JPEGProducer(source_rows,protocol["camera_root"],t0,period)
                producer.start()
            publisher = FixedArrivals(protocol["fixed_jobs"] if run["identity_workload"] else [], requests, t0)''')
replace("rows, raws, raw_frames, skips = [], [], [], []","rows, raws, raw_frames, skips, input_packets = [], [], [], [], []")
replace("actual = graph.run_image(framebank[slot]).copy()",'''if producer:
                    producer.pin(selected[slot]["frame0"])
                actual = graph.run_image(framebank[slot]).copy()''')
replace("after = snapshot(child.pid)\n                completed",'''input_wait_started = time.monotonic_ns()
                if producer:
                    packet = producer.take(frame)
                    received = time.monotonic_ns()
                    input_packets.append({**packet["record"],"foreground_wait_started_monotonic_ns":input_wait_started,
                                          "foreground_received_monotonic_ns":received})
                    del packet
                else:
                    received = input_wait_started
                after = snapshot(child.pid)
                completed''')
replace('"worker_CPU_tick_delta": after["total_CPU_ticks"] - before["total_CPU_ticks"]})',
        '"worker_CPU_tick_delta": after["total_CPU_ticks"] - before["total_CPU_ticks"], "JPEG_input_wait_ms": (received-input_wait_started)/1e6})')
replace("published = publisher.finish()\n            publisher = None",'''system_after = sampled_system()
            if producer:
                producer_record = producer.finish(timeout=30)
                assert len(producer_record["records"]) == 392 and producer_record["pinned_at_end"] is None
                producer = None
            else:
                producer_record = {"status":"INPUT_PRODUCER_DISABLED","thread_alive":False,"records":[]}
            published = publisher.finish()
            publisher = None''')
replace('== background["model_forwards"] == 10','== background["model_forwards"] == (10 if run["identity_workload"] else 0)')
replace('write(folder / "fixed_job_publication.json", published)', '''write(folder / "fixed_job_publication.json", published)
            write(folder / "producer_record.json", producer_record)
            write(folder / "input_packets.json", input_packets)
            write(folder / "system_boundaries.json", {"before":system_before,"after":system_after})''')
replace('"actual_background_jobs": 10, "fixed_jobs_not_triggered_by_this_counter": True,',
        '"actual_background_jobs": len(background["jobs"]), "fixed_jobs_not_triggered_by_this_counter": True,')
replace('max(row["publisher_lateness_ms"] for row in published["records"])',
        'max((row["publisher_lateness_ms"] for row in published["records"]),default=0.)')
replace('"foreground_proc_status": Path("/proc/self/status").read_text(), "foreground_affinity": sorted(os.sched_getaffinity(0))}',
        '''"foreground_proc_status": Path("/proc/self/status").read_text(), "foreground_affinity": sorted(os.sched_getaffinity(0)),
                    "actual_producer_frames":len(producer_record["records"]), "common_JPEG_prewarm_ms":jpeg_prewarm_ms,
                    "resident_identity_warmups":len(background["warmups"])}''')
replace('assert len(state["cases"]) == 4','assert len(state["cases"]) == 8')
replace('ALL4_OLD_NEW_NEW_OLD_IDENTITY_FIXED10_O8_ARM_REPEATS_COMPLETE','ALL8_WORKLOAD_2X2_MIRROR_ORDER_REPEATS_COMPLETE')
replace('if publisher is not None:\n            state["publisher_after_failure"] = publisher.close()', '''if producer is not None:
            try:
                state["producer_after_failure"] = producer.close(timeout=30)
            except BaseException as error:
                state["producer_close_error"] = repr(error)
                state["producer_thread_still_alive"] = producer.thread.is_alive()
        if publisher is not None:
            state["publisher_after_failure"] = publisher.close()''')
replace('if graph:\n                graph.close()', 'if graph:\n                state["graph_memory_before_close"] = graph.memory()\n                graph.close()')
(payload/"board_workload_ablation.py").write_bytes(runner.encode())
for f in payload.glob("*.py"):ast.parse(f.read_text(encoding="utf-8"),filename=str(f))
old=load(PROJECT/"identity_joint_pair_20261030/protocol/run_v1.json")
p={k:v for k,v in old.items()if k not in["runs","payload_files","status","created_UTC","expected_O8_warmups","expected_identity_queries","expected_identity_warmups"]}
conditions={"A":(False,False),"B":(True,False),"C":(False,True),"D":(True,True)}
order=list("ABCDDCBA")
p.update({"status":"FROZEN_BEFORE_NEW_WORKLOAD_FACTOR_MODEL_FORWARD","created_UTC":datetime.now(timezone.utc).isoformat(),
          "task_root":"/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031",
          "expected_boot_id":"e7059099-ecb8-451e-a9aa-a66c8222196b",
          "O8_hwh_sha256":"d6cf7f228c93f06523ad8e71efa9c280ba924ecc93d13f8ecdf90351238b4a6a",
          "camera_manifest_SHA256":sha(PROJECT/"pynq_periodic_joint_20261030/camera_delivery/manifest.json"),
          "models":{"old":old["models"]["old"]},"all_workers_resident_and_same_warmup_even_when_zero_jobs":True,
          "input_factor_scope":"producer read+SHA+bounded bank+pin+take; background10images still read source files in both W-on conditions",
          "model_timing_includes_input_pin_if_enabled":True,
          "common_full_JPEG_hash_read_before_each_period":True,"no_global_cache_or_swap_controls":True,
          "runs":[{"run":f'r{i+1}_{name}',"condition":name,"repeat":1 if i<4 else 2,
                   "input_producer":conditions[name][0],"identity_workload":conditions[name][1],
                   "identity_model":"old","policy":"shared","background_affinity":[0,1]}for i,name in enumerate(order)],
          "expected_qualification_O8_forwards":8,"expected_O8_warmups":16,
          "expected_identity_queries":40,"expected_identity_warmups":8,
          "maximum_timed_O8_forwards":3136,"maximum_total_board_image_forwards":3208,
          "default_model_or_threshold_changed":False,"new_independent_test":False,
          "explicit_existing_O8_download_for_new_experiment_permitted_by_task":True,
          "posthoc_after_completed_original_trigger_diagnostic":True,"whole_goal_complete":False})
preflight=load(ROOT/"evidence/board_preflight02.json");state=json.loads(preflight["stdout"])
assert state["accelerator_lock_available"]and not state["own_task_script_processes"]
assert state["boot_id"]==p["expected_boot_id"]and state["PL_bitfile_name"]is None
for row in state["records"]:
    if row["file"].endswith(".py"):p["runtime_files"].append({"file":row["file"],"sha256":row["sha256"]})
p["payload_files"]=[{"file":f.name,"bytes":f.stat().st_size,"sha256":sha(f)}for f in sorted(payload.glob("*.py"))]
(ROOT/"protocol").mkdir(exist_ok=True)
path=ROOT/"protocol/run_v1.json";assert not path.exists();path.write_bytes((json.dumps(p,indent=2)+chr(10)).encode())
out=payload/"run_protocol.json";out.write_bytes(path.read_bytes())
bundle=ROOT/"workload_input_v1.tar.gz";assert not bundle.exists()
with tarfile.open(bundle,"w:gz")as tar:
    for f in sorted(payload.iterdir()):tar.add(f,arcname=f.name,recursive=False)
meta={"created_UTC":datetime.now(timezone.utc).isoformat(),"bytes":bundle.stat().st_size,"sha256":sha(bundle),
      "members":len(list(payload.iterdir())),"protocol_sha256":sha(path),"planned_maximum_model_image_forwards":3208}
(ROOT/"evidence/input_bundle.json").write_bytes((json.dumps(meta,indent=2)+chr(10)).encode())
print(json.dumps(meta))
