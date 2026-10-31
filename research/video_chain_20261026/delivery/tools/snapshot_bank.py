"""Causal, time-bounded snapshot candidates sharing encoded native frames."""
from dataclasses import dataclass
import math

def clipped_box(box,width,height):
    if len(box)!=4 or not all(math.isfinite(v) for v in box):return None
    x1=max(0,min(width,math.floor(box[0])));y1=max(0,min(height,math.floor(box[1])))
    x2=max(0,min(width,math.ceil(box[2])));y2=max(0,min(height,math.ceil(box[3])))
    return (x1,y1,x2,y2) if x2>x1 and y2>y1 else None

@dataclass(frozen=True)
class Snapshot:
    frame: int
    source_time: float
    decoded_wall_ns: int
    box: tuple
    quality: float
    confidence: float
    quality_png: bytes=b''

class SnapshotBank:
    def __init__(self,per_track=3,recent_seconds=2.,max_bytes=33554432,max_tracks=32):
        if min(per_track,recent_seconds,max_bytes,max_tracks)<=0:raise ValueError('Invalid snapshot limits')
        self.k=per_track;self.recent=recent_seconds;self.max_bytes=max_bytes;self.max_tracks=max_tracks
        self.tracks={};self.encoded={};self.peak_bytes=0;self.evictions=0;self.last_time=None
    def _reclaim(self):
        used={s.frame for snapshots in self.tracks.values() for s in snapshots}
        self.encoded={frame:data for frame,data in self.encoded.items() if frame in used}
    @property
    def bytes(self):return sum(len(data) for data in self.encoded.values())+sum(len(s.quality_png) for values in self.tracks.values() for s in values)
    def advance(self,source_time):
        if self.last_time is not None and source_time<self.last_time:raise ValueError('Source time went backwards')
        self.last_time=source_time
        self.tracks={tid:[s for s in values if source_time-s.source_time<=self.recent] for tid,values in self.tracks.items()}
        self.tracks={tid:values for tid,values in self.tracks.items() if values};self._reclaim()
    def consider(self,track_id,snapshot,encoded_supplier):
        self.advance(snapshot.source_time)
        if not math.isfinite(snapshot.quality) or snapshot.quality<0:raise ValueError('Invalid sharpness')
        existing=self.tracks.get(track_id,[])
        if any(s.frame==snapshot.frame for s in existing):return False
        proposed=sorted(existing+[snapshot],key=lambda s:(-s.quality,s.frame))[:self.k]
        if snapshot not in proposed:return False
        if snapshot.frame not in self.encoded:self.encoded[snapshot.frame]=bytes(encoded_supplier())
        self.tracks[track_id]=proposed;self._reclaim()
        while len(self.tracks)>self.max_tracks or self.bytes>self.max_bytes:
            tid,index=min(((tid,i) for tid,values in self.tracks.items() for i,s in enumerate(values)),key=lambda key:(self.tracks[key[0]][key[1]].quality,self.tracks[key[0]][key[1]].frame,key[0]))
            self.tracks[tid].pop(index);self.evictions+=1
            if not self.tracks[tid]:del self.tracks[tid]
            self._reclaim()
        assert self.bytes<=self.max_bytes
        self.peak_bytes=max(self.peak_bytes,self.bytes)
        return any(s.frame==snapshot.frame for s in self.tracks.get(track_id,[]))
    def take(self,track_id,event_source_time):
        self.advance(event_source_time)
        candidates=self.tracks.pop(track_id,[])
        result=[(s,self.encoded[s.frame]) for s in candidates]
        assert all(s.source_time<=event_source_time for s,_ in result)
        self._reclaim();return result
