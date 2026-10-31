from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
path=ROOT/'results/media_verification.json';r=load(path);b=load(ROOT/'results/browser_verification.json')
assert not r['browser_verified'] and b['all_tests_passed'] and len(b['tests'])==12 and all(t['pass'] for t in b['tests'])
assert not b['main_annotation_draft_opened_or_modified']
for row in r['media']+r['reused_baselines']:
    assert sha(PROJECT/'phase3_diagnosis_20261026/inputs'/row['file'])==row['sha256']
assert len(r['media'])==6 and all(x['strict_full_decode']=='PASS' and x['frames']==1962 and x['duration_s']==78.48 for x in r['media'])
backup=ROOT/'results/media_verification_before_browser.json';assert not backup.exists();shutil.copyfile(path,backup)
r.update(status='SIX_MEDIA_STRICT_DECODE_AND_THREE_PAIR_BROWSER_CHECKS_COMPLETE',browser_verified=True,browser_tests=12,
  browser_evidence_sha256=sha(ROOT/'results/browser_verification.json'),browser_screenshot_sha256=sha(ROOT/'results/browser_source9365.png'))
path.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({'status':r['status'],'browser_tests':12}))
