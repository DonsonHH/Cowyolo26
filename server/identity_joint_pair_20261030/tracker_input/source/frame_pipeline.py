"""NumPy equivalent of the exact cached Results/Boxes to counter path."""
import numpy as np
from types import SimpleNamespace
from cow_tracker.byte_tracker import BYTETracker
from cow_tracker.zone_counter import ZoneCounter
from cow_tracker.confirmation_counter import ConfirmationHandoffCounter
from cow_tracker.support import xyxy2xywh

class Boxes:
    def __init__(self,data):
        self.data=np.asarray(data,dtype=np.float32)
        if self.data.ndim==1:self.data=self.data[None,:]
        assert self.data.ndim==2 and self.data.shape[1] in [6,7]
    def __len__(self):return len(self.data)
    def __getitem__(self,key):return Boxes(self.data[key])
    @property
    def xyxy(self):return self.data[:,:4]
    @property
    def xywh(self):return xyxy2xywh(self.xyxy)
    @property
    def conf(self):return self.data[:,-2]
    @property
    def cls(self):return self.data[:,-1]
    @property
    def id(self):return self.data[:,4] if self.data.shape[1]==7 else None

class FramePipeline:
    def __init__(self,spec,config,counter_kwargs):
        self.spec=spec
        self.tracker=BYTETracker(SimpleNamespace(**config))
        self.base=ZoneCounter(**counter_kwargs)
        self.handoff=ConfirmationHandoffCounter(**counter_kwargs)
        self.image=None  # The frozen AABB ByteTrack has no image-dependent code path.
    def update(self,frame,predictions):
        spec=self.spec;W,H=spec['width'],spec['height'];time_s=frame/spec['fps']
        raw=np.asarray([[*r['xyxy'],r['confidence'],r['class']] for r in predictions],np.float32).reshape(-1,6)
        boxes=Boxes(raw)
        out=self.tracker.update(boxes,self.image,feats=None)
        if len(out):
            # Results.update clips its tracked coordinates to the original shape.
            values=out[:,:-1].copy()
            values[:,[0,2]]=values[:,[0,2]].clip(0,W)
            values[:,[1,3]]=values[:,[1,3]].clip(0,H)
            boxes=Boxes(values)
        ids=boxes.id.astype(np.int32).tolist() if boxes.id is not None else [None]*len(boxes)
        active={tid for tid in ids if tid is not None};positions={};tentative={};post=[]
        low,high=spec['perpendicular_ROI']
        for box,confidence,tid in zip(boxes.xyxy.tolist(),boxes.conf.tolist(),ids):
            x1,y1,x2,y2=box;cx=(x1+x2)/(2*W);cy=(y1+y2)/(2*H)
            post.append({'frame0':frame,'time_s':time_s,'track_id':tid,'confidence':confidence,'xyxy':box})
            cross=cx if spec['axis']=='y' else cy;axis=cy if spec['axis']=='y' else cx
            if tid is not None and low<cross<high:positions[tid]=axis
        for t in self.tracker.tracked_stracks:
            if t.is_activated:continue
            x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float);cx=(x1+x2)/(2*W);cy=(y1+y2)/(2*H)
            if low<(cx if spec['axis']=='y' else cy)<high:tentative[int(t.track_id)]=cy if spec['axis']=='y' else cx
        baseevents=self.base.update(time_s,positions)
        events=self.handoff.update(time_s,positions,tentative,active)
        for row in baseevents+events:row['frame0']=frame
        observation={'frame0':frame,'time_s':time_s,'confirmed_positions':positions,'confirmed_IDs':sorted(active),
                     'tentative_positions':tentative,'accepted_history':self.handoff.last_acceptances}
        return {'observation':observation,'post_tracker':post,'confirmed_only_events':baseevents,'handoff_events':events}
