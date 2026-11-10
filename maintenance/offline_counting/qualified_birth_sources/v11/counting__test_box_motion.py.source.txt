"""Regression for entrance truncation changing apparent box aspect ratio."""
import unittest
import numpy as np
from .tracking import TrackingSession


class BoxMotionTests(unittest.TestCase):
    def test_measured_fast_entrance_keeps_one_identity_with_observed_velocity(self):
        # Actual S256 board detections, Aug15 realtime regression. These rows
        # test identity continuity only: they do not contain a full passage.
        data = [
            (19.0, [827.18,0.,936.44,67.21,.45,0]),
            (19.4, [834.87,0.,934.90,178.49,.25,0]),
            (19.8, [836.41,4.59,941.05,226.58,.79,0]),
            (20.2, [814.87,91.51,950.29,336.62,.70,0]),
            (20.6, [777.64,242.22,937.68,552.07,.90,0]),
        ]
        config = {'tracker': {'motion_box':'observed_velocity','track_high_thresh':.2,'track_low_thresh':.1,
                              'new_track_thresh':.25,'match_thresh':.8,'fuse_score':False},
                  'counter': {'stable_samples':2}}
        session = TrackingSession(config,1280,720,3,'actual-fast-entrance')
        observed=[]
        for index,(stamp,box) in enumerate(data):
            tracks,events,_=session.update(index,stamp,np.asarray([box],np.float32))
            self.assertEqual(events,[])
            if index:
                self.assertEqual(len(tracks),1)
                observed.append(tracks[0]['track_id'])
                self.assertLess(tracks[0]['xyxy'][2]-tracks[0]['xyxy'][0],200)
        self.assertEqual(len(set(observed)),1)

    def test_invalid_motion_representation_is_rejected(self):
        with self.assertRaises(ValueError):
            TrackingSession({'tracker':{'motion_box':'invalid'}},100,100,3,'invalid')

    def test_predicted_crossing_without_image_detection_never_counts(self):
        session = TrackingSession({'tracker':{'motion_box':'observed_velocity'},'counter':{'stable_samples':2}},100,100,5,'blank')
        for i,y in enumerate([15,25,35]):
            session.update(i,i*.2,np.array([[30,y-25,60,y+25,.9,0]],np.float32))
        for i in range(3,9):
            tracks,events,_=session.update(i,i*.2,np.empty((0,6),np.float32))
            self.assertEqual((tracks,events),([],[]))
        self.assertEqual(session.counter.summary()['IN'],0)

    def test_simultaneous_opposite_measured_tracks_and_bounded_history(self):
        session = TrackingSession({'tracker':{'motion_box':'observed_velocity','fuse_score':False},'counter':{'stable_samples':2}},1000,720,5,'two')
        events=[]
        for i,y in enumerate([.15,.25,.42,.6,.75,.85]):
            boxes=np.array([[100,y*720-160,220,y*720+160,.9,0],
                            [700,(1-y)*720-160,820,(1-y)*720+160,.9,0]],np.float32)
            tracks,new,_=session.update(i,i*.2,boxes);events.extend(new)
            for track in session.tracker.tracked_stracks:
                self.assertLessEqual(len(track.observations),2)
        self.assertCountEqual([e['direction'] for e in events],['A->B','B->A'])


if __name__=='__main__':
    unittest.main()
