"""Recorded crop, clockwise rotation and letterbox transforms."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Transform:
    source_width: int
    source_height: int
    roi: tuple
    rotation: int
    size: int
    resized_width: int
    resized_height: int
    pad_left: int
    pad_top: int

    @classmethod
    def create(cls, width, height, roi, rotation, size):
        if rotation not in (0, 90, 180, 270) or size <= 0:
            raise ValueError("Rotation must be 0/90/180/270 clockwise; positive input size required")
        x1, y1, x2, y2 = map(int, roi or (0, 0, width, height))
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("Detection ROI must be inside original video")
        w, h = x2 - x1, y2 - y1
        if rotation in (90, 270):
            w, h = h, w
        gain = min(size / w, size / h)
        nw, nh = max(1, round(w * gain)), max(1, round(h * gain))
        return cls(width, height, (x1, y1, x2, y2), rotation, size,
                   nw, nh, (size - nw) // 2, (size - nh) // 2)

    @property
    def oriented_shape(self):
        x1, y1, x2, y2 = self.roi
        w, h = x2 - x1, y2 - y1
        return (w, h) if self.rotation in (90, 270) else (h, w)

    def _points(self, points, inverse=False):
        points = np.asarray(points, np.float64).reshape(-1, 2).copy()
        x1, y1, x2, y2 = self.roi
        w, h = x2 - x1, y2 - y1
        oh, ow = self.oriented_shape
        if inverse:
            points[:, 0] = (points[:, 0] - self.pad_left) * ow / self.resized_width
            points[:, 1] = (points[:, 1] - self.pad_top) * oh / self.resized_height
            x, y = points.T.copy()
            if self.rotation == 90:
                points = np.column_stack((y, h - x))
            elif self.rotation == 180:
                points = np.column_stack((w - x, h - y))
            elif self.rotation == 270:
                points = np.column_stack((w - y, x))
            points += (x1, y1)
        else:
            points -= (x1, y1)
            x, y = points.T.copy()
            if self.rotation == 90:
                points = np.column_stack((h - y, x))
            elif self.rotation == 180:
                points = np.column_stack((w - x, h - y))
            elif self.rotation == 270:
                points = np.column_stack((y, w - x))
            points[:, 0] = points[:, 0] * self.resized_width / ow + self.pad_left
            points[:, 1] = points[:, 1] * self.resized_height / oh + self.pad_top
        return points

    def boxes(self, values, inverse=False):
        values = np.asarray(values, np.float64).reshape(-1, 4)
        if not len(values):
            return values.copy()
        corners = values[:, [0, 1, 2, 1, 2, 3, 0, 3]].reshape(-1, 2)
        points = self._points(corners, inverse).reshape(-1, 4, 2)
        result = np.concatenate((points.min(1), points.max(1)), axis=1)
        if inverse:
            result[:, [0, 2]] = result[:, [0, 2]].clip(0, self.source_width)
            result[:, [1, 3]] = result[:, [1, 3]].clip(0, self.source_height)
        return result

    def preprocess(self, image):
        import cv2
        if image.shape[:2] != (self.source_height, self.source_width):
            raise ValueError("Source dimensions changed; start a new session")
        x1, y1, x2, y2 = self.roi
        crop = image[y1:y2, x1:x2]
        if self.rotation:
            crop = np.rot90(crop, -(self.rotation // 90))
        resized = cv2.resize(crop, (self.resized_width, self.resized_height), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)
        canvas[self.pad_top:self.pad_top + self.resized_height,
               self.pad_left:self.pad_left + self.resized_width] = resized
        return np.ascontiguousarray(canvas[..., ::-1].transpose(2, 0, 1)[None], np.float32) / np.float32(255)
