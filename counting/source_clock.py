"""PTS sampling and elapsed-source-time prediction, with the legacy unit step."""
import math
import numpy as np
from maintenance.counting_r1.tracker import SecondStageIoUTracker, TrackState


class SourceSampler:
    def __init__(self, hz):
        if hz is not None and (not math.isfinite(hz) or hz <= 0):
            raise ValueError("Positive finite sampling frequency required")
        self.period = 1. / hz if hz else None
        self.anchor = None
        self.next_index = 0
        self.unavailable_slots = 0

    def select(self, time_s):
        if self.period is None:
            return True
        if self.anchor is None:
            self.anchor = time_s
        target = self.anchor + self.next_index * self.period
        if time_s + 1e-9 < target:
            return False
        reached = math.floor((time_s - self.anchor) / self.period + 1e-8)
        self.unavailable_slots += max(0, reached - self.next_index)
        self.next_index = reached + 1
        return True


def predict_interval(kalman, mean, covariance, delta):
    """Fractional nominal-tick extension of the frozen constant-velocity model.

    For frozen per-axis unit noise (qp,qv), a continuous Gaussian extension has
    Dpp=qp+qv/6, Dpv=-qv/2, Dvv=qv. Integrating F(t) D F(t)' gives the blocks below.
    D is PSD for qp>=qv/12, satisfied by every frozen XYAH noise component.
    Q(1) is exactly the old diagonal Q; integer intervals compose the unit model.
    """
    if not math.isfinite(delta) or delta <= 0:
        raise ValueError("Positive finite prediction interval required")
    if abs(delta - 1.) <= 1e-8:
        return kalman.predict(mean, covariance)
    height = mean[3]
    qp = np.square([kalman._std_weight_position * height] * 2 + [1e-2, kalman._std_weight_position * height])
    qv = np.square([kalman._std_weight_velocity * height] * 2 + [1e-5, kalman._std_weight_velocity * height])
    motion = kalman._motion_mat.copy()
    motion[np.arange(4), np.arange(4) + 4] = delta
    noise = np.zeros((8, 8), dtype=float)
    noise[np.arange(4), np.arange(4)] = delta * qp + qv * (delta**3 / 3 - delta**2 / 2 + delta / 6)
    noise[np.arange(4) + 4, np.arange(4) + 4] = delta * qv
    cross = qv * (delta**2 - delta) / 2
    noise[np.arange(4), np.arange(4) + 4] = cross
    noise[np.arange(4) + 4, np.arange(4)] = cross
    return motion @ mean, motion @ covariance @ motion.T + noise


class SourceTimeTracker(SecondStageIoUTracker):
    def __init__(self, args, nominal_hz, lost_seconds):
        self.nominal_hz, self.lost_seconds = nominal_hz, lost_seconds
        self.source_time = None
        self.delta = 1.
        super().__init__(args)

    def update_at(self, time_s, detections):
        if not math.isfinite(time_s) or self.source_time is not None and time_s <= self.source_time:
            raise ValueError("Tracker requires strictly increasing finite source time")
        self.delta = (time_s - self.source_time) * self.nominal_hz if self.source_time is not None else 1.
        self.source_time = time_s
        for name in ("tracked_stracks", "lost_stracks"):
            retained = []
            for track in getattr(self, name):
                if time_s - track.source_last_observed_s > self.lost_seconds + 1e-8:
                    track.mark_removed()
                    self.removed_stracks.append(track)
                else:
                    retained.append(track)
            setattr(self, name, retained)
        self.removed_stracks = self.removed_stracks[-1000:]
        result = super().update(detections)
        for track in self.tracked_stracks:
            if track.frame_id == self.frame_id:
                track.source_last_observed_s = time_s
        return result

    def multi_predict(self, tracks):
        if abs(self.delta - 1.) <= 1e-8:
            return super().multi_predict(tracks)
        for track in tracks:
            mean = track.mean.copy()
            if track.state != TrackState.Tracked:
                mean[7] = 0
            track.mean, track.covariance = predict_interval(self.kalman_filter, mean, track.covariance, self.delta)

    def _remove_stale_lost(self, removed):
        # Lifetimes are checked by source seconds before association, never ticks.
        return None
