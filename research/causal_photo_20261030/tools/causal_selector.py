"""Bounded past-only selection; no pixels, gallery, identities, or future input."""
from collections import deque

ROI = (870.0, 0.0, 1920.0, 1440.0)
MAX_AGE_FRAMES = 25
MAX_FRAMES = 6
EDGE_GUARD_PX = 16.0


def clipped(box):
    x, y, z, w = box
    a, b, c, d = ROI
    return [max(a, min(c, x)), max(b, min(d, y)),
            max(a, min(c, z)), max(b, min(d, w))]


def area(box):
    return max(0., box[2] - box[0]) * max(0., box[3] - box[1])


def candidate(frame, row, others):
    box = clipped(row['xyxy']); size = area(box)
    overlap = 0.
    for other in others:
        if other['track_id'] == row['track_id']:
            continue
        b = clipped(other['xyxy'])
        intersection = area([max(box[0], b[0]), max(box[1], b[1]),
                             min(box[2], b[2]), min(box[3], b[3])])
        overlap = max(overlap, intersection / size if size else 0.)
    margin = min(box[0] - ROI[0], box[1] - ROI[1],
                 ROI[2] - box[2], ROI[3] - box[3])
    score = size * (1. - overlap) * min(1., max(0., margin) / EDGE_GUARD_PX)
    return {'frame0': frame, 'track_id': int(row['track_id']),
            'xyxy': list(row['xyxy']), 'clipped_xyxy': box,
            'visible_box_area_px2': size, 'minimum_edge_margin_px': margin,
            'max_other_box_overlap_fraction': overlap, 'selection_score': score}


class CausalSelector:
    def __init__(self):
        self.frames = deque()
        self.last_frame = None

    def observe(self, frame, rows):
        if self.last_frame is not None:
            assert frame > self.last_frame, 'Frame availability must be strictly increasing'
        self.last_frame = frame
        rows = [dict(r, xyxy=list(r['xyxy'])) for r in rows if r['track_id'] is not None]
        assert len({r['track_id'] for r in rows}) == len(rows)
        candidates = [candidate(frame, r, rows) for r in rows]
        self.frames.append((frame, candidates))
        while self.frames and (frame - self.frames[0][0] > MAX_AGE_FRAMES or len(self.frames) > MAX_FRAMES):
            self.frames.popleft()

    def choose(self, frame, track_id):
        assert frame == self.last_frame
        choices = [dict(r) for f, rows in self.frames for r in rows
                   if r['track_id'] == track_id and frame - MAX_AGE_FRAMES <= f <= frame]
        current = next(r for r in choices if r['frame0'] == frame)
        selected = max(choices, key=lambda r: (r['selection_score'], r['frame0']))
        return {'event_frame0': frame, 'track_id': track_id,
                'selected': selected, 'current': current, 'candidates': choices,
                'selected_age_frames': frame - selected['frame0'],
                'maximum_buffered_frames': MAX_FRAMES}
