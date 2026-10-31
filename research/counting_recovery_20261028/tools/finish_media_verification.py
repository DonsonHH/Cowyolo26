from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    path=ROOT/'results/media_verification.json';record=load(path);browser=load(ROOT/'results/browser_verification.json')
    assert record['browser_verified'] is False and len(record['media'])==8
    assert browser['all_tests_passed'] and len(browser['tests'])==14
    assert all(r['pass'] is True for r in browser['tests'])
    assert browser['main_annotation_draft_opened_or_modified'] is False
    assert browser['tests'][-1]['state']['clock'].startswith('源帧9420')
    for row in record['media']:
        assert sha(ROOT/'previews'/row['file'])==row['sha256']
        assert sha(ROOT.parent/'phase3_diagnosis_20261026/inputs'/row['file'])==row['sha256']
        assert row['strict_full_decode']=='PASS' and row['frames']==1962
    backup=ROOT/'results/media_verification_prebrowser.json';assert not backup.exists();shutil.copyfile(path,backup)
    record.update(status='EIGHT_NEW_MEDIA_DECODED_AND_FOUR_CONDITIONS_BROWSER_VERIFIED',browser_verified=True,
                  browser_tests=14,browser_evidence_sha256=sha(ROOT/'results/browser_verification.json'),
                  browser_screenshot_sha256=sha(ROOT/'results/browser_preview.png'))
    path.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'status':record['status'],'browser_tests':14}))
if __name__=='__main__':main()
