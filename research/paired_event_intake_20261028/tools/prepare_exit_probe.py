from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
clock=PROJECT/'tracker_clock_20261028/protocol/clock_v1.json';p=json.loads(clock.read_text(encoding='utf-8'))
source=next(s for s in p['sources'] if s['name']=='full640_5hz_seed28')
out=ROOT/'protocol/exit_probe_v1.json';assert not out.exists()
value={'name':'Read-only first/second association probe for existing seed28 ID117 case',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'clock_protocol_sha256':sha(clock),
       'source':source,'weights':next(w for w in p['weights'] if w['seed']==28),
       'installed_source':p['installed_source'],
       'matching_source_sha256':sha(ROOT/'evidence/installed_matching.py'),
       'target_ID':117,'probe_frames':list(range(9340,9391,5)),
       'required_full_original_track_history_event_regression':True,
       'hypotheses_ranked':['raw output unavailable or below highconfidence in B region',
                            'eligible rawboxes fail first/secondstage association',
                            'tracked box center outside ROI'],
       'scope':'Explains saved algorithm outputs; predicted IoU candidates are not human identity correspondences',
       'counter_parameters_changed':False,'new_detector_forwards':0,'training_updates':0,
       'independent_source_accuracy':None,'board_execution':False,'whole_goal_complete':False}
out.write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({'exit_probe_protocol_sha256':sha(out),'frames':len(value['probe_frames'])}))
