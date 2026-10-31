from pathlib import Path
from datetime import datetime, timezone
import concurrent.futures, hashlib, json, urllib.request

ROOT = Path(__file__).resolve().parents[1]
sources = [
    ("university_README", "https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/readme.txt"),
    ("author_paper_HTML", "https://arxiv.org/html/2105.01938"),
    ("identity_root", "https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/"),
    ("identity_test_root", "https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Test/"),
    ("identity_train_split", "https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Train/RGBDCows2020/Identification/single_train_valid_test_splits.json")]
dest = ROOT / "evidence/primary_texts"
dest.mkdir(parents=True, exist_ok=False)


def capture(item):
    name, url = item
    record = {"name": name, "URL": url, "created_UTC": datetime.now(timezone.utc).isoformat()}
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "cow-research-identity-intake"}), timeout=25) as response:
            data = response.read(3000000)
            assert len(data) < 3000000
            record.update({"HTTP_status": response.status, "content_type": response.headers.get("Content-Type"), "bytes": len(data),
                           "sha256": hashlib.sha256(data).hexdigest(), "resolved_URL": response.url})
        output = dest / (name + ".response")
        output.write_bytes(data)
        record.update({"status": "PRIMARY_TEXT_CAPTURED", "file": str(output.resolve())})
    except Exception as error:
        record.update({"status": "TEXT_NOT_CAPTURED", "error": repr(error)[:350]})
    return record


with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    rows = list(pool.map(capture, sources))
result = {"records": rows, "new_image_pixels_read": 0, "new_model_forwards": 0, "proxy_or_node_settings_changed": False}
output = ROOT / "results/primary_source_capture.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(rows))
