from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    protocol=ROOT/'protocol/clock_v1.json';assert not protocol.exists();protocol.parent.mkdir(exist_ok=True)
    old=PROJECT/'counting_recovery_20261028';p=load(old/'protocol/recovery_v2.json')
    sources=[]
    for name in ['full640_5hz_seed26','full640_5hz_seed27','full640_5hz_seed28','channel320_5hz_seed26','channel320_25hz_seed26']:
        folder=old/'delivery/results/replay_v2'/name
        if not folder.exists():folder=old/'delivery/results/full640_confirmation'/name
        summary=load(folder/'summary.json');files=[]
        for f in ['pretracker_boxes.csv','source_tracks.csv','source_warmup_tracks.csv','source_events.json','summary.json']:
            path=folder/f;files.append({'name':f,'sha256':sha(path),'bytes':path.stat().st_size})
        rel=folder.relative_to(old/'delivery').as_posix()
        sources.append({'name':name,'remote_folder':f'{REMOTE}/counting_recovery_20261028/{rel}',
                        'seed':summary['seed'],'stride':summary['arm']['stride'],'stable_samples':summary['arm']['stable_samples'],
                        'files':files,'prior_predicted_down':summary['predicted_down'],'prior_predicted_up':summary['predicted_up']})
    controls=[{'name':'crop25Hz_buffer150','source':'channel320_25hz_seed26','track_buffer':150,
               'nominal_lost_budget_s':6.,'comparison':'same25Hz_buffer30; buffer only'},
              {'name':'crop5Hz_buffer6','source':'channel320_5hz_seed26','track_buffer':6,
               'nominal_lost_budget_s':1.2,'comparison':'same5Hz_buffer30; buffer only'}]
    record={'name':'Cached ByteTrack exact regression and two fixed wallclock buffer controls',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'source_frame_range_inclusive':[8912,10873],
      'history_start':0,'source_fps':25,'previous_protocol_sha256':sha(old/'protocol/recovery_v2.json'),
      'source_video_sha256':p['source_sha256'],'weights':p['weights'],'sources':sources,
      'installed_source':[{'file':f,'sha256':sha(old/'evidence'/f)} for f in ['installed_track.py','installed_byte_tracker.py','installed_bytetrack.yaml']],
      'baseline_buffer':30,'required_exact_replays_before_controls':5,'controls':controls,
      'counter':{'lower':.4,'upper':.6,'maximum_gap_s':2.,'stable_samples_5Hz':3,'stable_samples_25Hz':11},
      'roi_x':[.34,.75],'native_image_height':1440,'native_image_width':2560,
      'hypotheses_ranked':['same30updatebuffer changes nominal lost retention at5Hz/25Hz',
                           'multiobject box changes affect association despite outputframecoverage',
                           'stable A/B observations insufficient; requires eventtruth to attribute realmisses'],
      'prediction_if_clock_dominates':'buffer rescaling changes IDcontinuity and may change events; direction not assumed',
      'negative_outcome_rule':'if both fixedcontrols reproduce baseline events, do not claim buffer resolves undercount',
      'no_parameter_search_or_target_count':True,'independent_source_reference_available':False,
      'causal_scope':'Only samecachedinput samefrequency buffer change; does not normalize everyKalman component acrossfrequencies',
      'new_detector_forwards':0,'training_updates':0,'board_execution':False,'whole_goal_complete':False}
    protocol.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'protocol_sha256':sha(protocol),'exact_replays':5,'controls':2}))
if __name__=='__main__':main()
