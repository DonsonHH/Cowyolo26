from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
red=load(ROOT/'results/baseline_red_tests.json');assert red['gate_passed'] and red['failures']==2 and red['expected_two_failures_reproduced']
source=(ROOT/'input/secondstage_tracker.py').read_text(encoding='utf-8');tree=ast.parse(source)
cls=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='SecondStageIoUTracker')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_second_association')
body='\n'.join(source.splitlines()[method.lineno-1:method.end_lineno])+'\n'
old='strack_pool[i].state == TrackState.Tracked';new='strack_pool[i].state in (TrackState.Tracked, TrackState.Lost)'
assert body.count(old)==1
header='''"""Fixed pure-IoU secondstage, additionally eligible Lost pool objects only.

No observed box is fabricated. Lost matches require an actual low-score detection
and the same IoU gate; high-score firststage and buffer expiry are unchanged.
"""
from __future__ import annotations
import ast,inspect,textwrap
from ultralytics.trackers.byte_tracker import STrack,TrackState
from ultralytics.trackers.utils import matching
from secondstage_tracker import SecondStageIoUTracker

class LostLowScoreTracker(SecondStageIoUTracker):
'''
scope='''
def verify_method_scope():
    before=ast.parse(textwrap.dedent(inspect.getsource(SecondStageIoUTracker._second_association)))
    after=ast.parse(textwrap.dedent(inspect.getsource(LostLowScoreTracker._second_association)))
    hits=[n for n in ast.walk(before) if isinstance(n,ast.Compare) and ast.unparse(n)=='strack_pool[i].state == TrackState.Tracked']
    assert len(hits)==1
    class Eligibility(ast.NodeTransformer):
        def visit_Compare(self,node):
            if node is hits[0]:return ast.parse('strack_pool[i].state in (TrackState.Tracked, TrackState.Lost)',mode='eval').body
            return self.generic_visit(node)
    expected=Eligibility().visit(before)
    assert ast.dump(expected,include_attributes=False)==ast.dump(after,include_attributes=False)
    assert LostLowScoreTracker._first_association is SecondStageIoUTracker._first_association
    assert LostLowScoreTracker.get_dists is SecondStageIoUTracker.get_dists
    assert LostLowScoreTracker._init_new_tracks is SecondStageIoUTracker._init_new_tracks
    return {'eligibility_expression_changes':1,'all_other_secondstage_AST_identical':True,
            'firststage_and_new_track_methods_inherited_unchanged':True,'secondstage_IoU_and_threshold_unchanged':True}
'''
target=ROOT/'tools/lost_tracker.py';assert not target.exists();target.write_text(header+body.replace(old,new)+scope,encoding='utf-8')
for name in ['zone_counter.py','confirmation_counter.py','event_metrics.py']:
    dest=ROOT/'input'/name;assert not dest.exists();shutil.copyfile(PROJECT/'secondstage_iou_20261028/input'/name,dest)
p=load(PROJECT/'secondstage_iou_20261028/protocol/secondstage_v1.json')
prior=[]
for seed in [26,27,28]:
    folder=PROJECT/f'secondstage_iou_20261028/delivery/results/secondstage_iou_seed{seed}'
    prior.append({'seed':seed,'remote_folder':f'/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028/results/secondstage_iou_seed{seed}',
      'files':[{'name':n,'sha256':sha(folder/n),'bytes':(folder/n).stat().st_size} for n in ['source_tracks.csv','source_warmup_tracks.csv','all_posttracker_boxes.csv','confirmed_only_events.json','handoff_events.json','observations.json','summary.json']]})
q={'name':'Singlefactor Lost low-score secondstage eligibility paired control',
   'created_UTC':datetime.now(timezone.utc).isoformat(),'source_scope_inclusive':[8912,10873],'history_start':0,'source_fps':25,
   'source_sha256':p['source_sha256'],'weights':p['weights'],'sources':p['sources'],'installed_source':p['installed_source'],
   'matching_source_sha256':p['matching_source_sha256'],'prior_secondstage_protocol_sha256':sha(PROJECT/'secondstage_iou_20261028/protocol/secondstage_v1.json'),
   'baseline_module_sha256':sha(ROOT/'input/secondstage_tracker.py'),'candidate_module_sha256':sha(target),
   'input_modules':{p.name:sha(p) for p in (ROOT/'input').glob('*.py')},'counter':p['counter'],'ROI_x':p['ROI_x'],
   'prior_baselines':prior,'variants':['active_only_iou','allow_lost_iou'],
   'only_change':'Secondstage eligible pool Tracked -> (Tracked,Lost); same actual low detections, IoU>=0.5 gate, firststage, buffers and mainconfirmationcounter',
   'no_explicit_new_age_limit':'Existing track_buffer30 expiry unchanged; candidate does not tune retention or add extra motion gating.',
   'main_counter':'sameconfirmationhandoff','confirmed_only_diagnostic_counter_retained':True,
   'red_record_sha256':sha(ROOT/'results/baseline_red_tests.json'),
   'required_gates':['actual lowrecovery red/green','single eligibility ASTchange','allthree activeonly baselines exact',
                     'actual Lostmatches detected andage logged','12independent counterpaths andcosts','allseed/adverse results and physical ambiguity retained'],
   'hypotheses':['if Lost eligibility matters, low observations may reactivate sameID after gap',
                 'if detection gaps persist, complete events may remain absent',
                 'expanding eligible pool may steal ambiguous detection from other tracks'],
   'no_target_count_or_threshold_search':True,'new_detector_forwards':0,'training_updates':0,
   'independent_source_accuracy':None,'FPGA_execution_verified':False,'whole_goal_complete':False}
out=ROOT/'protocol/lost_v1.json';assert not out.exists();out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(q,indent=2),encoding='utf-8')
print(json.dumps({'protocol_sha256':sha(out),'candidate_module_sha256':sha(target),'baseline_main_predictions':[12,11,11]}))
