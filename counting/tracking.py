"""Frozen short-term tracking connected to bounded source-time counting state."""
import math
from types import SimpleNamespace
import numpy as np
from .source_clock import SourceTimeTracker
from frame_pipeline import Boxes
from .counter import PassageCounter
from .channel import ChannelPolygon, admitted_detection_mask
from .protocol import gate_from_config

DEFAULT_TRACKER = dict(tracker_type="bytetrack", track_high_thresh=.25, track_low_thresh=.1,
                       new_track_thresh=.25, track_buffer=30, match_thresh=.8, fuse_score=True)


class TrackingSession:
    def __init__(self, config, width, height, sample_hz, session_id):
        self.width, self.height, self.sample_hz = width, height, sample_hz
        self.session_id, self.config = session_id, config
        self.track_only_in_channel = config.get("track_only_in_channel", False)
        if not isinstance(self.track_only_in_channel, bool):
            raise ValueError("track_only_in_channel must be boolean")
        self.channel_polygon = (ChannelPolygon(gate_from_config(config)["channel_polygon"])
                                if config.get("channel_polygon") is not None else None)
        self.epoch = 0
        tracker = {**DEFAULT_TRACKER, **config.get("tracker", {})}
        if tracker.get('prediction_axis') not in (None, config.get('axis', 'y')):
            raise ValueError('prediction_axis must match the counting axis')
        lost_seconds = float(config.get("lost_seconds", 6.))
        tracker["track_buffer"] = max(1, math.ceil(sample_hz * lost_seconds))
        self.tracker_config = tracker
        self.counter_config = {**config.get("counter", {}),
                               "ttl_s": max(lost_seconds, float(config.get("counter", {}).get("maximum_gap_s", 2.))) + 1 / sample_hz}
        self.counter_config["in_direction"] = config.get("in_direction", "A->B")
        self.last_time = None
        self.maximum_state_count = 0
        self._reset()

    def _reset(self):
        self.tracker = SourceTimeTracker(SimpleNamespace(**self.tracker_config), self.sample_hz,
                                         float(self.config.get("lost_seconds", 6.)))
        self.counter = PassageCounter(self.session_id, **self.counter_config)

    def update(self, frame, time_s, detections):
        uncertain = []
        self.last_time = time_s
        lo, hi = self.config.get("perpendicular_roi", [0., 1.])
        axis = self.config.get("axis", "y")
        values = np.asarray(detections, np.float32).reshape(-1, 6)
        if self.track_only_in_channel:
            # Apply the physical channel before association: an outside false
            # detection must not acquire or steal an in-channel identity.
            mask = admitted_detection_mask(values[:, :4], self.width, self.height, axis, (lo, hi), self.channel_polygon)
            values = values[mask]
        raw = self.tracker.update_at(time_s, Boxes(values))
        positions, tentative, active, tracks = {}, {}, set(), []
        def position(box):
            if self.channel_polygon is not None:
                box = np.asarray(box, dtype=float).copy()
                box[[0, 2]] = box[[0, 2]].clip(0, self.width)
                box[[1, 3]] = box[[1, 3]].clip(0, self.height)
            x1, y1, x2, y2 = box
            cx, cy = (x1 + x2) / (2 * self.width), (y1 + y2) / (2 * self.height)
            along, across = (cy, cx) if axis == "y" else (cx, cy)
            admitted = lo < across < hi and (self.channel_polygon is None or self.channel_polygon.contains(cx, cy))
            return along, admitted
        def identity(track_id):
            return f"{self.epoch}:{int(track_id)}"
        for row in raw:
            box = row[:4].astype(float)
            box[[0, 2]] = box[[0, 2]].clip(0, self.width)
            box[[1, 3]] = box[[1, 3]].clip(0, self.height)
            tid = identity(row[4])
            active.add(tid)
            along, admitted = position(box)
            if admitted:
                positions[tid] = along
            tracks.append({"track_id": tid, "xyxy": box.tolist(), "confidence": float(row[5])})
        for track in self.tracker.tracked_stracks:
            if track.is_activated:
                continue
            along, admitted = position(track.xyxy)
            if admitted:
                tentative[identity(track.track_id)] = along
        retained = {identity(t.track_id) for t in self.tracker.tracked_stracks + self.tracker.lost_stracks}
        events, newly_uncertain = self.counter.update(time_s, frame, positions, tentative, active, retained)
        for event in events:
            event["event_id"] = f"{self.session_id}:{self.epoch}:{event['event_id'].rsplit(':', 1)[-1]}"
        self.maximum_state_count = max(self.maximum_state_count, self.counter.maximum_state_count)
        return tracks, events, uncertain + newly_uncertain

    def finish(self):
        return self.counter.finish()
