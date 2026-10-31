"""Record local assets and build evidence without contacting board/server."""
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORKSPACE = Path(r"C:\Users\Donson\Documents\ChatGPT\奶牛")
EXPORT = ROOT.parent


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def local_asset(name, path, expected=None, metadata_source=None):
    path = Path(path)
    found = path.is_file()
    actual = digest(path) if found else None
    return {"name": name, "path": str(path), "local_exists": found,
            "sha256": actual, "expected_sha256": expected,
            "expected_hash_matches": actual == expected if found and expected else None,
            "verification_status": "LOCAL_BYTES_HASHED" if found else "UNVERIFIED_PATH_UNAVAILABLE",
            "metadata_source": metadata_source, "uploaded_payload": False}


def main():
    result = {"base_commit": "8b377a0cc6ea666afab94804c8571f541c224529",
              "python_executable": sys.executable, "python": sys.version,
              "platform": platform.platform(),
              "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "lap")},
              "scorer_v2_dependencies": "Python standard library only",
              "compiler": shutil.which("g++"),
              "board_environment": "NOT_QUERIED_R1_NO_BOARD_ACCESS",
              "remote_asset_paths": "Historical metadata only; server/board bytes not accessed in R1",
              "assets": []}
    targets = [
        ("PC640 development candidate", "cows2021_adaptation_20261027/delivery/results/training/seed26/weights/last.pt",
         "51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74"),
        ("old192 checkpoint", "pynq_rot192_compile_20261029/delivery/results/qualification/frozen_S192_rot90_seed26.pt",
         "7b01cead4841f17d561f2a6bd768f9b229f1b3bd142818d8302135d3c69ffd45"),
        ("new192 checkpoint", "pynq_mosaic192_compile_20261030/delivery/results/qualification/frozen_mosaic050_seed26.pt",
         "628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb"),
    ]
    for name, path, expected in targets:
        result["assets"].append(local_asset(name, WORKSPACE / path, expected))
    for size in (256, 320):
        protocol = WORKSPACE / f"pynq_o8_sizes_20261030/s{size}/protocol/compile_v1.json"
        value = json.loads(protocol.read_text(encoding="utf-8"))
        result["assets"].append({"name": f"{size} historical checkpoint", "path": value["source_checkpoint"],
                                 "expected_sha256": value["source_checkpoint_sha256"], "sha256": None,
                                 "verification_status": "REMOTE_BYTES_NOT_CHECKED",
                                 "metadata_source": str(protocol), "metadata_sha256": digest(protocol),
                                 "uploaded_payload": False})
    manifest_path = ROOT / "pynq/yolo26_optimization_8/hardware/accepted/firmware_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for kind in ("bit", "hwh", "xsa"):
        asset = manifest[kind]
        result["assets"].append(local_asset("O8 firmware " + kind, asset["path"], asset["sha256"],
                                            manifest_path.relative_to(ROOT).as_posix()))
    for prefix in ("pynq_rot192_compile_20261029", "pynq_mosaic192_compile_20261030"):
        path = WORKSPACE / prefix / "delivery/results/qualification/compiled/program/graph.bin"
        result["assets"].append(local_asset(prefix + " graph", path))
    (HERE / "results/environment_assets.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    attempts = [{"attempt": 0, "directory": str(EXPORT / "r1_native_build"),
                 "exit": 1, "failure": "initial build before source restoration: missing resident_methods.inc",
                 "active_library_replaced": False}]
    for number, directory in ((1, "r1_native_build_restored"), (2, "r1_native_build_pathfixed")):
        folder = EXPORT / directory
        record = json.loads((folder / "recompile.json").read_text())
        log = folder / "build.log"
        attempts.append({"attempt": number, "directory": str(folder), **record,
                         "compiler_log_bytes": log.stat().st_size,
                         "path_bin_prepended": number == 2})
    build = {"status": "NOT_COMPILED_LOCAL_TOOLCHAIN_BLOCKED", "attempts": attempts,
             "compiler_version": "MinGW-W64 GCC 13.2.0 x86_64-posix-seh-rev0",
             "two_post_restoration_attempts_exit_1_without_diagnostics": True,
             "compatible_compiler_not_established": True,
             "native_runtime_correctness_proven": False,
             "source_hash_recovery_proven_separately": True,
             "followup": "Rebuild in a compatible existing PC/ARM environment in a later authorized task; no new hardware toolchain installed in R1."}
    (HERE / "results/native_build.json").write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"assets": len(result["assets"]), "dependencies": result["dependencies"],
                      "build_status": build["status"]}))


if __name__ == "__main__":
    main()
