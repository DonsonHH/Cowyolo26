from pathlib import Path
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((ROOT/'evidence/result_transfer.json').read_text());archive=ROOT/'results_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(out/member.name).resolve();assert file.is_relative_to(out.resolve());assert not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
manifest=json.loads((out/'results/assembly_manifest.json').read_text());assert len(manifest)==meta['files_bound_by_manifest']
for r in manifest:
    file=out/r['relative_file'];assert file.stat().st_size==r['bytes'] and sha(file)==r['sha256']
for r in json.loads((ROOT/'results/input_audit.json').read_text())['new_images']:assert sha(ROOT/r['relative_file'])==sha(out/r['relative_file'])==r['sha256']
v2=ROOT/'tools/run_study_v2.py';assert not v2.exists();v2.write_bytes((ROOT/'tools/run_study.py').read_bytes())
assert sha(v2)==sha(out/'tools/run_study_v2.py')
(ROOT/'tools/run_study.py').write_bytes((out/'tools/run_study.py').read_bytes())
for f in ['protocol/study_v1.json','protocol/study_v2.json','results/input_audit.json']:assert sha(ROOT/f)==sha(out/f)
report={'status':'TRANSFER128_MEMBERS127_HASHES_AND_RETAINED_FAILED_SOURCE_VERIFIED','archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'members':len(members),'hashed_files':len(manifest)}
path=ROOT/'results/transfer_verification.json';assert not path.exists();path.write_text(json.dumps(report,indent=2)+'\n')
s=json.loads((out/'results/study_v2/summary.json').read_text())
for row in s['conditions']:
    m=row['curated_metrics'];print(row['condition'],row['gallery_condition'],'C/W/U',m['known_correct_accepted_C'],m['known_wrong_accepted_W'],m['known_rejected_U'],'FAR',m['unknown_false_accepts'],'Top1',m['known_closed_top1_correct'],'realpass',row['real_event_passed_fixed_threshold'])
    for r in row['real_accepted_candidates']:print(' real:',r['query_id'],r['predicted_id'],round(r['similarity'],6),round(r['threshold'],6))
print(json.dumps(report))
