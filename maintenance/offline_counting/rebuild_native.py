"""Rebuild five frozen O8 sources with a job-local Windows compiler workaround."""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--sources", type=Path, default=root / "pynq/yolo26_optimization_8/native_sources")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    files = ("queue_runtime.cpp", "native_runtime.cpp", "graph_executor.cpp", "resident_methods.inc", "software_fusion.inc")
    sources = {}
    for name in files:
        shutil.copy2(args.sources / name, output / name)
        sources[name] = digest(output / name)
    command = [str(args.compiler)]
    tools = {}
    dll_directory = None
    if platform.system() == "Windows":
        compiler_root = args.compiler.resolve().parent.parent
        candidates = list((compiler_root / "libexec/gcc").glob("*/*/cc1plus.exe"))
        if len(candidates) != 1:
            raise ValueError("Select an unambiguous existing MinGW compiler tree")
        frontend = output / "compiler_frontend"
        frontend.mkdir()
        for source in (candidates[0], candidates[0].with_name("collect2.exe"),
                       compiler_root / "bin/as.exe", compiler_root / "bin/ld.exe",
                       compiler_root / "bin/libwinpthread-1.dll"):
            shutil.copy2(source, frontend / source.name)
            tools[source.name] = digest(frontend / source.name)
        command.append("-B" + str(frontend) + os.sep)
        dll_directory = os.add_dll_directory(str(frontend))
    command += ["-O3", "-std=c++17", "-shared", "-fopenmp", "-ffp-contract=off"]
    if platform.machine().lower().startswith("arm"):
        command += ["-fPIC", "-mcpu=cortex-a9", "-mfpu=neon", "-mfloat-abi=hard"]
    elif platform.system() == "Windows":
        command += ["-static-libgcc", "-static-libstdc++"]
    else:
        command += ["-fPIC"]
    command += ["queue_runtime.cpp"]
    if platform.system() == "Windows":
        command += ["-Wl,-Bstatic", "-lgomp", "-Wl,-Bdynamic"]
    library = output / ("native_queue_pc.dll" if platform.system() == "Windows" else "native_queue.so")
    command += ["-o", library.name]
    if platform.system() != "Windows":
        command += ["-ldl"]
    result = subprocess.run(command, cwd=output, capture_output=True)
    (output / "build.log").write_bytes(result.stdout + result.stderr)
    loaded = False
    if result.returncode == 0:
        handle = ctypes.CDLL(str(library))
        assert hasattr(handle, "o7_run") and hasattr(handle, "o8_create")
        loaded = True
    record = {"status": "PASS" if loaded else "FAIL", "command": command,
              "exit": result.returncode, "source_sha256": sources,
              "job_local_compiler_file_sha256": tools, "library_load_verified": loaded,
              "library_sha256": digest(library) if library.exists() else None,
              "active_library_replaced": False, "model_forwards": 0}
    (output / "rebuild.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    if dll_directory:
        dll_directory.close()
    raise SystemExit(0 if loaded else 1)


if __name__ == "__main__":
    main()
