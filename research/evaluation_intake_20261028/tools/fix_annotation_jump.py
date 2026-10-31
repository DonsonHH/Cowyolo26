from pathlib import Path
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
page = ROOT.parent / 'phase3_diagnosis_20261026/annotation_workbench/index.html'
original = page.read_bytes()
backup = ROOT / 'results/annotation_index_before_fix.html'
assert not backup.exists()
edits = [
    (b"$('seek').value=f;$('jump').value=f}", b"$('seek').value=f;if(document.activeElement!==$('jump'))$('jump').value=f}"),
    (b"$('jumpButton').onclick=", b"$('jump').onfocus=()=>video.pause();$('jumpButton').onclick="),
    ('</div></header>'.encode(), '<p id="qaNotice" class="help badge" hidden>QA测试视图：事件仅用于功能检查，不是科研参考。</p></div></header>'.encode('utf-8')),
    (b"const focus={first:8912,last:10873};", b"$('qaNotice').hidden=!new URLSearchParams(location.search).has('qa');\nconst focus={first:8912,last:10873};")
]
updated = original
for before, after in edits:
    assert updated.count(before) == 1, before
    updated = updated.replace(before, after)
assert b"cow-source-annotation-v1-" in updated
assert b"const fresh=()=>({schema_version:'cattle-passages-v1'" in updated
backup.parent.mkdir(parents=True, exist_ok=True)
backup.write_bytes(original)
page.write_bytes(updated)
record = {'old_sha256': hashlib.sha256(original).hexdigest(), 'new_sha256': hashlib.sha256(updated).hexdigest(),
          'changes': ['Preserve activejump edit duringclock refresh', 'Pause onjump focus', 'VisibleQAonlynotice'],
          'source_config_schema_storage_keys_and_event_definition_changed': False,
          'old_page_preserved': True, 'main_draft_not_opened_or_modified': True,
          'browser_retest': 'pending'}
(ROOT / 'results/annotation_jump_fix.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record))
