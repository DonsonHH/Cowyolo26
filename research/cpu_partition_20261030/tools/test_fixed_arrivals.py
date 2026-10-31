"""Behavior tests: release gate, immutable source jobs, close, queue failure."""
import copy
import json
import queue
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixed_arrivals
if not hasattr(fixed_arrivals.os, "sched_getaffinity"):
    fixed_arrivals.os.sched_getaffinity = lambda pid: {0}

jobs = [{"fixed_job_index": index, "source_frame0": 100 + index, "requested_enqueue_offset_ns": index * 3000000} for index in range(10)]
original = copy.deepcopy(jobs)
requests = queue.Queue(maxsize=16)
epoch = time.monotonic_ns() + 150000000
publisher = fixed_arrivals.FixedArrivals(jobs, requests, epoch)
publisher.start()
time.sleep(.005)
if time.monotonic_ns() < epoch:
    assert requests.empty()
result = publisher.finish(timeout=3)
received = [requests.get_nowait() for _ in range(10)]
assert requests.empty() and jobs == original
assert [row["fixed_job_index"] for row in received] == list(range(10))
assert all(row["enqueued_monotonic_ns"] >= row["requested_enqueue_monotonic_ns"] == epoch + row["requested_enqueue_offset_ns"] for row in received)
future = fixed_arrivals.FixedArrivals(jobs, queue.Queue(maxsize=16), time.monotonic_ns() + 10000000000)
future.start()
closed = future.close()
assert not closed["thread_alive"] and not closed["records"]
full = queue.Queue(maxsize=1)
full.put("already_full")
failed = fixed_arrivals.FixedArrivals(jobs, full, time.monotonic_ns())
failed.start()
try:
    failed.finish(timeout=3)
except AssertionError:
    assert failed.error is not None and not failed.thread.is_alive()
else:
    raise AssertionError("Queue overflow must surface as publisher failure")
print(json.dumps({"status": "FIXED_ARRIVAL_RELEASE_SOURCE_IMMUTABILITY_CLEAN_CLOSE_AND_OVERFLOW_BEHAVIORS_PASS", "checks": 4,
                  "new_model_forwards": 0, "platform": sys.platform}))
