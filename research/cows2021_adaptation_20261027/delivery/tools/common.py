from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda:file.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    partial=path.with_name(path.name+'.partial')
    partial.write_text(json.dumps(value,indent=2),encoding='utf-8');partial.replace(path)


def state_digest(model):
    h=hashlib.sha256()
    for name,tensor in sorted(model.state_dict().items()):
        h.update(name.encode());h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def verify_similarity_review(label_summary):
    """A similarity screen can only be closed by an explicit evidence record."""
    audit=Path(label_summary['source_image_audit_path'])
    assert audit.resolve().is_relative_to(ROOT/'results')
    assert sha(audit/'summary.json')==label_summary['source_image_audit_sha256']
    overlap_path=audit/'overlap.json';overlap=json.loads(overlap_path.read_text())
    pairs=overlap['cross_development_role_dHash_le2_review_cues']
    if not pairs:
        assert label_summary['dHash_candidate_review_still_pending'] is False
        return {'pairs':0,'review_record':None,'review_record_sha256':None}
    path=ROOT/'results/dHash_review_v1.json';review=json.loads(path.read_text())
    assert review['status']=='ALL_CROSS_ROLE_DHASH_CUES_REVIEWED_NO_CONFIRMED_SOURCE_DUPLICATES'
    assert review['source_overlap_sha256']==sha(overlap_path)
    expected={(r['train'],r['validation'],r['distance']) for r in pairs}
    actual={(r['train'],r['validation'],r['distance']) for r in review['reviewed_pairs']}
    assert expected==actual and len(review['reviewed_pairs'])==len(pairs)
    assert all(r['decision']=='distinct_capture_images_retained' for r in review['reviewed_pairs'])
    assert review['cross_farm_or_unseen_cow_independence_claimed'] is False
    assert review['source_overlap_quarantine_required'] is False
    return {'pairs':len(pairs),'review_record':str(path),'review_record_sha256':sha(path)}
