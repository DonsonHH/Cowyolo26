# Ultralytics-derived code: AGPL-3.0, https://ultralytics.com/license
"""R1 maintenance entry: frozen NumPy tracker with second-stage fusion removed."""
from __future__ import annotations

import ast
import inspect
import sys
import textwrap
from pathlib import Path

FROZEN_ROOT = Path(__file__).resolve().parents[2] / "pynq/cow_research_numpy_tracker_20261029"
if "cow_tracker" in sys.modules:
    loaded = Path(sys.modules["cow_tracker"].__file__).resolve().parent
    if loaded != (FROZEN_ROOT / "cow_tracker").resolve():
        raise ImportError("A different cow_tracker is loaded; use a fresh interpreter")
sys.path.insert(0, str(FROZEN_ROOT))
from cow_tracker.byte_tracker import BYTETracker, STrack, TrackState
from cow_tracker import matching


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
    """Verify the complete second-stage AST and inherited surrounding rules."""
    before = ast.parse(textwrap.dedent(inspect.getsource(BYTETracker._second_association)))
    after = ast.parse(textwrap.dedent(inspect.getsource(SecondStageIoUTracker._second_association)))
    hits = [node for node in ast.walk(before)
            if isinstance(node, ast.If) and ast.unparse(node.test) == "self.args.fuse_score"]
    if len(hits) != 1:
        raise AssertionError("Frozen second-stage method changed")
    class RemoveFusion(ast.NodeTransformer):
        def visit_If(self, node):
            return None if node is hits[0] else self.generic_visit(node)
    expected = RemoveFusion().visit(before)
    if ast.dump(expected, include_attributes=False) != ast.dump(after, include_attributes=False):
        raise AssertionError("Change exceeds removal of second-stage score fusion")
    for name in ("update", "_first_association", "_unconfirmed_association", "_split_detections",
                 "_init_new_tracks", "_remove_stale_lost", "get_dists"):
        if getattr(SecondStageIoUTracker, name) is not getattr(BYTETracker, name):
            raise AssertionError(f"Unexpected surrounding rule change: {name}")
    return {"removed_score_fusion_blocks": 1, "all_other_secondstage_AST_identical": True,
            "firststage_unconfirmed_thresholds_lost_rules_inherited": True}
