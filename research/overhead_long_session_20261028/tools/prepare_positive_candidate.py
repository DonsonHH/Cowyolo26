from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'evidence/camera1_2023Aug17_listing.json').read_text(encoding='utf-8'))
selection=json.loads((ROOT/'protocol/selection_v1.json').read_text(encoding='utf-8'))
visual=ROOT/'evidence/next_probe_visual_review.json';review=json.loads(visual.read_text(encoding='utf-8'))
assert review['positive_observation']['source_filename']=='2023-08-17T13-25-38.mp4'
item=next(r for r in catalog['videos'] if r['filename']==review['positive_observation']['source_filename'])
selection.update(name='First successfully native-probed cow-present long-video candidate retained for full admission',selected=item,
    selection_rule='Content-enriched selection after fixed 25/50/75 percent byte probes of all six remaining files; first chronologically positive observed main-channel cow.',
    positive_native_visual_review_sha256=hashlib.sha256(visual.read_bytes()).hexdigest(),
    original_background_candidate_retained=True,selection_is_random_unseen_test=False,
    camera_private_header_before_MPEG_PS=True,whole_source_validation_pending=True)
target=ROOT/'protocol/positive_candidate_v1.json';assert not target.exists();target.write_text(json.dumps(selection,indent=2),encoding='utf-8')
print(json.dumps({'selected':item,'next':'Full byte download and separate native decode/annotation admission; no model until reference preparation.'}))
