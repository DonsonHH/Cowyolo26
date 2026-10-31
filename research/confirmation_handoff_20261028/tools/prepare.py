from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    old=PROJECT/'tracker_clock_20261028/protocol/clock_v1.json';p=json.loads(old.read_text(encoding='utf-8'))
    red=ROOT/'results/behavior_baseline_red.txt';green=ROOT/'results/behavior_candidate_green.txt'
    assert 'failures=2' in red.read_text(encoding='utf-8') and green.read_text(encoding='utf-8').rstrip().endswith('OK')
    path=ROOT/'protocol/handoff_v1.json';assert not path.exists();path.parent.mkdir(exist_ok=True)
    result={'name':'One immediate tentative observation admitted only at confirmation',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'previous_clock_protocol_sha256':sha(old),
       'source_scope_inclusive':[8912,10873],'history_start':0,'source_fps':25,
       'sources':[r for r in p['sources'] if r['name'].startswith('full640_5hz')],
       'weights':p['weights'],'installed_source':p['installed_source'],
       'frozen_base_counter_sha256':sha(ROOT/'input/zone_counter.py'),
       'handoff_module_sha256':sha(ROOT/'tools/confirmation_counter.py'),
       'behavior_baseline_red_sha256':sha(red),'behavior_candidate_green_sha256':sha(green),
       'ROI_x':[.34,.75],'counter':{'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.},
       'policy':{'history_limit_per_tentative_ID':1,'must_be_previous_update':True,
                 'must_match_current_confirmed_ID':True,'only_first_confirmation_admits_history':True,
                 'unconfirmed_may_publish_event':False,'event_publication_at_current_confirmed_tick':True,
                 'drop_on_confirmation_failure':True,'symmetric_A_B_rules':True},
       'required_gates':['allthree original tracks/history/events exact','handoff-disabled wrapper events exact',
                         'onlycounter observationhandoff changes','independent replay ofcausal traces',
                         'perID/time/directionevent differences reported','no targetcount selection'],
       'case_expectation':'seed26 ID95 and seed27 ID57 may gain stable A via source9305; seed28 B discontinuity separately remains unresolved',
       'development_data_reused':True,'independent_reference_available':False,
       'new_detector_forwards':0,'training_updates':0,'board_execution':False,'whole_goal_complete':False}
    assert len(result['sources'])==3;path.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'protocol_sha256':sha(path),'seeds':[26,27,28]}))
if __name__=='__main__':main()
