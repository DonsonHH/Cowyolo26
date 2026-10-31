"""Track-local two-region counter with explicit censoring and gap policy."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class TrackState:
    origin: Optional[str] = None
    candidate: Optional[str] = None
    streak: int = 0
    last_seen: float = -1e30

class ZoneCounter:
    def __init__(self, lower=.4, upper=.6, stable_samples=3, maximum_gap_s=2.):
        if not 0 <= lower < upper <= 1: raise ValueError('Invalid region boundaries')
        if stable_samples < 1 or maximum_gap_s <= 0: raise ValueError('Invalid stability/gap settings')
        self.lower=lower;self.upper=upper;self.stable_samples=stable_samples;self.maximum_gap_s=maximum_gap_s
        self.states={};self.last_tick=None

    def update(self, time_s, positions):
        if self.last_tick is not None and time_s < self.last_tick: raise ValueError('Time must be monotonic')
        self.last_tick=time_s;events=[]
        for tid,state in self.states.items():
            if tid not in positions: state.candidate=None;state.streak=0
        for tid,position in positions.items():
            if not 0 <= position <= 1: continue
            state=self.states.setdefault(tid,TrackState())
            if time_s-state.last_seen > self.maximum_gap_s: state.origin=None;state.candidate=None;state.streak=0
            state.last_seen=time_s
            zone='A' if position < self.lower else ('B' if position > self.upper else None)
            if zone is None: state.candidate=None;state.streak=0;continue
            state.streak=state.streak+1 if zone==state.candidate else 1;state.candidate=zone
            if state.streak < self.stable_samples or state.origin==zone: continue
            previous=state.origin;state.origin=zone
            if previous is not None: events.append({'time_s':float(time_s),'track_id':tid,'direction':previous+'->'+zone})
        return events
