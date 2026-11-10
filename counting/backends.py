"""YOLO26 one-to-one Nx6 detector adapters; imports happen only when selected."""
import sys
from pathlib import Path
import numpy as np


class OnnxDetector:
    def __init__(self, model, threads=1):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model), sess_options=opts, providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0]
        self.size = int(self.input.shape[-1])
        if self.input.shape != [1, 3, self.size, self.size]:
            raise ValueError("Expected fixed YOLO26 batch1 square RGB NCHW input")

    def infer(self, tensor):
        return self.session.run(None, {self.input.name: tensor})[0]

    def close(self):
        self.session = None


class O8Detector:
    def __init__(self, root, program, plan, size, initialize=True):
        import fcntl
        root = Path(root).resolve()
        lock_path = root.parent / "yolo26_stage_d/reports/accelerator_job.lock"
        self.lock = lock_path.open("a")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for path in (root, root / "runtime_fast", root / "runtime"):
            sys.path.insert(0, str(path))
        if initialize:
            from device_initialize import initialize as init
            self.initialization = init(root)
        from native_graph import NativeGraph
        self.size = size
        self.graph = NativeGraph(size, program=str(program), plan=str(plan), options=4,
                                 firmware_manifest=str(root / "hardware/accepted/firmware_manifest.json"))

    def infer(self, tensor):
        return self.graph.run(tensor).copy()

    def infer_bgr(self, canvas):
        canvas = np.asarray(canvas)
        if canvas.dtype != np.uint8 or canvas.shape != (self.size, self.size, 3) or not canvas.flags.c_contiguous:
            raise ValueError("Native BGR input requires contiguous uint8 letterboxed HWC bytes")
        if not getattr(self.graph, "has_bgr", False):
            raise ValueError("Registered native engine has no BGR entry")
        return self.graph.run_image(canvas).copy()

    def close(self):
        import fcntl
        try:
            self.graph.close()
        finally:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()


def decode(raw, transform, confidence, cow_class_ids):
    raw = np.asarray(raw)
    if raw.ndim != 3 or raw.shape[0] != 1 or raw.shape[2] != 6 or not np.isfinite(raw).all():
        raise ValueError("Expected finite YOLO26 one-to-one [1,N,6] xyxy/conf/class output")
    rows = raw[0]
    rows = rows[(rows[:, 4] >= confidence) & np.isin(rows[:, 5], cow_class_ids)].copy()
    rows[:, :4] = transform.boxes(rows[:, :4], inverse=True)
    return rows[(rows[:, 2] > rows[:, 0]) & (rows[:, 3] > rows[:, 1])]
