"""One current-image zoom of a weak origin detection, never an inferred identity."""
import math
from collections import deque
import numpy as np

from .channel import ChannelPolygon, admitted_detection_mask
from .endpoint_recovery import iou, select_local_detection
from .protocol import gate_from_config
from .tracking import DEFAULT_TRACKER


class BirthRefinement:
    def __init__(self, config, width, height):
        options = config.get("birth_refinement", {})
        if not isinstance(options, dict) or not isinstance(options.get("enabled", False), bool):
            raise ValueError("birth_refinement needs boolean enabled")
        self.enabled = options.get("enabled", False)
        self.scale = float(options.get("roi_scale", 1.5))
        if not math.isfinite(self.scale) or not 1 < self.scale <= 3:
            raise ValueError("Invalid birth refinement crop scale")
        endpoint = config.get("endpoint_recovery", {})
        if self.enabled and endpoint.get("enabled", False) and endpoint.get("maximum_per_frame", 2) != 1:
            raise ValueError("Birth and endpoint refinement share one extra call per image")
        self.width, self.height = width, height
        self.gate = gate_from_config(config)
        self.polygon = ChannelPolygon(self.gate["channel_polygon"]) if "channel_polygon" in self.gate else None
        tracker = {**DEFAULT_TRACKER, **config.get("tracker", {})}
        # TrackingSession passes float32 scores to BYTETracker. Match its exact
        # threshold representation, including the strict low-score boundary.
        self.new_threshold = float(np.float32(tracker["new_track_thresh"]))
        self.high_threshold = float(np.float32(tracker["track_high_thresh"]))
        self.low_threshold = float(np.float32(tracker["track_low_thresh"]))
        self.match_threshold, self.fuse_score = tracker["match_thresh"], tracker["fuse_score"]
        self.seed_threshold = float(np.float32(config.get("confidence", .2)))
        self.maximum_age = float(endpoint.get("maximum_age_s", 1.))
        self.border_fraction = float(options.get("minimum_border_fraction", .02))
        if not math.isfinite(self.border_fraction) or not 0 <= self.border_fraction <= .1:
            raise ValueError("Invalid birth refinement border fraction")
        coordinate = 1 if self.gate["axis"] == "y" else 0
        roi = config.get("detection_roi_xyxy") or [0, 0, width, height]
        self.along_coordinate = coordinate
        self.along_bounds = (roi[coordinate], roi[coordinate + 2])
        self.weak_motion = options.get('weak_motion_support', False)
        self.minimum_motion = float(options.get('minimum_motion_per_s', .05))
        if not isinstance(self.weak_motion,bool) or not math.isfinite(self.minimum_motion) or not 0 < self.minimum_motion <= 2:
            raise ValueError('Invalid weak motion support configuration')
        self.weak_history = deque(maxlen=2)

    def record(self, time_s, detections):
        """Keep only bounded prior detector measurements; these never count."""
        if not self.enabled or not self.weak_motion:
            return
        if not math.isfinite(time_s) or self.weak_history and time_s <= self.weak_history[-1][0]:
            raise ValueError('Weak motion records need increasing source times')
        rows = np.asarray(detections,dtype=float).reshape(-1,6)
        rows = rows[self._admitted(rows)]
        rows = [row.copy() for row in rows if self.seed_threshold <= row[4] < self.new_threshold and self._zone(row)]
        rows.sort(key=lambda row:-row[4])
        self.weak_history.append((time_s,rows[:32]))

    def _motion_support(self, time_s, seed):
        if not self.weak_motion:
            return None
        coordinate = self.along_coordinate
        extent = self.height if coordinate == 1 else self.width
        center = np.clip([seed[coordinate],seed[coordinate+2]],0,extent).sum()/2
        zone = self._zone(seed)
        heading = 1 if zone == 'A' else -1
        for stamp, rows in reversed(self.weak_history):
            if not 0 < time_s-stamp <= self.maximum_age:
                continue
            for prior in rows:
                if prior[5] != seed[5] or self._zone(prior) != zone or iou(seed,prior) < .2:
                    continue
                previous = np.clip([prior[coordinate],prior[coordinate+2]],0,extent).sum()/2
                speed = heading*(center-previous)/(extent*(time_s-stamp))
                if speed >= self.minimum_motion:
                    return {'kind':'weak_motion','time_s':stamp,'detection':prior.tolist(),'motion_per_s':speed}
        return None

    def _admitted(self, rows):
        rows = np.asarray(rows, dtype=float).reshape(-1, 6)
        return admitted_detection_mask(rows[:, :4], self.width, self.height, self.gate["axis"],
                                       self.gate["perpendicular_roi"], self.polygon)

    def _zone(self, box):
        coordinate = 1 if self.gate["axis"] == "y" else 0
        extent = self.height if coordinate == 1 else self.width
        center = np.clip([box[coordinate], box[coordinate + 2]], 0, extent).sum() / (2 * extent)
        return "A" if center < self.gate["lower"] else "B" if center > self.gate["upper"] else None

    def proposal(self, time_s, detections, tracked):
        if not self.enabled:
            return None
        rows = np.asarray(detections, dtype=float).reshape(-1, 6)
        admitted = self._admitted(rows)
        # Descending real score, then detector order: one bounded zoom per image.
        for index in sorted(range(len(rows)), key=lambda i: (-rows[i, 4], i)):
            seed = rows[index]
            if not admitted[index] or not self.seed_threshold <= seed[4] < self.new_threshold or self._zone(seed) is None:
                continue
            lower, upper = self.along_bounds
            margin = (upper - lower) * self.border_fraction
            if seed[self.along_coordinate] <= lower + margin or seed[self.along_coordinate + 2] >= upper - margin:
                continue
            if any(j != index and admitted[j] and other[4] >= self.new_threshold and iou(seed, other) >= .2
                   for j, other in enumerate(rows)):
                continue
            usable_track, supported = False, False
            for track in tracked:
                observations = getattr(track, "observations", ())
                if not observations or not hasattr(track, "box_at"):
                    continue
                last_time, _ = observations[-1]
                if not 0 < time_s - last_time <= self.maximum_age:
                    continue
                overlap = iou(seed, track.box_at(time_s))
                supported |= overlap >= .2
                if seed[4] >= self.high_threshold:
                    cost = 1 - overlap * seed[4] if self.fuse_score else 1 - overlap
                    association_possible = cost <= (self.match_threshold if track.is_activated else .7)
                else:
                    association_possible = track.is_activated and seed[4] > self.low_threshold and 1 - overlap <= .5
                if association_possible:
                    usable_track = True
                    break
            support = {'kind':'initial_score'} if seed[4] > self.low_threshold else {'kind':'recent_track'} if supported else self._motion_support(time_s,seed)
            if usable_track or support is None:
                continue
            center, size = (seed[:2] + seed[2:4]) / 2, seed[2:4] - seed[:2]
            roi = np.rint(np.r_[center - size * self.scale / 2, center + size * self.scale / 2]).astype(int)
            roi[[0, 2]] = roi[[0, 2]].clip(0, self.width)
            roi[[1, 3]] = roi[[1, 3]].clip(0, self.height)
            if roi[2] - roi[0] < 16 or roi[3] - roi[1] < 16:
                continue
            return {"seed_index": index, "seed_detection": seed.tolist(), "roi": roi.tolist(),
                    "predicted_box": seed[:4].tolist(), "reason": "weak_origin_detection", "support":support}
        return None

    def select(self, proposal, candidates, existing):
        existing = np.asarray(existing, dtype=float).reshape(-1, 6)
        keep = self._admitted(existing) & (existing[:, 4] >= self.high_threshold)
        keep[proposal["seed_index"]] = False
        candidates = np.asarray(candidates, dtype=float).reshape(-1, 6)
        candidates = candidates[self._admitted(candidates)]
        candidates = np.asarray([row for row in candidates if self._zone(row) == self._zone(proposal["predicted_box"])],
                                dtype=float).reshape(-1, 6)
        return select_local_detection(proposal["predicted_box"], candidates, existing[keep], self.new_threshold, True)
