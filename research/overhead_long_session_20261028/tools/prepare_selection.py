from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
catalog=ROOT/'evidence/camera1_2023Aug17_listing.json';data=json.loads(catalog.read_text(encoding='utf-8'))
assert len(data['videos'])==7
chosen=sorted(data['videos'],key=lambda r:r['filename'])[0];assert chosen['filename']=='2023-08-17T12-54-41.mp4'
out=ROOT/'protocol';out.mkdir(exist_ok=False)
value={'name':'One metadata-selected ordinary overhead long video, reference preparation before predictions',
       'dataset':'MultiCamCows2024','camera':1,'day':'2023Aug17','selected':chosen,
       'directory_catalog_sha256':hashlib.sha256(catalog.read_bytes()).hexdigest(),
       'selection_rule':'Earliest filename timestamp in official camera1 2023Aug17 directory; no alternative chosen by outcome.',
       'maximum_source_bytes':600*1024*1024,'range_chunk_bytes':4*1024*1024,
       'current_12_count_milestone_preserved':True,'new_model_prediction_allowed_this_phase':False,
       'native_overview_interval_seconds':5,'native_focused_review_hz':5,
       'source_date_choice_does_not_prove_independent_physical_IDs':True,'whole_goal_complete':False}
(out/'selection_v1.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value))
