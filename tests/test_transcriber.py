import unittest

from app.transcriber import merge_transcript_segments


class TranscriptMergeTests(unittest.TestCase):
    def test_merge_and_padding(self):
        segments = [
            {"start_seconds": 10.0, "end_seconds": 25.0, "text": "Guten Tag."},
            {"start_seconds": 30.0, "end_seconds": 45.0, "text": "Willkommen."},
            {"start_seconds": 80.0, "end_seconds": 90.0, "text": "Kurz."},
        ]
        result = merge_transcript_segments(
            segments,
            merge_gap=10.0,
            min_duration=20.0,
            padding=2.0,
            total_duration=100.0,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start_seconds"], 8.0)
        self.assertEqual(result[0]["end_seconds"], 47.0)
        self.assertIn("Willkommen", result[0]["text"])


if __name__ == "__main__":
    unittest.main()
