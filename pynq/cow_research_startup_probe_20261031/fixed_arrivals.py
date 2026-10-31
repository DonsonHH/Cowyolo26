from pathlib import Path
import copy
import hashlib
import json
import threading
import time
import os


class FixedArrivals:
    def __init__(self, jobs, requests, epoch_ns):
        self.jobs = jobs
        self.requests = requests
        self.epoch_ns = epoch_ns
        self.stop = threading.Event()
        self.records = []
        self.error = None
        self.thread = threading.Thread(target=self._run, name="fixed_identity_arrivals", daemon=False)

    def _run(self):
        try:
            for source in self.jobs:
                release = self.epoch_ns + source["requested_enqueue_offset_ns"]
                while not self.stop.is_set():
                    remaining = (release - time.monotonic_ns()) / 1e9
                    if remaining <= 0:
                        break
                    self.stop.wait(min(remaining, .05))
                if self.stop.is_set():
                    return
                job = copy.deepcopy(source)
                job["release_monotonic_ns"] = release
                job["requested_enqueue_monotonic_ns"] = release
                job["enqueued_monotonic_ns"] = time.monotonic_ns()
                self.requests.put_nowait(job)
                finished = time.monotonic_ns()
                self.records.append({"fixed_job_index": job["fixed_job_index"], "source_frame0": job["source_frame0"],
                                     "requested_monotonic_ns": release, "enqueue_started_monotonic_ns": job["enqueued_monotonic_ns"],
                                     "enqueue_returned_monotonic_ns": finished, "publisher_native_TID": threading.get_native_id(),
                                     "publisher_CPU_affinity": sorted(os.sched_getaffinity(0)),
                                     "publisher_lateness_ms": (job["enqueued_monotonic_ns"] - release) / 1e6})
        except BaseException as error:
            self.error = repr(error)

    def start(self):
        self.thread.start()

    def finish(self, timeout=3):
        self.thread.join(timeout)
        assert not self.thread.is_alive(), "Keep original publisher handle; do not restart experiment"
        assert self.error is None, self.error
        assert len(self.records) == len(self.jobs) and len(self.jobs) in (0,10)
        return {"status": "ALL_FIXED_JOBS_PUBLISHED", "thread_alive": False, "records": self.records}

    def close(self):
        self.stop.set()
        self.thread.join(3)
        return {"thread_alive": self.thread.is_alive(), "records": self.records, "error": self.error}
