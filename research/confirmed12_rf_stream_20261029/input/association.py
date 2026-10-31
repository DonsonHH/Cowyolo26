"""Observation-only passage/RF association and frozen visual candidate fallback."""
from dataclasses import dataclass
from collections import Counter
from typing import Optional
import math

@dataclass(frozen=True)
class Passage:
    event_id: str
    opened: int
    closed: int
    snapshot_id: Optional[str]
    direction: str='A->B'
    reader: str='lane1'
    def __post_init__(self):
        if self.closed<self.opened:raise ValueError('Passage time order invalid')
        if self.direction not in ['A->B','B->A']:raise ValueError('Unknown direction')

@dataclass(frozen=True)
class Read:
    read_id: str
    code: str
    captured: int
    received: int
    reader: str='lane1'
    valid: bool=True

@dataclass(frozen=True)
class Candidate:
    predicted_identity: str
    similarity: float
    threshold: float
    model_version: str
    def accepted(self):
        return math.isfinite(self.similarity) and math.isfinite(self.threshold) and self.similarity>=self.threshold

class Resolver:
    def __init__(self,passages,reads,registry,guard=1,wait=5):
        if guard<0 or wait<0:raise ValueError('Negative association budget')
        self.passages=list(passages);self.reads=list(reads);self.registry=dict(registry);self.guard=guard;self.wait=wait
        if len({p.event_id for p in passages})!=len(passages):raise ValueError('Duplicate passage IDs')
        if len({r.read_id for r in reads})!=len(reads):raise ValueError('Duplicate observation IDs')
        self.outputs={};self.consumed=set();self.last_now=None
    def eligible(self,p,r):
        return r.reader==p.reader and p.opened-self.guard<=r.captured<=p.closed+self.guard
    def advance(self,now):
        if self.last_now is not None and now<self.last_now:raise ValueError('Time went backwards')
        self.last_now=now;new=[]
        for p in sorted(self.passages,key=lambda p:(p.closed+self.wait,p.event_id)):
            if p.event_id in self.outputs or p.closed+self.wait>now:continue
            cutoff=p.closed+self.wait
            reads=[r for r in self.reads if r.valid and r.received>=r.captured and r.received<=cutoff and r.read_id not in self.consumed and self.eligible(p,r)]
            codes=sorted({r.code for r in reads})
            shared=any(sum(other.opened<=cutoff and self.eligible(other,r) for other in self.passages)>1 for r in reads)
            late=[r.read_id for r in self.reads if r.valid and r.received>=r.captured and cutoff<r.received<=now and self.eligible(p,r)]
            if len(codes)==1 and not shared and codes[0] in self.registry:
                status='RF_UNIQUE_CANDIDATE';identity=self.registry[codes[0]]
                self.consumed.update(r.read_id for r in reads)
            else:
                identity=None
                status='RF_SHARED_WINDOW' if shared else 'RF_MULTI_CODE' if len(codes)>1 else 'RF_UNREGISTERED_CODE' if codes else 'RF_NO_TIMELY_READ'
            result={'event_id':p.event_id,'decision_tick':cutoff,'rf_status':status,'identity_candidate':identity,
                    'timely_observation_ids':[r.read_id for r in reads],'candidate_code_count':len(codes),
                    'late_observation_ids':late,'snapshot_id':p.snapshot_id,'direction':p.direction,
                    'source':'rf' if identity is not None else 'unresolved','reason':None if identity is not None else status}
            self.outputs[p.event_id]=result;new.append(result)
        for p in self.passages:
            if p.event_id in self.outputs:
                cutoff=p.closed+self.wait
                self.outputs[p.event_id]['late_observation_ids']=[r.read_id for r in self.reads if r.valid and r.received>=r.captured and cutoff<r.received<=now and self.eligible(p,r)]
        return new

def apply_visual(result,candidates):
    """One frozen visual query, no registry or expected identity lookup."""
    result=dict(result)
    if result['identity_candidate'] is not None:return result
    snapshot=result['snapshot_id']
    if snapshot is None:result.update(source='unresolved',reason='SNAPSHOT_MISSING');return result
    candidate=candidates.get(snapshot)
    if candidate is None:result.update(source='unresolved',reason='CANDIDATE_UNAVAILABLE');return result
    if not candidate.accepted():result.update(source='unresolved',reason='VISUAL_REJECTED',model_version=candidate.model_version);return result
    result.update(identity_candidate=candidate.predicted_identity,source='visual',reason=None,model_version=candidate.model_version)
    return result

def score_ledger(truth,outputs):
    if len({r['event_id'] for r in truth})!=len(truth):raise ValueError('Duplicate reference event IDs')
    byid={row['event_id']:row for row in outputs}
    if len(byid)!=len(outputs):raise ValueError('Multiple terminal outputs for one event')
    counts=Counter();detail=[]
    for expected in truth:
        row=byid.get(expected['event_id'])
        outcome='M' if row is None else 'U' if row['identity_candidate'] is None else 'C' if row['identity_candidate']==expected['expected_identity'] else 'W'
        counts[outcome]+=1;detail.append({'event_id':expected['event_id'],'outcome':outcome})
    ids={r['event_id'] for r in truth};extras=sum(row['event_id'] not in ids for row in outputs)
    assert sum(counts[k] for k in ['C','W','U','M'])==len(truth)
    return {'N':len(truth),**{k:counts[k] for k in ['C','W','U','M']},'extra_outputs':extras,
            'wrong_fraction_among_assigned':counts['W']/(counts['C']+counts['W']) if counts['C']+counts['W'] else None,'per_event':detail}
