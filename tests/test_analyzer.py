import unittest

from app.analyzer import Segment, _merge_segments, _non_silent_segments


class AnalyzerTests(unittest.TestCase):
    def test_non_silent_segments(self):
        result = _non_silent_segments(
            100.0,
            [Segment(0.0, 5.0), Segment(30.0, 40.0), Segment(90.0, 100.0)],
        )
        self.assertEqual(result, [Segment(5.0, 30.0), Segment(40.0, 90.0)])

    def test_merge_short_gap(self):
        result = _merge_segments(
            [Segment(10.0, 20.0), Segment(25.0, 40.0), Segment(60.0, 80.0)],
            10.0,
        )
        self.assertEqual(result, [Segment(10.0, 40.0), Segment(60.0, 80.0)])


if __name__ == "__main__":
    unittest.main()
