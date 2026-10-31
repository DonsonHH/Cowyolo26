import time as _startup_time
BOOTSTRAP_MODULE_BEGIN_NS = _startup_time.monotonic_ns()
from pathlib import Path
import os, sys, json, gzip, hashlib, time, fcntl, multiprocessing, traceback, gc, resource
os.environ["XILINX_XRT"] = "/usr"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np

ROOT = Path(__file__).resolve().parent
O8 = Path("/home/xilinx/jupyter_notebooks/yolo26_optimization_8")
PORT = Path("/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029")
VIDEO = Path("/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030")
MODEL = Path("/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030")
sys.path[:0] = [str(O8), str(O8 / "runtime_fast"), str(PORT), str(PORT / "source/lap-0.5.13")]
from background_fixed_worker import worker
from fixed_arrivals import FixedArrivals
from process_cpu import snapshot
from jpeg_producer import JPEGProducer

from startup_support import run_parent
BOOTSTRAP_MODULE_END_NS = _startup_time.monotonic_ns()

if __name__ == '__main__':
    run_parent(Path(__file__).name)
