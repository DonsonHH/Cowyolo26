from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,gzip
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
meta=load(ROOT/'evidence/result_transfer.json');archive=ROOT/'results_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for m in members:
        assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
        file=(out/m.name).resolve();assert file.is_relative_to(out.resolve());assert not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(m).read())
manifest=load(out/'results/assembly_manifest.json');assert len(manifest)==meta['files_bound_by_manifest']
for r in manifest:
    file=out/r['relative_file'];assert file.stat().st_size==r['bytes'] and sha(file)==r['sha256']
for relative in ['tools/geometry.py','tools/run_pairs.py','tools/input_controls.py','tools/plot_results.py','protocol/pairs_v1.json','protocol/input_controls_v1.json']:
    assert sha(ROOT/relative)==sha(out/relative)
assert sha(ROOT/'evidence/main_cases_before_input_controls.json')==sha(out/'results/pairs/case_selection.json')
s=load(out/'results/pairs/summary.json')
for r in s['condition_summaries']:
    print(r['split'],r['condition'],'GT/TP/FN/unmatchedPred',r['references'],r['matched'],r['unmatched_references'],r['unmatched_predictions'])
    for name in ['complete','clipped']:
        st=r['strata'][name];print(' ',name,'matched',st['matched'],'gate',st['engineering_crop_gate_passes'],
            'coverage_median',round(st['metrics_on_matched']['reference_coverage']['median'],4),
            'outside_median',round(st['metrics_on_matched']['reference_exterior_fraction']['median'],4),
            'ideal_outside_median',round(st['ideal_AABB_exterior_fraction_all_references']['median'],4))
controls=load(out/'results/input_controls/summary.json')
for r in controls['metrics']:print('CONTROL',r['condition'],r['orientation'],r['imgsz'],r['rect'],r['repeat'],'TP',r['matched'],'refs',r['references'])
report={'status':'ALL_PACKED_FILES_HASHED_AND_SAFE_EXTRACTION_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'members':len(members),'hashed_files':len(manifest)}
p=ROOT/'results/transfer_verification.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
