"""Optional observation-centred association; extrapolated boxes never count."""
import numpy as np
from maintenance.counting_r1.tracker import STrack


class ObservationTrack(STrack):
    """Predict centre from two actual detections, retaining last observed size.

    Short-term matching uses this prediction. Current matched outputs use the
    actual detection box. Unmatched tracks remain Lost and produce no counter
    observation. No image, future sample or permanent identity is inferred.
    """
    def __init__(self, xywh, score, cls):
        super().__init__(xywh, score, cls)
        self.observed_at = None
        self.query_time = None
        self.observations = []

    def _record(self, detection):
        box = detection._tlwh.copy()
        box[2:] += box[:2]
        stamp = detection.observed_at
        if self.observations and stamp <= self.observations[-1][0]:
            raise ValueError('Actual observations must have increasing source timestamps')
        self.observations = (self.observations + [(stamp, box)])[-2:]
        self.query_time = stamp

    def activate(self, kalman_filter, frame_id):
        super().activate(kalman_filter, frame_id)
        self._record(self)

    def update(self, new_track, frame_id):
        super().update(new_track, frame_id)
        self._record(new_track)

    def re_activate(self, new_track, frame_id, new_id=False):
        super().re_activate(new_track, frame_id, new_id)
        self._record(new_track)

    @property
    def xyxy(self):
        if not self.observations:
            return super().xyxy
        stamp, box = self.observations[-1]
        if self.query_time is None or self.query_time <= stamp or len(self.observations) < 2:
            return box.copy()
        previous_time, previous_box = self.observations[-2]
        # Prediction is bounded in time and affects association only. Keep size
        # independent of entrance truncation and avoid aspect-ratio expansion.
        elapsed = min(self.query_time - stamp, 1.5)
        if stamp - previous_time > 1.5:
            return box.copy()
        velocity = ((box[:2] + box[2:]) - (previous_box[:2] + previous_box[2:])) / (2 * (stamp - previous_time))
        return box + np.tile(velocity * elapsed, 2)
