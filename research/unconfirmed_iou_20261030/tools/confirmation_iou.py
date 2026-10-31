"""Experiment-only stage-specific cost; original tracker source is untouched."""
from cow_tracker.byte_tracker import BYTETracker

class UnconfirmedIoUTracker(BYTETracker):
    def _unconfirmed_association(self,unconfirmed,u_detection,detections,activated,removed):
        original=self.args.fuse_score
        try:
            self.args.fuse_score=False
            return super()._unconfirmed_association(unconfirmed,u_detection,detections,activated,removed)
        finally:
            self.args.fuse_score=original
