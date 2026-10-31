"""Bind existing browser QA to current local media and the served page.

No prediction, training, annotation changes, or model accuracy assessment.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = ROOT.parent / 'phase3_diagnosis_20261026/annotation_workbench'
INPUTS = WORKBENCH.parent / 'inputs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = ROOT / 'results/media_verification.json'
    media = json.loads(path.read_text(encoding='utf-8'))
    assert media['browser_verified'] is False
    qa_path = ROOT / 'results/browser_verification.json'
    qa = json.loads(qa_path.read_text(encoding='utf-8'))
    assert qa['status'] == 'ALL_THREE_NATIVE_COORDINATE_VIDEO_PAIRS_PLAYBACK_SEEK_EDIT_PAUSE_AND_BOUNDARIES_VERIFIED'
    assert len(qa['tests']) == 6
    assert qa['source_annotation_draft_modified'] is False
    assert qa['source_count_accuracy_verified'] is False
    assert qa['final_view']['clock'] == '源帧9420 · 376.80秒'
    assert qa['final_view']['seed'] == '26'
    for video in qa['final_view']['videos']:
        assert video['paused'] is True and video['error'] is None
        assert video['duration'] == 78.48 and video['ready'] >= 2
        assert (video['width'], video['height']) == (1280, 720)
        assert abs(video['time'] - (9420 - 8912) / 25) < .01
    assert len(media['media']) == len(media['reused_original_media']) == 6
    for row in media['media']:
        new = ROOT / 'previews' / row['file']
        copied = INPUTS / row['file']
        assert sha(new) == sha(copied) == row['sha256']
        assert new.stat().st_size == row['bytes']
        assert row['strict_full_decode'] == 'PASS'
        assert (row['frames'], row['fps'], row['duration_s']) == (1962, 25, 78.48)
    for row in media['reused_original_media']:
        old = ROOT.parent / 'cows2021_adaptation_20261027/previews' / row['file']
        assert sha(old) == sha(INPUTS / row['file']) == row['sha256']
        assert row['exact_new_track_regression_passed'] is True
        assert row['old_media_fully_decoded_and_browser_verified'] is True
    page = WORKBENCH / 'video_rotation_preview.html'
    data = WORKBENCH / 'video_rotation_preview_data.json'
    page_sha = sha(page)
    assert page_sha == sha(ROOT / 'templates/video_rotation_preview.html')
    fix_path = ROOT / 'results/browser_jump_race_fix.json'
    fix = json.loads(fix_path.read_text(encoding='utf-8'))
    assert fix['new_page_sha256'] == page_sha
    assert fix['experiment_predictions_or_counter_rules_changed'] is False
    base = 'http://127.0.0.1:8779/annotation_workbench/'
    live = []
    for file in [page, data]:
        with urllib.request.urlopen(base + file.name, timeout=15) as response:
            payload = response.read()
            assert response.status == 200
            assert hashlib.sha256(payload).hexdigest() == sha(file)
            live.append({'url': base + file.name, 'HTTP': response.status,
                         'sha256_matches_local_file': True})
    screenshot = ROOT / 'results/browser_source9420.png'
    with Image.open(screenshot) as im:
        im.load()
        assert im.width >= 700 and im.height >= 1200
    snapshot = ROOT / 'results/media_verification_before_browser_binding.json'
    assert not snapshot.exists()
    snapshot.write_bytes(path.read_bytes())
    media.update(status='ALL_MEDIA_HASHES_STRICT_DECODE_AND_THREE_PAIRS_BROWSER_VERIFIED',
                 reviewed_UTC=datetime.now(timezone.utc).isoformat(),
                 page_sha256=page_sha, data_sha256=sha(data), browser_verified=True,
                 browser_evidence_sha256=sha(qa_path),
                 browser_screenshot_sha256=sha(screenshot),
                 live_local_HTTP=live,
                 source_accuracy_verified=False, whole_goal_complete=False)
    path.write_text(json.dumps(media, ensure_ascii=False, indent=2), encoding='utf-8')
    fix.update(status='EDIT_PAUSE_VALUE_RETENTION_AND_BOTH_BOUNDARIES_BROWSER_RETEST_PASSED',
               browser_evidence_sha256=sha(qa_path),
               initial_failure_evidence_sha256=sha(ROOT / 'results/browser_before_jump_fix.json'),
               old_page_preserved_sha256=sha(ROOT / 'results/video_rotation_preview_before_edit_pause.html'))
    assert fix['old_page_sha256'] == fix['old_page_preserved_sha256']
    fix_path.write_text(json.dumps(fix, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': media['status'], 'page_sha256': page_sha,
                      'verified_media_files': 12, 'local_HTTP': live,
                      'source_accuracy_verified': False, 'whole_goal_complete': False}))


if __name__ == '__main__':
    main()
