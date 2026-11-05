"""Stage three prespecified, source-only held-out sessions; no model execution."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera1/"
SOURCES = [
    ("2023Aug15", "2023-08-15T12-50-59.mp4", 260112424),
    ("2023Aug16", "2023-08-16T12-52-13.mp4", 260833320),
    ("2023Aug18", "2023-08-18T12-53-40.mp4", 260538408),
]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def stage(folder, source):
    day, name, size = source
    url = BASE + day + "/" + name
    target = folder / name
    row = {"day": day, "file": name, "url": url, "expected_bytes": size,
           "selection": "first chronological daytime camera1 file on prespecified dates; before predictions"}
    try:
        if not target.exists():
            partial = target.with_suffix(".mp4.partial")
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            with urlopen(Request(url, headers=headers), timeout=45) as response:
                if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                    raise ValueError("Resume range was not honored")
                row["publisher_last_modified"] = response.headers.get("Last-Modified")
                with partial.open("ab" if offset else "wb") as file:
                    for block in iter(lambda: response.read(1024 * 1024), b""):
                        file.write(block)
                        if file.tell() > size:
                            raise ValueError("Response exceeds prespecified length")
            if partial.stat().st_size != size:
                raise ValueError("Incomplete source response")
            partial.rename(target)
        if target.stat().st_size != size:
            raise ValueError("Existing source differs from expected size")
        row.update(status="STAGED_SOURCE_ONLY", bytes=size, sha256=digest(target))
    except Exception as error:
        row.update(status="FAILED", error=repr(error))
    print(json.dumps(row), flush=True)
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        rows = list(executor.map(lambda source: stage(args.output, source), SOURCES))
    value = {"status": "STAGED" if all(row["status"] == "STAGED_SOURCE_ONLY" for row in rows) else "INCOMPLETE",
             "new_model_forwards": 0, "ground_truth_supplied_by_this_script": False, "files": rows}
    temporary = args.output / "source_manifest.json.partial"
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(args.output / "source_manifest.json")
    raise SystemExit(0 if value["status"] == "STAGED" else 1)
