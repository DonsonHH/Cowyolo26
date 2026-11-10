"""Software fixtures for perspective channel boundaries; no real-accuracy claim."""
import unittest
import numpy as np

from .protocol import gate_from_config
from .tracking import TrackingSession


POLYGON = [[.2, 0.], [.4, 0.], [.8, 1.], [.2, 1.]]


def config():
    return {"axis": "y", "perpendicular_roi": [0, 1], "channel_polygon": POLYGON,
            "track_only_in_channel": True, "counter": {"stable_samples": 2},
            "tracker": {"track_high_thresh": .2, "new_track_thresh": .25, "fuse_score": False}}


def detection(x, y):
    return [x - 5, y - 10, x + 5, y + 10, .9, 0]


class PolygonAdmissionTests(unittest.TestCase):
    def test_off_channel_box_inside_old_sideband_is_excluded_before_association(self):
        session = TrackingSession(config(), 100, 100, 5, "software-polygon")
        for frame in range(3):
            tracks, events, _ = session.update(frame, frame * .2, [detection(65, 20)])
            self.assertEqual(tracks, [])
            self.assertEqual(events, [])
        self.assertEqual(session.tracker.tracked_stracks, [])

    def test_reference_gate_retains_the_physical_polygon(self):
        self.assertIn("channel_polygon", gate_from_config(config()))

    def test_wider_end_is_admitted_without_admitting_the_narrow_end(self):
        for y, expected in ((20, False), (80, True)):
            session = TrackingSession(config(), 100, 100, 5, "software-perspective")
            for frame in range(3):
                tracks, _, _ = session.update(frame, frame * .2, [detection(65, y)])
            self.assertEqual(bool(tracks), expected)

    def test_true_passage_uses_observed_positions_inside_polygon(self):
        session = TrackingSession(config(), 100, 100, 5, "software-passage")
        events = []
        for frame, y in enumerate((20, 20, 30, 40, 50, 60, 70, 70)):
            _, emitted, _ = session.update(frame, frame * .2, [[25, y - 20, 45, y + 20, .9, 0]])
            events.extend(emitted)
        self.assertEqual([event["kind"] for event in events], ["IN"])

    def test_legacy_gate_has_no_new_null_field(self):
        self.assertEqual(gate_from_config({}), {"axis": "y", "perpendicular_roi": [0., 1.], "lower": .4, "upper": .6})

    def test_inverse_crop_and_rotation_are_applied_before_polygon_membership(self):
        from .geometry import Transform
        from .backends import decode
        transform = Transform.create(100, 100, [10, 0, 90, 100], 90, 192)
        boxes = np.asarray([[60, 10, 70, 30], [60, 70, 70, 90]], dtype=float)
        raw = np.column_stack((transform.boxes(boxes), [.9, .9], [0, 0]))[None]
        values = decode(raw, transform, .2, [0])
        session = TrackingSession(config(), 100, 100, 5, "software-source-coordinates")
        for frame in range(3):
            tracks, _, _ = session.update(frame, frame * .2, values)
        self.assertEqual(len(tracks), 1)
        np.testing.assert_allclose(tracks[0]["xyxy"], boxes[1], atol=.002)

    def test_rendered_gate_stops_at_the_physical_boundary(self):
        from .render import draw_channel
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        draw_channel(image, config())
        self.assertTrue(image[40, 40].any())
        self.assertFalse(image[40, 90].any())


class PolygonGeometryTests(unittest.TestCase):
    def polygon(self, values=POLYGON):
        from .channel import ChannelPolygon
        return ChannelPolygon(values)

    def test_boundary_is_strictly_excluded(self):
        polygon = self.polygon()
        for point in ((.2, .5), (.6, .5), (.2, 0.)):
            self.assertFalse(polygon.contains(*point))
        self.assertTrue(polygon.contains(.6 - 1e-8, .5))

    def test_canonical_order_is_invariant_to_rotation_and_reversal(self):
        values = POLYGON[2:] + POLYGON[:2]
        self.assertEqual(self.polygon().as_list(), self.polygon(values[::-1]).as_list())

    def test_invalid_polygons_are_rejected(self):
        invalid = [[], [[0, 0], [1, 1]], [[0, 0], [1, 0], [1, 0]],
                   [[0, 0], [.5, .5], [1, 1]], [[0, 0], [1, 1], [0, 1], [1, 0]],
                   [[0, 0], [1.1, 0], [1, 1]], [[False, 0], [1, 0], [1, 1]],
                   [[0, 0], [float("nan"), 0], [1, 1]]]
        for values in invalid:
            with self.assertRaises(ValueError, msg=str(values)):
                self.polygon(values)

    def test_concave_gate_segments_do_not_cross_an_excluded_notch(self):
        polygon = self.polygon([[.1, .1], [.9, .1], [.9, .9], [.6, .9], [.6, .4], [.4, .4], [.4, .9], [.1, .9]])
        self.assertFalse(polygon.contains(.5, .6))
        self.assertTrue(polygon.contains(.2, .6))
        np.testing.assert_allclose(polygon.gate_segments("y", .6), [((.1, .6), (.4, .6)), ((.6, .6), (.9, .6))])
        np.testing.assert_allclose(polygon.gate_segments("x", .5), [((.5, .1), (.5, .4))])

    def test_polygon_is_the_full_region_and_cannot_hide_a_second_sideband(self):
        values = config()
        values["perpendicular_roi"] = [.3, .7]
        with self.assertRaisesRegex(ValueError, "perpendicular_roi"):
            gate_from_config(values)

    def test_different_shapes_produce_different_reference_gates(self):
        other = config()
        other["channel_polygon"] = [[.1, 0], [.9, 0], [.9, 1], [.1, 1]]
        self.assertNotEqual(gate_from_config(config()), gate_from_config(other))

    def test_collinear_boundary_is_not_an_interior_gate(self):
        polygon = self.polygon([[.2, .2], [.8, .2], [.8, .8], [.2, .8]])
        self.assertEqual(polygon.gate_segments("y", .2), [])
        self.assertEqual(polygon.gate_segments("x", .2), [])
        for axis in ("x", "y"):
            values = config()
            values["axis"] = axis
            values["channel_polygon"] = polygon.as_list()
            values["counter"] = {"lower": .2, "upper": .6}
            with self.assertRaisesRegex(ValueError, "Both counting gates"):
                gate_from_config(values)

    def test_collinear_notch_does_not_hide_real_side_intervals(self):
        polygon = self.polygon([[.1, .1], [.4, .1], [.4, .6], [.6, .6], [.6, .1], [.9, .1], [.9, .9], [.1, .9]])
        self.assertFalse(polygon.contains(.5, .6))
        np.testing.assert_allclose(polygon.gate_segments("y", .6), [((.1, .6), (.4, .6)), ((.6, .6), (.9, .6))])


if __name__ == "__main__":
    unittest.main(verbosity=2)
