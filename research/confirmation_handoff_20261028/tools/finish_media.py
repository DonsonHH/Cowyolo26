from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    path=ROOT/'results/media_verification.json';r=load(path);b=load(ROOT/'results/browser_verification.json')
    assert not r['browser_verified'] and len(r['media'])==6
    assert b['all_tests_passed'] and len(b['tests'])==13 and all(t['pass'] for t in b['tests'])
    assert b['main_annotation_draft_opened_or_modified'] is False
    for item in r['media']+r['reused_baselines']:
        assert sha(ROOT.parent/'phase3_diagnosis_20261026/inputs'/item['file'])==item['sha256']
    shutil.copyfile(path,ROOT/'results/media_verification_before_browser.json')
    r.update(status='SIX_MEDIA_STRICT_DECODE_AND_THREE_PAIRED_CONDITIONS_BROWSER_VERIFIED',browser_verified=True,browser_tests=13,
       browser_evidence_sha256=sha(ROOT/'results/browser_verification.json'),
       browser_screenshot_sha256=sha(ROOT/'results/browser_source9345_viewport.png'))
    path.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({'status':r['status'],'browser_tests':13}))
if __name__=='__main__':main()
