"""Actual-codec bounded history selection and causal measured-speed checks."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from .realtime import LatestCapture, fast_history_needed
from .test_realtime import video
from .tracking import TrackingSession


class CaptureHistoryTests(unittest.TestCase):
    def test_waiting_for_future_sequence_does_not_return_an_older_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'SOFTWARE_FIXTURE.avi'
            video(source,[.5]*5,100)
            capture=LatestCapture(source)
            try:
                capture.start()
                packet=capture.take_after(3)
                self.assertIsNotNone(packet)
                self.assertGreater(packet[0],3)
            finally:capture.close()

    def test_two_latest_arrived_frames_can_be_consumed_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'SOFTWARE_FIXTURE.avi'
            video(source,[.5]*5,100)
            capture=LatestCapture(source,capture_options={'buffer_frames':2})
            try:
                capture.start();capture.thread.join(2)
                self.assertFalse(capture.thread.is_alive())
                first=capture.take_after(-1,prefer_history=True)
                second=capture.take_after(first[0],prefer_history=True)
                self.assertEqual((first[0],second[0]),(3,4))
                self.assertIsNone(capture.take_after(second[0],prefer_history=True))
                self.assertEqual(capture.snapshot()['maximum_application_queue_frames'],2)
                self.assertEqual(capture.snapshot()['history_frames_processed'],1)
                self.assertEqual(capture.snapshot()['overwritten_before_read'],3)
            finally:capture.close()

    def test_normal_selection_keeps_latest_and_discards_extra_history(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'SOFTWARE_FIXTURE.avi'
            video(source,[.5]*5,100)
            capture=LatestCapture(source,capture_options={'buffer_frames':2})
            try:
                capture.start();capture.thread.join(2)
                self.assertEqual(capture.take_after(-1)[0],4)
                self.assertIsNone(capture.take_after(4))
                self.assertEqual(capture.snapshot()['overwritten_before_read'],4)
            finally:capture.close()

    def test_only_two_current_real_observations_can_request_fast_history(self):
        session=TrackingSession({'tracker':{'motion_box':'observed_velocity'}},100,100,5,'fixture')
        self.assertFalse(fast_history_needed(session,'y',.35))
        for i,y in enumerate([20,30]):
            session.update(i,i*.2,np.array([[30,y-20,60,y+20,.9,0]],np.float32))
        self.assertTrue(fast_history_needed(session,'y',.35))
        self.assertFalse(fast_history_needed(session,'y',1.0))
        session.update(2,.4,np.empty((0,6),np.float32))
        self.assertFalse(fast_history_needed(session,'y',.35))
