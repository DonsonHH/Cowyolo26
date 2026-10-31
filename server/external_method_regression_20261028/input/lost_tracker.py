"""Fixed pure-IoU secondstage, additionally eligible Lost pool objects only.

No observed box is fabricated. Lost matches require an actual low-score detection
and the same IoU gate; high-score firststage and buffer expiry are unchanged.
"""
from __future__ import annotations
import ast,inspect,textwrap
from ultralytics.trackers.byte_tracker import STrack,TrackState
from ultralytics.trackers.utils import matching
from secondstage_tracker import SecondStageIoUTracker

class LostLowScoreTracker(SecondStageIoUTracker):
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
        r_tracked_stracks = [strack_pool[i] for i in u_track if strack_pool[i].state in (TrackState.Tracked, TrackState.Lost)]
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
