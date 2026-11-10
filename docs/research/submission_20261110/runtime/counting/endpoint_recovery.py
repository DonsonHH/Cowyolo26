"""Bounded real-detector verification of a partially confirmed gate arrival.

This policy neither updates tracks nor emits passages. A selected detection must
still pass ordinary association and the unchanged confirmed-observation counter.
"""
from collections import deque
import math
import numpy as np
from .channel import ChannelPolygon, admitted_detection_mask
from .protocol import gate_from_config


def iou(a, b):
    intersection = max(0., min(a[2], b[2]) - max(a[0], b[0])) * max(0., min(a[3], b[3]) - max(a[1], b[1]))
    area_a = max(0., a[2] - a[0]) * max(0., a[3] - a[1])
    area_b = max(0., b[2] - b[0]) * max(0., b[3] - b[1])
    return intersection / (area_a + area_b - intersection) if area_a + area_b > intersection else 0.


def select_local_detection(predicted, candidates, existing, confidence, reacquire):
    """Select a real local measurement while rejecting a neighboring cow."""
    area = max(0., predicted[2] - predicted[0]) * max(0., predicted[3] - predicted[1])
    accepted = []
    for row in candidates:
        candidate_area = (row[2] - row[0]) * (row[3] - row[1])
        target_overlap = iou(predicted, row[:4])
        if row[4] < confidence or not .25 * area <= candidate_area <= 4 * area or target_overlap < (.35 if reacquire else .2):
            continue
        if any(iou(row[:4], other[:4]) >= min(.5, target_overlap) for other in existing):
            continue
        accepted.append(row)
    key = (lambda row: (iou(predicted, row[:4]), row[4])) if reacquire else (lambda row: (row[4], iou(predicted, row[:4])))
    return max(accepted, key=key, default=None)


class EndpointRecovery:
    def __init__(self, config, width, height):
        options = config.get("endpoint_recovery", {})
        if not isinstance(options, dict) or not isinstance(options.get("enabled", False), bool):
            raise ValueError("endpoint_recovery must contain a boolean enabled")
        self.enabled = options.get("enabled", False)
        self.scale = float(options.get("roi_scale", 1.5))
        self.max_age = float(options.get("maximum_age_s", 1.))
        self.max_per_frame = options.get("maximum_per_frame", 2)
        self.budget = options.get("maximum_extra_forwards", 32)
        self.reacquire = options.get("reacquire_missing_tracks", False)
        self.max_reacquisitions = options.get("maximum_reacquisitions_per_origin", 8)
        if not isinstance(self.reacquire, bool):
            raise ValueError("reacquire_missing_tracks must be boolean")
        if not math.isfinite(self.scale) or not 1 < self.scale <= 3 or not math.isfinite(self.max_age) or not 0 < self.max_age <= 2:
            raise ValueError("Invalid endpoint recovery scale or age")
        limits = [self.max_per_frame, self.max_reacquisitions] + ([] if self.budget is None else [self.budget])
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in limits) or self.max_per_frame > 8:
            raise ValueError("Endpoint recovery needs positive bounded integer budgets")
        self.width, self.height = width, height
        self.gate = gate_from_config(config)
        self.polygon = ChannelPolygon(self.gate["channel_polygon"]) if "channel_polygon" in self.gate else None
        self.confidence = float(config.get("confidence", .2))
        self.history, self.attempts = {}, {}
        self.reserved_forwards = 0

    def _in_channel(self, detections):
        values = np.asarray(detections, dtype=float).reshape(-1, 6)
        mask = admitted_detection_mask(values[:, :4], self.width, self.height, self.gate["axis"],
                                       self.gate["perpendicular_roi"], self.polygon)
        return values[mask]

    def record(self, time_s, tracks, states):
        self.history = {key: value for key, value in self.history.items() if key in states}
        live_origins = {(key, state.origin_time) for key, state in states.items()}
        self.attempts = {key: value for key, value in self.attempts.items() if key[:2] in live_origins}
        for track in tracks:
            tid = track["track_id"]
            if tid in states and states[tid].last_seen == time_s:
                self.history.setdefault(tid, deque(maxlen=2)).append((time_s, np.asarray(track["xyxy"], dtype=float)))

    def proposals(self, time_s, detections, states, stable_samples):
        if not self.enabled or self.budget is not None and self.reserved_forwards >= self.budget:
            return []
        detections = self._in_channel(detections)
        result = []
        def priority(tid):
            state = states[tid]
            destination = "A" if state.origin == "B" else "B"
            pending = state.candidate == destination and 0 < state.streak < stable_samples
            gate = self.gate["lower"] if destination == "A" else self.gate["upper"]
            distance = abs(state.last_position - gate) if state.last_position is not None else float("inf")
            return (not pending, distance, state.last_seen, tid)
        identities = sorted(states, key=priority) if self.reacquire else sorted(states)
        for tid in identities:
            state, history = states[tid], self.history.get(tid, ())
            if state.origin not in ("A", "B") or len(history) < 2:
                continue
            destination = "A" if state.origin == "B" else "B"
            pending = state.candidate == destination and 0 < state.streak < stable_samples
            if not pending and not self.reacquire:
                continue
            (t0, box0), (t1, box1) = history
            age = time_s - t1
            if not 0 < age <= self.max_age or t1 <= t0:
                continue
            center0, center1 = (box0[:2] + box0[2:]) / 2, (box1[:2] + box1[2:]) / 2
            if not pending and time_s - t0 > self.max_age:
                continue
            dimension = 1 if self.gate["axis"] == "y" else 0
            heading = -1 if destination == "A" else 1
            if not pending and (center1[dimension] - center0[dimension]) * heading <= 0:
                continue
            key = (tid, state.origin_time, destination) if pending else (tid, state.origin_time, destination, "reacquire")
            limit = 2 if pending else self.max_reacquisitions
            if self.attempts.get(key, 0) >= limit:
                continue
            center = center1 + (center1 - center0) * age / (t1 - t0)
            size = box1[2:] - box1[:2]
            predicted = np.r_[center - size / 2, center + size / 2]
            if any(iou(predicted, row[:4]) >= .2 for row in detections):
                continue
            roi = np.rint(np.r_[center - size * self.scale / 2, center + size * self.scale / 2]).astype(int)
            roi[[0, 2]] = roi[[0, 2]].clip(0, self.width)
            roi[[1, 3]] = roi[[1, 3]].clip(0, self.height)
            if roi[2] - roi[0] < 16 or roi[3] - roi[1] < 16:
                continue
            self.attempts[key] = self.attempts.get(key, 0) + 1
            self.reserved_forwards += 1
            proposal = {"track_id": tid, "roi": roi.tolist(), "predicted_box": predicted.tolist()}
            if self.reacquire:
                proposal["reason"] = "endpoint_confirmation" if pending else "anchored_track_reacquisition"
            result.append(proposal)
            if len(result) >= self.max_per_frame or self.budget is not None and self.reserved_forwards >= self.budget:
                break
        return result

    def select(self, proposal, candidates, existing):
        return select_local_detection(proposal["predicted_box"], self._in_channel(candidates),
                                      self._in_channel(existing), self.confidence, self.reacquire)

    def superseded_global_indices(self, proposal, selected, existing, time_s, high_threshold,
                                  association_predictions=None):
        """Replace a weak view only when the target beats competing real histories.

        Overlap alone cannot identify a cow: another overlapping weak cow must
        remain available to ordinary one-to-one association. Predictions decide
        measurement ownership here; they never become counter observations.
        """
        competitors={}
        for tid,history in self.history.items():
            if tid==proposal['track_id'] or len(history)<2:continue
            (t0,b0),(t1,b1)=history
            age=time_s-t1
            if not 0<age<=self.max_age or t1<=t0:continue
            c0,c1=(b0[:2]+b0[2:])/2,(b1[:2]+b1[2:])/2
            center=c1+(c1-c0)*age/(t1-t0)
            size=b1[2:]-b1[:2]
            competitors[tid]=np.r_[center-size/2,center+size/2]
        # The tracker also retains tentative observations. A just-confirmed
        # neighbor can already have two real measurements while record() has
        # seen only its first confirmed output. Use its actual association
        # prediction instead of silently omitting that competing identity.
        competitors.update(association_predictions or {})
        competitors.pop(proposal['track_id'],None)
        removed=[]
        for index,row in enumerate(existing):
            if row[5]!=selected[5] or row[4]>=high_threshold or iou(row,selected)<.5:continue
            target_overlap=iou(row,proposal['predicted_box'])
            other_overlap=max((iou(row,box) for box in competitors.values()),default=0.)
            if target_overlap>=.5 and target_overlap>other_overlap+.05:
                removed.append(index)
        return removed
