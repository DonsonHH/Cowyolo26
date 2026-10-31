from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((ROOT/'evidence/result_transfer.json').read_text());archive=ROOT/'results_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for m in members:
        assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
        target=(out/m.name).resolve();assert target.is_relative_to(out.resolve());assert not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
manifest=json.loads((out/'results/assembly_manifest.json').read_text());assert len(manifest)==meta['files_bound_by_manifest']
for r in manifest:
    p=out/r['relative_file'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
for p in (ROOT/'data').rglob('*.jpg'):assert sha(p)==sha(out/p.relative_to(ROOT))
for relative in ['tools/run_study.py','tools/crop_rules.py','protocol/study_v1.json','results/input_audit.json']:assert sha(ROOT/relative)==sha(out/relative)
summary=json.loads((out/'results/study/summary.json').read_text())
print('Choices',summary['all_rule_selected_choices'])
for r in summary['evaluation_conditions']:
    if r['is_validation_selected_rule'] and r['threshold_method']=='validation_calibrated' or r['rule']=='P0_original' and r['threshold_method']=='original_fixed':
        m=r['curated_metrics'];print(r['condition'],r['rule'],r['threshold_method'],'C/W/U/F',*[m[k] for k in ['known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']],'realpass',r['real_event_passed_threshold'])
        for e in r['real_event_accepted_candidates']:print(' REAL',e['query_id'],e['predicted_id'],e['similarity'],e['threshold'])
record={'status':'RESULT_TRANSFER_ALL_MEMBERS_MANIFEST_AND_SOURCE_IDENTICAL_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'members':len(members),'hashed_files':len(manifest)}
p=ROOT/'results/transfer_verification.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
