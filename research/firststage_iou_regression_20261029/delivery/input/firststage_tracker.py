from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.trackers.utils import matching

class FirstStagePureIoUTracker(BYTETracker):
    def _first_association(self,pool,detections,activated,refind):
        costs=matching.iou_distance(pool,detections)
        matches,u_track,u_detection=matching.linear_assignment(costs,thresh=self.args.match_thresh)
        self._apply_matches(matches,pool,detections,activated,refind)
        return u_track,u_detection
