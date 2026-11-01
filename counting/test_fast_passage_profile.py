"""Two-observation profile: real fast-passage regression and adverse event cases."""
import json
import unittest
from pathlib import Path

from .counter import PassageCounter


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "maintenance/offline_counting/selected_counter_profile_v2.json"


class FastPassageProfileTests(unittest.TestCase):
    def play(self, positions, times=None):
        config = json.loads(PROFILE.read_text())["counter"]
        counter = PassageCounter("two-observation-fixture", **config)
        events = []
        for i, point in enumerate(positions):
            current = point if isinstance(point, dict) else {1: point}
            stamp = times[i] if times is not None else i * .2
            emitted, _ = counter.update(stamp, i, current, {}, set(current), {1, 2})
            events.extend(emitted)
        return counter, events

    def test_user_confirmed_actual_fast_passage_is_counted_once(self):
        trace = json.loads((ROOT / "maintenance/offline_counting/results/r5_aug15_fast_passage_trace.json").read_text())
        counter, events = self.play([row["center_y_fraction"] for row in trace["rows"]],
                                    [row["time_s"] for row in trace["rows"]])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["direction"], "A->B")
        self.assertEqual(counter.summary()["IN"], 1)

    def test_single_destination_spike_does_not_count(self):
        _, events = self.play([.2, .2, .5, .8, .5, .2, .2])
        self.assertEqual(events, [])

    def test_unstable_origin_does_not_count(self):
        _, events = self.play([.2, .5, .8, .8])
        self.assertEqual(events, [])

    def test_starting_in_middle_does_not_count(self):
        _, events = self.play([.5, .5, .8, .8])
        self.assertEqual(events, [])

    def test_missing_observation_breaks_destination_confirmation(self):
        _, events = self.play([.2, .2, .8, {}, .8, {}])
        self.assertEqual(events, [])

    def test_long_gap_does_not_join_disconnected_fragments(self):
        _, events = self.play([.2, .2, .8, .8], [0., .2, 4., 4.2])
        self.assertEqual(events, [])

    def test_true_return_counts_both_directions_once(self):
        counter, events = self.play([.2, .2, .5, .8, .8, .5, .2, .2])
        self.assertEqual([event["direction"] for event in events], ["A->B", "B->A"])
        self.assertEqual(counter.summary()["NET"], 0)

    def test_simultaneous_opposite_passages_stay_separate(self):
        _, events = self.play([{1: .2, 2: .8}] * 2 + [{1: .5, 2: .5}] + [{1: .8, 2: .2}] * 2)
        self.assertCountEqual([event["direction"] for event in events], ["A->B", "B->A"])

    def test_incomplete_video_end_does_not_force_a_count(self):
        counter, events = self.play([.2, .2, .5])
        self.assertEqual(events, [])
        records = counter.finish()
        self.assertTrue(records)
        self.assertTrue(all(not record["counts_as_complete_passage"] for record in records))


if __name__ == "__main__":
    unittest.main()
