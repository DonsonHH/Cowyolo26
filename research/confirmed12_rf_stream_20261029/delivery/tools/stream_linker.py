"""Causal visual reservations around the unchanged observation-only Resolver."""
import hashlib
from dataclasses import replace,asdict
from association import Passage,Read,Resolver

class OnlineLinker:
    def __init__(self,registry,*,reader='lane1',wait_frames=15,orphan_gap_frames=50,horizon_frame0=10873):
        if min(wait_frames,orphan_gap_frames)<0 or horizon_frame0<0:raise ValueError('Invalid timing budget')
        self.reader=reader;self.wait=wait_frames;self.gap=orphan_gap_frames;self.horizon=horizon_frame0
        self.resolver=Resolver([],[],registry,guard=0,wait=wait_frames)
        self.slots={};self.active={};self.last_positions={};self.events={};self.outputs={};self.reads={};self.last_now=None;self.audit=[]
    def _new_slot(self,track,now):
        sid='v-'+hashlib.sha256(f'{self.reader}:{track}:{now}:{len(self.slots)}'.encode()).hexdigest()[:20]
        row={'reservation_id':sid,'track_id':track,'opened_frame0':now,'closed_frame0':None,'last_seen_frame0':now,
             'event_id':None,'orphan_closed':False,'birth_was_late_count':False}
        self.slots[sid]=row;self.active[track]=sid
        self.resolver.passages.append(Passage(sid,now,self.horizon+self.wait+1,None,reader=self.reader))
        self.audit.append({'frame0':now,'kind':'RESERVATION_OPENED','reservation_id':sid,'track_id':track})
        return row
    def _replace_passage(self,sid,**fields):
        i=next(i for i,p in enumerate(self.resolver.passages) if p.event_id==sid)
        self.resolver.passages[i]=replace(self.resolver.passages[i],**fields)
    def _close_orphan(self,slot,now):
        sid=slot['reservation_id'];slot['closed_frame0']=slot['last_seen_frame0'];slot['orphan_closed']=True
        self._replace_passage(sid,closed=slot['last_seen_frame0'])
        self.resolver.outputs[sid]={'event_id':sid,'identity_candidate':None,'rf_status':'UNCOUNTED_VISUAL_RESERVATION',
                                    'late_observation_ids':[]}
        if self.active.get(slot['track_id'])==sid:del self.active[slot['track_id']]
        self.audit.append({'frame0':now,'kind':'UNCOUNTED_RESERVATION_CLOSED','reservation_id':sid})
    def step(self,now,positions,closing_events,reads):
        if not isinstance(now,int) or not 0<=now<=self.horizon or self.last_now is not None and now<self.last_now:
            raise ValueError('Source frame clock must be monotonic within the declared session')
        for read in reads:
            if read.received>now:raise ValueError('Future read must not be supplied before receipt')
            old=self.reads.get(read.read_id)
            if old is not None:
                if old!=read:raise ValueError('Conflicting duplicate read ID')
                self.audit.append({'frame0':now,'kind':'IDENTICAL_READ_RETRANSMISSION','read_id':read.read_id});continue
            self.reads[read.read_id]=read;self.resolver.reads.append(read)
        for track,position in positions.items():
            if not 0<=position<=1:raise ValueError('Native visual position outside image')
            slot=self.slots.get(self.active.get(track))
            if slot is not None and slot['event_id'] is not None:
                previous=self.last_positions.get(track)
                reentered=previous is not None and not .4<=previous<=.6 and .4<=position<=.6
                if reentered:slot=None
            if slot is None and .25<=position<=.75:slot=self._new_slot(track,now)
            if slot is not None and slot['event_id'] is None:slot['last_seen_frame0']=now
            self.last_positions[track]=position
        for event in closing_events:
            expected_keys={'event_id','track_id','direction','snapshot_id'}
            if set(event)!=expected_keys:raise ValueError('Closing event must contain observations only')
            identity=event['event_id']
            if identity in self.events:
                old=self.events[identity]
                if old['closed_frame0']!=now or old['input']!=event:raise ValueError('Conflicting duplicate event')
                continue
            track=event['track_id'];slot=self.slots.get(self.active.get(track))
            if slot is None or slot['event_id'] is not None:
                slot=self._new_slot(track,now);slot['birth_was_late_count']=True
            slot.update(closed_frame0=now,event_id=identity)
            self._replace_passage(slot['reservation_id'],closed=now,snapshot_id=event['snapshot_id'],direction=event['direction'])
            self.events[identity]={'input':dict(event),'reservation_id':slot['reservation_id'],'closed_frame0':now}
            self.audit.append({'frame0':now,'kind':'COUNTED_PASSAGE_CLOSED','event_id':identity,'reservation_id':slot['reservation_id']})
        for slot in list(self.slots.values()):
            if slot['event_id'] is None and slot['closed_frame0'] is None and now-slot['last_seen_frame0']>self.gap:self._close_orphan(slot,now)
        for passage in self.resolver.passages:
            if passage.event_id in self.resolver.outputs or passage.closed+self.wait>now:continue
            slot=self.slots[passage.event_id]
            if slot['event_id'] is not None:
                self.audit.append({'frame0':now,'kind':'RF_CAUSAL_CONTEXT','event_id':slot['event_id'],
                    'target_reservation_id':passage.event_id,'passages':[asdict(p) for p in self.resolver.passages],
                    'received_reads':[asdict(r) for r in self.resolver.reads],
                    'already_consumed_read_ids':sorted(self.resolver.consumed)})
        generated=self.resolver.advance(now);new=[]
        for raw in generated:
            slot=self.slots[raw['event_id']];identity=slot['event_id'];assert identity is not None
            row={**raw,'event_id':identity,'reservation_id':slot['reservation_id'],
                 'decision_frame0':raw['decision_tick'],'emitted_frame0':now,'verified_identity':False,
                 'identity_namespace':'synthetic_RF_registry' if raw['identity_candidate'] is not None else None,
                 'late_observation_ids':list(raw['late_observation_ids'])}
            self.outputs[identity]=row;new.append(row)
            self.audit.append({'frame0':now,'kind':'RF_DECISION','event_id':identity,'rf_status':raw['rf_status']})
        for identity,row in self.outputs.items():
            sid=self.events[identity]['reservation_id'];raw=self.resolver.outputs[sid]
            assert row['identity_candidate']==raw['identity_candidate'] and row['rf_status']==raw['rf_status']
            row['late_observation_ids']=list(raw['late_observation_ids'])
        self.last_now=now;return new
    def finish(self,now):
        for slot in list(self.slots.values()):
            if slot['event_id'] is None and slot['closed_frame0'] is None:self._close_orphan(slot,now)
        return self.step(now,{},[],[])
    def export(self):
        return {'slots':list(self.slots.values()),'events':self.events,'outputs':list(self.outputs.values()),
                'consumed_read_ids':sorted(self.resolver.consumed),'audit':self.audit}
