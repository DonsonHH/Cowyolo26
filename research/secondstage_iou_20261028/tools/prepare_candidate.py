from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,shutil,textwrap
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
red=json.loads((ROOT/'results/baseline_red_tests.json').read_text(encoding='utf-8'))
assert red['gate_passed'] and red['expected_two_baseline_failures_observed'] and red['failures']==2
base=PROJECT/'counting_recovery_20261028/evidence/installed_byte_tracker.py';source=base.read_text(encoding='utf-8')
tree=ast.parse(source);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BYTETracker')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_second_association')
body='\n'.join(source.splitlines()[method.lineno-1:method.end_lineno])+'\n'
remove='            if self.args.fuse_score:\n                dists = matching.fuse_score(dists, detections_second)\n'
assert body.count(remove)==1;modified=body.replace(remove,'')
header='''"""Pinned secondstage method with only score fusion removed. Shared install unchanged."""
from __future__ import annotations
import ast,inspect,textwrap
from ultralytics.trackers.byte_tracker import BYTETracker,STrack,TrackState
from ultralytics.trackers.utils import matching

class SecondStageIoUTracker(BYTETracker):
'''
scope='''
def verify_method_scope():
    before=ast.parse(textwrap.dedent(inspect.getsource(BYTETracker._second_association)))
    after=ast.parse(textwrap.dedent(inspect.getsource(SecondStageIoUTracker._second_association)))
    hits=[]
    for n in ast.walk(before):
        if isinstance(n,ast.If) and ast.unparse(n.test)=='self.args.fuse_score':hits.append(n)
    assert len(hits)==1
    class RemoveFusion(ast.NodeTransformer):
        def visit_If(self,node):
            if node is hits[0]:return None
            return self.generic_visit(node)
    expected=RemoveFusion().visit(before)
    assert ast.dump(expected,include_attributes=False)==ast.dump(after,include_attributes=False)
    assert SecondStageIoUTracker._first_association is BYTETracker._first_association
    assert SecondStageIoUTracker.get_dists is BYTETracker.get_dists
    return {'removed_score_fusion_blocks':1,'all_other_secondstage_AST_identical':True,
            'firststage_methods_inherited_unchanged':True,'lost_eligibility_and_threshold_unchanged':True}
'''
path=ROOT/'tools/secondstage_tracker.py';assert not path.exists();path.write_text(header+modified+scope,encoding='utf-8')
inp=ROOT/'input';inp.mkdir(exist_ok=True)
sources={'zone_counter.py':PROJECT/'confirmation_handoff_20261028/input/zone_counter.py',
         'confirmation_counter.py':PROJECT/'confirmation_handoff_20261028/tools/confirmation_counter.py',
         'event_metrics.py':PROJECT/'counting_eval_20261026/tools/event_metrics.py'}
for name,p in sources.items():
    dest=inp/name;assert not dest.exists();shutil.copyfile(p,dest);assert sha(dest)==sha(p)
old=PROJECT/'confirmation_handoff_20261028/protocol/handoff_v1.json';p=json.loads(old.read_text(encoding='utf-8'))
protocol={'name':'Onefactor secondstage IoU cost with fixed firststage and confirmation counter',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'source_scope_inclusive':[8912,10873],'history_start':0,'source_fps':25,
 'previous_handoff_protocol_sha256':sha(old),'source_sha256':json.loads((PROJECT/'paired_event_intake_20261028/results/frozen_prediction_catalog_v2.json').read_text(encoding='utf-8'))['source_sha256'],
 'weights':p['weights'],'sources':p['sources'],'installed_source':p['installed_source'],
 'matching_source_sha256':sha(PROJECT/'paired_event_intake_20261028/evidence/installed_matching.py'),
 'base_BYTETracker_source_sha256':sha(base),'candidate_module_sha256':sha(path),
 'input_modules':{name:sha(inp/name) for name in sources},'counter':p['counter'],'ROI_x':[.34,.75],
 'baseline_and_candidate_order':['installed_baseline','secondstage_iou'],
 'only_change':'Remove secondstage scorefusion; cost=1-IoU, threshold stays0.5. Firststage fuse_score=True retained; lost eligibility unchanged.',
 'all3_seeds_both_tracker_variants_required':True,'main_counter':'sameconfirmationhandoff for both variants',
 'confirmed_only_counter_retained_for_diagnosis':True,
 'prior_handoff_paths':{str(seed):f'/share/home/renly/projects/idcoo_research_20261026/confirmation_handoff_20261028/results/replay_v2/seed{seed}' for seed in [26,27,28]},
 'red_behavior_record_sha256':sha(ROOT/'results/baseline_red_tests.json'),
 'required_gates':['actual tracker red/green sequence','single secondstage block AST change','allthree baselines exact prior tracks/history/bothcounters',
                   'nonempty secondstage decision costs and selections recorded','independent 12counter paths and costs','allseed and adverse results kept'],
 'no_target_count_or_threshold_search':True,'prediction_comparison_not_TP_FP_FN_vs_truth':True,
 'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy':None,'FPGA_execution_verified':False,'whole_goal_complete':False}
out=ROOT/'protocol/secondstage_v1.json';assert not out.exists();out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
print(json.dumps({'candidate_module_sha256':sha(path),'protocol_sha256':sha(out),'only_change':'secondstage scorefusion removal'}))
