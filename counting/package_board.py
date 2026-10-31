"""Package complete counting Python sources; reuse board model/runtime assets."""
import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path


def package(output):
    root = Path(__file__).resolve().parents[1]
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    files = [*root.joinpath("counting").glob("*.py"), *root.joinpath("counting").glob("*.html")]
    files += [root / "maintenance/counting_r1" / name for name in ("__init__.py", "tracker.py", "event_metrics_v2.py")]
    frozen = root / "pynq/cow_research_numpy_tracker_20261029"
    files += [*frozen.joinpath("cow_tracker").glob("*.py"), frozen / "frame_pipeline.py"]
    manifest = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with tarfile.open(output, "w:gz") as archive:
        for path in files:
            archive.add(path, arcname=path.relative_to(root).as_posix())
        data = json.dumps({"source_sha256": manifest, "models_or_data_included": False}, indent=2).encode()
        entry = tarfile.TarInfo("COUNTING_SOURCE_MANIFEST.json")
        entry.size = len(data)
        archive.addfile(entry, io.BytesIO(data))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = package(args.output)
    print(json.dumps({"source_files": len(result), "models_or_data_included": False}))
