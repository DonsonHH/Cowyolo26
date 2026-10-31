from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
p=load(ROOT/"protocol/run_v1.json");e=load(ROOT/"protocol/execution_v1.json")
admission=load(ROOT/"results/pixel_admission.json")
assert admission["status"]=="ALL90_FROZEN_BECA_MEMBERS_CRC_RGB_AND_NO_QA_OR_INTERNAL_DUPLICATE_PASS"
assert len(list((ROOT/"input/images").glob("*.jpg")))==90
for name,digest in e["files_sha256"].items():assert sha(ROOT/name)==digest
files=sorted([f for base in["input","protocol","tools","evidence"]for f in(ROOT/base).rglob("*")if f.is_file()and"__pycache__"not in f.parts]+[ROOT/"results/pixel_admission.json"])
manifest=ROOT/"input_bundle_manifest_v1.json";assert not manifest.exists()
manifest.write_text(json.dumps([{"file":f.relative_to(ROOT).as_posix(),"bytes":f.stat().st_size,"sha256":sha(f)}for f in files],ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
archive=ROOT/"BECA_transfer_input_v1.tar.gz";assert not archive.exists()
with tarfile.open(archive,"w:gz")as tar:
    for f in files+[manifest]:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
metadata={"status":"FIXED90_JPEGS_FROZEN_CODE_AND_COMPLETE_RANGE_EVIDENCE_BUNDLED",
          "created_UTC":datetime.now(timezone.utc).isoformat(),"file":str(archive.resolve()),
          "bytes":archive.stat().st_size,"sha256":sha(archive),"members":len(files)+1,"whole_goal_complete":False}
out=ROOT/"results/input_bundle_v1.json";assert not out.exists()
out.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
remote="/share/home/renly/projects/idcoo_research_20261026/beca_fixed_transfer_20261030"
script=f"""set -euo pipefail
cd {remote}
test ! -e evaluation_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
r=Path.cwd();archive=r/'BECA_transfer_input_v1.tar.gz'
assert archive.stat().st_size=={metadata['bytes']} and hashlib.sha256(archive.read_bytes()).hexdigest()=='{metadata['sha256']}'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)=={metadata['members']}
 for member in members:
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  path=(r/member.name).resolve();assert path.is_relative_to(r)and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
manifest=json.loads((r/'input_bundle_manifest_v1.json').read_text())
for row in manifest:
 path=r/row['file'];assert path.stat().st_size==row['bytes']and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
e=json.loads((r/'protocol/execution_v1.json').read_text())
assert hashlib.sha256((r/'protocol/run_v1.json').read_bytes()).hexdigest()==e['protocol_sha256']
for name,digest in e['files_sha256'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest
for model in e['models']:assert hashlib.sha256(Path(model['checkpoint']).read_bytes()).hexdigest()==model['checkpoint_sha256']
print(json.dumps({{'status':'ALL_INPUT_FILES_AND_TWO_EXISTING_CHECKPOINT_HASHES_VERIFIED_BEFORE_FORWARD','members':len(members),'model_forwards':0}}))
PY
bash -n tools/evaluation.slurm
bash -n tools/collect_final.sh
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/evaluation.slurm)
printf '%s\\n' "$job_id" > evaluation_job_id.txt
printf 'BECA_FIXED_TRANSFER_JOB_ID=%s\\n' "$job_id"
"""
path=ROOT/"tools/stage_submit.sh";assert not path.exists();path.write_text(script,encoding="utf-8")
print(json.dumps(metadata,ensure_ascii=False))
