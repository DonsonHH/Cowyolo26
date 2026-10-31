from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((ROOT/"evidence/collection.txt").read_text().strip().splitlines()[-1])
archive=ROOT/"BECA_transfer_delivery_v1.tar.gz"
assert archive.stat().st_size==report["bytes"]and sha(archive)==report["sha256"]
dest=ROOT/"delivery";dest.mkdir(exist_ok=False)
with tarfile.open(archive)as tar:
    members=tar.getmembers()
    assert len(members)==report["members"]and len({r.name for r in members})==len(members)
    for member in members:
        rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and".."not in rel.parts
        path=(dest/member.name).resolve();assert path.is_relative_to(dest.resolve())and not path.exists()
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
manifest=json.loads((dest/"result_manifest.json").read_text())
assert len(manifest)==report["manifest_files"]
assert {r["file"]for r in manifest}=={r.name for r in members}-{"result_manifest.json"}
for row in manifest:
    path=dest/row["file"];assert path.stat().st_size==row["bytes"]and sha(path)==row["sha256"]
assert sum(r["file"].startswith("input/images/")and r["file"].endswith(".jpg")for r in manifest)==90
for name in["protocol/run_v1.json","protocol/execution_v1.json","results/pixel_admission.json"]:
    assert sha(ROOT/name)==sha(dest/name)
out=ROOT/"results/delivery_extraction.json";assert not out.exists()
out.write_text(json.dumps({"status":"FULL496_MEMBER_ORIGINAL_ARCHIVE_SHA_AND495_MANIFEST_FILES_VERIFIED",
                           "created_UTC":datetime.now(timezone.utc).isoformat(),"archive":report,"manifest_files":len(manifest),
                           "original_JPEGs":90,"new_model_forwards":0,"whole_goal_complete":False},ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":"FULL_ORIGINALS_EXTRACTED_AND_HASH_VERIFIED","archive_bytes":archive.stat().st_size,"manifest_files":len(manifest)}))
