import unittest
from snapshot_bank import SnapshotBank,Snapshot,clipped_box

def shot(frame,score=1.):return Snapshot(frame,frame/25,frame,(1,2,100,200),score,.8)
class CaptureContract(unittest.TestCase):
    def test_box_clip_preserves_source_pixel_bounds(self):
        self.assertEqual(clipped_box((-2.1,3.4,30.2,40.9),20,30),(0,3,20,30))
        self.assertIsNone(clipped_box((5,5,4,8),20,30));self.assertIsNone(clipped_box((float('nan'),0,1,2),20,30))
    def test_quality_selection_is_causal(self):
        bank=SnapshotBank();bank.consider(1,shot(1,2),lambda:b'a');bank.consider(1,shot(2,5),lambda:b'b')
        candidates=bank.take(1,2/25);self.assertEqual([s.frame for s,_ in candidates],[2,1])
    def test_old_frames_expire_even_when_track_stays(self):
        bank=SnapshotBank();bank.consider(1,shot(0,100),lambda:b'a');bank.consider(1,shot(75,1),lambda:b'b')
        self.assertEqual([s.frame for s,_ in bank.take(1,3.)],[75])
    def test_native_frame_shared_between_animals(self):
        bank=SnapshotBank();bank.consider(1,shot(0),lambda:b'12345');bank.consider(2,shot(0),lambda:self.fail('Same frame encoded twice'))
        self.assertEqual(bank.bytes,5);self.assertEqual(len(bank.take(1,0)),1);self.assertEqual(bank.bytes,5)
    def test_byte_cap_evicts_instead_of_growing(self):
        bank=SnapshotBank(max_bytes=8);bank.consider(1,shot(0,1),lambda:b'12345');bank.consider(2,shot(1,2),lambda:b'12345')
        self.assertLessEqual(bank.bytes,8);self.assertEqual(bank.evictions,1);self.assertEqual(bank.take(1,1/25),[])
    def test_huge_snapshot_becomes_explicit_empty(self):
        bank=SnapshotBank(max_bytes=2);bank.consider(1,shot(0),lambda:b'large')
        self.assertEqual(bank.take(1,0),[]);self.assertEqual(bank.bytes,0)
    def test_return_event_does_not_reuse_old_capture(self):
        bank=SnapshotBank();bank.consider(1,shot(1),lambda:b'a');self.assertEqual(len(bank.take(1,1/25)),1)
        self.assertEqual(bank.take(1,2/25),[]);bank.consider(1,shot(3),lambda:b'b');self.assertEqual(bank.take(1,3/25)[0][0].frame,3)
    def test_equal_sharpness_prefers_earlier_frame(self):
        bank=SnapshotBank(per_track=1);bank.consider(1,shot(1),lambda:b'a')
        self.assertFalse(bank.consider(1,shot(2),lambda:b'b'));self.assertEqual(bank.take(1,2/25)[0][0].frame,1)

if __name__=='__main__':unittest.main(verbosity=2)
