"""Bounded confirmed-observation passage state; totals survive state eviction."""
import math
from dataclasses import dataclass


@dataclass
class State:
    origin: str | None = None
    candidate: str | None = None
    streak: int = 0
    last_seen: float = -1e30
    last_position: float | None = None
    origin_time: float | None = None
    origin_frame: int | None = None
    emitted: bool = False
    unanchored_start: tuple | None = None
    unanchored_reported: bool = False


class PassageCounter:
    def __init__(self, session_id, lower=.4, upper=.6, stable_samples=3,
                 maximum_gap_s=2., ttl_s=10., in_direction="A->B"):
        if not 0 <= lower < upper <= 1 or stable_samples < 1 or maximum_gap_s <= 0 or ttl_s < maximum_gap_s:
            raise ValueError("Invalid counting boundaries, stability or TTL")
        if in_direction not in ("A->B", "B->A"):
            raise ValueError("in_direction must be A->B or B->A")
        self.session_id, self.lower, self.upper = session_id, lower, upper
        self.stable_samples, self.maximum_gap_s, self.ttl_s = stable_samples, maximum_gap_s, ttl_s
        self.in_direction = in_direction
        self.states, self.pending, self.seen = {}, {}, {}
        self.counts = {"IN": 0, "OUT": 0}
        self.last_time = None
        self.maximum_state_count = 0
        self.event_sequence = 0

    def zone(self, pos):
        return "A" if pos < self.lower else "B" if pos > self.upper else None

    def _observe(self, time_s, frame, tid, pos, emit):
        state = self.states.setdefault(tid, State())
        if time_s - state.last_seen > self.maximum_gap_s:
            state.origin, state.candidate, state.streak = None, None, 0
            state.origin_time, state.origin_frame = None, None
            state.unanchored_start, state.unanchored_reported = None, False
            state.emitted = False
        zone = self.zone(pos)
        if state.origin is None and zone is None and state.unanchored_start is None:
            state.unanchored_start = (time_s, frame)
        state.streak = state.streak + 1 if zone is not None and state.candidate == zone else 1 if zone else 0
        state.candidate = zone
        state.last_seen, state.last_position = time_s, pos
        if zone is None or state.streak < self.stable_samples or state.origin == zone:
            return None
        origin, entry_time, entry_frame = state.origin, state.origin_time, state.origin_frame
        state.origin, state.origin_time, state.origin_frame = zone, time_s, frame
        if origin is None or not emit:
            return None
        direction = origin + "->" + zone
        kind = "IN" if direction == self.in_direction else "OUT"
        self.counts[kind] += 1
        self.event_sequence += 1
        state.emitted = True
        return {"session_id": self.session_id, "event_id": f"{self.session_id}:{self.event_sequence:06d}",
                "track_id": tid, "direction": direction, "kind": kind, "entry_time_s": entry_time,
                "entry_frame0": entry_frame, "time_s": time_s, "frame0": frame, "axis_position": pos}

    def _censor(self, tid, state, reason, time_s):
        if state.last_position is None:
            return None
        # Stable destination already reached: that complete event remains complete.
        if state.emitted and state.origin is not None and self.zone(state.last_position) == state.origin:
            return None
        return {"session_id": self.session_id, "track_id": tid, "time_s": time_s,
                "last_seen_s": state.last_seen, "reason": reason,
                "origin": state.origin, "last_axis_position": state.last_position,
                "status": "uncertain_or_truncated", "counts_as_complete_passage": False}

    def update(self, time_s, frame, confirmed, tentative, confirmed_ids, retained_ids):
        if not math.isfinite(time_s) or self.last_time is not None and time_s <= self.last_time:
            raise ValueError("Strictly increasing finite source times required")
        active = set(confirmed_ids)
        if not set(confirmed) <= active or active & set(tentative):
            raise ValueError("Confirmed and tentative IDs inconsistent")
        if any(not math.isfinite(pos) or not 0 <= pos <= 1 for pos in [*confirmed.values(), *tentative.values()]):
            raise ValueError("Positions must be finite fractions")
        events, uncertain = [], []
        previous_pending = self.pending
        for tid in list(self.states):
            state = self.states[tid]
            if tid in confirmed and time_s - state.last_seen > self.maximum_gap_s:
                uncertain.append({"session_id": self.session_id, "track_id": tid, "time_s": time_s,
                                  "last_seen_s": state.last_seen, "previous_origin": state.origin,
                                  "previous_axis_position": state.last_position, "axis_position": confirmed[tid],
                                  "reason": "observation_gap", "status": "uncertain_or_truncated",
                                  "counts_as_complete_passage": False})
            if tid not in retained_ids or time_s - state.last_seen > self.ttl_s:
                record = self._censor(tid, state, "track_removed_or_expired", time_s)
                if record:
                    uncertain.append(record)
                del self.states[tid]
        # Keep confirmation guard while the tracker can still revive that identity.
        self.seen = {tid: stamp for tid, stamp in self.seen.items() if tid in retained_ids}
        for tid in active:
            if tid not in self.seen and tid in previous_pending:
                stamp, old_frame, pos = previous_pending[tid]
                if stamp == self.last_time and time_s - stamp <= self.maximum_gap_s:
                    self._observe(stamp, old_frame, tid, pos, False)
            self.seen[tid] = time_s
        # Admission is historical evidence only. A current observation outside the
        # lane breaks the streak even when this is the first confirmed tick.
        for tid, state in self.states.items():
            if tid not in confirmed:
                state.candidate, state.streak = None, 0
        for tid, pos in confirmed.items():
            event = self._observe(time_s, frame, tid, pos, True)
            if event:
                events.append(event)
            state = self.states[tid]
            if state.unanchored_start is not None and not state.unanchored_reported:
                uncertain.append({"session_id": self.session_id, "track_id": tid,
                                  "time_s": state.unanchored_start[0], "frame0": state.unanchored_start[1],
                                  "reason": "track_first_observed_between_zones",
                                  "status": "uncertain_or_truncated", "counts_as_complete_passage": False})
                state.unanchored_reported = True
        self.pending = {tid: (time_s, frame, pos) for tid, pos in tentative.items() if tid not in self.seen}
        self.last_time = time_s
        self.maximum_state_count = max(self.maximum_state_count, len(self.states) + len(self.pending) + len(self.seen))
        return events, uncertain

    def finish(self):
        records = [self._censor(tid, state, "video_end", self.last_time)
                   for tid, state in self.states.items()]
        self.states.clear()
        self.pending.clear()
        self.seen.clear()
        return [row for row in records if row]

    def summary(self):
        return {**self.counts, "NET": self.counts["IN"] - self.counts["OUT"],
                "active_states": len(self.states), "pending": len(self.pending), "confirmation_guards": len(self.seen),
                "maximum_state_count": self.maximum_state_count}
