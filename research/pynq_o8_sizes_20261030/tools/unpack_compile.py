from pathlib import Path
import tarfile,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=load(ROOT/'evidence/compile_transfer.json');a=ROOT/'compile_delivery.tar.gz';assert sha(a)==m['sha256'] and a.stat().st_size==m['bytes']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(a) as t:
 assert len(t.getmembers())==m['members']
 for member in t.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=(out/member.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(member).read())
manifest=load(out/'compile_result_manifest.json');assert len(manifest)==m['manifest_files']
for row in manifest:assert sha(out/row['file'])==row['sha256'] and (out/row['file']).stat().st_size==row['bytes']
for case in ['s256','s320']:
 for name in ['protocol/compile_v1.json','tools/compile_fixed_size.py','tools/normalize_graph.py']:assert sha(ROOT/case/name)==sha(out/case/name)
result={'status':'ALL104_MEMBERS103_HASHES_EXACT_INCLUDING_FAILED320_QUALIFICATION','archive_sha256':sha(a),'members':m['members'],'files':len(manifest)}
(ROOT/'results/compile_transfer_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
