from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=PROJECT/'orientation_video_20261027/protocol/video_rotation_v1.json'
freeze=PROJECT/'orientation_video_20261027/input/checkpoint_freeze.json'
weights=[{'seed':r['seed'],'checkpoint':r['checkpoint'],'sha256':r['checkpoint_sha256']} for r in json.loads(freeze.read_text())['conditions']]
assert [r['seed'] for r in weights]==[26,27,28]
arms=[{'name':'baseline_full320_5hz','crop_x':[0,2560],'imgsz':320,'stride':5,'confidence':.2,'stable_samples':3},
      {'name':'full640_5hz','crop_x':[0,2560],'imgsz':640,'stride':5,'confidence':.2,'stable_samples':3},
      {'name':'channel320_5hz','crop_x':[716,2074],'imgsz':320,'stride':5,'confidence':.2,'stable_samples':3},
      {'name':'channel640_5hz','crop_x':[716,2074],'imgsz':640,'stride':5,'confidence':.2,'stable_samples':3},
      {'name':'channel320_25hz','crop_x':[716,2074],'imgsz':320,'stride':1,'confidence':.2,'stable_samples':11},
      {'name':'channel320_lowconf_5hz','crop_x':[716,2074],'imgsz':320,'stride':5,'confidence':.1,'stable_samples':3}]
protocol={'name':'User steered sourceundercount recovery fixedpairedreplays v1',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'source_sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1',
    'source_video':REMOTE+'/data/multicam_samples/camera1/2023-08-14T12-54-48.mp4',
    'source_scope_inclusive':[8912,10873],'source_fps':25,'history_start':0,
    'feedback':{'human_reports':'Morethan8, approximatelyteens','exactcount_or_event_truth_available':False,
                'do_not_optimize_to_target_count':True,'board_supplied_later':True},
    'weights':weights,'pilot_seed':26,'all_seed_verification':'Afterpilot inspectallarms; extend highestnativeROIrawcoverage5Hz arm, tiepreferlowerimgsz toseeds27/28. Selectionnotbasedontargetcount. Keepallresults.',
    'arms':arms,'detection_rotation':'clockwise90 after optionalhorizontalcrop, exactpixelpermutation',
    'restore':'BeforeByteTrack restorebox coords pluscropxoffset, nativeorig_img/shape. ROIandcounter nativecoords.',
    'roi_x':[.34,.75],'gate_y':[.4,.6],'maximum_gap_s':2,
    'stable_duration_rule':'5Hz3samples=0.4sbetweenfirstlast;25Hz11samples=0.4s. Dense3samples isseparatetemporaldiagnosticonly.',
    'tracker':'samebuiltinbytetrack.yaml','library_ultralytics':'8.4.63',
    'required_gates':['exactbaselineevent/trackregression','crop/rotationcornerinversecontrols','nativecoordsbeforetracker',
                      'allarms andallseedfinalsreported','rawandtrackedcoverage','independentcounterreplay','strictmediaandbrowserreview'],
    'prior_protocol_sha256':sha(old),'checkpoint_freeze_sha256':sha(freeze),
    'training_updates':0,'independent_source_accuracy':None,'PYNQ_execution':False,'whole_goal_complete':False}
path=ROOT/'protocol/recovery_v1.json';path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists()
path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
inputs=ROOT/'input';inputs.mkdir(exist_ok=True)
(inputs/'prior_protocol.json').write_bytes(old.read_bytes());(inputs/'checkpoint_freeze.json').write_bytes(freeze.read_bytes())
for seed in [26,27,28]:
    src=PROJECT/f'orientation_video_20261027/delivery/results/inference/clockwise90_seed{seed}'
    dst=inputs/f'baseline_seed{seed}';dst.mkdir()
    for name in ['source_events.json','source_tracks.csv','source_warmup_tracks.csv']:(dst/name).write_bytes((src/name).read_bytes())
print(json.dumps({'protocol_sha256':sha(path),'conditions':len(arms),'pilot_seed':26}))
