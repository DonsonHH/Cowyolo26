from pathlib import Path,PurePosixPath
from collections import defaultdict
import ast,copy,csv,hashlib,importlib.util,json,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('prior_independent_reference',PROJECT/'secondstage_iou_20261028/tools/verify_local.py')
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
iou,counter,read,norm=reference.iou,reference.counter,reference.read,reference.normalized
def scope_check():
    tree=ast.parse((ROOT/'input/secondstage_tracker.py').read_text(encoding='utf-8'))
    cls=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='SecondStageIoUTracker')
    method=copy.deepcopy(next(c for c in cls.body if isinstance(c,ast.FunctionDef) and c.name=='_second_association'))
    hits=[n for n in ast.walk(method) if isinstance(n,ast.Compare) and ast.unparse(n)=='strack_pool[i].state == TrackState.Tracked'];assert len(hits)==1
    class Change(ast.NodeTransformer):
        def visit_Compare(self,node):
            return ast.parse('strack_pool[i].state in (TrackState.Tracked, TrackState.Lost)',mode='eval').body if node is hits[0] else self.generic_visit(node)
    expected=Change().visit(method)
    tree=ast.parse((ROOT/'tools/lost_tracker.py').read_text(encoding='utf-8'));cls=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='LostLowScoreTracker')
    methods=[m for m in cls.body if isinstance(m,ast.FunctionDef)]
    assert len(methods)==1 and ast.dump(expected,include_attributes=False)==ast.dump(methods[0],include_attributes=False)
def main():
    target=ROOT/'results/local_verification.json';assert not target.exists()
    record=load(ROOT/'results/replay_delivery_record.json');archive=ROOT/'results/replay_delivery.tar.gz';dest=ROOT/'delivery';assert not dest.exists()
    assert sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==record['manifest_sha256']
        rows=json.loads(raw);expected={r['path']:r for r in rows};members=tf.getmembers()
        assert len(rows)==len(expected)==record['manifest_files']==77 and len(members)==record['archive_members']==78
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    p=load(ROOT/'protocol/lost_v1.json');summary=load(dest/'results/summary.json');assert summary['protocol_sha256']==sha(ROOT/'protocol/lost_v1.json')
    assert summary['candidate_module_sha256']==p['candidate_module_sha256']==sha(ROOT/'tools/lost_tracker.py');scope_check()
    assert load(dest/'results/candidate_green_tests.json')['gate_passed'] and load(dest/'results/candidate_green_tests.json')['tests']==12
    records=[];totals={'cost_entries':0,'nonempty_decisions':0,'all_low_matches':0,'all_lost_recoveries':0,'lost_recoveries_in_scope':0,'ROI_track_rows_including_history':0};maxerr=0.;matched_lost_rows=[]
    for c in summary['conditions']:
        folder=dest/'results'/c['name'];source=next(s for s in p['sources'] if s['seed']==c['seed'])
        rawfolder=PROJECT/'counting_recovery_20261028/delivery/results/replay_v2'/source['name']
        if not rawfolder.exists():rawfolder=PROJECT/'counting_recovery_20261028/delivery/results/full640_confirmation'/source['name']
        raw=defaultdict(list)
        for r in read(rawfolder/'pretracker_boxes.csv'):raw[int(r['frame'])].append(r)
        tracks=norm(read(folder/'source_tracks.csv'));history=norm(read(folder/'source_warmup_tracks.csv'));positions=defaultdict(dict)
        for r in history+tracks:
            assert .34<(r['x1']+r['x2'])/5120<.75 and r['axis_position']==(r['y1']+r['y2'])/2880
            positions[r['source_frame']][r['track_id']]=r['axis_position']
        totals['ROI_track_rows_including_history']+=len(tracks)+len(history)
        post=read(folder/'all_posttracker_boxes.csv');ids=defaultdict(set)
        for r in post:
            if r['track_id']!='':ids[int(r['source_frame'])].add(int(r['track_id']))
        expanded={f:dict(row) for f,row in positions.items()};known=set();pending={};obs=load(folder/'observations.json')
        assert [r['source_frame'] for r in obs]==list(range(0,10874,5))
        for r in obs:
            f=r['source_frame'];active=set(r['confirmed_IDs']);tentative={int(k):v for k,v in r['tentative_positions'].items()}
            assert active==ids.get(f,set()) and {int(k):v for k,v in r['confirmed_positions'].items()}==positions.get(f,{})
            accepted=[]
            for tid in sorted(active-known):
                if tid in pending:
                    y=pending[tid];expanded.setdefault(f-5,{})[tid]=y
                    accepted.append({'track_id':tid,'observation_time_s':(f-5)/25,'confirmation_time_s':f/25,'axis_position':y,'observation_source_frame':f-5,'confirmation_source_frame':f})
            assert r['accepted_history']==accepted;known.update(active);pending=tentative
        ordinary=counter(positions);handoff=counter(expanded)
        assert ordinary==load(folder/'confirmed_only_events.json') and handoff==load(folder/'handoff_events.json')
        assert len(handoff)==c['predicted_down']+c['predicted_up'] and c['predicted_up']==0
        if c['variant']=='active_only_iou':
            old=PROJECT/f'secondstage_iou_20261028/delivery/results/secondstage_iou_seed{c["seed"]}'
            assert tracks==norm(read(old/'source_tracks.csv')) and history==norm(read(old/'source_warmup_tracks.csv'))
            assert ordinary==load(old/'confirmed_only_events.json') and handoff==load(old/'handoff_events.json')
            assert post==read(old/'all_posttracker_boxes.csv')
        matches=0;recoveries=[];decisions=load(folder/'secondstage_decisions.json');assert len(decisions)==c['nonempty_secondstage_decisions']
        for d in decisions:
            f=d['source_frame'];low=[r for r in raw[f] if .1<float(r['confidence'])<.25]
            assert len(low)==len(d['low_detections']) and not set(d['eligible_IDs'])&set(d['excluded_IDs'])
            assert all(state in ([1,2] if c['variant']=='allow_lost_iou' else [1]) for state in d['eligible_states'])
            for j,b in enumerate(d['low_detections']):
                assert b['stage_local_index']==j and b['confidence']==float(low[j]['confidence'])
                assert np.allclose(b['xyxy'],[float(low[j][k]) for k in ['x1','y1','x2','y2']],atol=.0005,rtol=0)
            for i,a in enumerate(d['eligible_xyxy']):
                for j,b in enumerate(d['low_detections']):
                    cost=1-iou(a,b['xyxy']);err=abs(cost-d['costs'][i][j]);maxerr=max(maxerr,err);assert err<1e-6;totals['cost_entries']+=1
            pairs=d['applied_pairs'];assert len(pairs)==len({a['row_index'] for a in pairs})==len({a['low_stage_index'] for a in pairs})
            for a in pairs:
                i,j=a['row_index'],a['low_stage_index'];assert a['track_ID']==d['eligible_IDs'][i] and a['state_before']==d['eligible_states'][i]
                assert a['last_observed_source_frame']==d['eligible_last_observed_frames'][i]
                assert a['observation_gap_source_frames']==f-a['last_observed_source_frame']
                assert a['cost']==d['costs'][i][j]<=.5 and a['confidence']==d['low_detections'][j]['confidence']
                if a['state_before']==2:
                    assert c['variant']=='allow_lost_iou' and 0<a['observation_gap_source_frames']<=155
                    recovery={**a,'source_frame':f};recoveries.append(recovery)
                    rect=d['low_detections'][j]['xyxy'];cx=(rect[0]+rect[2])/5120
                    matched_lost_rows.append({'condition':c['name'],'seed':c['seed'],**recovery,'actual_detection_ROI':.34<cx<.75,
                        'current_ID_in_ROI_output':a['track_ID'] in positions.get(f,{})})
            matches+=len(pairs)
        csvrecover=read(folder/'lost_low_recoveries.csv')
        assert len(csvrecover)==len(recoveries)==c['lost_recoveries_all_history']
        assert matches==c['low_matches_all_history']
        for row,actual in zip(csvrecover,recoveries):
            for k,v in actual.items():assert float(row[k])==v
        assert c['lost_recoveries_in_scope']==sum(a['source_frame']>=8912 for a in recoveries)
        totals['nonempty_decisions']+=len(decisions);totals['all_low_matches']+=matches;totals['all_lost_recoveries']+=len(recoveries);totals['lost_recoveries_in_scope']+=c['lost_recoveries_in_scope']
        records.append({'condition':c['name'],'independent_event_paths':2,'handoff_events':len(handoff),'low_matches':matches,'lost_recoveries':len(recoveries)})
    comparisons=[]
    for seed in [26,27,28]:
        a=load(dest/f'results/active_only_iou_seed{seed}/handoff_events.json');b=load(dest/f'results/allow_lost_iou_seed{seed}/handoff_events.json')
        normalize=lambda events:[{k:v for k,v in e.items() if k!='track_id'} for e in events]
        comparisons.append({'seed':seed,'baseline_events':len(a),'candidate_events':len(b),'times_and_directions_exact':normalize(a)==normalize(b),'full_event_records_exact':a==b})
    with (ROOT/'results/lost_recoveries_audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(matched_lost_rows[0]));writer.writeheader();writer.writerows(matched_lost_rows)
    result={'status':'ALL77_FILES_TWELVE_COUNTER_PATHS_LOST_AGES_AND_IOU_COSTS_VERIFIED',
      'protocol_sha256':sha(ROOT/'protocol/lost_v1.json'),'summary_sha256':sha(dest/'results/summary.json'),'candidate_module_sha256':p['candidate_module_sha256'],
      'files':77,'conditions':records,'counter_paths':12,'baseline_full_regressions':3,'trace_updates':13050,**totals,
      'maximum_cost_difference':maxerr,'comparisons':comparisons,'single_eligibility_expression_AST_change':True,
      'current_scope_actual_low_detection_in_ROI':sum(a['source_frame']>=8912 and a['actual_detection_ROI'] for a in matched_lost_rows),
      'current_scope_recovery_ID_actually_output_in_ROI':sum(a['source_frame']>=8912 and a['current_ID_in_ROI_output'] for a in matched_lost_rows),
      'maximum_recovery_gap_frames':max(a['observation_gap_source_frames'] for a in matched_lost_rows),
      'removal_check_occurs_after_association_155frame_gap_possible':True,
      'independent_source_accuracy':None,'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
