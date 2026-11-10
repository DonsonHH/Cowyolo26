"""Pure scheduling fixtures only; no inference or accuracy results."""
import unittest
from .budget_schedule import PairBudgetPlan, CallLedger


class BudgetScheduleTests(unittest.TestCase):
    def test_real_inputs_reproduce_two_and_half_hz_budget(self):
        for frames,expected in ((403,202),(649,325),(405,203),(599,300),(600,300)):
            plan=PairBudgetPlan(frames)
            self.assertEqual(plan.real_call_budget,expected)
            self.assertTrue(all(release<frames for _,_,release in plan.slots))

    def test_tail_is_predeclared_and_has_no_local_bonus(self):
        for frames in range(1,33):
            p=PairBudgetPlan(frames)
            self.assertEqual(len(p.slots),len(set((b,s) for b,s,_ in p.slots)))
            for b in p.blocks:
                if b.second_frame0 is None:
                    self.assertIsNone(p.decision(b,'conditional_local_pair',True))

    def test_global_and_local_use_same_two_slots(self):
        p=PairBudgetPlan(4)
        b=p.blocks[0]
        self.assertEqual(p.decision(b,'global_pair',True)['observation_frame0'],2)
        local=p.decision(b,'conditional_local_pair',True)
        self.assertEqual((local['release_frame0'],local['observation_frame0']),(2,0))
        self.assertEqual(p.decision(b,'conditional_local_pair',False)['observation_frame0'],2)

    def test_missing_or_extra_call_cannot_pass(self):
        p=PairBudgetPlan(4)
        ledger=CallLedger(p)
        ledger.record(0,0,'global',0,'a'*64,'b'*64)
        with self.assertRaises(ValueError):ledger.finish()
        ledger.record(0,1,'local',0,'c'*64,'d'*64)
        self.assertEqual(ledger.finish()['executed_real_calls'],2)
        with self.assertRaises(ValueError):ledger.record(1,0,'global',4,'e'*64,'f'*64)

    def test_future_or_wrong_image_and_reordering_are_rejected(self):
        p=PairBudgetPlan(4)
        for slot,kind,frame in ((1,'global',2),(0,'local',0),(0,'global',2)):
            with self.subTest(slot=slot,kind=kind,frame=frame),self.assertRaises(ValueError):
                CallLedger(p).record(0,slot,kind,frame,'a'*64,'b'*64)
        ledger=CallLedger(p);ledger.record(0,0,'global',0,'a'*64,'b'*64)
        with self.assertRaises(ValueError):ledger.record(0,1,'local',2,'a'*64,'b'*64)

    def test_every_policy_has_exactly_equal_actual_call_opportunities(self):
        for condition in ('global_pair','conditional_local_pair'):
            plan=PairBudgetPlan(17)
            ledger=CallLedger(plan)
            for b in plan.blocks:
                ledger.record(b.index,0,'global',b.first_frame0,'a'*64,'b'*64)
                decision=plan.decision(b,condition,b.index%2==0)
                if decision:
                    ledger.record(b.index,1,decision['kind'],decision['observation_frame0'],'a'*64,'b'*64)
            self.assertEqual(ledger.finish()['executed_real_calls'],plan.real_call_budget)


if __name__=='__main__':unittest.main()
