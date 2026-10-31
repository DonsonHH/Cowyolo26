"""Pinned secondstage method with only score fusion removed. Shared install unchanged."""
from __future__ import annotations
import ast,inspect,textwrap
from ultralytics.trackers.byte_tracker import BYTETracker,STrack,TrackState
from ultralytics.trackers.utils import matching

class SecondStageIoUTracker(BYTETracker):
    def _second_association(
        self,
        strack_pool: list[STrack],
        u_track: list[int],
        detections_second: list[STrack],
        activated: list[STrack],
        refind: list[STrack],
        lost: list[STrack],
    ) -> None:
        """Second-stage association between remaining tracked tracks and low-score detections."""
        r_tracked_stracks = [strack_pool[i] for i in u_track if strack_pool[i].state == TrackState.Tracked]
        if r_tracked_stracks and detections_second:
            dists = matching.iou_distance(r_tracked_stracks, detections_second)
            matches, u_track, _ = matching.linear_assignment(dists, thresh=0.5)
            self._apply_matches(matches, r_tracked_stracks, detections_second, activated, refind)
        else:
            u_track = list(range(len(r_tracked_stracks)))

        for it in u_track:
            track = r_tracked_stracks[it]
            if track.state != TrackState.Lost:
                track.mark_lost()
                lost.append(track)

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
