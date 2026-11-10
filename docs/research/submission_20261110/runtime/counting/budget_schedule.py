"""An exact source-frame call schedule for a controlled global/local budget comparison."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetBlock:
    index: int
    first_frame0: int
    second_frame0: int | None


class PairBudgetPlan:
    """Each full four-frame block has two real-call slots; no extra EOF calls."""
    def __init__(self, frames, source_fps=5., block_frames=4, second_offset=2):
        if isinstance(frames, bool) or not isinstance(frames, int) or frames < 1:
            raise ValueError('A known positive source frame count is required')
        if (isinstance(block_frames, bool) or not isinstance(block_frames, int)
                or isinstance(second_offset, bool) or not isinstance(second_offset, int)
                or not 0 < second_offset < block_frames):
            raise ValueError('Second call must lie strictly inside each source block')
        import math
        if isinstance(source_fps, bool) or not math.isfinite(source_fps) or source_fps <= 0:
            raise ValueError('A finite positive CFR source rate is required')
        self.frames, self.source_fps = frames, float(source_fps)
        self.block_frames, self.second_offset = block_frames, second_offset
        self.blocks = tuple(BudgetBlock(i, f, f+second_offset if f+second_offset < frames else None)
                            for i, f in enumerate(range(0, frames, block_frames)))
        self.slots = tuple((b.index, slot, frame)
                           for b in self.blocks for slot, frame in ((0,b.first_frame0),(1,b.second_frame0))
                           if frame is not None)

    @property
    def real_call_budget(self):
        return len(self.slots)

    def decision(self, block, policy, eligible_local):
        if policy not in {'global_pair', 'conditional_local_pair'} or not isinstance(eligible_local, bool):
            raise ValueError('Declare a valid policy and a boolean causal local eligibility')
        if block not in self.blocks:
            raise ValueError('Block does not belong to this frozen plan')
        if block.second_frame0 is None:
            return None
        if policy == 'conditional_local_pair' and eligible_local:
            return {'kind':'local','release_frame0':block.second_frame0,
                    'observation_frame0':block.first_frame0}
        return {'kind':'global','release_frame0':block.second_frame0,
                'observation_frame0':block.second_frame0}


class CallLedger:
    """Bind one inference receipt to each planned slot, independently of detections."""
    def __init__(self, plan):
        self.plan = plan
        self.records = []

    def record(self, block_index, slot, kind, observation_frame0, input_sha256, output_sha256):
        if len(self.records) >= len(self.plan.slots):
            raise ValueError('Neural call exceeds frozen budget')
        block, expected_slot, release = self.plan.slots[len(self.records)]
        if (block_index, slot) != (block, expected_slot):
            raise ValueError('Model calls must follow the frozen source-slot order')
        if (isinstance(observation_frame0, bool) or not isinstance(observation_frame0, int)
                or kind not in {'global','local'}):
            raise ValueError('A real input source frame and call kind are required')
        first = self.plan.blocks[block].first_frame0
        if (slot==0 and (kind!='global' or observation_frame0!=first)
                or slot==1 and kind=='global' and observation_frame0!=release
                or slot==1 and kind=='local' and observation_frame0!=first):
            raise ValueError('Local uses this block first image; global uses the released image')
        for digest in (input_sha256, output_sha256):
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('Each actual input and output needs a SHA256 digest')
        self.records.append({'block':block,'slot':slot,'kind':kind,
                             'release_frame0':release,'observation_frame0':observation_frame0,
                             'input_sha256':input_sha256,'output_sha256':output_sha256})

    def finish(self):
        if len(self.records) != self.plan.real_call_budget:
            raise ValueError('Incomplete budget execution; retain the failed run')
        return {'planned_real_calls':self.plan.real_call_budget,'executed_real_calls':len(self.records),
                'global_calls':sum(r['kind']=='global' for r in self.records),
                'local_calls':sum(r['kind']=='local' for r in self.records),
                'warmup_calls_are_outside_this_schedule':True}
