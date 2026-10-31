"""Admit one immediately preceding tentative observation only at confirmation.

Uses the frozen ZoneCounter per identity, so admitting a past observation never
rewinds another identity's clock. Only currently confirmed observations emit.
"""
import math
from zone_counter import ZoneCounter

class ConfirmationHandoffCounter:
    def __init__(self,lower=.4,upper=.6,stable_samples=3,maximum_gap_s=2.,retain_prior=True):
        ZoneCounter(lower,upper,stable_samples,maximum_gap_s)  # same parameter validation
        self.config=dict(lower=lower,upper=upper,stable_samples=stable_samples,maximum_gap_s=maximum_gap_s)
        self.retain_prior=retain_prior;self.counters={};self.pending={};self.confirmed_seen=set()
        self.last_tick=None;self.last_acceptances=[];self.maximum_pending_tracks=0

    def update(self,time_s,confirmed_positions,tentative_positions,confirmed_ids=None):
        if not math.isfinite(time_s) or self.last_tick is not None and time_s<=self.last_tick:
            raise ValueError('Updates require strictly increasing finite times')
        active=set(confirmed_positions) if confirmed_ids is None else set(confirmed_ids)
        if not set(confirmed_positions)<=active or active&set(tentative_positions):
            raise ValueError('Confirmed and tentative identities must be consistent and disjoint')
        for p in [*confirmed_positions.values(),*tentative_positions.values()]:
            if not math.isfinite(p) or not 0<=p<=1:raise ValueError('Positions must lie within native image axis')
        previous=self.last_tick;old_pending=self.pending;self.last_acceptances=[]
        for tid in sorted(active):
            if tid not in self.counters and (tid in confirmed_positions or tid in old_pending):
                counter=ZoneCounter(**self.config);self.counters[tid]=counter
                item=old_pending.get(tid)
                if self.retain_prior and tid not in self.confirmed_seen and item and item[0]==previous and time_s-item[0]<=self.config['maximum_gap_s']:
                    assert counter.update(item[0],{tid:item[1]})==[]
                    self.last_acceptances.append({'track_id':tid,'observation_time_s':item[0],'confirmation_time_s':time_s,'axis_position':item[1]})
        emitted={}
        for tid,counter in self.counters.items():
            position={tid:confirmed_positions[tid]} if tid in confirmed_positions else {}
            events=counter.update(time_s,position)
            if events:
                assert tid in active and tid in confirmed_positions and all(e['time_s']==time_s for e in events)
                emitted[tid]=events
        self.confirmed_seen.update(active)
        # A failed confirmation discards the old entry. Repeated tentative samples
        # replace a single entry; their history never accumulates stable evidence.
        self.pending={tid:(time_s,pos) for tid,pos in tentative_positions.items() if self.retain_prior and tid not in self.confirmed_seen}
        self.maximum_pending_tracks=max(self.maximum_pending_tracks,len(self.pending));self.last_tick=time_s
        return [event for tid in confirmed_positions for event in emitted.get(tid,[])]
